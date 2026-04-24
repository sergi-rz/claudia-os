# Claudia Onboarding — Configuracion inicial

Asistente de configuracion inicial de Claudia OS. Te entrevista de forma conversacional para conocerte y genera los ficheros de contexto personal que dan forma a tu asistente.

## Que hace

La primera vez que usas Claudia OS, necesita saber quien eres y como quieres trabajar. En lugar de pedirte que edites ficheros de configuracion a mano, el onboarding es una conversacion guiada donde Claudia te pregunta lo esencial: tu nombre, a que te dedicas, como prefieres que trabaje, y como quieres organizar tus proyectos.

Con tus respuestas genera automaticamente los ficheros de identidad, restricciones, workspaces y configuracion tecnica. Si ya tienes un perfil configurado, te ofrece actualizarlo, empezar de cero, o cancelar.

## Como usarlo

```
/claudia-onboarding
```

Eso es todo. Claudia te guia con preguntas de una en una. El flujo completo dura unos 2-3 minutos.

### Que te pregunta

1. **Tu nombre** -- Como te llamas
2. **Nombre del asistente** -- Si quieres llamarla Claudia u otro nombre
3. **A que te dedicas** -- Profesion, proyectos, herramientas
4. **Personalidad** -- Directa y al grano, detallada, o intermedio
5. **Idioma** -- En que idioma trabajais (si no queda claro por la conversacion)
6. **Zona horaria** -- Para calendario y recordatorios (acepta ciudades: "Madrid", "Mexico")
7. **Autonomia** -- Si prefieres que pida permiso o que actue y te cuente despues
8. **Foco actual** -- En que estas poniendo mas energia ahora mismo (3-6 meses)
9. **Horizonte** -- Hacia donde quieres ir en 1-2 anos (solo si no quedo claro antes)
10. **Lo que frena** -- Bloqueos o tensiones actuales (opcional)
11. **Workspaces** -- Areas de trabajo ademas de la personal (clientes, proyectos propios, etc.)
12. **Corpus de creador** -- Si tienes un workspace de contenido, puede sincronizar tus publicaciones
13. **Modo de uso** -- Solo este ordenador, ordenador siempre encendido, o servidor/VPS

Puedes decir "saltar" en cualquier pregunta y usara valores por defecto razonables.

## Que ficheros genera

| Fichero | Contenido |
|---------|-----------|
| `user/context/identity.md` | Quien eres y quien es tu asistente (personalidad, idioma, timezone) |
| `user/context/goals.md` | Objetivos activos, horizonte y bloqueos (solo si respondio a las preguntas de foco) |
| `user/context/constraints.md` | Restricciones de comportamiento y nivel de autonomia |
| `user/context/workspaces.md` | Mapa de tus areas de trabajo |
| `user/config/settings.json` | Ajustes tecnicos (timezone, idioma) |
| `user/credentials/.env` | Fichero de credenciales (vacio, para rellenar despues) |
| `user/memory/MEMORY.md` | Indice de memorias (vacio inicialmente) |
| `user/workspaces/_me/notes/tasks.md` | Plantilla de tareas con secciones Pendientes/Recordatorios/Completadas |
| `user/workspaces/_me/notes/ideas.md` | Plantilla de ideas |
| `user/context/memory.md` | Solo si eliges multi-dispositivo: config de memoria sincronizada |

Ademas crea los directorios de cada workspace adicional que hayas mencionado.

## Configuracion

### Requisitos

Ninguno. El onboarding es la primera skill que ejecutas y no depende de nada externo.

### Modos de infraestructura (`runtime` en settings.json)

Segun lo que elijas en la pregunta de entorno de ejecucion:

- **local** (ordenador personal) -- Claudia instala crons con tu permiso; las automatizaciones funcionan mientras el ordenador este encendido.
- **server** (VPS/nube) -- Maquina siempre disponible. Crons y tareas autonomas sin restricciones de horario.

El backup en GitHub es siempre opcional, independientemente del modo.

## Donde se guarda todo

Todo se genera dentro de `user/`:

```
user/
  context/          -- Identidad, restricciones, workspaces
  config/           -- Settings tecnicos (timezone, idioma)
  credentials/      -- .env con tokens (vacio tras onboarding)
  memory/           -- MEMORY.md (indice de memorias)
  workspaces/
    _me/notes/      -- Tareas e ideas (siempre se crea)
    {tus-areas}/    -- Workspaces adicionales que hayas pedido
```

## Skills relacionadas

- **notes** -- Las plantillas de tareas e ideas que genera el onboarding son las que usa la skill de notas
- **telegram-bot** -- Si eliges modo "siempre encendido" o VPS, el catalogo final de skills te muestra como activar Telegram
- **claudia-corpus-sync** -- Si tienes un workspace de creador, el onboarding te ofrece configurar la sincronizacion de contenido publicado
- **memory-search** -- El MEMORY.md generado es el indice que memory-search mantiene actualizado

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-onboarding/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Salta la pregunta sobre corpus de creador — no tengo canales de contenido"
- "Al final del onboarding, genera también un fichero user/context/projects.md con mis proyectos activos"
- "Usa un tono más breve y directo en las preguntas — menos conversacional"
- "Añade siempre el workspace 'clientes' por defecto sin preguntar"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **Ya tengo un perfil y quiero cambiarlo**: ejecuta `/claudia-onboarding` de nuevo. Te preguntara si quieres actualizar, empezar de cero, o cancelar.
- **Me equivoque en una respuesta**: puedes editar los ficheros generados directamente en `user/context/`. Son markdown plano.
- **El sync multi-dispositivo no funciona**: verifica que el remote de git esta configurado (`git remote -v`) y que tienes permisos de push al repositorio.
