package workers

import (
	"database/sql"
	"encoding/json"
	"log"
	"sync"
	"time"
)

type AuditEvent struct {
	ServiceName string                 `json:"service_name"`
	EventType   string                 `json:"event_type"`
	Severity    string                 `json:"severity"`
	Payload     map[string]interface{} `json:"payload"`
	CreatedAt   time.Time              `json:"created_at"`
}

type AuditWorkerPool struct {
	db          *sql.DB
	queue       chan AuditEvent
	workerCount int
	wg          sync.WaitGroup
	stopChan    chan struct{}
}

func NewAuditWorkerPool(db *sql.DB, workerCount int, queueSize int) *AuditWorkerPool {
	return &AuditWorkerPool{
		db:          db,
		queue:       make(chan AuditEvent, queueSize),
		workerCount: workerCount,
		stopChan:    make(chan struct{}),
	}
}

func (p *AuditWorkerPool) Start() {
	for i := 1; i <= p.workerCount; i++ {
		p.wg.Add(1)
		go p.worker(i)
	}
	log.Printf("[GOROUTINES] Worker Pool de Auditoría iniciado con %d workers concurrentes", p.workerCount)
}

func (p *AuditWorkerPool) Enqueue(event AuditEvent) {
	select {
	case p.queue <- event:
	default:
		log.Printf("[WARN] Cola de auditoría llena, descartando evento: %s", event.EventType)
	}
}

func (p *AuditWorkerPool) worker(id int) {
	defer p.wg.Done()
	for {
		select {
		case event := <-p.queue:
			p.saveEvent(event)
		case <-p.stopChan:
			// Procesar remanentes antes de apagar
			for len(p.queue) > 0 {
				event := <-p.queue
				p.saveEvent(event)
			}
			return
		}
	}
}

func (p *AuditWorkerPool) saveEvent(event AuditEvent) {
	payloadBytes, _ := json.Marshal(event.Payload)
	query := `INSERT INTO audit_logs (service_name, event_type, severity, payload, created_at)
	          VALUES ($1, $2, $3, $4, $5)`
	_, err := p.db.Exec(query, event.ServiceName, event.EventType, event.Severity, payloadBytes, time.Now())
	if err != nil {
		log.Printf("[AUDIT ERROR] Error guardando log asíncrono: %v", err)
	}
}

func (p *AuditWorkerPool) Stop() {
	close(p.stopChan)
	p.wg.Wait()
	log.Println("[GOROUTINES] Worker Pool de Auditoría apagado limpiamente.")
}
