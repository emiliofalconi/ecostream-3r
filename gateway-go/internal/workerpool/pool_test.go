package workerpool

import (
	"testing"
	"time"
)

func TestWorkerPoolNonBlockingDrop(t *testing.T) {
	// Pool con capacidad ultra reducida (2 items) y 0 workers activos para saturar
	pool := &WorkerPool{
		db:          nil,
		queue:       make(chan AuditEvent, 2),
		workerCount: 0,
		quit:        make(chan struct{}),
	}

	ev1 := AuditEvent{EventType: "EV_1"}
	ev2 := AuditEvent{EventType: "EV_2"}
	ev3 := AuditEvent{EventType: "EV_3"} // Debe ser descartado

	if !pool.Enqueue(ev1) {
		t.Fatal("ev1 debió ser aceptado")
	}
	if !pool.Enqueue(ev2) {
		t.Fatal("ev2 debió ser aceptado")
	}

	// Al intentar encolar ev3 cuando el canal está lleno, debe retornar false y no bloquearse
	start := time.Now()
	accepted := pool.Enqueue(ev3)
	elapsed := time.Since(start)

	if accepted {
		t.Fatal("ev3 debió haber sido descartado por canal lleno")
	}

	if elapsed > 100*time.Millisecond {
		t.Fatalf("Enqueue bloqueó el hilo durante %v", elapsed)
	}

	metrics := pool.Metrics()
	if metrics.DroppedEvents != 1 {
		t.Errorf("Se esperaba 1 evento descartado, obtenido %d", metrics.DroppedEvents)
	}
}
