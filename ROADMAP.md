# Hoja de ruta de Claudia OS

Este documento refleja la dirección del proyecto. No es un compromiso de fechas sino una declaración de intenciones y prioridades.

## Estado actual (v1)

El sistema es funcional y se usa a diario en producción. El core (onboarding, memoria, separación core/user, sistema de skills) es estable. Algunas skills individuales están en fases más tempranas: funcionan, pero pueden cambiar de interfaz o comportamiento entre versiones.

Incluye:

- Onboarding completo con generación de perfil personal
- 14 skills activas (investigación, notas, imagen, Gmail, Calendar, Telegram, intake...)
- Memoria persistente entre conversaciones
- Separación core/user que permite actualizaciones sin pérdida de datos
- Sistema de blueprints: plantillas de skills en `blueprints/` que Claudia adapta al contexto de cada usuario con `/claudia-blueprint`
- Actualización del framework desde el propio asistente (`/claudia-update`)
- Soporte para despliegue local y VPS

## Próximas prioridades

**Skills y capacidades**
- Evolución de `claudia-gmail`: organización automática de bandeja, limpieza, briefings periódicos de correo y alertas por criterios personalizados
- Skill de finanzas personales y profesionales: estructura base para seguimiento de gastos, ingresos y presupuestos, pensada para que cada usuario la adapte a su situación
- Más blueprints de inicio para distintos perfiles (consultor, creador de contenido, gestor de proyectos)
- Mejora del briefing diario: personalización de secciones y horario

**Portabilidad**
- Guía de adaptación para usar Claudia OS fuera de Claude Code (Codex, OpenCode, aider u otros agentes de terminal). El objetivo es documentar qué depende de Claude Code y qué ajustes necesita cada entorno alternativo

**Onboarding y experiencia inicial**
- Validación de entorno antes de empezar (Python, Node, dependencias)

## Fuera de scope (por ahora)

Estas cosas no están en los planes inmediatos, no porque sean malas ideas sino porque añadirían complejidad sin beneficiar al caso de uso principal:

- Interfaz web o app móvil. El punto de entrada es un agente de terminal
- Multi-usuario / multi-tenant. Claudia OS es deliberadamente personal
- Despliegue en cloud gestionado. La soberanía de datos es un principio, no una opción
- Integraciones con plataformas de terceros como Notion, Linear o Slack. Posibles como skills de comunidad, no como core

## Cómo crece Claudia OS

El core se mantiene estable y compacto a propósito. La mayoría de nuevas capacidades llegarán como **blueprints** (plantillas que cada Claudia adapta al contexto de su usuario) o como **skills de comunidad**, no como cambios en el core.

Las prioridades del core las marca lo que bloquea a un usuario real en su primer día. Después, lo que reduce fricción en el uso diario.

Si tienes una idea o crees que una funcionalidad puede servir al resto de usuarios, abre un hilo en [Discussions](https://github.com/sergi-rz/claudia-os/discussions). Si ya tienes algo funcionando, abre una PR.

→ [Cómo contribuir](CONTRIBUTING.md)
