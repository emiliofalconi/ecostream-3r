package http

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"time"
)

// Server envuelve el servidor HTTP estándar
type Server struct {
	httpServer *http.Server
}

// NewServer inicializa el servidor HTTP
func NewServer(port string, router *Router) *Server {
	return &Server{
		httpServer: &http.Server{
			Addr:         fmt.Sprintf(":%s", port),
			Handler:      router.Handler(),
			ReadTimeout:  10 * time.Second,
			WriteTimeout: 15 * time.Second,
			IdleTimeout:  60 * time.Second,
		},
	}
}

// Start arranca el servidor HTTP en segundo plano
func (s *Server) Start() error {
	log.Printf("[INFO] [HTTP] Servidor REST escuchando en http://0.0.0.0%s", s.httpServer.Addr)
	if err := s.httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return fmt.Errorf("error al arrancar servidor HTTP: %w", err)
	}
	return nil
}

// Shutdown apaga limpiamente el servidor HTTP
func (s *Server) Shutdown(ctx context.Context) error {
	log.Println("[INFO] [HTTP] Apagando servidor REST...")
	return s.httpServer.Shutdown(ctx)
}
