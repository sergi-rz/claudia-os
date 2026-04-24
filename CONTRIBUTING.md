# Contribuir a Claudia OS

Claudia OS mejora cuando la gente que lo usa encuentra cosas que no funcionan, ideas que lo harían mejor, o casos de uso que no están cubiertos. Si usas el sistema y tienes algo que aportar (un bug, una skill nueva, una mejora de documentación, una receta de blueprint), es bienvenido.

Claudia OS es un **sistema de IA personal**: cada usuario clona el repo y lo personaliza para sí mismo. No es un producto multi-tenant ni un paquete monolítico. Eso condiciona qué tiene sentido aportar y qué no.

## Contribuciones sin código

No hace falta escribir código para mejorar el proyecto:

- **Reportar bugs.** Si algo no funciona en una instalación limpia, abre un issue con el contexto suficiente para reproducirlo
- **Proponer skills.** Si tienes una idea para una skill que sería útil para otros, descríbela en un issue
- **Mejorar documentación.** Si algo en el README, en un SKILL.md, o en las guías de setup es confuso, una PR con la mejora es perfectamente válida
- **Blueprints.** Si has montado una configuración que funciona bien para un perfil concreto (consultor, creador, gestor de proyectos...) y crees que podría ayudar a otros, compártela

## Qué sí tiene sentido aportar

- **Bugs reales** en el core (`core/`, `.claude/skills/<skill>/`, `scripts/`) que afectan a cualquier instalación limpia.
- **Mejoras de skills existentes** que no dependan del usuario concreto (mejor error handling, compatibilidad multiplataforma, documentación más clara).
- **Nuevas skills** pensadas como core reutilizable, no como personalización de tu propia vida.
- **Fixes de documentación** (README, SKILL.md, setup guides).
- **Blueprints** (`blueprints/*.md`): plantillas de skills que Claudia adapta al contexto de cada usuario en lugar de instalarlas tal cual. Si tienes una forma de trabajar con Claudia que podría ser útil para otros, un blueprint es la forma correcta de compartirla: describe qué debería hacer la skill y cada Claudia la convierte en una skill personalizada para su usuario.

## Qué NO va aquí

- Tu identidad, workspaces, memorias, credenciales, vaults: esas viven en **tu fork** bajo `user/`, que el repo público deja vacío a propósito.
- Personalizaciones de skill concretas: esas viven en `.claude/skills/<skill>/user/` de tu fork, no en el core.
- Datos reales: emails, nombres de contactos, tokens, logs, contenido personal.
## Flujo de PR

1. Abre un issue primero si el cambio no es trivial, para confirmar que encaja con el diseño.
2. Haz fork, crea una rama descriptiva.
3. Antes de abrir la PR, ejecuta:
   ```bash
   ./scripts/reset-test-install.sh /tmp/claudia-clean-check
   ```
   Verifica que no aparecen datos personales tuyos en el resultado.
4. Escribe una descripción clara: qué problema resuelve, cómo lo has probado.

## Separación core / user (regla dura)

Cualquier cambio que toque archivos bajo `user/`, `.claude/skills/*/user/`, `user/credentials/`, `user/memory/`, o similares **no entra en el core**. Si tu caso de uso te exige tocar esos directorios, es señal de que lo tuyo es personalización, no contribución. Añádelo a tu propia instancia.

## Licencia

Al abrir una PR aceptas que tu aportación se publique bajo [MIT License](LICENSE).

## Dónde discutir

- **Bugs y features:** issues en [sergi-rz/claudia-os](https://github.com/sergi-rz/claudia-os/issues).
- **Vulnerabilidades de seguridad:** ver [SECURITY.md](SECURITY.md). No se reportan en issues públicos.
