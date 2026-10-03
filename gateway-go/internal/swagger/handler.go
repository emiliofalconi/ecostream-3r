package swagger

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
)

const swaggerUIHTML = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>EcoStream 3R - API Swagger UI</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  <style>
    body { margin: 0; background: #fafafa; }
    .swagger-ui .topbar { background-color: #0d9488; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: "/swagger/openapi.json",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout"
      });
    };
  </script>
</body>
</html>`

type Handler struct {
	openAPIPath string
}

func NewHandler(openAPIPath string) *Handler {
	return &Handler{openAPIPath: openAPIPath}
}

func (h *Handler) UIHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, swaggerUIHTML)
}

func (h *Handler) SpecHandler(w http.ResponseWriter, r *http.Request) {
	// Intentar cargar la ruta configurada o rutas relativas comunes
	paths := []string{
		h.openAPIPath,
		"docs/swagger/openapi.json",
		"../docs/swagger/openapi.json",
		"/app/docs/swagger/openapi.json",
	}

	for _, p := range paths {
		if abs, err := filepath.Abs(p); err == nil {
			if data, err := os.ReadFile(abs); err == nil {
				w.Header().Set("Content-Type", "application/json")
				w.Write(data)
				return
			}
		}
	}

	http.Error(w, "openapi.json no encontrado", http.StatusNotFound)
}
