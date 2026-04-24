#!/bin/bash
# speak.sh — Convierte texto a voz con ElevenLabs y lo reproduce (macOS/Linux/Windows)
#
# Uso:
#   echo "Hola, soy Claudia" | ./speak.sh
#   ./speak.sh "Hola, soy Claudia"
#   ./speak.sh --file resumen.txt
#
# Variables de entorno requeridas (se leen de user/credentials/.env
# relativo al repo, lo resuelve CLAUDIA_ROOT automáticamente):
#   ELEVENLABS_API_KEY
#   ELEVENLABS_VOICE_ID

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDIA_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_FILE="$CLAUDIA_ROOT/user/credentials/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${ELEVENLABS_API_KEY:-}" ]]; then
  echo "Error: ELEVENLABS_API_KEY no configurada" >&2
  exit 1
fi

if [[ -z "${ELEVENLABS_VOICE_ID:-}" ]]; then
  echo "Error: ELEVENLABS_VOICE_ID no configurada" >&2
  exit 1
fi

MODEL="${ELEVENLABS_MODEL:-eleven_turbo_v2_5}"
VOLUME="${ELEVENLABS_VOLUME:-1.0}"

# Leer texto: argumento, --file, o stdin
if [[ "${1:-}" == "--file" && -n "${2:-}" ]]; then
  TEXT="$(cat "$2")"
elif [[ -n "${1:-}" ]]; then
  TEXT="$1"
elif [[ ! -t 0 ]]; then
  TEXT="$(cat)"
else
  echo "Uso: speak.sh \"texto\" | speak.sh --file archivo.txt | echo \"texto\" | speak.sh" >&2
  exit 1
fi

if [[ -z "$TEXT" ]]; then
  echo "Error: texto vacío" >&2
  exit 1
fi

# Limitar a 5000 caracteres (límite de ElevenLabs por request)
TEXT="${TEXT:0:5000}"

TMP_FILE="/tmp/claudia-voice-$$.mp3"

# Llamar a ElevenLabs API
HTTP_CODE=$(curl -s -w "%{http_code}" -o "$TMP_FILE" \
  -X POST "https://api.elevenlabs.io/v1/text-to-speech/${ELEVENLABS_VOICE_ID}" \
  -H "Accept: audio/mpeg" \
  -H "Content-Type: application/json" \
  -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
  -d "$(jq -n \
    --arg text "$TEXT" \
    --arg model "$MODEL" \
    '{
      text: $text,
      model_id: $model,
      voice_settings: {
        stability: 0.5,
        similarity_boost: 0.75,
        style: 0.0,
        speed: 1.2
      }
    }')")

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "Error: ElevenLabs API respondió con HTTP $HTTP_CODE" >&2
  [[ -f "$TMP_FILE" ]] && cat "$TMP_FILE" >&2 && rm -f "$TMP_FILE"
  exit 1
fi

# Reproducir y limpiar
case "$(uname -s)" in
  Darwin)
    afplay -v "$VOLUME" "$TMP_FILE" ;;
  Linux)
    if   command -v mpg123 &>/dev/null; then mpg123 -q "$TMP_FILE"
    elif command -v ffplay  &>/dev/null; then ffplay -nodisp -autoexit -loglevel quiet "$TMP_FILE"
    elif command -v aplay   &>/dev/null; then aplay "$TMP_FILE"
    else echo "Error: no se encontró reproductor de audio (instala mpg123 o ffplay)" >&2; exit 1
    fi ;;
  MINGW*|CYGWIN*|MSYS*)
    powershell -c "(New-Object Media.SoundPlayer '$TMP_FILE').PlaySync()" ;;
  *)
    echo "Error: plataforma no soportada ($(uname -s))" >&2; exit 1 ;;
esac
rm -f "$TMP_FILE"
