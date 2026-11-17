#!/usr/bin/env python3
"""
Claudia OS — HTTP mínimo para la intake, solo con la librería estándar.

Sustituye a `requests` en los scripts de la intake para que funcionen en una instalación nueva
sin instalar nada (en macOS, el Python de Homebrew ni siquiera deja hacer `pip install` normal).
Imita lo poco de `requests` que se usa: get, head y post con JSON, y una respuesta con
ok, status_code, url, headers, content, text, json() y raise_for_status().
"""

import json as _json
import ssl
import urllib.error
import urllib.request

DEFAULT_USER_AGENT = "claudia-intake/1.0"


def _ssl_context():
    # El Python del instalador oficial de macOS no trae certificados para urllib hasta que se
    # ejecuta «Install Certificates». Si certifi está (va con muchos paquetes), se usa.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_CONTEXT = _ssl_context()


class HTTPError(Exception):
    def __init__(self, response):
        super().__init__(f"{response.status_code} para {response.url}")
        self.response = response


class Response:
    def __init__(self, status_code, url, headers, content):
        self.status_code = status_code
        self.url = url
        self.headers = headers
        self.content = content

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    @property
    def text(self):
        charset = self.headers.get_content_charset() if self.headers else None
        return self.content.decode(charset or "utf-8", errors="replace")

    def json(self):
        return _json.loads(self.content)

    def raise_for_status(self):
        if not self.ok:
            raise HTTPError(self)


def request(method, url, headers=None, timeout=20, json=None, allow_redirects=True):
    """Hace la petición y devuelve un Response. Los errores HTTP (4xx/5xx) no lanzan excepción,
    igual que en requests: hay que mirar .ok o llamar a raise_for_status(). Los de red, sí."""
    headers = dict(headers or {})
    headers.setdefault("User-Agent", DEFAULT_USER_AGENT)
    data = None
    if json is not None:
        data = _json.dumps(json).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    handlers = [urllib.request.HTTPSHandler(context=_CONTEXT)]
    if not allow_redirects:
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        handlers.append(_NoRedirect())
    opener = urllib.request.build_opener(*handlers)

    try:
        with opener.open(req, timeout=timeout) as resp:
            body = b"" if method == "HEAD" else resp.read()
            return Response(resp.status, resp.geturl(), resp.headers, body)
    except urllib.error.HTTPError as e:
        body = e.read() if method != "HEAD" else b""
        return Response(e.code, e.geturl() or url, e.headers, body)


def get(url, **kwargs):
    return request("GET", url, **kwargs)


def head(url, **kwargs):
    return request("HEAD", url, **kwargs)


def post(url, **kwargs):
    return request("POST", url, **kwargs)
