package workerpool

import (
	"context"
	"database/sql"
	"encoding/json"
	"log"
	"sync"
	"sync/atomic"
	"time"
)

// AuditEvent representa un evento asíncrono para registro y persistencia desacoplada
type AuditEvent struct {
	ServiceName string                 `json:"service_name"`
	EventType   string                 `json:"event_type"`
	Severity    string                 `json:"severity"` // INFO, WARN, ERROR, CRITICAL
	Payload     map[string]interface{} `json:"payload"`
	CreatedAt   time.Time              `json:"created_at"`
}

// PoolMetrics expone telemetría del worker pool para observabilidad
type PoolMetrics struct {
	Capacity        int    `json:"capacity"`
	CurrentQueueLen int    `json:"current_queue_len"`
	ProcessedEvents uint64 `json:"processed_events"`
	DroppedEvents   uint64 `json:"dropped_events"`
	ActiveWorkers   int    `json:"active_workers"`
}

// WorkerPool coordina un canal acotado con un grupo fijo de goroutines
type WorkerPool struct {
	db              *sql.DB
	queue           chan AuditEvent
	workerCount     int
	wg              sync.WaitGroup
	quit            chan struct{}
	processedEvents atomic.Uint64
	droppedEvents   atomic.Uint64
}

// NewWorkerPool inicializa el pool de workers asíncronos
func NewWorkerPool(db *sql.DB, capacity int, workerCount int) *WorkerPool {
	if capacity <= 0 {
		capacity = 1000
	}
	if workerCount <= 0 {
		workerCount = 4
	}

	p := &WorkerPool{
		db:          db,
		queue:       make(chan AuditEvent, capacity),
		workerCount: workerCount,
		quit:        make(chan struct{}),
	}

	for i := 0; i < workerCount; i++ {
		p.wg.Add(1)
		go p.worker(i)
	}

	return p
}

// Enqueue envía un evento de auditoría de forma no bloqueante (Non-blocking queue)
func (p *WorkerPool) Enqueue(event AuditEvent) bool {
	if event.CreatedAt.IsZero() {
		event.CreatedAt = time.Now()
	}
	if event.ServiceName == "" {
		event.ServiceName = "gateway-go"
	}
	if event.Severity == "" {
		event.Severity = "INFO"
	}

	select {
	case p.queue <- event:
		return true
	default:
		// Cola saturada: incrementa contador atómico de descarte para evitar starvation del caller
		p.droppedEvents.Add(1)
		log.Printf("[WARN] [WorkerPool] Cola de auditoría saturada. Evento descartado: %s", event.EventType)
		return false
	}
}

// worker procesa eventos de auditoría y los persiste en PostgreSQL
func (p *WorkerPool) worker(id int) {
	defer p.wg.Done()

	for {
		select {
		case <-p.quit:
			// Drenar canal remanente antes de salir
			for event := range p.queue {
				p.persistEvent(event)
			}
			return
		case event, ok := <-p.queue:
			if !ok {
				return
			}
			p.persistEvent(event)
		}
	}
}

func (p *WorkerPool) persistEvent(event AuditEvent) {
	p.processedEvents.Add(1)

	if p.db == nil {
		return
	}

	payloadJSON, err := json.Marshal(event.Payload)
	if err != nil {
		payloadJSON = []byte("{}")
	}

	query := `
		INSERT INTO audit_logs (service_name, event_type, severity, payload, created_at)
		VALUES ($1, $2, $3, $4, $5)
	`
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	if _, err := p.db.ExecContext(ctx, query, event.ServiceName, event.EventType, event.Severity, payloadJSON, event.CreatedAt); err != nil {
		log.Printf("[ERROR] [WorkerPool] Fallo al persistir audit_log: %v", err)
	}
}

// Metrics retorna las estadísticas del pool
func (p *WorkerPool) Metrics() PoolMetrics {
	return PoolMetrics{
		Capacity:        cap(p.queue),
		CurrentQueueLen: len(p.queue),
		ProcessedEvents: p.processedEvents.Load(),
		DroppedEvents:   p.droppedEvents.Load(),
		ActiveWorkers:   p.workerCount,
	}
}

// Stop drena y detiene de forma limpia los workers
func (p *WorkerPool) Stop(timeout time.Duration) {
	close(p.quit)
	close(p.queue)

	done := make(chan struct{})
	go func() {
		p.wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		log.Println("[INFO] [WorkerPool] Workers detenidos limpiamente y cola drenada.")
	case <-time.After(timeout):
		log.Println("[WARN] [WorkerPool] Timeout agotado al detener workers.")
	}
}
