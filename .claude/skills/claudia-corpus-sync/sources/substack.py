"""Substack corpus source: sitemap + HTML→Markdown conversion."""

import json
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError:
    print("ERROR: beautifulsoup4 no está instalado. pip install beautifulsoup4")
    raise


# --- HTML parsing ---

def extract_date(soup):
    script = soup.find("script", type="application/ld+json")
    if script:
        try:
            data = json.loads(script.string)
            date_str = data.get("datePublished", "")
            if date_str:
                return datetime.fromisoformat(date_str).strftime("%Y-%m-%d")
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def extract_title(soup):
    h1 = soup.find("h1", class_="post-title")
    return h1.get_text(strip=True) if h1 else None


def extract_subtitle(soup):
    h3 = soup.find("h3", class_="subtitle")
    return h3.get_text(strip=True) if h3 else None


def slugify(title, date):
    slug = title.lower()
    slug = re.sub(r'[¿¡"«»""\'\'…]', '', slug)
    for src, dst in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n'), ('ü', 'u')]:
        slug = slug.replace(src, dst)
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    if len(slug) > 60:
        slug = slug[:60].rsplit('-', 1)[0]
    return f"{date}-{slug}.md"


def _convert(el):
    if isinstance(el, NavigableString):
        return str(el)
    if not isinstance(el, Tag):
        return ""
    tag = el.name
    if tag in ('script', 'style', 'button', 'form', 'input', 'svg', 'picture'):
        return ""
    el_class = " ".join(el.get("class", []))
    if any(c in el_class for c in [
        'post-ufi', 'like-button', 'image-link', 'image2', 'visibility-check',
        'pencraft', 'can-restack', 'captioned-image-container', 'image-caption',
        'image2-inset', 'youtube-inner',
    ]):
        return ""
    if tag == 'p':
        inner = _children(el)
        return inner.strip() + "\n\n" if inner.strip() else ""
    if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        inner = _children(el).strip()
        return f"{'#' * int(tag[1])} {inner}\n\n" if inner else ""
    if tag == 'blockquote':
        inner = _children(el).strip()
        return '\n'.join(f'> {l}' for l in inner.split('\n')) + "\n\n"
    if tag == 'ul':
        items = []
        for li in el.find_all('li', recursive=False):
            item = re.sub(r'\n{2,}', '\n', _children(li).strip())
            items.append(f"- {item}")
        return '\n'.join(items) + "\n\n"
    if tag == 'ol':
        items = []
        for i, li in enumerate(el.find_all('li', recursive=False), 1):
            item = re.sub(r'\n{2,}', '\n', _children(li).strip())
            items.append(f"{i}. {item}")
        return '\n'.join(items) + "\n\n"
    if tag == 'hr':
        return "* * *\n\n"
    if tag == 'br':
        return "\n"
    if tag in ('strong', 'b'):
        inner = _children(el)
        return f"**{inner.strip()}**" if inner.strip() else ""
    if tag in ('em', 'i'):
        inner = _children(el)
        return f"*{inner.strip()}*" if inner.strip() else ""
    if tag == 'a':
        href = el.get('href', '')
        inner = _children(el).strip()
        return f"[{inner}]({href})" if inner and href else inner
    if tag == 'code':
        return f"`{el.get_text()}`"
    if tag == 'pre':
        code = el.find('code')
        text = code.get_text() if code else el.get_text()
        return f"```\n{text}\n```\n\n"
    return _children(el)


def _children(el):
    return "".join(_convert(c) for c in el.children)


def extract_body(soup):
    body_div = soup.find("div", class_="body markup")
    if not body_div:
        return None
    md = _children(body_div)
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = re.sub(r' +\n', '\n', md)
    return md.strip()


def html_to_corpus_md(html):
    """Convierte HTML de Substack a (filename, md_content). Devuelve None si falla."""
    soup = BeautifulSoup(html, 'html.parser')
    date = extract_date(soup)
    title = extract_title(soup)
    subtitle = extract_subtitle(soup)
    body = extract_body(soup)
    if not all([date, title, body]):
        return None
    lines = [date, "", f"# {title}", ""]
    if subtitle:
        lines += [f"### {subtitle}", ""]
    lines += [body, ""]
    return slugify(title, date), "\n".join(lines)


# --- Sitemap / sync ---

def fetch_sitemap(base_url):
    sitemap_url = base_url.rstrip('/') + '/sitemap.xml'
    req = urllib.request.Request(sitemap_url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ClaudiaBot/1.0)"
    })
    with urllib.request.urlopen(req) as response:
        xml_content = response.read()
    root = ET.fromstring(xml_content)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [loc.text for loc in root.findall("sm:url/sm:loc", ns) if loc.text]


def post_slug(url):
    m = re.match(r"https?://[^/]+/p/([^/?#]+)", url)
    return m.group(1) if m else None


def download_html(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')


def normalize_title(t):
    t = re.sub(r'[^\w\s]', '', t.lower().strip())
    return re.sub(r'\s+', ' ', t)


def existing_corpus(corpus_dir):
    existing = {}
    if not os.path.exists(corpus_dir):
        return existing
    for fn in os.listdir(corpus_dir):
        if not fn.endswith('.md'):
            continue
        with open(os.path.join(corpus_dir, fn), encoding='utf-8') as f:
            lines = f.readlines()
        date = title = None
        for line in lines[:10]:
            line = line.strip()
            if re.match(r'^\d{4}-\d{2}-\d{2}$', line):
                date = line
            elif line.startswith('# '):
                title = line[2:].strip()
                break
        if date and title:
            existing[(date, normalize_title(title))] = fn
    return existing


def sync(config, workspace_root, do_sync):
    base_url = config["url"]
    corpus_dir = os.path.join(workspace_root, config["corpus_dir"])
    excluded = set(config.get("excluded_slugs", []))

    print(f"[substack] Publicación: {base_url}")
    urls = fetch_sitemap(base_url)
    post_urls = {slug: u for u in urls if (slug := post_slug(u)) and slug not in excluded}
    print(f"[substack] Posts en sitemap: {len(post_urls)}")

    existing = existing_corpus(corpus_dir)
    print(f"[substack] En corpus: {len(existing)}")

    missing = []
    for slug, url in sorted(post_urls.items()):
        try:
            html = download_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            date = extract_date(soup)
            title = extract_title(soup)
            if not date or not title:
                continue
            if (date, normalize_title(title)) in existing:
                continue
            missing.append((slug, url, html, date, title))
            time.sleep(0.5)
        except Exception as e:
            print(f"  ERROR descargando {slug}: {e}")

    if not missing:
        print("[substack] Al día.")
        return {"processed": 0, "errors": 0}

    print(f"[substack] Nuevos: {len(missing)}")
    for _, _, _, date, title in missing:
        print(f"  - {title} ({date})")

    if not do_sync:
        return {"processed": 0, "errors": 0, "missing": len(missing)}

    os.makedirs(corpus_dir, exist_ok=True)
    processed = errors = 0
    for slug, url, html, date, title in missing:
        result = html_to_corpus_md(html)
        if result:
            fn, content = result
            with open(os.path.join(corpus_dir, fn), 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  -> {fn}")
            processed += 1
        else:
            print(f"  ERROR procesando: {slug}")
            errors += 1
    return {"processed": processed, "errors": errors}
