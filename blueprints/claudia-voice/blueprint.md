---
name: claudia-voice
version: 0.1.0
scope: addon
toca: .claude/skills/claudia-voice/, .claude/hooks/voice-response.sh, .claude/hooks/voice-welcome.sh, user/credentials/.env
reversibilidad: rm -rf .claude/skills/claudia-voice/ .claude/hooks/voice-response.sh .claude/hooks/voice-welcome.sh
riesgo: bajo — crea ficheros nuevos y añade variables al .env, no modifica nada existente
assets:
  - source: assets/SKILL.md
    target: .claude/skills/claudia-voice/SKILL.md
  - source: assets/speak.sh
    target: .claude/skills/claudia-voice/speak.sh
    mode: "0755"
  - source: assets/voice-response.sh
    target: .claude/hooks/voice-response.sh
    mode: "0755"
  - source: assets/voice-welcome.sh
    target: .claude/hooks/voice-welcome.sh
    mode: "0755"
---

# Blueprint: claudia-voice

Instala una skill de texto a voz que convierte respuestas de Claudia en audio usando ElevenLabs y las reproduce por los altavoces del equipo. Incluye dos hooks opcionales: uno que reproduce automáticamente texto marcado con `[voice]...[/voice]` en las respuestas, y otro que saluda al usuario al iniciar sesión.

Compatible con macOS, Linux y Windows nativo.

---

## Paso 1 — Metadatos

Ver frontmatter arriba.

---

## Paso 2 — Discovery

Antes de proponer nada al usuario, lee y toma nota. **No actúes — solo observa.**

1. **Skills existentes** — lista `.claude/skills/*/SKILL.md`. Comprueba que no existe ya una skill llamada `claudia-voice`. Si existe, para y avisa al usuario.

2. **Hooks existentes** — lista `.claude/hooks/`. Comprueba que no existen `voice-response.sh` ni `voice-welcome.sh`. Si existen, avisa.

3. **Credenciales ElevenLabs** — lee `user/credentials/.env` (si existe). ¿Están definidas `ELEVENLABS_API_KEY` y `ELEVENLABS_VOICE_ID`? Si no, el usuario las tendrá que configurar.

4. **Reproductor de audio** — detecta la plataforma (`uname -s`) y comprueba que hay un reproductor disponible:
   - macOS: `afplay` (preinstalado)
   - Linux: `mpg123`, `ffplay`, o `aplay`
   - Windows nativo: PowerShell

5. **Identidad del usuario** — lee `user/context/identity.md` si existe. El hook de bienvenida usa el nombre del usuario para el saludo.

6. **Configuración de hooks en settings.json** — lee `.claude/settings.json` para saber si ya hay hooks configurados y en qué formato, para proponer la integración de los hooks de voz.

Al terminar, tienes un mapa del entorno real del usuario. Ese mapa alimenta el Paso 3.

---

## Paso 3 — Propuesta adaptada + confirmación

Muestra al usuario un resumen **adaptado a lo que encontraste en Discovery**:

```
He revisado tu instancia. Propongo:

**Estado de credenciales:**
- ELEVENLABS_API_KEY: <configurada / pendiente>
- ELEVENLABS_VOICE_ID: <configurada / pendiente>

**Reproductor de audio:** <detectado: afplay/mpg123/etc. | no encontrado>

**Voy a crear:**
- .claude/skills/claudia-voice/SKILL.md
- .claude/skills/claudia-voice/speak.sh
- .claude/hooks/voice-response.sh (reproduce [voice]...[/voice] automáticamente)
- .claude/hooks/voice-welcome.sh (saludo al iniciar sesión)

**Voy a modificar:**
- user/credentials/.env — añadir variables ELEVENLABS_* si no existen
- .claude/settings.json — registrar los hooks

**No voy a tocar** ningún fichero existente más allá de añadir líneas.

¿OK, o ajustamos (quitar hooks, cambiar rutas)?
```

**Espera OK explícito.** Si el usuario no quiere los hooks (solo la skill), ajustar.

---

## Paso 4 — Pre-flight

**Bloquear y parar si:**
- `git status --porcelain -- .claude/skills/claudia-voice/ .claude/hooks/voice-response.sh .claude/hooks/voice-welcome.sh` devuelve cualquier línea.
- Hay un merge o rebase en curso.
- `.claude/skills/claudia-voice/` ya existe (colisión no detectada en Discovery).

**Avisar pero no bloquear si:**
- No hay reproductor de audio instalado — la skill se instala igual pero no funcionará hasta que el usuario instale uno (sugerir `sudo apt install mpg123` en Linux).
- Las credenciales de ElevenLabs no están configuradas — la skill se instala pero no funcionará hasta que las configure.
- Hay cambios sin commit en otras rutas del repo.

---

## Paso 5 — Cambios

1. Crear directorio `.claude/skills/claudia-voice/`.

2. Aplicar assets:
   - `assets/SKILL.md` → `.claude/skills/claudia-voice/SKILL.md`
   - `assets/speak.sh` → `.claude/skills/claudia-voice/speak.sh` (chmod 755)
   - `assets/voice-response.sh` → `.claude/hooks/voice-response.sh` (chmod 755, solo si el usuario aceptó hooks)
   - `assets/voice-welcome.sh` → `.claude/hooks/voice-welcome.sh` (chmod 755, solo si el usuario aceptó hooks)

3. Crear `user/behavior.md` vacío en el directorio de la skill para personalización futura:
   ```
   mkdir -p .claude/skills/claudia-voice/user
   touch .claude/skills/claudia-voice/user/behavior.md
   ```

4. Añadir variables de ElevenLabs a `user/credentials/.env` si no existen:
   ```
   # ELEVENLABS — skill: claudia-voice
   # API key y voice ID en https://elevenlabs.io/app/voice-lab
   ELEVENLABS_API_KEY=
   ELEVENLABS_VOICE_ID=
   # Opcionales:
   # ELEVENLABS_MODEL=eleven_turbo_v2_5
   # ELEVENLABS_VOLUME=1.0
   ```

5. Registrar los hooks en `.claude/settings.json` si el usuario los aceptó. Adaptarse al formato existente de hooks en ese fichero.

---

## Paso 6 — Post

**No commitees nada.** Los blueprints se aplican, se revisan, y commitea el usuario.

- Muestra `git status`.
- Muestra `git diff --stat HEAD -- .claude/skills/claudia-voice/ .claude/hooks/voice-response.sh .claude/hooks/voice-welcome.sh`.
- Recuerda al usuario:
  - **Rollback:** `rm -rf .claude/skills/claudia-voice/ .claude/hooks/voice-response.sh .claude/hooks/voice-welcome.sh`
  - **Setup de ElevenLabs:** crear cuenta gratuita en https://elevenlabs.io, copiar API key y Voice ID, añadirlos al `.env`
  - **Commit cuando conforme:** `feat: add claudia-voice skill via blueprint v0.1.0`

---

## Paso 7 — Verificación

1. Ejecuta `.claude/skills/claudia-voice/speak.sh "Hola, soy Claudia"`.
2. Comprueba que:
   - Se genera un fichero MP3 temporal y se reproduce por los altavoces.
   - Si las credenciales no están configuradas, el script muestra un error claro indicando qué variable falta.
   - El hook `voice-response.sh` existe y es ejecutable (`-x`).
3. Si hay credenciales configuradas, prueba el flujo completo: responde con un `[voice]Prueba de voz instalada correctamente[/voice]` y verifica que el hook lo intercepta y reproduce.
4. Si algún check falla, para y debug antes de dar el blueprint por aplicado.
