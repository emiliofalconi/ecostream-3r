"""
Generador de Spritesheet Estilo Stardew Valley para EcoStream 3R
Crea 'assets/sprites/tileset_stardew.png' y su atlas 'assets/sprites/tileset.json'.
Todos los tiles son de 32x32 píxeles con paleta cálida inspirada en Stardew Valley.
"""
import json
import os
from PIL import Image, ImageDraw

TILE_SIZE = 32
GRID_COLS = 8
GRID_ROWS = 6
IMAGE_WIDTH = GRID_COLS * TILE_SIZE
IMAGE_HEIGHT = GRID_ROWS * TILE_SIZE

# Paleta Stardew Valley Cozy & Water Tech
C_GRASS_BASE = (106, 169, 63)
C_GRASS_DARK = (78, 134, 46)
C_GRASS_LIGHT = (135, 194, 85)

C_DIRT_BASE = (194, 154, 100)
C_DIRT_DARK = (156, 118, 70)
C_DIRT_LIGHT = (218, 178, 126)

C_WATER_CLEAR = (64, 164, 223)
C_WATER_DEEP = (41, 128, 185)
C_WATER_HIGHLIGHT = (168, 224, 255)

C_WATER_GRAY = (127, 143, 166)
C_WATER_GRAY_DARK = (92, 104, 122)

C_WATER_DIRTY = (90, 62, 54)
C_WATER_DIRTY_DARK = (60, 40, 35)

C_WOOD_BASE = (139, 90, 43)
C_WOOD_DARK = (97, 58, 26)
C_WOOD_LIGHT = (182, 127, 72)

C_STONE_BASE = (149, 165, 166)
C_STONE_DARK = (110, 123, 124)
C_STONE_LIGHT = (189, 195, 199)

C_SKIN = (255, 219, 172)
C_OVERALLS = (41, 128, 185)
C_HAT = (241, 196, 15)
C_BOOTS = (86, 50, 20)
C_SHIRT = (231, 76, 60)

atlas = {}

def get_tile_image(col, row):
    return col * TILE_SIZE, row * TILE_SIZE

img = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

def draw_grass(c, r, name):
    x, y = get_tile_image(c, r)
    draw.rectangle([x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1], fill=C_GRASS_BASE)
    # Textura orgánica
    for dx, dy in [(4, 6), (12, 18), (22, 10), (18, 26), (6, 24), (26, 20)]:
        draw.point((x + dx, y + dy), fill=C_GRASS_DARK)
        draw.point((x + dx + 1, y + dy), fill=C_GRASS_LIGHT)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_dirt(c, r, name):
    x, y = get_tile_image(c, r)
    draw.rectangle([x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1], fill=C_DIRT_BASE)
    for dx, dy in [(6, 8), (14, 22), (24, 6), (20, 20), (4, 16)]:
        draw.rectangle([x + dx, y + dy, x + dx + 1, y + dy + 1], fill=C_DIRT_DARK)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_water_clear(c, r, name):
    x, y = get_tile_image(c, r)
    draw.rectangle([x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1], fill=C_WATER_CLEAR)
    # Ondulaciones
    draw.line([x + 4, y + 8, x + 16, y + 8], fill=C_WATER_HIGHLIGHT, width=1)
    draw.line([x + 14, y + 20, x + 26, y + 20], fill=C_WATER_HIGHLIGHT, width=1)
    draw.line([x + 2, y + 14, x + 10, y + 14], fill=C_WATER_DEEP, width=1)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_stone_wall(c, r, name):
    x, y = get_tile_image(c, r)
    draw.rectangle([x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1], fill=C_STONE_BASE)
    # Ladrillos rústicos
    draw.line([x, y + 10, x + TILE_SIZE, y + 10], fill=C_STONE_DARK)
    draw.line([x, y + 21, x + TILE_SIZE, y + 21], fill=C_STONE_DARK)
    draw.line([x + 10, y, x + 10, y + 10], fill=C_STONE_DARK)
    draw.line([x + 22, y + 10, x + 22, y + 21], fill=C_STONE_DARK)
    draw.line([x + 12, y + 21, x + 12, y + TILE_SIZE], fill=C_STONE_DARK)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_wood_fence(c, r, name):
    x, y = get_tile_image(c, r)
    # Fondo transparente con postes de cerca
    draw.rectangle([x + 4, y + 4, x + 8, y + 28], fill=C_WOOD_BASE, outline=C_WOOD_DARK)
    draw.rectangle([x + 24, y + 4, x + 28, y + 28], fill=C_WOOD_BASE, outline=C_WOOD_DARK)
    draw.rectangle([x + 2, y + 8, x + 30, y + 12], fill=C_WOOD_LIGHT, outline=C_WOOD_DARK)
    draw.rectangle([x + 2, y + 18, x + 30, y + 22], fill=C_WOOD_LIGHT, outline=C_WOOD_DARK)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_pipe_clean(c, r, name, horizontal=True):
    x, y = get_tile_image(c, r)
    if horizontal:
        draw.rectangle([x, y + 10, x + TILE_SIZE - 1, y + 22], fill=C_WOOD_BASE, outline=C_WOOD_DARK)
        draw.rectangle([x, y + 13, x + TILE_SIZE - 1, y + 19], fill=C_WATER_CLEAR)
        draw.rectangle([x + 2, y + 15, x + TILE_SIZE - 3, y + 17], fill=C_WATER_HIGHLIGHT)
    else:
        draw.rectangle([x + 10, y, x + 22, y + TILE_SIZE - 1], fill=C_WOOD_BASE, outline=C_WOOD_DARK)
        draw.rectangle([x + 13, y, x + 19, y + TILE_SIZE - 1], fill=C_WATER_CLEAR)
        draw.rectangle([x + 15, y + 2, x + 17, y + TILE_SIZE - 3], fill=C_WATER_HIGHLIGHT)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_pipe_leak(c, r, name):
    x, y = get_tile_image(c, r)
    draw_pipe_clean(c, r, name, horizontal=True)
    # Grieta y chorro de agua
    draw.line([x + 14, y + 10, x + 18, y + 14], fill=(220, 20, 60), width=2)
    # Gotas / Salpicadura de agua
    draw.ellipse([x + 12, y + 2, x + 18, y + 8], fill=C_WATER_HIGHLIGHT, outline=C_WATER_DEEP)
    draw.ellipse([x + 20, y + 24, x + 26, y + 30], fill=C_WATER_HIGHLIGHT, outline=C_WATER_DEEP)
    draw.point((x + 15, y + 5), fill=(255, 255, 255))
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_valve(c, r, name, closed=False):
    x, y = get_tile_image(c, r)
    draw_pipe_clean(c, r, name, horizontal=True)
    # Válvula de rueda en el centro
    v_color = (192, 57, 43) if closed else (39, 174, 96)
    draw.ellipse([x + 10, y + 6, x + 22, y + 18], fill=v_color, outline=(40, 40, 40))
    draw.ellipse([x + 14, y + 10, x + 18, y + 14], fill=(240, 240, 240))
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_crops(c, r, name, watered=False):
    x, y = get_tile_image(c, r)
    fill_dirt = C_DIRT_DARK if watered else C_DIRT_BASE
    draw.rectangle([x, y, x + TILE_SIZE - 1, y + TILE_SIZE - 1], fill=fill_dirt)
    # Surcos de tierra
    draw.line([x, y + 8, x + TILE_SIZE, y + 8], fill=(120, 80, 40) if watered else C_DIRT_DARK)
    draw.line([x, y + 20, x + TILE_SIZE, y + 20], fill=(120, 80, 40) if watered else C_DIRT_DARK)
    # Plantas verdes creciendo
    p_color = (46, 204, 113) if watered else (39, 174, 96)
    for px in [6, 16, 26]:
        draw.ellipse([x + px - 3, y + 4, x + px + 3, y + 10], fill=p_color)
        draw.ellipse([x + px - 3, y + 16, x + px + 3, y + 22], fill=p_color)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_water_filter_plant(c, r, name):
    x, y = get_tile_image(c, r)
    # Tanque de filtrado ecológico
    draw.rectangle([x + 2, y + 4, x + 30, y + 28], fill=C_WOOD_BASE, outline=C_WOOD_DARK)
    draw.rectangle([x + 6, y + 8, x + 26, y + 14], fill=(189, 195, 199)) # Filtro de grava
    draw.rectangle([x + 6, y + 16, x + 26, y + 24], fill=(52, 73, 94))   # Carbón activo
    draw.ellipse([x + 12, y + 10, x + 20, y + 18], fill=C_WATER_HIGHLIGHT)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

def draw_character(c, r, name, shirt_color):
    x, y = get_tile_image(c, r)
    # Cabeza con sombrero de paja Stardew
    draw.ellipse([x + 8, y + 4, x + 24, y + 12], fill=C_HAT, outline=(180, 140, 20))
    draw.rectangle([x + 12, y + 8, x + 20, y + 14], fill=C_SKIN)
    # Ojos pixel
    draw.point((x + 14, y + 10), fill=(40, 40, 40))
    draw.point((x + 18, y + 10), fill=(40, 40, 40))
    # Torso con camisa y overol
    draw.rectangle([x + 10, y + 14, x + 22, y + 22], fill=shirt_color)
    draw.rectangle([x + 12, y + 16, x + 20, y + 24], fill=C_OVERALLS)
    # Tirantes
    draw.line([x + 12, y + 16, x + 12, y + 22], fill=(20, 70, 140))
    draw.line([x + 20, y + 16, x + 20, y + 22], fill=(20, 70, 140))
    # Piernas / Botas
    draw.rectangle([x + 11, y + 24, x + 14, y + 29], fill=C_BOOTS)
    draw.rectangle([x + 18, y + 24, x + 21, y + 29], fill=C_BOOTS)
    # Herramienta en mano (llave inglesa)
    draw.rectangle([x + 22, y + 16, x + 26, y + 18], fill=C_STONE_LIGHT)
    draw.point((x + 26, y + 15), fill=C_STONE_DARK)
    draw.point((x + 26, y + 19), fill=C_STONE_DARK)
    atlas[name] = {"col": c, "row": r, "x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

# --- Generación del Tileset Grid ---
# Fila 0: Terrenos Base
draw_grass(0, 0, "grass")
draw_dirt(1, 0, "dirt")
draw_water_clear(2, 0, "water_reservoir")
draw_stone_wall(3, 0, "stone_edge")
draw_wood_fence(4, 0, "wood_fence")

# Fila 1: Tuberías y Flujos (REDUCIR)
draw_pipe_clean(0, 1, "pipe_horizontal", horizontal=True)
draw_pipe_clean(1, 1, "pipe_vertical", horizontal=False)
draw_pipe_leak(2, 1, "pipe_leak_active")
draw_valve(3, 1, "valve_open", closed=False)
draw_valve(4, 1, "valve_closed", closed=True)

# Fila 2: Agricultura y Aguas Grises (REUSAR)
draw_crops(0, 2, "crops_dry", watered=False)
draw_crops(1, 2, "crops_watered", watered=True)

# Fila 3: Planta y Filtros (RECICLAR)
draw_water_filter_plant(0, 3, "recycle_plant")

# Fila 4: Jugadores (Multi-Color para Cross-play)
draw_character(0, 4, "player_red", shirt_color=(231, 76, 60))
draw_character(1, 4, "player_blue", shirt_color=(52, 152, 219))
draw_character(2, 4, "player_green", shirt_color=(46, 204, 113))
draw_character(3, 4, "player_yellow", shirt_color=(241, 196, 15))

# Guardar archivos
os.makedirs("assets/sprites", exist_ok=True)
png_path = "assets/sprites/tileset_stardew.png"
json_path = "assets/sprites/tileset.json"

img.save(png_path)
with open(json_path, "w", encoding="utf-8") as f:
    json.dump({
        "tile_size": TILE_SIZE,
        "sheet_width": IMAGE_WIDTH,
        "sheet_height": IMAGE_HEIGHT,
        "tiles": atlas
    }, f, indent=2)

print(f"Generado con éxito: {png_path} ({IMAGE_WIDTH}x{IMAGE_HEIGHT})")
print(f"Atlas de coordenadas: {json_path}")
