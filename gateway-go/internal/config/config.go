package config

import (
	"os"
	"strconv"
)

type Config struct {
	HTTPPort          string
	GRPCPort          string
	DatabaseURL       string
	JWTSecret         string
	JWTExpirationHours int
	AllowedOrigins    string
	SimulationWorker  string
}

func LoadConfig() *Config {
	return &Config{
		HTTPPort:           getEnv("GATEWAY_HTTP_PORT", "8080"),
		GRPCPort:           getEnv("GATEWAY_GRPC_PORT", "50051"),
		DatabaseURL:        getEnv("DATABASE_URL", "postgres://ecostream_user:ecostream_secure_pass@postgres:5432/ecostream_db?sslmode=disable"),
		JWTSecret:          getEnv("JWT_SECRET", "super_secret_eco_jwt_key_ucab_2026_change_in_prod"),
		JWTExpirationHours: getEnvAsInt("JWT_EXPIRATION_HOURS", 24),
		AllowedOrigins:     getEnv("CORS_ALLOWED_ORIGINS", "*"),
		SimulationWorker:   getEnv("DEFAULT_SIMULATION_URL", "engine-rust:50052"),
	}
}

func getEnv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}

func getEnvAsInt(key string, fallback int) int {
	if val := os.Getenv(key); val != "" {
		if intVal, err := strconv.Atoi(val); err == nil {
			return intVal
		}
	}
	return fallback
}
