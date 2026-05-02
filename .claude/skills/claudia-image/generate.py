#!/usr/bin/env python3
"""
Genera imágenes con Google AI Studio y OpenAI.

Uso:
  python3 generate.py "un diagrama técnico sobre microservicios" --output imagen.png
  python3 generate.py "charcoal sketch of a brain" --style charcoal --output brain.png
  python3 generate.py "blog header about AI" --style dark-diagram --size 16:9 --output header.png
  python3 generate.py "retrato artístico" --model openai-hd --size 3:2 --output retrato.png

Proveedores:

  Google (GOOGLE_AI_API_KEY):
    flash         — Gemini 2.5 Flash Image — GRATIS, solo 1:1 (default)
    nano2         — Gemini 3.1 Flash Image — ~$0.045/img, solo 1:1
    pro           — Gemini 3 Pro Image — ~$0.045/img, solo 1:1
    imagen-fast   — Imagen 4 Fast — $0.02/img, aspect ratios (default para no-1:1)
    imagen        — Imagen 4 Standard — $0.04/img, aspect ratios
    imagen-ultra  — Imagen 4 Ultra — $0.06/img, máxima calidad, aspect ratios

  OpenAI (OPENAI_API_KEY):
    openai-low    — GPT Image 2 (low) — ~$0.006/img, aspect ratios
    openai        — GPT Image 2 (medium) — ~$0.05/img, aspect ratios
    openai-hd     — GPT Image 2 (high) — ~$0.21/img, máxima calidad, aspect ratios

Tamaños (--size):
  1:1   — Cuadrado (default)
  16:9  — Paisaje ancho (blog headers, thumbnails YT)
  3:2   — Paisaje moderado
  4:3   — Paisaje suave
  3:4   — Retrato suave
  2:3   — Retrato moderado
  9:16  — Retrato alto

Estilos predefinidos (--style):

  Incluidos (core):
    dark-diagram — Infografía sobre negro puro. Line-art blanco con cyan y violeta
    woodcut      — Grabado xilográfico B&N. Trazos tallados, alto contraste

  Estilos del usuario:
    Se cargan automáticamente de user/styles.json (en el directorio de la skill).
    Ver user/styles.json para los disponibles.

  (sin estilo) — Prompt directo sin modificar
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Cargar .env de user/credentials/
SCRIPT_DIR = Path(__file__).parent
CLAUDIA_ROOT = SCRIPT_DIR.parent.parent.parent  # .claude/skills/image → raíz
ENV_FILE = CLAUDIA_ROOT / "user" / "credentials" / ".env"

def load_env():
    for candidate in [ENV_FILE]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

GOOGLE_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not GOOGLE_API_KEY and not OPENAI_API_KEY:
    print("=" * 60, file=sys.stderr)
    print("  Image — Configuración inicial", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)
    print("Necesitas al menos una API key para generar imágenes.", file=sys.stderr)
    print(file=sys.stderr)
    print("  Opción 1 — Google AI Studio (recomendado, tiene tier gratuito):", file=sys.stderr)
    print("    1. Ve a https://aistudio.google.com/apikey", file=sys.stderr)
    print("    2. Crea una API key", file=sys.stderr)
    print(f"    3. Añade a {ENV_FILE}:", file=sys.stderr)
    print("       GOOGLE_AI_API_KEY=tu_key", file=sys.stderr)
    print(file=sys.stderr)
    print("  Opción 2 — OpenAI:", file=sys.stderr)
    print("    1. Ve a https://platform.openai.com/api-keys", file=sys.stderr)
    print("    2. Crea una API key", file=sys.stderr)
    print(f"    3. Añade a {ENV_FILE}:", file=sys.stderr)
    print("       OPENAI_API_KEY=tu_key", file=sys.stderr)
    print(file=sys.stderr)
    print("  AVISO DE COSTES:", file=sys.stderr)
    print("  El modelo 'flash' de Google es gratuito (solo imágenes 1:1).", file=sys.stderr)
    print("  El resto de modelos tienen coste por imagen:", file=sys.stderr)
    print("    Google Imagen 4:    $0.02 — $0.06 / imagen", file=sys.stderr)
    print("    Google Gemini Pro:  ~$0.045 / imagen", file=sys.stderr)
    print("    OpenAI GPT Image 2: $0.05 — $0.21 / imagen", file=sys.stderr)
    print(file=sys.stderr)
    print("  Recomendamos configurar un límite de gasto mensual:", file=sys.stderr)
    print("    Google → https://aistudio.google.com (Settings > Billing)", file=sys.stderr)
    print("    OpenAI → https://platform.openai.com/settings/organization/limits", file=sys.stderr)
    sys.exit(1)

# Modelos disponibles
MODELS = {
    # Google: Gemini (generateContent) — solo 1:1, 1024x1024
    "flash":        {"id": "gemini-2.5-flash-image",         "type": "gemini", "provider": "google", "price": "gratis"},
    "nano2":        {"id": "gemini-3.1-flash-image-preview",  "type": "gemini", "provider": "google", "price": "~$0.045/img"},
    "pro":          {"id": "gemini-3-pro-image-preview",      "type": "gemini", "provider": "google", "price": "~$0.045/img"},
    # Google: Imagen 4 (predict) — soporta aspect ratios
    "imagen-fast":  {"id": "imagen-4.0-fast-generate-001",    "type": "imagen", "provider": "google", "price": "$0.02/img"},
    "imagen":       {"id": "imagen-4.0-generate-001",         "type": "imagen", "provider": "google", "price": "$0.04/img"},
    "imagen-ultra": {"id": "imagen-4.0-ultra-generate-001",   "type": "imagen", "provider": "google", "price": "$0.06/img"},
    # OpenAI: GPT Image 2
    "openai-low":   {"id": "gpt-image-2", "type": "openai", "provider": "openai", "price": "~$0.006/img", "quality": "low"},
    "openai":       {"id": "gpt-image-2", "type": "openai", "provider": "openai", "price": "~$0.05/img",  "quality": "medium"},
    "openai-hd":    {"id": "gpt-image-2", "type": "openai", "provider": "openai", "price": "~$0.21/img",  "quality": "high"},
}

ASPECT_RATIOS = ["1:1", "16:9", "3:2", "4:3", "3:4", "2:3", "9:16"]

OPENAI_SIZES = {
    "1:1":  "1024x1024",
    "16:9": "1536x864",
    "3:2":  "1536x1024",
    "4:3":  "1024x768",
    "3:4":  "768x1024",
    "2:3":  "1024x1536",
    "9:16": "864x1536",
}

STYLES = {
    "dark-diagram": (
        "Technical infographic diagram on solid pure black background (#000000). "
        "NO gradients, NO noise texture, NO stars or particles. Flat solid black edge to edge. "
        "All diagram elements rendered in thin precise line-art (1-2px weight feel). "
        "PRIMARY LINE COLOR: white (#FFFFFF) for main structural lines, borders, and labels. "
        "ACCENT COLOR 1: teal cyan (#00D4AA) for highlights, active states, key connections, "
        "and primary data paths. Applied as thin lines with subtle outer glow (very soft, 3-5px "
        "spread, 30% opacity) to create a gentle luminous effect without overwhelming. "
        "ACCENT COLOR 2: soft violet purple (#9B7FFF) for secondary elements, categories, "
        "annotations, and supporting connections. Same subtle glow treatment. "
        "NO other colors. Strictly black, white, cyan, and violet only. "
        "ICONS: minimal geometric line-art icons (circles, squares, hexagons) with thin strokes "
        "matching the line weight. NO filled shapes, NO solid blocks of color, NO photographic elements. "
        "TYPOGRAPHY: section headers in bold italic serif font (like Georgia Bold Italic), "
        "all labels and body text in clean light-weight sans-serif (like Inter Light or SF Pro Light). "
        "All text in white. Sizes clearly hierarchical: headers large, labels medium, annotations small. "
        "LAYOUT: generous spacing between sections. Clear visual flow with directional arrows "
        "or connection lines. Nodes connected by thin lines with small arrow endpoints. "
        "Rounded-corner boxes with thin borders for grouping elements. "
        "The aesthetic is cerebral and precise, like a polished dark-mode presentation slide "
        "or a developer dashboard. Clean, technical, modern. "
        "Subject: "
    ),
    "woodcut": (
        "Black and white woodcut print illustration, printed on slightly off-white paper "
        "(warm ivory, like aged printmaking paper with very subtle fiber texture). "
        "The paper fills the entire frame edge to edge. "
        "All imagery rendered in the woodcut relief printing technique: carved lines where "
        "the wood was gouged away appear as white (the paper showing through), raised areas "
        "that received ink appear as solid black. "
        "LINE QUALITY: bold, confident carved lines with natural irregularities from the wood. "
        "Visible wood grain texture running through the black inked areas (subtle parallel lines "
        "within the solid blacks where the wood grain transferred). Carved edges are slightly "
        "rough and organic, NOT digitally smooth. "
        "CONTRAST: dramatic, high-contrast. Deep solid blacks and clean whites with minimal "
        "mid-tones. Where shading is needed, use parallel carved hatch lines (cross-hatching "
        "for darker areas, single-direction hatching for lighter areas). NO smooth gradients. "
        "STRICTLY BLACK AND WHITE. No gray tones, no color, no colored accents. "
        "The only tonal variation comes from the density of hatch lines and the warm paper tone. "
        "COMPOSITION: strong, bold, graphic. Elements have weight and presence. "
        "Clear figure-ground separation. Dramatic use of positive and negative space. "
        "The aesthetic references Renaissance and Edo-period woodcuts (Durer, Hokusai) "
        "but with modern subject matter. Powerful, tactile, timeless. "
        "NO digital effects, NO photographs, NO 3D rendering, NO text overlay. "
        "Subject: "
    ),
}

# Cargar estilos del usuario desde user/styles.json (si existe)
USER_STYLES_FILE = SCRIPT_DIR / "user" / "styles.json"
if USER_STYLES_FILE.exists():
    try:
        _user_styles = json.loads(USER_STYLES_FILE.read_text())
        for name, data in _user_styles.items():
            STYLES[name] = data["prompt"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Aviso: error cargando user/styles.json: {e}", file=sys.stderr)


def generate_gemini(model_id: str, prompt: str, aspect_ratio: str = "1:1") -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GOOGLE_API_KEY}"
    gen_config = {"responseModalities": ["TEXT", "IMAGE"]}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config,
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())

    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if "inlineData" in part:
                return base64.b64decode(part["inlineData"]["data"])
            if "text" in part:
                print(f"Modelo: {part['text']}", file=sys.stderr)

    raise RuntimeError(f"No se recibió imagen de {model_id}")


def generate_imagen(model_id: str, prompt: str, aspect_ratio: str) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:predict?key={GOOGLE_API_KEY}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"aspectRatio": aspect_ratio, "sampleCount": 1},
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())

    predictions = data.get("predictions", [])
    if predictions:
        return base64.b64decode(predictions[0]["bytesBase64Encoded"])

    raise RuntimeError(f"No se recibió imagen de {model_id}")


def generate_openai(model_id: str, prompt: str, aspect_ratio: str, quality: str = "medium") -> bytes:
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY no configurada.", file=sys.stderr)
        print(f"Añade OPENAI_API_KEY=tu_key a {ENV_FILE}", file=sys.stderr)
        sys.exit(1)

    url = "https://api.openai.com/v1/images/generations"
    size = OPENAI_SIZES.get(aspect_ratio, "1024x1024")
    payload = {
        "model": model_id,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "output_format": "png",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                                }, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())

    items = data.get("data", [])
    if items and "b64_json" in items[0]:
        return base64.b64decode(items[0]["b64_json"])

    raise RuntimeError(f"No se recibió imagen de {model_id}")


def resolve_model(model_arg: str | None, size: str) -> dict:
    if model_arg:
        if model_arg not in MODELS:
            print(f"Error: modelo '{model_arg}' no reconocido. Opciones: {', '.join(MODELS.keys())}", file=sys.stderr)
            sys.exit(1)
        model = MODELS[model_arg]
        if model["type"] == "gemini" and size != "1:1":
            print(f"Aviso: {model_arg} solo genera 1:1 (1024x1024). Ignorando --size {size}.", file=sys.stderr)
        if model["provider"] == "google" and not GOOGLE_API_KEY:
            print(f"Error: {model_arg} requiere GOOGLE_AI_API_KEY.", file=sys.stderr)
            sys.exit(1)
        if model["provider"] == "openai" and not OPENAI_API_KEY:
            print(f"Error: {model_arg} requiere OPENAI_API_KEY.", file=sys.stderr)
            sys.exit(1)
        return model
    # Auto: modelo gratuito (flash) para 1:1, imagen-fast para otros ratios
    if GOOGLE_API_KEY:
        return MODELS["flash"] if size == "1:1" else MODELS["imagen-fast"]
    return MODELS["openai-low"]


def generate_image(prompt: str, style: str | None = None, model_arg: str | None = None,
                   size: str = "1:1", output: str = "output.png") -> str:

    full_prompt = STYLES[style] + prompt if style and style in STYLES else prompt
    model = resolve_model(model_arg, size)
    model_id = model["id"]

    try:
        if model["type"] == "gemini":
            img_data = generate_gemini(model_id, full_prompt, size)
        elif model["type"] == "imagen":
            img_data = generate_imagen(model_id, full_prompt, size)
        elif model["type"] == "openai":
            img_data = generate_openai(model_id, full_prompt, size, model.get("quality", "medium"))
        else:
            raise RuntimeError(f"Tipo de modelo desconocido: {model['type']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error API ({e.code}): {body}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(img_data)
    print(f"Imagen guardada: {output_path} ({len(img_data)} bytes) [{model_id}, {model['price']}]")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Genera imágenes con Google AI Studio y OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("prompt", help="Descripción de la imagen a generar")
    parser.add_argument("--model", "-m", choices=list(MODELS.keys()),
                        help="Modelo (default: flash para 1:1, imagen-fast para otros ratios)")
    parser.add_argument("--style", choices=list(STYLES.keys()), help="Estilo predefinido")
    parser.add_argument("--size", "-s", choices=ASPECT_RATIOS, default="1:1",
                        help="Aspect ratio (default: 1:1)")
    parser.add_argument("--output", "-o", default="output.png", help="Ruta de salida (default: output.png)")
    args = parser.parse_args()

    generate_image(args.prompt, args.style, args.model, args.size, args.output)


if __name__ == "__main__":
    main()
