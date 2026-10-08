package auth

import (
	"context"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

// GRPCHandler adapta el servicio de autenticación a gRPC
type GRPCHandler struct {
	ecostreamv1.UnimplementedAuthServiceServer
	service *Service
}

// NewGRPCHandler crea un nuevo handler gRPC para AuthService
func NewGRPCHandler(service *Service) *GRPCHandler {
	return &GRPCHandler{service: service}
}

// Register atiende solicitudes de registro gRPC
func (h *GRPCHandler) Register(ctx context.Context, req *ecostreamv1.RegisterRequest) (*ecostreamv1.RegisterResponse, error) {
	if req.Username == "" || req.Email == "" || req.Password == "" {
		return nil, status.Error(codes.InvalidArgument, "todos los campos son requeridos")
	}

	user, token, expiresAt, err := h.service.Register(ctx, req.Username, req.Email, req.Password, req.DefaultRole)
	if err != nil {
		return &ecostreamv1.RegisterResponse{
			Success: false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.RegisterResponse{
		Success:       true,
		Message:       "Usuario registrado exitosamente",
		Token:         token,
		User:          user,
		ExpiresAtUnix: expiresAt,
	}, nil
}

// Login atiende solicitudes de inicio de sesión gRPC
func (h *GRPCHandler) Login(ctx context.Context, req *ecostreamv1.LoginRequest) (*ecostreamv1.LoginResponse, error) {
	if req.UsernameOrEmail == "" || req.Password == "" {
		return nil, status.Error(codes.InvalidArgument, "usuario y contraseña requeridos")
	}

	user, token, expiresAt, err := h.service.Login(ctx, req.UsernameOrEmail, req.Password)
	if err != nil {
		return &ecostreamv1.LoginResponse{
			Success: false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.LoginResponse{
		Success:       true,
		Message:       "Inicio de sesión exitoso",
		Token:         token,
		User:          user,
		ExpiresAtUnix: expiresAt,
	}, nil
}

// VerifyToken valida la autenticidad del token gRPC
func (h *GRPCHandler) VerifyToken(ctx context.Context, req *ecostreamv1.VerifyTokenRequest) (*ecostreamv1.VerifyTokenResponse, error) {
	if req.Token == "" {
		return &ecostreamv1.VerifyTokenResponse{
			Valid:   false,
			Message: "Token no proporcionado",
		}, nil
	}

	claims, err := h.service.VerifyToken(req.Token)
	if err != nil {
		return &ecostreamv1.VerifyTokenResponse{
			Valid:   false,
			Message: err.Error(),
		}, nil
	}

	return &ecostreamv1.VerifyTokenResponse{
		Valid:    true,
		UserId:   claims.UserID,
		Username: claims.Username,
		Role:     ecostreamv1.PlayerRole(claims.Role),
		Message:  "Token válido",
	}, nil
}

// GetProfile recupera los datos del perfil de usuario vía gRPC
func (h *GRPCHandler) GetProfile(ctx context.Context, req *ecostreamv1.GetProfileRequest) (*ecostreamv1.GetProfileResponse, error) {
	if req.UserId == "" {
		return nil, status.Error(codes.InvalidArgument, "user_id es requerido")
	}

	user, err := h.service.GetProfile(ctx, req.UserId)
	if err != nil {
		return &ecostreamv1.GetProfileResponse{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	return &ecostreamv1.GetProfileResponse{
		Success: true,
		User:    user,
	}, nil
}
