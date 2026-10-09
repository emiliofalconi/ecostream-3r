package swagger

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

func TestSwaggerUIHandler(t *testing.T) {
	handler := NewHandler("../../docs/swagger/openapi.json")
	req := httptest.NewRequest(http.MethodGet, "/swagger/", nil)
	w := httptest.NewRecorder()

	handler.UIHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("se esperaba 200 OK en Swagger UI, obtenido: %d", w.Code)
	}

	body := w.Body.String()
	if !strings.Contains(body, "SwaggerUIBundle") {
		t.Errorf("Swagger UI HTML no contiene SwaggerUIBundle")
	}
	if !strings.Contains(body, "/swagger/openapi.json") {
		t.Errorf("Swagger UI HTML no referencia la URL del spec openapi.json")
	}
}

func TestSwaggerSpecHandler_ValidJSONAndPaths(t *testing.T) {
	specPath := "docs/swagger/openapi.json"
	// Si se ejecuta desde el paquete swagger
	if _, err := os.Stat(specPath); os.IsNotExist(err) {
		specPath = "../../docs/swagger/openapi.json"
	}

	handler := NewHandler(specPath)
	req := httptest.NewRequest(http.MethodGet, "/swagger/openapi.json", nil)
	w := httptest.NewRecorder()

	handler.SpecHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("se esperaba 200 OK en OpenAPI spec, obtenido: %d", w.Code)
	}

	contentType := w.Header().Get("Content-Type")
	if !strings.Contains(contentType, "application/json") {
		t.Errorf("Content-Type debería ser application/json, obtenido: %s", contentType)
	}

	var openAPIDoc map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &openAPIDoc); err != nil {
		t.Fatalf("el archivo OpenAPI no es un JSON válido: %v", err)
	}

	paths, ok := openAPIDoc["paths"].(map[string]interface{})
	if !ok {
		t.Fatalf("OpenAPI doc no contiene sección 'paths'")
	}

	expectedEndpoints := []string{
		"/healthz",
		"/readyz",
		"/api/v1/auth/register",
		"/api/v1/auth/login",
		"/api/v1/rooms",
		"/api/v1/rooms/join",
		"/api/v1/leaderboard",
		"/api/v1/matches/finish",
		"/api/v1/matches/history",
	}

	for _, ep := range expectedEndpoints {
		if _, exists := paths[ep]; !exists {
			t.Errorf("endpoint requerido '%s' no encontrado en OpenAPI spec", ep)
		}
	}
}
