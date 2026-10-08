package matchmaking

import (
	"context"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/auth"
	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

// GRPCHandler adapta el servicio de matchmaking a gRPC
type GRPCHandler struct {
	ecostreamv1.UnimplementedMatchmakingServiceServer
	service    *Service
	jwtManager *auth.JWTManager
}

// NewGRPCHandler crea un nuevo handler gRPC para MatchmakingService
func NewGRPCHandler(service *Service, jwtManager *auth.JWTManager) *GRPCHandler {
	return &GRPCHandler{
		service:    service,
		jwtManager: jwtManager,
	}
}

func (h *GRPCHandler) authenticateToken(tokenStr string) (*auth.UserClaims, error) {
	if tokenStr == "" {
		return nil, status.Error(codes.Unauthenticated, "token de autenticación requerido")
	}
	claims, err := h.jwtManager.VerifyToken(tokenStr)
	if err != nil {
		return nil, status.Error(codes.Unauthenticated, "token inválido o expirado")
	}
	return claims, nil
}

// CreateRoom atiende peticiones gRPC para crear una nueva sala
func (h *GRPCHandler) CreateRoom(ctx context.Context, req *ecostreamv1.CreateRoomRequest) (*ecostreamv1.CreateRoomResponse, error) {
	claims, err := h.authenticateToken(req.Token)
	if err != nil {
		return nil, err
	}

	role := req.SelectedRole
	if role == ecostreamv1.PlayerRole_ROLE_UNSPECIFIED {
		role = ecostreamv1.PlayerRole(claims.Role)
	}

	room, ticket, err := h.service.CreateRoom(
		ctx,
		claims.UserID,
		claims.Username,
		req.RoomName,
		role,
		req.MaxPlayers,
		req.DifficultyLevel,
	)
	if err != nil {
		return &ecostreamv1.CreateRoomResponse{
			Success: false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.CreateRoomResponse{
		Success:    true,
		Message:    "Sala creada exitosamente",
		Room:       room,
		RoomTicket: ticket,
	}, nil
}

// JoinRoom atiende peticiones gRPC para unirse por código de sala
func (h *GRPCHandler) JoinRoom(ctx context.Context, req *ecostreamv1.JoinRoomRequest) (*ecostreamv1.JoinRoomResponse, error) {
	claims, err := h.authenticateToken(req.Token)
	if err != nil {
		return nil, err
	}

	if req.RoomCode == "" {
		return nil, status.Error(codes.InvalidArgument, "código de sala requerido")
	}

	role := req.SelectedRole
	if role == ecostreamv1.PlayerRole_ROLE_UNSPECIFIED {
		role = ecostreamv1.PlayerRole(claims.Role)
	}

	room, ticket, err := h.service.JoinRoom(ctx, req.RoomCode, claims.UserID, claims.Username, role)
	if err != nil {
		return &ecostreamv1.JoinRoomResponse{
			Success: false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.JoinRoomResponse{
		Success:    true,
		Message:    "Unido a la sala con éxito",
		Room:       room,
		RoomTicket: ticket,
	}, nil
}

// QuickMatch une a una partida automáticamente
func (h *GRPCHandler) QuickMatch(ctx context.Context, req *ecostreamv1.QuickMatchRequest) (*ecostreamv1.QuickMatchResponse, error) {
	claims, err := h.authenticateToken(req.Token)
	if err != nil {
		return nil, err
	}

	role := req.PreferredRole
	if role == ecostreamv1.PlayerRole_ROLE_UNSPECIFIED {
		role = ecostreamv1.PlayerRole(claims.Role)
	}

	room, ticket, err := h.service.QuickMatch(ctx, claims.UserID, claims.Username, role)
	if err != nil {
		return &ecostreamv1.QuickMatchResponse{
			Success: false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.QuickMatchResponse{
		Success:    true,
		Message:    "Matchmaking rápido exitoso",
		Room:       room,
		RoomTicket: ticket,
	}, nil
}

// LeaveRoom abandona la sala activa
func (h *GRPCHandler) LeaveRoom(ctx context.Context, req *ecostreamv1.LeaveRoomRequest) (*ecostreamv1.LeaveRoomResponse, error) {
	claims, err := h.authenticateToken(req.Token)
	if err != nil {
		return nil, err
	}

	err = h.service.LeaveRoom(ctx, req.RoomId, claims.UserID)
	if err != nil {
		return &ecostreamv1.LeaveRoomResponse{
			Success: false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.LeaveRoomResponse{
		Success: true,
		Message: "Saliste de la sala exitosamente",
	}, nil
}

// GetRoomStatus consulta el estado de la sala (Cache-Aside)
func (h *GRPCHandler) GetRoomStatus(ctx context.Context, req *ecostreamv1.GetRoomStatusRequest) (*ecostreamv1.GetRoomStatusResponse, error) {
	_, err := h.authenticateToken(req.Token)
	if err != nil {
		return nil, err
	}

	room, err := h.service.GetRoomStatus(ctx, req.RoomId)
	if err != nil {
		return &ecostreamv1.GetRoomStatusResponse{
			Success: false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.GetRoomStatusResponse{
		Success: true,
		Message: "Estado de sala recuperado",
		Room:    room,
	}, nil
}

// StartMatch arranca la partida
func (h *GRPCHandler) StartMatch(ctx context.Context, req *ecostreamv1.StartMatchRequest) (*ecostreamv1.StartMatchResponse, error) {
	claims, err := h.authenticateToken(req.Token)
	if err != nil {
		return nil, err
	}

	room, ticket, err := h.service.StartMatch(ctx, req.RoomId, claims.UserID, req.FillWithBots)
	if err != nil {
		return &ecostreamv1.StartMatchResponse{
			Success: false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.StartMatchResponse{
		Success:    true,
		Message:    "Partida iniciada",
		Room:       room,
		RoomTicket: ticket,
	}, nil
}

// ListAvailableRooms retorna la lista de salas públicas
func (h *GRPCHandler) ListAvailableRooms(ctx context.Context, req *ecostreamv1.ListAvailableRoomsRequest) (*ecostreamv1.ListAvailableRoomsResponse, error) {
	_, err := h.authenticateToken(req.Token)
	if err != nil {
		return nil, err
	}

	rooms, err := h.service.ListAvailableRooms(ctx, req.PageSize)
	if err != nil {
		return &ecostreamv1.ListAvailableRoomsResponse{
			Success: false,
			Rooms:   nil,
		}, nil
	}

	return &ecostreamv1.ListAvailableRoomsResponse{
		Success: true,
		Rooms:   rooms,
	}, nil
}
