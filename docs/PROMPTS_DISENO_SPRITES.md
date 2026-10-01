# Guía de Prompts para Generación de Assets y Sprites (Estilo Stardew Valley)

Este documento contiene los **prompts optimizados para modelos de generación de imágenes / arte por IA** (Midjourney, DALL-E 3, Stable Diffusion XL, Flux, o modelos especializados en Pixel Art) para crear el apartado visual completo del juego **EcoStream 3R**.

---

## 🎨 Especificaciones Técnicas Generales
- **Estilo Artístico:** 16-bit / 32-bit Cozy Pixel Art, vista ortogonal / top-down (cenital ligeramente inclinada ¾), inspirado en la estética pastoral y cálida de *Stardew Valley*.
- **Paleta de Colores:** Cálida, orgánica y saturación media:
  - Tonos tierra cálidos, maderas rústicas, pastos verdes naturales y agua azul cristalina.
  - Colores de alto contraste funcional para mecánicas del agua:
    - Azul celeste vibrante: Agua potable limpia.
    - Gris/Cian opaco: Aguas grises (reusables).
    - Marrón/Púrpura turbio: Aguas residuales contaminadas.
    - Rojo de alerta: Fugas y válvulas de emergencia cerradas.
    - Verde esmeralda: Riego ecológico y plantas florecidas.
- **Fondo:** Fondo transparente (PNG Alpha) para recortes y armado de spritesheets.

---

## 1. Prompt Maestro para la Hoja de Sprites Completa (Spritesheet Atlas)

> **Prompt:**
> ```text
> 2D pixel art game sprite sheet, top-down 3/4 RPG perspective, Stardew Valley aesthetic, 32x32 pixel grid layout, cohesive color palette. The sprite sheet contains:
> 1) Terrain tiles: warm green lush grass with small wildflowers, rich brown dirt pathways, rustic wooden fence segments, stone riverbank edges, and clear blue water pond tiles.
> 2) Water infrastructure (Reduce): wooden and copper irrigation channels, small garden sprinklers, cracked pipe leaking high-pressure water splashes, circular red closed valve, green open valve.
> 3) Agriculture & Reuse: dry plowed crop soil, healthy watered vegetable plots with glowing green cabbages and tomatoes.
> 4) Recycling & Purification: rustic watermill building with wooden wheel, bio-filter tank with visible layers of sand, gravel, and activated charcoal.
> 5) Characters: 4 cozy farmer technician avatars wearing denim overalls, straw hats, and boots, holding wrenches, with distinct shirt colors (red, blue, green, yellow) in 4-direction walking poses.
> Transparent background, clean pixel outlines, crisp pixels, no blur, no anti-aliasing, retro 16-bit aesthetic, master game asset sheet --v 6.0 --style raw
> ```

---

## 2. Prompts Específicos por Componente

### 2.1 Terrenos y Entorno Rural (Tileset de Suelo y Naturaleza)
> **Prompt:**
> ```text
> Top-down 2D pixel art tileset for farm and water reservoir environment, Stardew Valley art style. Includes seamless modular tiles: warm pastoral grass, cobblestone path, tilled soil, water pond edges with reeds and pebbles, rustic wooden dock. 32x32 pixel seamless tiles, warm earthy palette, crisp pixel art, clean borders, game ready asset, transparent background --v 6.0
> ```

### 2.2 Mecánica REDUCIR: Tuberías, Válvulas y Fugas
> **Prompt:**
> ```text
> Pixel art sprite pack of water conservation and pipe repair objects, top-down view, Stardew Valley style:
> - Wooden aqueduct channel with clear water flowing inside.
> - Copper pipe segment bursting with animated water splash droplets.
> - Wall-mounted brass pressure gauge and red emergency wheel valve.
> - Toolkit with wrench and sealant tape.
> 32x32 pixel sprites, retro cozy game asset, isolated on clean transparent background, pixel perfect --v 6.0
> ```

### 2.3 Mecánica REUSAR: Huertos y Desvío de Aguas Grises
> **Prompt:**
> ```text
> Top-down 2D pixel art sprites of rural irrigation and greywater recycling, cozy farm aesthetic like Stardew Valley:
> - Wooden sluice gates and diversion water valves.
> - Dry parched farmland plot transitioning into vibrant irrigated crop field with thriving crops.
> - Water reservoir barrel connected to drip irrigation pipes.
> Vibrant cozy colors, 32x32 pixel grid, game asset, transparent background, crisp pixel art --v 6.0
> ```

### 2.4 Mecánica RECICLAR: Molino Purificador y Filtros Biológicos
> **Prompt:**
> ```text
> Cozy pixel art game structure of an ecological water recycling station, top-down 3/4 perspective, Stardew Valley style:
> A rustic wooden watermill building with an active rotating water wheel, connected to layered biological purification tanks (gravel, charcoal, sand filter beds), showing murky wastewater entering on one side and sparkling clean water exiting into a pristine pond.
> 64x64 pixel game building sprite, warm cozy fantasy farming aesthetic, isolated on transparent background --v 6.0
> ```

### 2.5 Avatares de Jugadores (Cross-Play Multijugador)
> **Prompt:**
> ```text
> Pixel art character sprite sheet of a cute eco-farmer technician, Stardew Valley character style, top-down view. Wearing classic denim overalls, straw sunhat, brown work boots, and holding a mechanic wrench. Walk cycle animation frames facing front, back, and side, plus an action pose repairing a leak. 32x32 pixels per frame, warm friendly colors, clean pixel art, transparent background --v 6.0
> ```

---

## 💡 Recomendaciones para la Generación
1. **Modelos recomendados:**
   - **Midjourney v6**: Usar los parámetros `--style raw` y palabras clave `pixel art, 32x32, sprite sheet, transparent background`.
   - **DALL-E 3**: Añadir *"Create a 16-bit retro pixel art sprite sheet on a plain white or transparent background, no 3D render, no gradients, sharp pixelated edges"*.
2. **Post-procesamiento:**
   - Si la IA genera fondo blanco o negro, pasar la imagen por una herramienta como *remove.bg* o usar GIMP/Photoshop para seleccionar color y convertir a transparencia PNG.
   - Escalar en múltiplos enteros (1x, 2x, 4x) con interpolación de *"Vecino más cercano" (Nearest Neighbor)* para conservar la nitidez del pixel art.
