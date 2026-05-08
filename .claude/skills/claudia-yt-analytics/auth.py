#!/usr/bin/env python3
"""
Claudia OS — YouTube OAuth2 auth flow (loopback).

Flujo oficial de Google para aplicaciones de escritorio (loopback IP redirect).
Solo lectura: youtube.readonly + yt-analytics.readonly.

Uso:
    python3 auth.py mi-canal
    python3 auth.py mi-canal --port 8766 --no-browser

Headless / VPS:
  Si estás en una máquina sin entorno gráfico, abre un túnel SSH:

      ssh -L 8766:127.0.0.1:8766 usuario@tu-servidor

  Y en el servidor:

      python3 auth.py mi-canal --port 8766 --no-browser

  Copia la URL impresa, ábrela en el navegador local.
"""

import argparse
import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/yt-analytics.readonly',
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDIA_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
YT_CREDS_DIR = os.path.join(CLAUDIA_ROOT, 'user', 'credentials', 'youtube')
CREDENTIALS_FILE = os.path.join(YT_CREDS_DIR, 'credentials.json')
GMAIL_CREDENTIALS_FILE = os.path.join(CLAUDIA_ROOT, 'user', 'credentials', 'gmail', 'credentials.json')
TOKENS_DIR = os.path.join(YT_CREDS_DIR, 'tokens')


def print_setup_instructions():
    print("=" * 60)
    print("  YouTube Analytics — Configuración inicial")
    print("=" * 60)
    print()
    print("Necesitas un fichero credentials.json de Google Cloud.")
    print()
    print("Si ya tienes uno para Gmail (user/credentials/gmail/credentials.json),")
    print("puedes reutilizar el mismo proyecto de Google Cloud:")
    print("  1. Ve a https://console.cloud.google.com/apis/library")
    print("  2. Habilita: YouTube Data API v3")
    print("  3. Habilita: YouTube Analytics API")
    print("  4. Copia tu credentials.json existente:")
    print(f"     cp user/credentials/gmail/credentials.json {CREDENTIALS_FILE}")
    print()
    print("Si no tienes proyecto de Google Cloud:")
    print("  1. Ve a https://console.cloud.google.com/apis/credentials")
    print("  2. Crea un proyecto nuevo")
    print("  3. Habilita: YouTube Data API v3 y YouTube Analytics API")
    print("  4. Configura pantalla de consentimiento OAuth (External)")
    print("     - Añade scopes: youtube.readonly, yt-analytics.readonly")
    print("  5. Crea credenciales OAuth 2.0 (tipo: Desktop app)")
    print("  6. Descarga el JSON y guárdalo como:")
    print(f"     {CREDENTIALS_FILE}")
    print()
    print("Después vuelve a ejecutar este comando.")


def find_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        return CREDENTIALS_FILE
    if os.path.exists(GMAIL_CREDENTIALS_FILE):
        print(f"Usando credentials.json de Gmail: {GMAIL_CREDENTIALS_FILE}")
        print("(Asegúrate de que YouTube Data API v3 y YouTube Analytics API")
        print("estén habilitadas en ese mismo proyecto de Google Cloud.)\n")
        return GMAIL_CREDENTIALS_FILE
    return None


def main():
    parser = argparse.ArgumentParser(description='Autoriza un canal de YouTube.')
    parser.add_argument('channel', help='Nombre del canal (p.ej. mi-canal, trabajo).')
    parser.add_argument('--port', type=int, default=0,
                        help='Puerto fijo para el servidor loopback (0 = aleatorio).')
    parser.add_argument('--no-browser', action='store_true',
                        help='No intentar abrir el navegador automáticamente.')
    args = parser.parse_args()

    channel_name = args.channel.lower().replace(' ', '_')
    token_path = os.path.join(TOKENS_DIR, f'{channel_name}.json')

    os.makedirs(TOKENS_DIR, exist_ok=True)

    creds_file = find_credentials()
    if not creds_file:
        print_setup_instructions()
        sys.exit(1)

    print(f"Autorizando canal: {channel_name}\n")

    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)

    creds = flow.run_local_server(
        host='127.0.0.1',
        port=args.port,
        open_browser=not args.no_browser,
        authorization_prompt_message=(
            'Abre esta URL en un navegador para autorizar el canal:\n\n  {url}\n'
        ),
        success_message=(
            'Autorización correcta. Ya puedes cerrar esta pestaña del navegador.'
        ),
    )

    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes) if creds.scopes else SCOPES,
    }
    with open(token_path, 'w') as f:
        json.dump(token_data, f, indent=2)

    print(f"\nToken guardado en: {token_path}")


if __name__ == '__main__':
    main()
