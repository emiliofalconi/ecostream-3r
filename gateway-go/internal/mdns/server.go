package mdns

import (
	"fmt"
	"log"
	"net"
	"os"

	"github.com/grandcat/zeroconf"
)

// Server gestiona el anuncio del servicio en la red local vía Multicast DNS / DNS-SD
type Server struct {
	server *zeroconf.Server
}

// Start registra y anuncia el servicio EcoStream en la LAN sin requerir configuración manual de IPs
func Start(instanceName string, port int, enginePort int) (*Server, error) {
	if instanceName == "" {
		hostname, err := os.Hostname()
		if err == nil && hostname != "" {
			instanceName = fmt.Sprintf("EcoStream-%s", hostname)
		} else {
			instanceName = "EcoStream-Server"
		}
	}

	serviceType := "_ecostream._tcp"
	domain := "local."

	txtRecords := []string{
		"txtv=1",
		fmt.Sprintf("gateway_port=%d", port),
		fmt.Sprintf("engine_port=%d", enginePort),
		"name=EcoStream Game Server",
	}

	server, err := zeroconf.Register(
		instanceName,
		serviceType,
		domain,
		port,
		txtRecords,
		nil, // Enlaza en todas las interfaces de red activas
	)
	if err != nil {
		return nil, fmt.Errorf("fallo al registrar servicio mDNS: %w", err)
	}

	log.Printf("[INFO] [mDNS] Servicio ZeroConf anunciado: '%s.%s%s' en puerto %d (Engine: %d)",
		instanceName, serviceType, domain, port, enginePort)

	return &Server{server: server}, nil
}

// Shutdown detiene el anuncio mDNS limpiamente
func (s *Server) Shutdown() {
	if s.server != nil {
		log.Println("[INFO] [mDNS] Deteniendo anuncio de servicio ZeroConf...")
		s.server.Shutdown()
	}
}

// GetLocalIP obtiene la primera dirección IP IPv4 privada no-loopback de la máquina
func GetLocalIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return "127.0.0.1"
	}
	for _, address := range addrs {
		if ipnet, ok := address.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				return ipnet.IP.String()
			}
		}
	}
	return "127.0.0.1"
}
