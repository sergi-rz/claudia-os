#!/usr/bin/env python3
"""
Claudia OS — Gmail OAuth2 auth flow (loopback).

Usa el flujo oficial de Google para aplicaciones de escritorio ("Installed App",
loopback IP redirect). OOB (out-of-band, copiar código manualmente) fue
desaprobado por Google y deja de funcionar para nuevos clientes.

Flujo:
  1. Este script arranca un servidor HTTP efímero en 127.0.0.1:<puerto-libre>.
  2. Imprime la URL de autorización.
  3. Abres la URL en un navegador (ver notas más abajo si estás en un VPS sin GUI).
  4. Google redirige a 127.0.0.1:<puerto> con el código.
  5. El servidor local captura el código, intercambia por tokens y cierra.

Uso:
    python3 auth.py personal           # autoriza y guarda tokens/personal.json
    python3 auth.py trabajo            # cualquier nombre de cuenta

Opciones:
    --port N        Puerto fijo en vez de uno aleatorio (útil en VPS con túnel SSH).
    --no-browser    No intentar abrir navegador local; solo imprimir la URL.

Headless / VPS:
  Si estás en una máquina sin entorno gráfico, abre un túnel SSH hacia el puerto
  que elijas (ej. 8765):

      ssh -L 8765:127.0.0.1:8765 usuario@tu-servidor

  Y en el servidor lanza:

      python3 auth.py personal --port 8765 --no-browser

  Copia la URL impresa, ábrela en el navegador local — la redirección a
  127.0.0.1:8765 llegará al servidor remoto por el túnel.
"""

import argparse
import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDIA_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
GMAIL_CREDS_DIR = os.path.join(CLAUDIA_ROOT, 'user', 'credentials', 'gmail')
CREDENTIALS_FILE = os.path.join(GMAIL_CREDS_DIR, 'credentials.json')
TOKENS_DIR = os.path.join(GMAIL_CREDS_DIR, 'tokens')


def print_setup_instructions():
    print("=" * 60)
    print("  Gmail — Configuración inicial")
    print("=" * 60)
    print()
    print("Necesitas un fichero credentials.json de Google Cloud.")
    print("Sigue estos pasos:")
    print()
    print("  1. Ve a https://console.cloud.google.com/apis/credentials")
    print("  2. Crea un proyecto (o selecciona uno existente)")
    print("  3. Habilita la API de Gmail (APIs & Services → Library → Gmail API)")
    print("  4. Crea credenciales OAuth 2.0 (Create Credentials → OAuth client ID)")
    print("     - Tipo: Desktop app")
    print("  5. Descarga el JSON y guárdalo como:")
    print(f"     {CREDENTIALS_FILE}")
    print()
    print("Después vuelve a ejecutar este comando.")


def main():
    parser = argparse.ArgumentParser(description='Autoriza una cuenta de Gmail.')
    parser.add_argument('account', help='Nombre de la cuenta (p.ej. personal, trabajo).')
    parser.add_argument('--port', type=int, default=0,
                        help='Puerto fijo para el servidor loopback (0 = aleatorio).')
    parser.add_argument('--no-browser', action='store_true',
                        help='No intentar abrir el navegador automáticamente.')
    args = parser.parse_args()

    account_name = args.account.lower().replace(' ', '_')
    token_path = os.path.join(TOKENS_DIR, f'{account_name}.json')

    os.makedirs(TOKENS_DIR, exist_ok=True)

    if not os.path.exists(CREDENTIALS_FILE):
        print_setup_instructions()
        sys.exit(1)

    print(f"Autorizando cuenta: {account_name}\n")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    creds = flow.run_local_server(
        host='127.0.0.1',
        port=args.port,
        open_browser=not args.no_browser,
        authorization_prompt_message=(
            'Abre esta URL en un navegador para autorizar la cuenta:\n\n  {url}\n'
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
