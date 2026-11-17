#!/usr/bin/env python3
"""
Claudia OS — La Sala del Consejo (panel visual del Council).

Registra una sesión del Council voz a voz y la sirve en una página local donde se ve la mesa:
quién se sienta, quién está hablando, lo que dice cada uno (con sus citas) y la síntesis.
Solo librería estándar.

Uso (lo lanza el agente mientras delibera):
    python3 council_live.py serve [--port 8787] [--host 127.0.0.1]   # arranca el panel
    python3 council_live.py start --question "..." --members '<json>'  # abre sesión, imprime el id
    python3 council_live.py voice --member "Nombre" --headline "su postura en una línea" --file voz.md
    python3 council_live.py synthesis --file sintesis.json             # {acuerdo, tension, recomendacion}
    python3 council_live.py replies                                    # abre la ronda de réplicas (última sesión)
    python3 council_live.py voice --member "Nombre" --to "Otro" --type rebate --file replica.md
    # Fuentes citadas (repetible): --source "Título|AAAA-MM-DD|https://..."
    # Síntesis con opciones (preguntas abiertas): {"recomendacion": "...", "opciones": [
    #   {"titulo": "...", "detalle": "...", "apoyan": ["Nombre"], "pegas": ["Otro"]}]}
    python3 council_live.py synthesis --file sintesis2.json            # síntesis tras las réplicas
    python3 council_live.py list                                       # sesiones guardadas

`--members` es una lista JSON: [{"name": "El Escéptico", "kind": "rol", "why": "..."},
{"name": "Autor", "kind": "real", "entries": 45}, {"name": "Otra", "kind": "inferida"}].
Las fotos se buscan en user/config/mentor-photos/<id-del-mentor>.(jpg|jpeg|png|webp), con el id de
user/config/mentors.json. Sin foto, el panel pinta las iniciales.
"""

import argparse
import json
import mimetypes
import re
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent.parent
SESSIONS = REPO_ROOT / "user" / "data" / "council"
PHOTOS = REPO_ROOT / "user" / "config" / "mentor-photos"
MENTORS = REPO_ROOT / "user" / "config" / "mentors.json"
CURRENT = SESSIONS / "_current"
PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")
THEMES = HERE / "themes"                                   # temas que trae la skill
USER_THEMES = HERE.parent / "user" / "council-themes"      # temas del usuario (no los toca /claudia-update)
SETTINGS = REPO_ROOT / "user" / "config" / "settings.json"
STATIC = {"/base.css": "text/css; charset=utf-8", "/council.js": "text/javascript; charset=utf-8"}
THEME_FILES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
               ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml", ".woff2": "font/woff2"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read_text(args):
    if getattr(args, "file", None):
        return Path(args.file).read_text(encoding="utf-8")
    return args.text or ""


def _mentor_ids():
    try:
        return {m["name"]: m["id"] for m in json.loads(MENTORS.read_text())["mentors"]}
    except Exception:
        return {}


def _mentor_info():
    try:
        return {m["name"]: m for m in json.loads(MENTORS.read_text())["mentors"]}
    except Exception:
        return {}


def _photo_for(name, ids):
    mid = ids.get(name)
    if not mid:
        return None
    for ext in PHOTO_EXT:
        if (PHOTOS / f"{mid}{ext}").exists():
            return f"{mid}{ext}"
    return None


def _current_path():
    if not CURRENT.exists():
        sys.exit("No hay ninguna sesión abierta. Empieza con: council_live.py start ...")
    return SESSIONS / f"{CURRENT.read_text().strip()}.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)  # escritura atómica: el panel nunca lee un JSON a medias


def cmd_start(args):
    members = json.loads(args.members)
    ids, info = _mentor_ids(), _mentor_info()
    for m in members:
        m.setdefault("kind", "rol")
        if m["kind"] in ("real", "inferida"):
            m["photo"] = _photo_for(m["name"], ids)
        if m["name"] in info and info[m["name"]].get("description"):
            m.setdefault("description", info[m["name"]]["description"])
    SESSIONS.mkdir(parents=True, exist_ok=True)
    sid = datetime.now().strftime("%Y%m%d-%H%M%S")
    _save(SESSIONS / f"{sid}.json", {
        "id": sid, "question": args.question, "created_at": _now(),
        "members": members, "voices": [], "synthesis": None, "status": "deliberando", "round": 1,
    })
    CURRENT.write_text(sid)
    print(sid)


def cmd_voice(args):
    path = _current_path()
    data = _load(path)
    names = [m["name"] for m in data["members"]]
    for who in [args.member] + ([args.to] if args.to else []):
        if who not in names:
            sys.exit(f"'{who}' no está en la mesa: {', '.join(names)}")
    rnd = data.get("round", 1)
    voice = {"member": args.member, "text": _read_text(args).strip(), "at": _now(), "round": rnd}
    if args.headline:
        voice["headline"] = args.headline.strip()
    if args.type:
        if not args.to:
            sys.exit("--type solo tiene sentido en una réplica, con --to.")
        voice["type"] = args.type
    if args.source:
        voice["sources"] = []
        for raw in args.source:
            parts = [x.strip() for x in raw.split("|")]
            if len(parts) != 3:
                sys.exit(f"--source lleva 'Título|AAAA-MM-DD|url': {raw}")
            voice["sources"].append({"title": parts[0], "date": parts[1], "url": parts[2]})
    if args.to:
        voice["to"] = args.to
    data["voices"].append(voice)
    _save(path, data)
    n = sum(1 for v in data["voices"] if v.get("round", 1) == rnd)
    print(f"{'Réplica' if rnd == 2 else 'Voz'} de {args.member} añadida ({n}{'' if rnd == 2 else f'/{len(names)}'}).")


def cmd_synthesis(args):
    path = _current_path()
    data = _load(path)
    raw = _read_text(args)
    try:
        synth = json.loads(raw)
    except json.JSONDecodeError:
        synth = {"recomendacion": raw.strip()}
    names = {m["name"] for m in data["members"]}
    for op in synth.get("opciones", []) or []:
        for who in (op.get("apoyan", []) or []) + (op.get("pegas", []) or []):
            if who not in names:
                sys.exit(f"Opción «{op.get('titulo')}»: '{who}' no está en la mesa.")
    data["synthesis2" if data.get("round") == 2 else "synthesis"] = synth
    data["status"] = "cerrado"
    data["closed_at"] = _now()
    _save(path, data)
    CURRENT.unlink(missing_ok=True)
    print("Síntesis guardada. Sesión cerrada.")


def cmd_replies(args):
    """Reabre una sesión cerrada para la ronda de réplicas (por defecto, la última)."""
    sid = args.session
    if not sid:
        files = sorted(SESSIONS.glob("2*.json"), reverse=True)
        if not files:
            sys.exit("No hay sesiones.")
        sid = files[0].stem
    path = SESSIONS / f"{sid}.json"
    data = _load(path)
    if not data.get("synthesis"):
        sys.exit("La primera ronda aún no tiene síntesis: ciérrala antes de abrir las réplicas.")
    data["round"] = 2
    data["status"] = "deliberando"
    _save(path, data)
    CURRENT.write_text(sid)
    print(f"Ronda de réplicas abierta en {sid}.")


def cmd_list(_args):
    for p in sorted(SESSIONS.glob("*.json"), reverse=True)[:20]:
        d = _load(p)
        r2 = sum(1 for v in d["voices"] if v.get("round") == 2)
        print(f"{d['id']}  [{d['status']}]  {d['question'][:70]}" + (f"  ({r2} réplicas)" if r2 else ""))


def _theme_dir(name):
    """El tema del usuario manda sobre el de la skill si se llaman igual."""
    for base in (USER_THEMES, THEMES):
        d = base / name
        if (d / "theme.css").exists():
            return d
    return None


def _themes_index():
    seen, out = set(), []
    for base, source in ((USER_THEMES, "usuario"), (THEMES, "skill")):
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            if d.name in seen or not (d / "theme.css").exists():
                continue
            seen.add(d.name)
            try:
                label = json.loads((d / "theme.json").read_text()).get("label", d.name)
            except Exception:
                label = d.name
            out.append({"name": d.name, "label": label + (" (tuyo)" if source == "usuario" else ""), "source": source})
    return out


def _default_theme():
    try:
        return json.loads(SETTINGS.read_text()).get("skill_council", {}).get("theme") or "arturo"
    except Exception:
        return "arturo"


def _sessions_index():
    out = []
    for p in sorted(SESSIONS.glob("*.json"), reverse=True)[:50]:
        try:
            d = _load(p)
            out.append({"id": d["id"], "question": d["question"], "status": d["status"]})
        except Exception:
            continue
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path in STATIC:
            return self._send(200, (HERE / path.lstrip("/")).read_bytes(), STATIC[path])
        if path == "/api/sessions":
            return self._send(200, _sessions_index())
        if path == "/api/themes":
            return self._send(200, _themes_index())
        if path == "/api/config":
            return self._send(200, {"default_theme": _default_theme()})
        m = re.fullmatch(r"/themes/([\w-]+)/([\w.-]+)", path)
        if m:
            d = _theme_dir(m.group(1))
            ext = Path(m.group(2)).suffix.lower()
            f = d / m.group(2) if d else None
            if f and ext in THEME_FILES and f.is_file() and f.resolve().parent == d.resolve():
                return self._send(200, f.read_bytes(), THEME_FILES[ext])
            return self._send(404, {"error": "no encontrado"})
        m = re.fullmatch(r"/api/session/([\w-]+)", path)
        if m:
            sid = m.group(1)
            if sid == "latest":
                idx = _sessions_index()
                if not idx:
                    return self._send(404, {"error": "sin sesiones"})
                sid = idx[0]["id"]
            f = SESSIONS / f"{sid}.json"
            return self._send(200, f.read_bytes()) if f.exists() else self._send(404, {"error": "no existe"})
        m = re.fullmatch(r"/photos/([\w.-]+)", path)
        if m and m.group(1).lower().endswith(PHOTO_EXT):
            f = PHOTOS / m.group(1)
            if f.exists():
                return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "image/jpeg")
        return self._send(404, {"error": "no encontrado"})


def cmd_serve(args):
    SESSIONS.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Panel del Council en http://{args.host}:{args.port}  (Ctrl+C para parar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    p = argparse.ArgumentParser(description="Panel del Council")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8787); s.add_argument("--host", default="127.0.0.1")
    s = sub.add_parser("start"); s.add_argument("--question", required=True); s.add_argument("--members", required=True)
    s = sub.add_parser("voice"); s.add_argument("--member", required=True); s.add_argument("--to"); s.add_argument("--headline")
    s.add_argument("--type", choices=["rebate", "completa", "matiza"], help="Réplica: qué hace con lo que dijo el otro")
    s.add_argument("--source", action="append", help="Fuente citada: 'Título|AAAA-MM-DD|url' (repetible)")
    s.add_argument("--file"); s.add_argument("--text")
    s = sub.add_parser("synthesis"); s.add_argument("--file"); s.add_argument("--text")
    s = sub.add_parser("replies"); s.add_argument("--session")
    sub.add_parser("list")
    args = p.parse_args()
    {"serve": cmd_serve, "start": cmd_start, "voice": cmd_voice,
     "synthesis": cmd_synthesis, "replies": cmd_replies, "list": cmd_list}[args.cmd](args)


if __name__ == "__main__":
    main()
