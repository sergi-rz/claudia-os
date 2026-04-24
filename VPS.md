# Claudia OS en un VPS

Esta guía cubre la instalación de Claudia OS en un servidor Linux siempre encendido. Se centra en la infraestructura base: preparar el servidor, instalar Claude Code, clonar Claudia y aplicar las medidas de seguridad mínimas recomendadas.

La configuración de cada skill (Telegram, briefing, cron jobs...) está documentada en la propia skill. Esta guía solo prepara el terreno.

## Cuándo tiene sentido un VPS

**Ventajas sobre usar tu propio ordenador:**

- **Siempre encendido.** El bot de Telegram, los recordatorios, el briefing diario y cualquier cron job funcionan 24/7 sin depender de que tu portátil esté abierto.
- **Accesible desde cualquier sitio.** Puedes conectarte desde cualquier dispositivo con SSH o con la app de Claude Code.
- **No consume recursos de tu máquina.** CPU, RAM y batería de tu equipo quedan libres.

**Inconvenientes a tener en cuenta:**

- **Acceso a ficheros.** Lo que Claudia genera (imágenes, informes, exports) queda en el servidor. Para verlo en tu ordenador necesitas descargarlo. VS Code conectado por SSH facilita la navegación y la visualización de ficheros de texto y código, pero para imágenes o documentos más complejos sigue siendo un paso extra.
- **Sesiones SSH.** Si la conexión se corta, pierdes la sesión activa. Usar `tmux` o `screen` lo evita, pero son herramientas que requieren un mínimo de familiaridad con la terminal.
- **Voz.** `claudia-voice` no funciona en un VPS — no hay salida de audio en el servidor.
- **Flujos OAuth.** Las autorizaciones de Google (Gmail, Calendar) requieren copiar URLs y pegar tokens a mano, en lugar del flujo habitual de hacer clic en el navegador.
- **Mantenimiento.** El servidor necesita atención ocasional: actualizaciones del SO, vigilar espacio en disco, renovar credenciales.
- **Coste.** Aunque bajo (~4 €/mes en la configuración recomendada), es un gasto fijo que no existe si usas tu propio equipo.
- **Sin conexión, sin acceso.** A diferencia de una instalación local, sin internet no puedes acceder ni a tus ficheros ni a Claudia.

Si solo quieres usar Claudia en conversación y organización personal, una instalación local en tu ordenador es más que suficiente. El VPS compensa cuando quieres automatizaciones que funcionen sin intervención: bot de Telegram siempre activo, briefing diario, recordatorios que llegan aunque tu ordenador esté apagado.

## Servidor recomendado

[Hetzner](https://hetzner.cloud/?ref=0aQBTqe7Ntxd) *(enlace de afiliado)*. Modelo CX22 (~4 €/mes), Ubuntu 22.04.

Requisitos mínimos: 2 vCPU, 2 GB RAM, 20 GB disco.

## 1. Acceso inicial y usuario no root

Conéctate como root la primera vez y crea un usuario propio:

```bash
adduser claudia
usermod -aG sudo claudia
```

A partir de aquí trabaja siempre como ese usuario, no como root.

## 2. Seguridad SSH

Copia tu clave pública al servidor (desde tu máquina local):

```bash
ssh-copy-id claudia@IP_DEL_SERVIDOR
```

Luego endurece la configuración SSH en el servidor:

```bash
sudo nano /etc/ssh/sshd_config
```

Cambia o añade estas líneas:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Recarga SSH:

```bash
sudo systemctl reload sshd
```

> Antes de cerrar la sesión actual, abre una segunda conexión para verificar que puedes entrar con clave. Si algo falla, la sesión actual sigue abierta para corregirlo.

## 3. Firewall básico

```bash
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable
sudo ufw status
```

Abre puertos adicionales solo si una skill lo requiere explícitamente.

Si no vas a usar Tailscale y el puerto SSH quedará expuesto públicamente, instala fail2ban para bloquear ataques de fuerza bruta:

```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban --now
```

La configuración por defecto es suficiente para uso personal: bloquea IPs tras 5 intentos fallidos en 10 minutos.

## 4. Tailscale (opcional pero recomendado)

[Tailscale](https://tailscale.com) crea una red privada entre tus dispositivos. La ventaja práctica: puedes cerrar el puerto SSH en el firewall público y conectarte al servidor solo desde tu red Tailscale: el VPS queda invisible desde internet.

**Instalar en el servidor:**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Abre la URL que imprime, autoriza el dispositivo en tu cuenta de Tailscale, y anota el nombre o IP que te asigna (algo como `100.x.x.x` o `nombre-servidor.tail...ts.net`).

**Instalar en tu máquina local:** descarga la app desde [tailscale.com/download](https://tailscale.com/download) e inicia sesión con la misma cuenta.

Una vez ambos dispositivos están en la misma red Tailscale, puedes cerrar el puerto SSH público:

```bash
sudo ufw delete allow ssh
sudo ufw allow in on tailscale0 to any port 22
```

> **Importante:** antes de ejecutar estos comandos, verifica desde una segunda terminal que puedes conectarte por `ssh claudia@nombre-en-tailscale`. Si algo falla, Hetzner tiene una consola de emergencia en el panel de control (pestaña Console) que permite recuperar acceso sin SSH.

A partir de aquí te conectas con:

```bash
ssh claudia@nombre-en-tailscale
```

**Conectar desde Claude Code desktop:**

Antes de iniciar una sesión, abre el desplegable de entorno y selecciona **+ Add SSH connection**. Rellena:

- **Name**: el nombre que quieras darle (ej. `claudia-vps`)
- **SSH Host**: `claudia@nombre-en-tailscale` (o la IP si no usas Tailscale)
- **SSH Port**: déjalo vacío para usar el 22
- **Identity File**: ruta a tu clave privada, ej. `~/.ssh/id_rsa`

Una vez guardada, aparece en el desplegable. Al seleccionarla, Claude corre directamente en el servidor con acceso a sus ficheros.

## 5. Zona horaria y hostname

Configura la zona horaria antes de instalar nada. Afecta a cron jobs, recordatorios y briefings:

```bash
timedatectl status
sudo timedatectl set-timezone Europe/Madrid  # ajusta a tu zona
```

Opcionalmente, dale un nombre al servidor:

```bash
sudo hostnamectl set-hostname claudia-vps
```

## 6. Dependencias del sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip curl

# Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar
node --version    # 18+
python3 --version # 3.10+
```

## 7. Instalar Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Este es el método recomendado oficialmente: se actualiza automáticamente y evita problemas de permisos. Verifica la instalación:

```bash
claude --version
claude doctor
```

`claude doctor` comprueba que el entorno está correctamente configurado. Si reporta algún problema, resuélvelo antes de continuar.

## 8. Autenticar Claude Code en el servidor

```bash
claude
```

Claude Code imprime una URL. Ábrela en cualquier navegador, autoriza con tu cuenta de Anthropic, y el token queda guardado en `~/.claude/.credentials.json` con permisos `0600`.

**Si necesitas autenticación desatendida** (para scripts o cron sin sesión interactiva), genera un token de larga duración:

```bash
claude setup-token
```

Guarda el token que genera en `user/credentials/.env`:

```
CLAUDE_CODE_OAUTH_TOKEN=<token generado>
```

## 9. Clonar Claudia OS

**Si tienes tu instancia ya configurada en un repo privado (recomendado):**

Primero configura acceso SSH a GitHub desde el servidor. Es la forma más segura y no requiere gestionar contraseñas:

```bash
ssh-keygen -t ed25519 -C "claudia-vps" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

Añade esa clave pública en GitHub → **Settings → SSH and GPG keys → New SSH key**.

Luego clona con SSH:

```bash
git clone git@github.com:TU_USUARIO/TU_REPO_PRIVADO
cd TU_REPO_PRIVADO
```

Tu perfil, workspaces y configuración ya están ahí, no necesitas repetir el onboarding.

**Alternativa con token (HTTPS):** en vez de SSH, puedes clonar con HTTPS usando un Personal Access Token de GitHub como contraseña. Ve a GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic), crea uno con permiso `repo`, y úsalo cuando Git pida credenciales.

**Si es una instalación nueva:**

```bash
git clone https://github.com/sergi-rz/claudia-os
cd claudia-os
claude
```

Y dentro: `/claudia-onboarding`

## 10. Credenciales

```bash
cp user/credentials/.env.example user/credentials/.env
nano user/credentials/.env

# Permisos restrictivos
chmod 600 user/credentials/.env
```

Rellena solo las variables de las skills que vayas a activar.

## 11. Permisos del directorio de usuario

```bash
chmod 700 user/credentials/
chmod 700 user/memory/
```

Los ficheros de identidad, memoria y credenciales no deberían ser legibles por otros usuarios del sistema.

## 12. Verificación final

```bash
claude --version   # confirma la versión instalada
claude doctor      # verifica que el entorno está sano
```

Abre una sesión y comprueba que el repo carga correctamente:

```bash
claude
```

Verifica también que las credenciales están en su sitio:

```bash
ls -la user/credentials/.env   # debe existir con permisos 600
```

Si todo está en orden, el servidor está listo.

## Siguientes pasos

Una vez el entorno está verificado, el flujo habitual es:

1. Si es instalación nueva: ejecuta `/claudia-onboarding` dentro de Claude
2. Configura las skills que quieras activar. Cada una tiene su propia guía en `.claude/skills/<skill>/SKILL.md`
3. Para el bot de Telegram y recordatorios: `.claude/skills/telegram-bot/SKILL.md`
4. Para briefing diario y pipeline de contenido: `.claude/skills/claudia-intake/SKILL.md`

## Actualizar Claudia OS

```bash
git pull
```

Las actualizaciones modifican `core/` y `.claude/skills/`. Tu carpeta `user/` nunca se toca. Las nuevas funcionalidades suelen llegar primero como blueprints (configuraciones aplicables con `/claudia-blueprint`) antes de incorporarse al core, así que puedes probarlas sin esperar a una actualización formal.
