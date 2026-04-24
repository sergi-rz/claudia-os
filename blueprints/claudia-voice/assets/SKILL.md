---
name: claudia-voice
description: "Convierte texto a voz con ElevenLabs y lo reproduce por los altavoces. Usar cuando el usuario pida respuesta por voz o cuando el contexto lo haga útil."
scope: addon
---

# Voice — Texto a voz

Convierte texto a voz usando ElevenLabs y lo reproduce localmente. Compatible con macOS (`afplay`), Linux (`mpg123`/`ffplay`/`aplay`) y Windows nativo (`powershell`). WSL requiere configuración de audio adicional.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Uso directo

```bash
.claude/skills/claudia-voice/speak.sh "texto a decir"
echo "texto largo" | .claude/skills/claudia-voice/speak.sh
.claude/skills/claudia-voice/speak.sh --file resumen.txt
```

Límite: 5000 caracteres por llamada. Si el texto es más largo, dividirlo en bloques.

## Uso automático con [voice]

Cuando una respuesta contenga algo que merezca ser dicho en voz alta, envuélvelo en `[voice]texto aquí[/voice]`. Un hook lo detectará y lo reproducirá automáticamente. No hace falta llamar a speak.sh manualmente.

Criterios para usar el tag `[voice]`:
- El usuario pide explícitamente respuesta por voz
- Resultado final de una tarea larga (resumen de lo hecho)
- Información urgente o que requiere atención inmediata
- NO usar en respuestas cortas o conversacionales normales
- NO usar en código, listas técnicas o contenido que no tiene sentido oído
- El texto dentro del tag debe ser natural hablado — sin markdown, sin bullets, sin formateo

## Setup (primera vez)

Esta skill necesita una cuenta de ElevenLabs (plan gratuito: 10.000 caracteres/mes).

1. Crea cuenta en https://elevenlabs.io
2. Ve a Profile → API Keys → copia tu API key
3. Elige una voz en Voices → copia su Voice ID
4. Añade ambos a `user/credentials/.env`:
   ```
   ELEVENLABS_API_KEY=tu_key_aqui
   ELEVENLABS_VOICE_ID=tu_voice_id_aqui
   ```

Opcional: `ELEVENLABS_MODEL` (default: `eleven_turbo_v2_5`) y `ELEVENLABS_VOLUME` (default: `1.0`).

Si usas esta skill fuera de Claudia OS, exporta las variables directamente.

**Requisito adicional:** reproductor de audio según plataforma — macOS: `afplay` (preinstalado); Linux: `mpg123`, `ffplay`, o `aplay`; Windows nativo: PowerShell. WSL requiere configuración de audio adicional.
