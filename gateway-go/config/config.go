package config

import (
	"fmt"
	"net"
	"os"
	"strconv"
	"strings"
	"time"
)

// Config almacena toda la configuración centralizada del Gateway Go
type Config struct {
	HTTPPort                 string
	GRPCPort                 string
	DatabaseURL              string
	RedisURL                 string
	JWTSecret                string
	HMACSecret               string
	JWTExpirationDuration    time.Duration
	SimulationEngineURL      string // URL interna gRPC para llamadas Gateway -> Engine
	SimulationPublicEndpoint string // Endpoint público anunciado al cliente en RoomInfo
	SimulationPort           int    // Puerto numérico del motor de simulación
	WorkerPoolCapacity       int
	WorkerCount              int
	EnableMDNS               bool   // Habilitar anuncio de servicio vía mDNS en LAN
	MDNSInstanceName         string // Nombre de la instancia en mDNS
}

// LoadConfig carga las variables de entorno o asigna valores por defecto seguros para desarrollo y LAN
func LoadConfig() *Config {
	jwtHours := getEnvAsInt("JWT_EXPIRATION_HOURS", 24)

	// En Render o entornos PaaS estándar, el puerto HTTP se define en la variable PORT
	httpPort := getEnv("PORT", getEnv("GATEWAY_HTTP_PORT", "8080"))

	simEngineURL := getEnv("SIMULATION_ENGINE_URL", "localhost:50052")
	simPort := getEnvAsInt("SIMULATION_GRPC_PORT", 50052)

	// Si no se define SIMULATION_PUBLIC_ENDPOINT, inferir automáticamente para LAN usando IP local
	simPublicEndpoint := os.Getenv("SIMULATION_PUBLIC_ENDPOINT")
	if strings.TrimSpace(simPublicEndpoint) == "" {
		localIP := getLocalIP()
		simPublicEndpoint = fmt.Sprintf("%s:%d", localIP, simPort)
	}

	return &Config{
		HTTPPort:                 httpPort,
		GRPCPort:                 getEnv("GATEWAY_GRPC_PORT", "50051"),
		DatabaseURL:              getEnv("DATABASE_URL", "postgres://ecostream_user:ecostream_secure_pass@localhost:5432/ecostream_db?sslmode=disable"),
		RedisURL:                 getEnv("REDIS_URL", "redis://localhost:6379"),
		JWTSecret:                getEnv("JWT_SECRET", "super_secret_eco_jwt_key_ucab_2026_change_in_prod"),
		HMACSecret:               getEnv("HMAC_SECRET", "super_secret_eco_hmac_ticket_key_2026"),
		JWTExpirationDuration:    time.Duration(jwtHours) * time.Hour,
		SimulationEngineURL:      simEngineURL,
		SimulationPublicEndpoint: simPublicEndpoint,
		SimulationPort:           simPort,
		WorkerPoolCapacity:       getEnvAsInt("WORKER_POOL_CAPACITY", 1000),
		WorkerCount:              getEnvAsInt("WORKER_COUNT", 4),
		EnableMDNS:               getEnvAsBool("ENABLE_MDNS", true),
		MDNSInstanceName:         getEnv("MDNS_INSTANCE_NAME", ""),
	}
}

func getLocalIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return "localhost"
	}
	for _, address := range addrs {
		if ipnet, ok := address.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				return ipnet.IP.String()
			}
		}
	}
	return "localhost"
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

func getEnvAsBool(key string, defaultVal bool) bool {
	if val, ok := os.LookupEnv(key); ok && val != "" {
		lower := strings.ToLower(val)
		return lower == "true" || lower == "1" || lower == "yes"
	}
	return defaultVal
}
