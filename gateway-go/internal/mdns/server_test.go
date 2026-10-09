package mdns

import (
	"testing"
	"time"
)

func TestMDNSServer_Lifecycle(t *testing.T) {
	// Probar que el servidor mDNS inicia y se apaga limpiamente
	srv, err := Start("Test-EcoStream-Instance", 8089, 50059)
	if err != nil {
		t.Fatalf("error al iniciar servidor mDNS: %v", err)
	}
	if srv == nil {
		t.Fatalf("esperado servidor mDNS no nulo")
	}

	time.Sleep(100 * time.Millisecond)

	// Comprobar shutdown sin pánico
	srv.Shutdown()
}

func TestGetLocalIP(t *testing.T) {
	ip := GetLocalIP()
	if ip == "" {
		t.Errorf("esperada una IP no vacía")
	}
}
