#!/usr/bin/env python3
"""
Descarga subtítulos automáticos de vídeos de YouTube y genera ficheros .md limpios.

Uso:
    python3 extract_subtitles.py <URL> [<URL2> ...] --output /ruta/destino/
    python3 extract_subtitles.py <URL> --output /ruta/ --lang en
    python3 extract_subtitles.py <URL> --output /ruta/ --cookies /ruta/cookies.txt
    python3 extract_subtitles.py <URL> --output /ruta/ --cookies-from-browser chrome

Requiere: yt-dlp
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

def _find_ytdlp():
    # Prefer user-installed (newer) over system package
    user_bin = os.path.expanduser("~/.local/bin/yt-dlp")
    if os.path.isfile(user_bin) and os.access(user_bin, os.X_OK):
        return user_bin
    system = shutil.which("yt-dlp")
    if system:
        return system
    raise FileNotFoundError("yt-dlp no encontrado. Instálalo con: sudo apt install yt-dlp")

_YTDLP = _find_ytdlp()


def _ytdlp_base_args(cookies_file=None, cookies_from_browser=None):
    args = []
    if cookies_file and os.path.exists(cookies_file):
        args += ["--cookies", cookies_file]
    elif cookies_from_browser:
        args += ["--cookies-from-browser", cookies_from_browser]
    return args


def get_video_info(url, cookies_file=None, cookies_from_browser=None):
    result = subprocess.run(
        [_YTDLP, *_ytdlp_base_args(cookies_file, cookies_from_browser), "--dump-json", "--skip-download", url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ERROR al obtener info: {result.stderr.strip()}")
        return None
    return json.loads(result.stdout)


def download_subs(url, tmpdir, lang="es", cookies_file=None, cookies_from_browser=None):
    result = subprocess.run(
        [
            _YTDLP,
            *_ytdlp_base_args(cookies_file, cookies_from_browser),
            "--write-auto-sub",
            "--sub-lang", lang,
            "--skip-download",
            "--sub-format", "vtt",
            "-o", os.path.join(tmpdir, "subs"),
            url,
        ],
        capture_output=True, text=True
    )
    for f in os.listdir(tmpdir):
        if f.endswith(".vtt"):
            return os.path.join(tmpdir, f)
    return None


def clean_vtt(vtt_path):
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    text_lines = []
    seen = set()

    for line in lines:
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        if re.match(r'^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->', line):
            continue
        if not line.strip():
            continue

        clean = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', line)
        clean = re.sub(r'</?c>', '', clean)
        clean = re.sub(r'align:start position:\d+%', '', clean)
        clean = clean.strip()

        if not clean:
            continue

        if clean not in seen:
            seen.add(clean)
            text_lines.append(clean)

    full_text = ' '.join(text_lines)
    full_text = re.sub(r' {2,}', ' ', full_text)
    return full_text


def split_into_paragraphs(text, sentences_per_paragraph=5):
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡A-Z])', text)
    paragraphs = []
    current = []
    for sentence in sentences:
        current.append(sentence)
        if len(current) >= sentences_per_paragraph:
            paragraphs.append(' '.join(current))
            current = []
    if current:
        paragraphs.append(' '.join(current))
    return '\n\n'.join(paragraphs)


def slugify(title):
    slug = title.lower()
    slug = re.sub(r'[¿¡"«»""\'\'…:|\-]', '', slug)
    slug = slug.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    slug = slug.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    slug = slug.replace('ü', 'u')
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    if len(slug) > 60:
        slug = slug[:60].rsplit('-', 1)[0]
    return slug


def process_video(url, output_dir, lang="es", cookies_file=None, cookies_from_browser=None):
    """Procesa un vídeo de YouTube y genera el .md en output_dir."""
    print(f"Procesando: {url}")

    info = get_video_info(url, cookies_file, cookies_from_browser)
    if not info:
        return None

    title = info.get("title", "Sin título")
    upload_date = info.get("upload_date", "")
    description = info.get("description", "")
    video_id = info.get("id", "")

    if upload_date:
        date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    print(f"  Título: {title}")
    print(f"  Fecha:  {date}")

    with tempfile.TemporaryDirectory() as tmpdir:
        vtt_path = download_subs(url, tmpdir, lang, cookies_file, cookies_from_browser)
        if not vtt_path:
            print(f"  ERROR: No se pudieron descargar subtítulos")
            return None
        raw_text = clean_vtt(vtt_path)

    if not raw_text:
        print(f"  ERROR: Subtítulos vacíos")
        return None

    transcript = split_into_paragraphs(raw_text)

    slug = slugify(title)
    filename = f"{date}-{slug}.md"

    desc_lines = []
    for line in description.split('\n'):
        if line.strip().startswith('http') or line.strip().startswith('#'):
            break
        if line.strip():
            desc_lines.append(line.strip())
    clean_description = '\n'.join(desc_lines[:10]) if desc_lines else ""

    lines = [
        date, "",
        f"# {title}", "",
        f"**Enlace al vídeo:** https://www.youtube.com/watch?v={video_id}", "",
    ]
    if clean_description:
        lines += ["## Descripción:", "", clean_description, ""]
    lines += ["## Transcripción del vídeo:", "", transcript, ""]

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"  -> {output_path}")
    return output_path


def main():
    args = sys.argv[1:]

    if not args or args[0].startswith('-'):
        print("Uso: python3 extract_subtitles.py <URL> [<URL2> ...] --output /ruta/")
        sys.exit(1)

    urls = []
    output_dir = None
    lang = "es"
    cookies_file = None
    cookies_from_browser = None

    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output_dir = args[i + 1]; i += 2
        elif args[i] == "--lang" and i + 1 < len(args):
            lang = args[i + 1]; i += 2
        elif args[i] == "--cookies" and i + 1 < len(args):
            cookies_file = args[i + 1]; i += 2
        elif args[i] == "--cookies-from-browser" and i + 1 < len(args):
            cookies_from_browser = args[i + 1]; i += 2
        else:
            urls.append(args[i]); i += 1

    if not output_dir:
        print("ERROR: --output es obligatorio")
        sys.exit(1)

    if not urls:
        print("ERROR: indica al menos una URL")
        sys.exit(1)

    processed, errors = [], []
    for url in urls:
        result = process_video(url, output_dir, lang, cookies_file, cookies_from_browser)
        if result:
            processed.append(result)
        else:
            errors.append(url)

    print(f"\n--- Resumen ---")
    print(f"Procesados: {len(processed)}")
    print(f"Errores:    {len(errors)}")
    for e in errors:
        print(f"  - {e}")


if __name__ == "__main__":
    main()
