#!/usr/bin/env python3
"""
Descarga y transcribe episodios de podcast desde URLs de plataformas populares.

Uso:
    python3 podcast_transcribe.py <URL> --output /ruta/destino/
    python3 podcast_transcribe.py <URL> --output /ruta/ --lang es
    python3 podcast_transcribe.py <URL> --output /ruta/ --model /ruta/modelo.bin

Estrategia de extracción (en orden):
    1. yt-dlp — funciona con muchas plataformas directamente
    2. Scrape de la página — busca <audio>, <enclosure> o links a RSS
    3. Parse de RSS — extrae URL del <enclosure> del episodio

Requiere: yt-dlp, ffmpeg, whisper-cli (whisper.cpp)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET

WHISPER_PATH = "/opt/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/opt/whisper.cpp/models/ggml-base.bin"

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".flac")

PODCAST_DOMAINS = [
    "spotify.com", "open.spotify.com",
    "podcasts.apple.com",
    "ivoox.com",
    "player.fm",
    "podbean.com",
    "transistor.fm",
    "buzzsprout.com",
    "anchor.fm", "podcasters.spotify.com",
    "spreaker.com",
    "soundcloud.com",
    "overcast.fm",
    "pocketcasts.com",
    "castbox.fm",
    "podcastaddict.com",
    "podcasts.google.com",
]


def _find_ytdlp():
    user_bin = os.path.expanduser("~/.local/bin/yt-dlp")
    if os.path.isfile(user_bin) and os.access(user_bin, os.X_OK):
        return user_bin
    system = shutil.which("yt-dlp")
    if system:
        return system
    return None


def _find_ffmpeg():
    return shutil.which("ffmpeg")


def _check_dependencies():
    missing = []
    if not _find_ytdlp():
        missing.append("yt-dlp (pip install yt-dlp)")
    if not _find_ffmpeg():
        missing.append("ffmpeg (sudo apt install ffmpeg)")
    if not os.path.isfile(WHISPER_PATH):
        missing.append(f"whisper-cli ({WHISPER_PATH})")
    if not os.path.isfile(WHISPER_MODEL):
        missing.append(f"whisper model ({WHISPER_MODEL})")
    if missing:
        print("ERROR: Faltan dependencias:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)


def _curl_fetch(url):
    result = subprocess.run(
        [
            "curl", "-s", "-L", "--max-time", "30",
            "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            url,
        ],
        capture_output=True, text=True, timeout=45,
    )
    if result.returncode == 0:
        return result.stdout
    return None


class AudioLinkParser(HTMLParser):
    """Extract audio URLs and RSS feed links from HTML."""

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.audio_urls = []
        self.rss_urls = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "audio":
            src = attrs_dict.get("src", "")
            if src:
                self.audio_urls.append(urljoin(self.base_url, src))
        if tag == "source" and attrs_dict.get("type", "").startswith("audio/"):
            src = attrs_dict.get("src", "")
            if src:
                self.audio_urls.append(urljoin(self.base_url, src))
        if tag == "a":
            href = attrs_dict.get("href", "")
            if href and any(ext in href.lower() for ext in AUDIO_EXTENSIONS):
                self.audio_urls.append(urljoin(self.base_url, href))
        if tag == "link":
            rel = attrs_dict.get("rel", "")
            link_type = attrs_dict.get("type", "")
            href = attrs_dict.get("href", "")
            if href and ("rss" in rel or "rss" in link_type or "atom" in link_type
                         or "application/rss+xml" in link_type):
                self.rss_urls.append(urljoin(self.base_url, href))
        if tag == "enclosure":
            url = attrs_dict.get("url", "")
            enc_type = attrs_dict.get("type", "")
            if url and ("audio" in enc_type or any(ext in url.lower() for ext in AUDIO_EXTENSIONS)):
                self.audio_urls.append(url)
        if tag == "meta":
            prop = attrs_dict.get("property", "") or attrs_dict.get("name", "")
            content = attrs_dict.get("content", "")
            if content and "rss" in prop.lower() and content.startswith("http"):
                self.rss_urls.append(content)


def _parse_rss_for_audio(rss_url, episode_hint=None):
    """Parse an RSS feed and return (audio_url, title, date, show_name)."""
    print(f"  Buscando audio en RSS: {rss_url}")
    content = _curl_fetch(rss_url)
    if not content:
        return None, None, None, None

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None, None, None, None

    channel = root.find(".//channel")
    show_name = ""
    if channel is not None:
        title_el = channel.find("title")
        if title_el is not None and title_el.text:
            show_name = title_el.text.strip()

    items = root.findall(".//item")
    if not items:
        return None, None, None, show_name

    best_item = items[0]
    if episode_hint:
        hint_lower = episode_hint.lower()
        for item in items:
            title_el = item.find("title")
            if title_el is not None and title_el.text and hint_lower in title_el.text.lower():
                best_item = item
                break

    enclosure = best_item.find("enclosure")
    audio_url = None
    if enclosure is not None:
        audio_url = enclosure.get("url")

    title = ""
    title_el = best_item.find("title")
    if title_el is not None and title_el.text:
        title = title_el.text.strip()

    date = ""
    pub_el = best_item.find("pubDate")
    if pub_el is not None and pub_el.text:
        date = pub_el.text.strip()

    return audio_url, title, date, show_name


def strategy_ytdlp(url, tmpdir):
    """Try extracting audio with yt-dlp."""
    ytdlp = _find_ytdlp()
    if not ytdlp:
        return None, {}

    print("  Estrategia 1: yt-dlp...")
    audio_path = os.path.join(tmpdir, "audio.%(ext)s")

    info_result = subprocess.run(
        [ytdlp, "--dump-json", "--skip-download", url],
        capture_output=True, text=True, timeout=60,
    )

    metadata = {}
    if info_result.returncode == 0:
        try:
            info = json.loads(info_result.stdout)
            metadata["title"] = info.get("title", "")
            metadata["date"] = info.get("upload_date", "")
            metadata["description"] = info.get("description", "")
            metadata["show"] = info.get("series", "") or info.get("album", "")
            metadata["duration"] = info.get("duration")
        except json.JSONDecodeError:
            pass

    result = subprocess.run(
        [
            ytdlp,
            "-x", "--audio-format", "mp3",
            "--audio-quality", "5",
            "-o", audio_path,
            "--no-playlist",
            url,
        ],
        capture_output=True, text=True, timeout=600,
    )

    if result.returncode != 0:
        print(f"    yt-dlp falló: {result.stderr.strip()[:200]}")
        return None, metadata

    for f in os.listdir(tmpdir):
        if any(f.endswith(ext) for ext in AUDIO_EXTENSIONS):
            print(f"    Audio descargado: {f}")
            return os.path.join(tmpdir, f), metadata

    return None, metadata


def strategy_page_scrape(url, tmpdir):
    """Scrape the page for audio links or RSS feed URLs."""
    print("  Estrategia 2: scrape de página...")
    html = _curl_fetch(url)
    if not html:
        print("    No se pudo descargar la página")
        return None, {}

    parser = AudioLinkParser(url)
    try:
        parser.feed(html)
    except Exception:
        pass

    # Try direct audio URLs first
    for audio_url in parser.audio_urls:
        print(f"    Encontrado audio directo: {audio_url[:100]}")
        audio_path = _download_audio(audio_url, tmpdir)
        if audio_path:
            return audio_path, {}

    # Try RSS feeds
    for rss_url in parser.rss_urls:
        audio_url, title, date, show = _parse_rss_for_audio(rss_url)
        if audio_url:
            print(f"    Encontrado audio en RSS: {audio_url[:100]}")
            audio_path = _download_audio(audio_url, tmpdir)
            if audio_path:
                metadata = {"title": title or "", "date": date or "", "show": show or ""}
                return audio_path, metadata

    # Look for RSS URL patterns in page text
    rss_patterns = re.findall(r'https?://[^\s"\'<>]+(?:feed|rss|\.xml)[^\s"\'<>]*', html, re.IGNORECASE)
    for rss_url in rss_patterns[:3]:
        audio_url, title, date, show = _parse_rss_for_audio(rss_url)
        if audio_url:
            print(f"    Encontrado audio en RSS (patrón): {audio_url[:100]}")
            audio_path = _download_audio(audio_url, tmpdir)
            if audio_path:
                metadata = {"title": title or "", "date": date or "", "show": show or ""}
                return audio_path, metadata

    print("    No se encontró audio ni RSS en la página")
    return None, {}


def _download_audio(audio_url, tmpdir):
    """Download an audio file from a direct URL."""
    parsed = urlparse(audio_url)
    ext = os.path.splitext(parsed.path)[1] or ".mp3"
    if ext not in AUDIO_EXTENSIONS:
        ext = ".mp3"
    dest = os.path.join(tmpdir, f"episode{ext}")

    result = subprocess.run(
        [
            "curl", "-s", "-L", "--max-time", "300",
            "-H", "User-Agent: Mozilla/5.0",
            "-o", dest,
            audio_url,
        ],
        capture_output=True, timeout=320,
    )

    if result.returncode == 0 and os.path.isfile(dest) and os.path.getsize(dest) > 10000:
        return dest
    return None


def convert_to_wav(audio_path, tmpdir):
    """Convert audio to WAV 16kHz mono for Whisper."""
    wav_path = os.path.join(tmpdir, "episode.wav")
    print("  Convirtiendo a WAV 16kHz mono...")

    result = subprocess.run(
        [
            _find_ffmpeg(),
            "-i", audio_path,
            "-ar", "16000",
            "-ac", "1",
            "-y",
            wav_path,
        ],
        capture_output=True, text=True, timeout=300,
    )

    if result.returncode != 0:
        print(f"    ffmpeg falló: {result.stderr.strip()[:200]}")
        return None

    if not os.path.isfile(wav_path):
        return None

    size_mb = os.path.getsize(wav_path) / (1024 * 1024)
    print(f"    WAV generado: {size_mb:.1f} MB")
    return wav_path


def transcribe_wav(wav_path, lang="auto", model=None):
    """Transcribe a WAV file with whisper-cli."""
    model = model or WHISPER_MODEL
    print(f"  Transcribiendo con Whisper (lang={lang})...")

    file_size = os.path.getsize(wav_path)
    duration_est = file_size / (16000 * 2)
    timeout = max(300, int(duration_est * 1.5))
    print(f"    Duración estimada: {duration_est / 60:.0f} min (timeout: {timeout}s)")

    result = subprocess.run(
        [
            WHISPER_PATH,
            "-m", model,
            "-f", wav_path,
            "-l", lang,
            "--no-timestamps",
            "-nt",
        ],
        capture_output=True, text=True, timeout=timeout,
    )

    if result.returncode != 0:
        print(f"    Whisper falló: {result.stderr.strip()[:200]}")
        return None

    text = result.stdout.strip()
    if not text:
        print("    Whisper no produjo transcripción")
        return None

    print(f"    Transcripción: {len(text)} caracteres")
    return text


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
    for orig, repl in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n'),('ü','u')]:
        slug = slug.replace(orig, repl)
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    if len(slug) > 60:
        slug = slug[:60].rsplit('-', 1)[0]
    return slug


def process_podcast(url, output_dir, lang="auto", model=None):
    """Main pipeline: URL → audio → WAV → transcription → .md"""
    print(f"Procesando podcast: {url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = None
        metadata = {}

        # Strategy 1: yt-dlp
        audio_path, metadata = strategy_ytdlp(url, tmpdir)

        # Strategy 2: page scrape
        if not audio_path:
            audio_path, meta2 = strategy_page_scrape(url, tmpdir)
            if not metadata.get("title"):
                metadata.update(meta2)

        if not audio_path:
            print("ERROR: No se pudo obtener el audio del podcast.")
            print("  Posibles causas:")
            print("  - La plataforma requiere autenticación (Spotify con DRM)")
            print("  - El contenido no es público")
            print("  - La URL no apunta a un episodio específico")
            return None

        wav_path = convert_to_wav(audio_path, tmpdir)
        if not wav_path:
            print("ERROR: No se pudo convertir el audio a WAV")
            return None

        raw_text = transcribe_wav(wav_path, lang, model)
        if not raw_text:
            print("ERROR: La transcripción falló")
            return None

    title = metadata.get("title", "").strip()
    show = metadata.get("show", "").strip()
    description = metadata.get("description", "").strip()

    date_raw = metadata.get("date", "")
    if date_raw and re.match(r'^\d{8}$', date_raw):
        date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    if not title:
        parsed = urlparse(url)
        title = parsed.path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ") or "Podcast sin título"

    transcript = split_into_paragraphs(raw_text)

    slug = slugify(title)
    filename = f"{date}-{slug}.md"

    lines = [date, ""]

    heading = f"# {title}"
    if show:
        heading = f"# {title} — {show}"
    lines += [heading, "", f"**Fuente:** {url}", ""]

    if description:
        desc_lines = []
        for line in description.split('\n'):
            if line.strip().startswith('http') or line.strip().startswith('#'):
                break
            if line.strip():
                desc_lines.append(line.strip())
        if desc_lines:
            lines += ["## Descripción:", "", '\n'.join(desc_lines[:10]), ""]

    lines += ["## Transcripción:", "", transcript, ""]

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"\n-> {output_path}")
    return output_path


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    _check_dependencies()

    url = None
    output_dir = None
    lang = "auto"
    model = None

    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output_dir = args[i + 1]; i += 2
        elif args[i] == "--lang" and i + 1 < len(args):
            lang = args[i + 1]; i += 2
        elif args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]; i += 2
        elif not args[i].startswith("-"):
            url = args[i]; i += 1
        else:
            i += 1

    if not url:
        print("ERROR: indica una URL")
        sys.exit(1)

    if not output_dir:
        print("ERROR: --output es obligatorio")
        sys.exit(1)

    result = process_podcast(url, output_dir, lang, model)
    if result:
        print(f"\nTranscripción guardada en: {result}")
    else:
        print("\nNo se pudo transcribir el podcast.")
        sys.exit(1)


if __name__ == "__main__":
    main()
