package config

import (
	"os"
	"testing"
)

func TestLoadConfig_Defaults(t *testing.T) {
	cfg := LoadConfig()
	if cfg.HTTPPort == "" {
		t.Errorf("HTTPPort no debería estar vacío")
	}
	if cfg.GRPCPort != "50051" {
		t.Errorf("esperado GRPCPort 50051, obtenido %s", cfg.GRPCPort)
	}
	if cfg.SimulationPort != 50052 {
		t.Errorf("esperado SimulationPort 50052, obtenido %d", cfg.SimulationPort)
	}
	if !cfg.EnableMDNS {
		t.Errorf("esperado EnableMDNS true por defecto")
	}
}

func TestLoadConfig_RenderPortEnv(t *testing.T) {
	os.Setenv("PORT", "10000")
	defer os.Unsetenv("PORT")

	cfg := LoadConfig()
	if cfg.HTTPPort != "10000" {
		t.Errorf("esperado que PORT sobreescriba HTTPPort con 10000, obtenido %s", cfg.HTTPPort)
	}
}

func TestLoadConfig_SimulationPublicEndpoint(t *testing.T) {
	os.Setenv("SIMULATION_PUBLIC_ENDPOINT", "engine.onrender.com:443")
	defer os.Unsetenv("SIMULATION_PUBLIC_ENDPOINT")

	cfg := LoadConfig()
	if cfg.SimulationPublicEndpoint != "engine.onrender.com:443" {
		t.Errorf("esperado engine.onrender.com:443, obtenido %s", cfg.SimulationPublicEndpoint)
	}
}
