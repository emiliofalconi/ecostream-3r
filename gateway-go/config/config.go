package config

import (
	"os"
	"strconv"
	"time"
)

// Config almacena toda la configuración centralizada del Gateway Go
type Config struct {
	HTTPPort              string
	GRPCPort              string
	DatabaseURL           string
	RedisURL              string
	JWTSecret             string
	HMACSecret            string
	JWTExpirationDuration time.Duration
	SimulationEngineURL   string
	WorkerPoolCapacity    int
	WorkerCount           int
}

// LoadConfig carga las variables de entorno o asigna valores por defecto seguros para desarrollo
func LoadConfig() *Config {
	jwtHours := getEnvAsInt("JWT_EXPIRATION_HOURS", 24)

	return &Config{
		HTTPPort:              getEnv("GATEWAY_HTTP_PORT", "8080"),
		GRPCPort:              getEnv("GATEWAY_GRPC_PORT", "50051"),
		DatabaseURL:           getEnv("DATABASE_URL", "postgres://ecostream_user:ecostream_secure_pass@localhost:5432/ecostream_db?sslmode=disable"),
		RedisURL:              getEnv("REDIS_URL", "redis://localhost:6379"),
		JWTSecret:             getEnv("JWT_SECRET", "super_secret_eco_jwt_key_ucab_2026_change_in_prod"),
		HMACSecret:            getEnv("HMAC_SECRET", "super_secret_eco_hmac_ticket_key_2026"),
		JWTExpirationDuration: time.Duration(jwtHours) * time.Hour,
		SimulationEngineURL:   getEnv("SIMULATION_ENGINE_URL", "localhost:50052"),
		WorkerPoolCapacity:    getEnvAsInt("WORKER_POOL_CAPACITY", 1000),
		WorkerCount:           getEnvAsInt("WORKER_COUNT", 4),
	}
}

func getEnv(key, defaultVal string) string {
	if val, ok := os.LookupEnv(key); ok && val != "" {
		return val
	}
	return defaultVal
}

func getEnvAsInt(key string, defaultVal int) int {
	if val, ok := os.LookupEnv(key); ok && val != "" {
		if intVal, err := strconv.Atoi(val); err == nil {
			return intVal
		}
	}
	return defaultVal
}
