package storage

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
)

// RedisClient envuelve el cliente de Redis para operaciones de Cache-Aside
type RedisClient struct {
	Client *redis.Client
}

// NewRedisClient inicializa la conexión con Redis
func NewRedisClient(redisURL string) (*RedisClient, error) {
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("error al parsear REDIS_URL: %w", err)
	}

	client := redis.NewClient(opt)

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		log.Printf("[WARN] No se pudo conectar a Redis inmediatamente: %v (degradación suave activa)", err)
	} else {
		log.Println("[INFO] Conexión establecida exitosamente con Redis 7")
	}

	return &RedisClient{Client: client}, nil
}

// Ping verifica la conectividad con Redis
func (r *RedisClient) Ping(ctx context.Context) error {
	if r == nil || r.Client == nil {
		return fmt.Errorf("redis no configurado")
	}
	return r.Client.Ping(ctx).Err()
}

// GetRoomCache obtiene el estado JSON de una sala desde Redis
func (r *RedisClient) GetRoomCache(ctx context.Context, roomCode string) (string, error) {
	if r == nil || r.Client == nil {
		return "", fmt.Errorf("redis no disponible")
	}
	key := fmt.Sprintf("room:%s", roomCode)
	return r.Client.Get(ctx, key).Result()
}

// SetRoomCache guarda el estado JSON de una sala en Redis con TTL
func (r *RedisClient) SetRoomCache(ctx context.Context, roomCode string, data string, ttl time.Duration) error {
	if r == nil || r.Client == nil {
		return nil // Degradación suave: no falla si redis está apagado
	}
	key := fmt.Sprintf("room:%s", roomCode)
	return r.Client.Set(ctx, key, data, ttl).Err()
}

// InvalidateRoomCache invalida la clave de sala al cambiar su estado
func (r *RedisClient) InvalidateRoomCache(ctx context.Context, roomCode string) error {
	if r == nil || r.Client == nil {
		return nil
	}
	key := fmt.Sprintf("room:%s", roomCode)
	return r.Client.Del(ctx, key).Err()
}

// Close cierra la conexión de Redis
func (r *RedisClient) Close() error {
	if r != nil && r.Client != nil {
		return r.Client.Close()
	}
	return nil
}
