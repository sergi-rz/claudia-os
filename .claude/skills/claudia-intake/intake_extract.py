#!/usr/bin/env python3
"""
Claudia OS — Intake Content Extraction
Pre-extrae contenido raw de URLs antes de pasar a Claude para síntesis.

Estrategias:
  - YouTube: delega a extract_subtitles.py (ya existente)
  - Twitter/X: FxTwitter API
  - Web genérica: requests + html.parser

Uso CLI:
    python3 intake_extract.py "https://example.com/article"
    python3 intake_extract.py "https://x.com/user/status/123"
    python3 intake_extract.py "https://youtube.com/watch?v=xyz"
"""

import json
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    sys.exit("Error: 'requests' no está instalado. pip3 install requests")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
YT_SCRIPT = REPO_ROOT / ".claude/skills/claudia-yt-transcript/extract_subtitles.py"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


# --- URL detection ---

def _is_youtube(url):
    host = urlparse(url).hostname or ""
    return any(h in host for h in ("youtube.com", "youtu.be"))


def _is_twitter(url):
    host = urlparse(url).hostname or ""
    return any(h in host for h in ("x.com", "twitter.com", "fxtwitter.com", "vxtwitter.com"))


def _parse_tweet_url(url):
    """Extrae screen_name y tweet_id de una URL de Twitter/X."""
    m = re.search(r"(?:x\.com|twitter\.com|fxtwitter\.com|vxtwitter\.com)/(\w+)/status/(\d+)", url)
    if m:
        return m.group(1), m.group(2)
    return None, None


# --- YouTube extractor ---

def extract_youtube(url):
    """Usa extract_subtitles.py para obtener transcripción."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["python3", str(YT_SCRIPT), url, "--output", tmpdir, "--lang", "es"],
            capture_output=True, text=True, timeout=120,
        )

        # Buscar el .md generado
        md_files = list(Path(tmpdir).glob("*.md"))
        if not md_files:
            # Intentar con inglés como fallback
            result = subprocess.run(
                ["python3", str(YT_SCRIPT), url, "--output", tmpdir, "--lang", "en"],
                capture_output=True, text=True, timeout=120,
            )
            md_files = list(Path(tmpdir).glob("*.md"))

        if not md_files:
            return {
                "url": url,
                "title": None,
                "author": None,
                "content_type": "youtube",
                "text": None,
                "error": f"No se pudo extraer transcripción. stderr: {result.stderr[:500]}",
                "metadata": {},
            }

        content = md_files[0].read_text()

        # Extraer título de la primera línea del .md
        title = None
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
            if line.startswith("**") and "**" in line[2:]:
                title = line.strip("* ")
                break

        return {
            "url": url,
            "title": title,
            "author": None,
            "content_type": "youtube",
            "text": content,
            "metadata": {"filename": md_files[0].name},
        }


# --- Twitter extractor ---

def extract_twitter(url):
    """Usa FxTwitter API para extraer tweet/thread."""
    screen_name, tweet_id = _parse_tweet_url(url)
    if not screen_name or not tweet_id:
        return {
            "url": url, "title": None, "author": None,
            "content_type": "tweet", "text": None,
            "error": "No se pudo parsear la URL de Twitter/X",
            "metadata": {},
        }

    api_url = f"https://api.fxtwitter.com/{screen_name}/status/{tweet_id}"
    try:
        resp = requests.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        # Fallback a syndication API
        return _twitter_fallback(url, screen_name, tweet_id, str(e))

    tweet = data.get("tweet", {})
    text = tweet.get("text", "")
    author_name = tweet.get("author", {}).get("name", screen_name)
    author_handle = tweet.get("author", {}).get("screen_name", screen_name)
    created = tweet.get("created_at", "")
    likes = tweet.get("likes", 0)
    rts = tweet.get("retweets", 0)
    replies = tweet.get("replies", 0)
    views = tweet.get("views", 0)

    # Tweet sin texto: solo contiene una URL (X Article u otro enlace)
    if not text:
        raw_text = tweet.get("raw_text", {}).get("text", "")
        if raw_text.startswith("http"):
            try:
                r = requests.head(raw_text, allow_redirects=True, timeout=10)
                target_url = r.url
            except Exception:
                target_url = raw_text

            # X Article — requiere JS, no es scrapeble con requests
            if "x.com/i/article/" in target_url:
                formatted = (
                    f"**X Article de @{author_handle}** ({author_name}) — {created}\n\n"
                    f"Artículo completo: {target_url}\n"
                    f"Tweet original: {url}\n\n"
                    f"[Likes: {likes} | RTs: {rts} | Replies: {replies} | Views: {views}]"
                )
                return {
                    "url": url,
                    "title": f"X Article de @{author_handle}",
                    "author": f"@{author_handle}",
                    "content_type": "article_x",
                    "text": formatted,
                    "metadata": {"likes": likes, "views": views, "article_url": target_url},
                }

            # Enlace externo — extraer como artículo web
            result = extract_web(target_url)
            result["author"] = f"@{author_handle}"
            result["metadata"] = {**result.get("metadata", {}), "via": url, "likes": likes, "views": views}
            return result

        return {
            "url": url, "title": f"@{author_handle}", "author": f"@{author_handle}",
            "content_type": "tweet", "text": None,
            "error": "Tweet sin contenido de texto extraíble",
            "metadata": {},
        }

    # Detectar si es article (contenido largo sin reply)
    is_article = len(text) > 1000 and not tweet.get("replying_to_status")
    content_type = "article_x" if is_article else "tweet"
    label = "Article" if is_article else "Tweet"

    formatted = (
        f"**{label} de @{author_handle}** ({author_name}) — {created}\n\n"
        f"{text}\n\n"
        f"[Likes: {likes} | RTs: {rts} | Replies: {replies} | Views: {views}]\n"
        f"Fuente: {url}"
    )

    return {
        "url": url,
        "title": f"@{author_handle}: {text[:80]}..." if len(text) > 80 else f"@{author_handle}: {text}",
        "author": f"@{author_handle}",
        "content_type": content_type,
        "text": formatted,
        "metadata": {"likes": likes, "rts": rts, "views": views},
    }


def _twitter_fallback(url, screen_name, tweet_id, original_error):
    """Fallback via syndication API."""
    try:
        synd_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=1"
        resp = requests.get(synd_url, timeout=10)
        if resp.ok:
            data = resp.json()
            text = data.get("text", "")
            user = data.get("user", {})
            return {
                "url": url,
                "title": f"@{user.get('screen_name', screen_name)}: {text[:80]}",
                "author": f"@{user.get('screen_name', screen_name)}",
                "content_type": "tweet",
                "text": text,
                "metadata": {"fallback": "syndication"},
            }
    except Exception:
        pass

    return {
        "url": url, "title": None, "author": screen_name,
        "content_type": "tweet", "text": None,
        "error": f"FxTwitter y syndication fallaron. Original: {original_error}",
        "metadata": {},
    }


# --- Web article extractor ---

class _ArticleParser(HTMLParser):
    """Extrae texto de tags de contenido comunes."""

    CONTENT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "figcaption", "td", "th"}
    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"}

    def __init__(self):
        super().__init__()
        self.title = None
        self.text_parts = []
        self._current_tag = None
        self._skip_depth = 0
        self._in_title = False
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if tag == "title":
            self._in_title = True
        if tag in self.CONTENT_TAGS:
            self._current_tag = tag

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "title":
            self._in_title = False
            self.title = "".join(self._title_parts).strip()
        if tag == self._current_tag:
            self._current_tag = None

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_title:
            self._title_parts.append(data)
        if self._current_tag:
            text = data.strip()
            if text:
                prefix = ""
                if self._current_tag.startswith("h"):
                    level = int(self._current_tag[1])
                    prefix = "#" * level + " "
                elif self._current_tag == "li":
                    prefix = "- "
                elif self._current_tag == "blockquote":
                    prefix = "> "
                self.text_parts.append(f"{prefix}{text}")


def extract_web(url):
    """Extrae contenido de artículo web genérico."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        return {
            "url": url, "title": None, "author": None,
            "content_type": "article", "text": None,
            "error": f"HTTP error: {e}",
            "metadata": {},
        }

    html = resp.text
    parser = _ArticleParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    text = "\n\n".join(parser.text_parts)

    # Si el parsing dio muy poco texto, devolver el raw truncado
    if len(text) < 100:
        # Limpiar HTML tags con regex básico como último recurso
        raw = re.sub(r"<[^>]+>", " ", html)
        raw = re.sub(r"\s+", " ", raw).strip()
        text = raw[:5000] if raw else text

    return {
        "url": url,
        "title": parser.title,
        "author": None,
        "content_type": "article",
        "text": text[:50000] if text else None,  # cap a 50K chars
        "metadata": {"content_length": len(text) if text else 0},
    }


# --- Dispatcher ---

def extract_content(url):
    """Dispatcher principal. Detecta tipo de URL y extrae contenido."""
    if _is_youtube(url):
        return extract_youtube(url)
    elif _is_twitter(url):
        return extract_twitter(url)
    else:
        return extract_web(url)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 intake_extract.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    result = extract_content(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
