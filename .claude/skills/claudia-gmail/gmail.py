#!/usr/bin/env python3
"""
Claudia OS — Gmail tool
Leer, buscar, organizar, crear borradores y enviar correos.

Uso:
    python3 gmail.py --account personal --action list [--max 20] [--unread]
    python3 gmail.py --account personal --action read --id <message_id>
    python3 gmail.py --account personal --action search --query "from:juan asunto:factura"
    python3 gmail.py --account personal --action draft --to "juan@example.com" --subject "Re: factura" --body "Hola Juan..."
    python3 gmail.py --account personal --action send --to "juan@example.com" --subject "Asunto" --body "Texto" [--html-body "<h1>HTML</h1>"]
    python3 gmail.py --account personal --action archive --id <message_id>
    python3 gmail.py --account personal --action label --id <message_id> --label "Clientes"
    python3 gmail.py --account personal --action accounts  # listar cuentas configuradas
"""

import argparse
import base64
import json
import os
import re
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDIA_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
GMAIL_CREDS_DIR = os.path.join(CLAUDIA_ROOT, 'user', 'credentials', 'gmail')
TOKENS_DIR = os.path.join(GMAIL_CREDS_DIR, 'tokens')
CREDENTIALS_FILE = os.path.join(GMAIL_CREDS_DIR, 'credentials.json')

SETTINGS_FILE = os.path.join(CLAUDIA_ROOT, 'user', 'config', 'settings.json')
CONTACT_ALIASES = {}
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE) as f:
            CONTACT_ALIASES = json.load(f).get('calendar_aliases', {})
    except (json.JSONDecodeError, OSError):
        pass


def resolve_sender(from_header):
    """Reemplaza la dirección de email por su alias si existe."""
    if not from_header or not CONTACT_ALIASES:
        return from_header
    # Extraer email del header "Nombre <email@example.com>" o "email@example.com"
    match = re.search(r'<([^>]+)>', from_header)
    email = match.group(1).lower() if match else from_header.strip().lower()
    for key, alias in CONTACT_ALIASES.items():
        if key.lower() == email:
            return alias
    return from_header


def load_credentials(account_name):
    token_path = os.path.join(TOKENS_DIR, f'{account_name}.json')
    if not os.path.exists(token_path):
        print(json.dumps({'error': f"No hay token para la cuenta '{account_name}'. Ejecuta auth.py primero."}))
        sys.exit(1)

    # Sin forzar scopes: se usan los que el token ya tiene. Si el token es compartido con otras
    # APIs de Google (Calendar, Drive), refrescarlo solo con el scope de Gmail y guardarlo
    # le quitaría los demás permisos.
    creds = Credentials.from_authorized_user_file(token_path)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            print(json.dumps({'error': f"Token revocado o expirado para '{account_name}'. Ejecuta: python3 auth.py {account_name}"}))
            sys.exit(1)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

    return creds


def get_service(account_name):
    creds = load_credentials(account_name)
    return build('gmail', 'v1', credentials=creds)


def list_accounts():
    if not os.path.exists(TOKENS_DIR):
        return []
    return [f.replace('.json', '') for f in os.listdir(TOKENS_DIR) if f.endswith('.json')]


def action_accounts():
    accounts = list_accounts()
    print(json.dumps({'accounts': accounts}))


def parse_message(msg, full=False):
    # Los nombres de cabecera no distinguen mayúsculas: hay remitentes que mandan «Message-Id».
    headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
    result = {
        'id': msg['id'],
        'thread_id': msg.get('threadId', ''),
        'from': resolve_sender(headers.get('from', '')),
        'subject': headers.get('subject', '(sin asunto)'),
        'date': headers.get('date', ''),
        'labels': msg.get('labelIds', []),
        'snippet': msg.get('snippet', ''),
    }
    if full:
        result['message_id_header'] = headers.get('message-id', '')
        result['to'] = headers.get('to', '')
        result['body'] = extract_body(msg.get('payload', {}))
    return result


def _html_to_text(html):
    """Convert HTML to plain text using stdlib html.parser."""
    from html.parser import HTMLParser
    import html as html_module

    class _TextExtractor(HTMLParser):
        SKIP_TAGS = {'style', 'script', 'head'}
        BLOCK_TAGS = {'p', 'br', 'div', 'tr', 'li', 'h1', 'h2', 'h3', 'h4', 'blockquote'}

        def __init__(self):
            super().__init__()
            self.parts = []
            self._skip = 0

        def handle_starttag(self, tag, attrs):
            if tag in self.SKIP_TAGS:
                self._skip += 1
            if tag in self.BLOCK_TAGS:
                self.parts.append('\n')

        def handle_endtag(self, tag):
            if tag in self.SKIP_TAGS:
                self._skip = max(0, self._skip - 1)
            if tag in self.BLOCK_TAGS:
                self.parts.append('\n')

        def handle_data(self, data):
            if not self._skip:
                self.parts.append(data)

    extractor = _TextExtractor()
    extractor.feed(html_module.unescape(html))
    text = ''.join(extractor.parts)
    # Strip invisible chars (U+200C zero-width non-joiner and similar)
    text = re.sub(r'[​‌‍⁠﻿​-‏﻿]+', '', text)
    # Drop whitespace-only lines, then collapse multiple blanks to one
    lines = [l.rstrip() for l in text.splitlines()]
    lines = [l for l in lines if l.strip()]
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _is_clean_plaintext(text):
    """Return True if text/plain looks like real content, not HTML noise."""
    invisible = len(re.findall(r'[​‌‍]', text))
    if invisible > 20:
        return False
    if re.search(r'font-family|mso-line-height|@media|\.ExternalClass', text):
        return False
    return True


def extract_body(payload):
    """Extrae el texto del cuerpo del mensaje. Prefiere text/plain limpio; si no, parsea text/html."""
    mime = payload.get('mimeType', '')

    if mime == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            text = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            if _is_clean_plaintext(text):
                return text

    if mime == 'text/html':
        data = payload.get('body', {}).get('data', '')
        if data:
            html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            return _html_to_text(html)

    # For multipart, try html first (better quality), then plain
    html_part = plain_part = None
    for part in payload.get('parts', []):
        if part.get('mimeType') == 'text/html':
            html_part = part
        elif part.get('mimeType') == 'text/plain':
            plain_part = part

    if html_part:
        result = extract_body(html_part)
        if result:
            return result
    if plain_part:
        result = extract_body(plain_part)
        if result:
            return result

    for part in payload.get('parts', []):
        if part.get('mimeType') not in ('text/html', 'text/plain'):
            body = extract_body(part)
            if body:
                return body

    return ''


def action_list(service, max_results=20, unread_only=False):
    query = 'is:unread' if unread_only else ''
    result = service.users().messages().list(
        userId='me', maxResults=max_results, q=query, labelIds=['INBOX']
    ).execute()

    messages = result.get('messages', [])
    items = []
    for m in messages:
        msg = service.users().messages().get(
            userId='me', id=m['id'], format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()
        items.append(parse_message(msg))

    print(json.dumps({'messages': items, 'count': len(items)}, ensure_ascii=False))


def action_read(service, message_id):
    msg = service.users().messages().get(
        userId='me', id=message_id, format='full'
    ).execute()
    print(json.dumps(parse_message(msg, full=True), ensure_ascii=False))


def action_search(service, query, max_results=20):
    result = service.users().messages().list(
        userId='me', maxResults=max_results, q=query
    ).execute()

    messages = result.get('messages', [])
    items = []
    for m in messages:
        msg = service.users().messages().get(
            userId='me', id=m['id'], format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()
        items.append(parse_message(msg))

    print(json.dumps({'messages': items, 'count': len(items), 'query': query}, ensure_ascii=False))


def get_send_as(service):
    """Direcciones 'Enviar como' de la cuenta.

    Devuelve None si el token no tiene scope para leer ajustes (gmail.settings.basic).
    En ese caso no se puede validar el remitente, pero sí fijarlo.
    """
    try:
        res = service.users().settings().sendAs().list(userId='me').execute()
    except HttpError as e:
        if e.resp.status in (401, 403):
            return None
        raise
    return [{
        'email': a.get('sendAsEmail', ''),
        'nombre': a.get('displayName', ''),
        'predeterminada': a.get('isDefault', False),
        'principal': a.get('isPrimary', False),
        # Los alias verificados vienen como 'accepted'. La cuenta principal no trae el campo.
        'verificada': a.get('verificationStatus', 'accepted') in ('accepted', ''),
    } for a in res.get('sendAs', [])]


def apply_from(mime, service, from_addr):
    """Fija la cabecera From. Valida contra los alias verificados si el scope lo permite.

    Sin --from, Gmail usa la dirección predeterminada de 'Enviar como' de la cuenta.
    """
    if not from_addr:
        return '(predeterminada de la cuenta)'

    match = re.search(r'<([^>]+)>', from_addr)
    email = (match.group(1) if match else from_addr).strip().lower()

    aliases = get_send_as(service)
    if aliases is None:
        # Sin scope de ajustes no se puede comprobar. Gmail rechazará el envío si no vale.
        mime['from'] = from_addr
        return from_addr + ' (sin verificar: falta scope gmail.settings.basic)'

    usables = [a['email'].lower() for a in aliases if a['verificada'] or a['principal']]
    if email not in usables:
        print(json.dumps({
            'error': f"'{email}' no es una dirección 'Enviar como' verificada en esta cuenta",
            'disponibles': usables,
            'ayuda': 'Gmail → Configuración → Cuentas e importación → Enviar como',
        }, ensure_ascii=False))
        sys.exit(1)

    mime['from'] = from_addr
    return from_addr


def action_sendas(service):
    """Lista las direcciones desde las que puede enviar esta cuenta."""
    aliases = get_send_as(service)
    if aliases is None:
        print(json.dumps({
            'error': 'el token de esta cuenta no tiene scope para leer ajustes',
            'scope_necesario': 'https://www.googleapis.com/auth/gmail.settings.basic',
            'ayuda': 'Reautoriza la cuenta con auth.py para poder listar y validar remitentes',
        }, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps({'send_as': aliases}, ensure_ascii=False))


def action_draft(service, to, subject, body, html_body=None, reply_to=None, thread_id=None, from_addr=None):
    """Crea un borrador. Nunca envía."""
    if html_body:
        mime = MIMEMultipart('alternative')
        mime.attach(MIMEText(body, 'plain'))
        mime.attach(MIMEText(html_body, 'html'))
    else:
        mime = MIMEText(body)
    mime['to'] = to
    mime['subject'] = subject
    remitente = apply_from(mime, service, from_addr)
    if reply_to:
        mime['In-Reply-To'] = reply_to
        mime['References'] = reply_to

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    message = {'raw': raw}
    if thread_id:
        message['threadId'] = thread_id

    draft = service.users().drafts().create(
        userId='me', body={'message': message}
    ).execute()

    print(json.dumps({
        'draft_id': draft['id'],
        'from': remitente,
        'to': to,
        'subject': subject,
        'thread_id': thread_id or '',
        'status': 'borrador creado (no enviado)',
    }, ensure_ascii=False))


def action_send(service, to, subject, body, html_body=None, reply_to=None, thread_id=None, from_addr=None):
    """Envía un correo. Soporta HTML opcional."""
    if html_body:
        mime = MIMEMultipart('alternative')
        mime.attach(MIMEText(body, 'plain'))
        mime.attach(MIMEText(html_body, 'html'))
    else:
        mime = MIMEText(body)
    mime['to'] = to
    mime['subject'] = subject
    remitente = apply_from(mime, service, from_addr)
    if reply_to:
        mime['In-Reply-To'] = reply_to
        mime['References'] = reply_to

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    message = {'raw': raw}
    if thread_id:
        message['threadId'] = thread_id

    sent = service.users().messages().send(userId='me', body=message).execute()
    print(json.dumps({
        'message_id': sent['id'],
        'from': remitente,
        'to': to,
        'subject': subject,
        'status': 'enviado',
    }, ensure_ascii=False))


def action_archive(service, message_id):
    service.users().messages().modify(
        userId='me', id=message_id,
        body={'removeLabelIds': ['INBOX']}
    ).execute()
    print(json.dumps({'status': 'archivado', 'id': message_id}))


def action_label(service, message_id, label_name):
    # Buscar o crear la etiqueta
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    label = next((l for l in labels if l['name'].lower() == label_name.lower()), None)

    if not label:
        label = service.users().labels().create(
            userId='me', body={'name': label_name}
        ).execute()

    service.users().messages().modify(
        userId='me', id=message_id,
        body={'addLabelIds': [label['id']]}
    ).execute()
    print(json.dumps({'status': 'etiquetado', 'id': message_id, 'label': label_name}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', required=False, help='Nombre de la cuenta (ej: personal)')
    parser.add_argument('--action', required=True,
                        choices=['list', 'read', 'search', 'draft', 'send', 'archive', 'label',
                                 'accounts', 'sendas'])
    parser.add_argument('--max', type=int, default=20)
    parser.add_argument('--unread', action='store_true')
    parser.add_argument('--id', help='ID del mensaje')
    parser.add_argument('--query', help='Query de búsqueda')
    parser.add_argument('--to', help='Destinatario del borrador')
    parser.add_argument('--subject', help='Asunto del borrador')
    parser.add_argument('--body', help='Cuerpo del borrador')
    parser.add_argument('--reply-to', help='Message-ID al que se responde')
    parser.add_argument('--thread-id', help='Thread ID para vincular el borrador al hilo')
    parser.add_argument('--html-body', help='Cuerpo HTML del correo (para draft y send); --body queda como alternativa en texto')
    parser.add_argument('--label', help='Nombre de la etiqueta')
    parser.add_argument('--from', dest='from_addr',
                        help='Remitente ("Nombre <a@b.com>" o "a@b.com"). Debe ser una dirección '
                             '"Enviar como" verificada. Sin esto se usa la predeterminada de la cuenta.')
    args = parser.parse_args()

    if args.action == 'accounts':
        action_accounts()
        return

    if not args.account:
        print(json.dumps({'error': '--account es obligatorio'}))
        sys.exit(1)

    try:
        service = get_service(args.account)

        if args.action == 'sendas':
            action_sendas(service)
        elif args.action == 'list':
            action_list(service, args.max, args.unread)
        elif args.action == 'read':
            if not args.id:
                print(json.dumps({'error': '--id es obligatorio para read'}))
                sys.exit(1)
            action_read(service, args.id)
        elif args.action == 'search':
            if not args.query:
                print(json.dumps({'error': '--query es obligatorio para search'}))
                sys.exit(1)
            action_search(service, args.query, args.max)
        elif args.action == 'draft':
            if not all([args.to, args.subject, args.body]):
                print(json.dumps({'error': '--to, --subject y --body son obligatorios para draft'}))
                sys.exit(1)
            action_draft(service, args.to, args.subject, args.body, html_body=args.html_body,
                         reply_to=args.reply_to, thread_id=args.thread_id, from_addr=args.from_addr)
        elif args.action == 'send':
            if not all([args.to, args.subject, args.body]):
                print(json.dumps({'error': '--to, --subject y --body son obligatorios para send'}))
                sys.exit(1)
            action_send(service, args.to, args.subject, args.body,
                        html_body=args.html_body, reply_to=args.reply_to, thread_id=args.thread_id,
                        from_addr=args.from_addr)
        elif args.action == 'archive':
            if not args.id:
                print(json.dumps({'error': '--id es obligatorio para archive'}))
                sys.exit(1)
            action_archive(service, args.id)
        elif args.action == 'label':
            if not args.id or not args.label:
                print(json.dumps({'error': '--id y --label son obligatorios para label'}))
                sys.exit(1)
            action_label(service, args.id, args.label)

    except HttpError as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
