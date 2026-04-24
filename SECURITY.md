# Política de seguridad

## Modelo de amenazas

Claudia OS es un sistema de IA personal que cada usuario ejecuta en **su propia máquina o VPS**, con **sus propias credenciales**. No hay servidor central, no hay base de datos compartida, no hay multi-tenancy.

Ejecutarlo en hosts compartidos o cuentas de usuario compartidas está fuera del modelo previsto.

Eso significa:

- Las credenciales (`user/credentials/`) viven localmente. Su seguridad depende de ti (permisos de fichero, backups, quién tiene acceso al VPS).
- El repo público **no contiene** credenciales, tokens, ni datos personales. Si encuentras algo así en una release, eso **sí** es una vulnerabilidad y queremos saberlo.
- Las skills ejecutan comandos y llaman a APIs externas con permisos amplios (lectura de Gmail, modificación de Calendar, envío de Telegram). Un fallo que permita ejecución no autorizada es crítico.

## Qué consideramos vulnerabilidad

- **Fuga de credenciales** en el repo, logs, o mensajes (incluido history de commits del core).
- **Ejecución de código** inesperada vía input de usuario, ficheros de configuración o contenido externo (emails, mensajes de Telegram, transcripciones, etc.).
- **Escalada de permisos**: una skill que acaba haciendo algo fuera de su scope declarado (p.ej. Gmail enviando sin cumplir las restricciones documentadas en `claudia-gmail/SKILL.md`).
- **Inyección de prompts** que haga que Claudia realice acciones destructivas sin la confirmación que `constraints.md` exige.
- **Problemas en OAuth flows** (Gmail, Calendar) que puedan exponer tokens.

## Qué NO es vulnerabilidad

- El diseño permite que Claudia envíe emails, lea tu calendario, o actúe sobre Telegram **con tus credenciales**: eso es la funcionalidad, no un bug.
- Personalizaciones de usuario que se rompan al actualizar el core: la regla explícita es que `user/` y `.claude/skills/*/user/` no se tocan; si algo fuera de esos paths se pisa, eso sí es un bug.

## Cómo reportar

**No abras un issue público** para vulnerabilidades. Envíalas a:

📧 **sergi@sergiruiz.es**

Incluye:
- Descripción del problema.
- Pasos para reproducir (comandos exactos, configuración mínima).
- Impacto esperado.
- Opcional: sugerencia de fix.

Responderé en un plazo razonable (típicamente pocos días). Si la vulnerabilidad es crítica, el fix puede requerir coordinación antes de hacerse público.

## Buenas prácticas recomendadas al usuario

- Guarda `user/credentials/.env` solo localmente. Nunca lo commitees.
- El `.gitignore` ya excluye `user/credentials/*` salvo `.env.example`, `.gitkeep` y `CLAUDE.md`. No lo modifiques.
- Si usas el modo multi-dispositivo (repo privado en GitHub), asegúrate de que el repo es **privado**. Contiene tu memoria, vault, workspaces.
- Revisa periódicamente los tokens activos en tu cuenta de Google, Telegram, etc. Revoca los que ya no uses.
- Si sospechas que tus credenciales se han filtrado: rota los tokens en las consolas de Google/Telegram, revoca OAuth grants, y regenera `user/credentials/.env`.
