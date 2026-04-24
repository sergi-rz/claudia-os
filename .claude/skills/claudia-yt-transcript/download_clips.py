#!/usr/bin/env python3
"""
Descarga clips recortados de YouTube para usar como b-roll.

Uso:
    # Descargar desde un fichero de clips:
    python3 download_clips.py clips.txt --output /ruta/destino/

    # Descargar un clip suelto:
    python3 download_clips.py --url URL --start 14:30 --end 14:45 --name hinton-charla --output /ruta/

    # Con audio (por defecto se descarga sin audio):
    python3 download_clips.py clips.txt --output /ruta/ --with-audio

Formato del fichero de clips (una línea por clip):
    nombre | URL | inicio | fin | notas opcionales
    hinton-nobel | https://youtube.com/watch?v=xxx | 2:15 | 2:30 | Charla Nobel 2024
    altman-congress | https://youtube.com/watch?v=yyy | 45:10 | 45:25 |

    Líneas vacías y comentarios (#) se ignoran.

Requiere: yt-dlp, ffmpeg
"""

import argparse
import os
import subprocess
import sys


def parse_time(t: str) -> str:
    """Normaliza formato de tiempo a HH:MM:SS para yt-dlp."""
    parts = t.strip().split(":")
    if len(parts) == 2:
        return f"00:{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    elif len(parts) == 3:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
    return t


def time_to_seconds(t: str) -> float:
    """Convierte HH:MM:SS a segundos."""
    parts = parse_time(t).split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def parse_clips_file(filepath: str) -> list[dict]:
    """Parsea un fichero de clips."""
    clips = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 4:
                print(f"  ⚠ Línea {line_num} ignorada (formato: nombre | url | inicio | fin): {line}")
                continue
            clips.append({
                "name": parts[0],
                "url": parts[1],
                "start": parts[2],
                "end": parts[3],
                "notes": parts[4] if len(parts) > 4 else "",
            })
    return clips


def download_clip(clip: dict, output_dir: str, with_audio: bool = False, max_height: int = 1080) -> bool:
    """Descarga un clip recortado de YouTube."""
    name = clip["name"]
    url = clip["url"]
    start = clip["start"]
    end = clip["end"]

    output_path = os.path.join(output_dir, f"{name}.mp4")

    if os.path.exists(output_path):
        print(f"  ⏭ {name}.mp4 ya existe, saltando")
        return True

    start_s = time_to_seconds(start)
    end_s = time_to_seconds(end)
    duration = end_s - start_s

    if duration <= 0:
        print(f"  ✗ {name}: duración inválida ({start} → {end})")
        return False

    if duration > 60:
        print(f"  ⚠ {name}: clip de {duration:.0f}s (>60s). ¿Seguro?")

    print(f"  ↓ {name} ({start} → {end}, {duration:.0f}s)")

    # Estrategia: descargar el vídeo completo y recortar con ffmpeg
    # yt-dlp --download-sections es más rápido pero a veces impreciso
    # Para clips cortos (<30s), usamos download-sections
    # Para clips más largos, descargamos y recortamos

    fmt = f"bv[height<={max_height}]" if not with_audio else f"bv[height<={max_height}]+ba"
    section = f"*{start}-{end}"

    cmd = [
        "yt-dlp",
        "--download-sections", section,
        "-f", fmt,
        "--merge-output-format", "mp4",
        "--no-warnings",
        "--quiet",
        "-o", output_path,
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            # Fallback: descargar completo y recortar con ffmpeg
            print(f"    Reintentando con ffmpeg...")
            return download_clip_ffmpeg(clip, output_dir, with_audio, max_height)

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"    ✓ {name}.mp4 ({size_mb:.1f} MB)")
            return True
        else:
            print(f"    ✗ No se generó el fichero")
            return False

    except subprocess.TimeoutExpired:
        print(f"    ✗ Timeout descargando {name}")
        return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


def download_clip_ffmpeg(clip: dict, output_dir: str, with_audio: bool, max_height: int) -> bool:
    """Fallback: descarga completo y recorta con ffmpeg."""
    import tempfile

    name = clip["name"]
    url = clip["url"]
    start = parse_time(clip["start"])
    end = clip["end"]
    output_path = os.path.join(output_dir, f"{name}.mp4")

    start_s = time_to_seconds(clip["start"])
    end_s = time_to_seconds(clip["end"])
    duration = end_s - start_s

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Descargar vídeo completo
        fmt = f"bv[height<={max_height}]" if not with_audio else f"bv[height<={max_height}]+ba"
        dl_cmd = [
            "yt-dlp", "-f", fmt, "--merge-output-format", "mp4",
            "--no-warnings", "--quiet", "-o", tmp_path, url,
        ]
        subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)

        if not os.path.exists(tmp_path):
            return False

        # Recortar con ffmpeg
        ff_cmd = [
            "ffmpeg", "-y", "-ss", str(start_s), "-i", tmp_path,
            "-t", str(duration), "-c", "copy",
        ]
        if not with_audio:
            ff_cmd.append("-an")
        ff_cmd.append(output_path)

        subprocess.run(ff_cmd, capture_output=True, text=True, timeout=60)

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"    ✓ {name}.mp4 ({size_mb:.1f} MB) [ffmpeg]")
            return True

        return False

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(description="Descarga clips de YouTube para b-roll")
    parser.add_argument("clips_file", nargs="?", help="Fichero con lista de clips")
    parser.add_argument("--url", help="URL de un clip suelto")
    parser.add_argument("--start", help="Tiempo de inicio (MM:SS o HH:MM:SS)")
    parser.add_argument("--end", help="Tiempo de fin")
    parser.add_argument("--name", help="Nombre del clip")
    parser.add_argument("--output", "-o", required=True, help="Directorio de salida")
    parser.add_argument("--with-audio", action="store_true", help="Incluir audio (por defecto solo vídeo)")
    parser.add_argument("--max-height", type=int, default=1080, help="Altura máxima del vídeo (default: 1080)")

    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)

    clips = []

    if args.clips_file:
        clips = parse_clips_file(args.clips_file)
        print(f"📋 {len(clips)} clips encontrados en {args.clips_file}")
    elif args.url and args.start and args.end:
        name = args.name or "clip"
        clips = [{"name": name, "url": args.url, "start": args.start, "end": args.end, "notes": ""}]
    else:
        parser.error("Necesitas un fichero de clips o --url --start --end")

    ok = 0
    fail = 0
    for clip in clips:
        if download_clip(clip, args.output, args.with_audio, args.max_height):
            ok += 1
        else:
            fail += 1

    print(f"\n{'✓' if fail == 0 else '⚠'} {ok}/{ok + fail} clips descargados en {args.output}")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
