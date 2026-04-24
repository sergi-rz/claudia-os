---
name: claudia-yt-transcript
description: "Descarga subtítulos y clips de vídeos de YouTube. Skill-librería usada por claudia-wisdom, claudia-research y directamente por el usuario."
scope: core
user-invocable: true
argument-hint: "<URL> [--lang es] [--output /ruta/]"
---

# YT Transcript — Subtítulos y clips de YouTube

Skill-librería que descarga y procesa contenido de YouTube. Usada por `/claudia-wisdom` y `/claudia-research`, y también invocable directamente.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Subtítulos

```bash
python3 .claude/skills/claudia-yt-transcript/extract_subtitles.py <URL> --output /ruta/destino/ [--lang es] [--cookies /ruta/cookies.txt]
```

Genera un `.md` limpio con título, fecha, enlace y transcripción formateada en párrafos.

## Clips (b-roll)

```bash
# Desde fichero de clips:
python3 .claude/skills/claudia-yt-transcript/download_clips.py clips.txt --output /ruta/

# Clip suelto:
python3 .claude/skills/claudia-yt-transcript/download_clips.py --url URL --start 14:30 --end 14:45 --name nombre --output /ruta/
```

Formato del fichero de clips: `nombre | URL | inicio | fin | notas opcionales`

## Setup (primera vez)

Esta skill no necesita credenciales, pero requiere dos herramientas:

```bash
# macOS
brew install yt-dlp ffmpeg

# Linux
pip install yt-dlp && sudo apt install ffmpeg
```

Sin `yt-dlp` o `ffmpeg`, los scripts mostrarán un error indicando qué falta.
