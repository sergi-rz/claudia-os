# Claudia Thinking — Modos de razonamiento profundo

Tres modos de razonamiento estructurado para cuando necesitas pensar en serio antes de decidir, comprometerte o reconstruir una idea desde cero. Inspirado en el framework Thinking Modes de Daniel Miessler.

## Que hace

No es una busqueda ni una investigacion (para eso esta `/research`). Es razonamiento interno: Claudia aplica un proceso estructurado para analizar tu decision, plan o pregunta desde multiples angulos. No busca en internet, no genera datos nuevos — trabaja con lo que ya sabe y lo que tu le das.

Hay tres modos, cada uno con un proposito distinto:

- **Council** — convoca un consejo de perspectivas diversas para deliberar sobre una decision
- **RedTeam** — ataca un plan de forma adversarial para encontrar fallos antes de ejecutarlo
- **FirstPrinciples** — deconstruye una pregunta hasta sus axiomas y la reconstruye desde cero

## Como usarlo

### Invocacion explicita

```
/thinking council Estoy entre contratar a un junior y formar, o buscar un senior que ya sepa. Tengo presupuesto limitado y necesito resultados en 3 meses.

/thinking redteam Mi plan es lanzar el MVP la semana que viene: solo login + dashboard basico, sin onboarding, y mandarlo a 50 beta testers del newsletter.

/thinking firstprinciples Por que todas las herramientas de gestion de proyectos acaban siendo un cementerio de tareas abandonadas?
```

### Auto-deteccion

Claudia puede activar un modo automaticamente cuando detecta senales claras en la conversacion:

- **Council**: presentas dos o mas opciones con trade-offs reales ("no se si A o B")
- **RedTeam**: anuncias un compromiso antes de ejecutar ("voy a...", "he decidido...")
- **FirstPrinciples**: un problema recurrente sin resolucion, o cuestionas una convencion

Cuando lo activa, te avisa primero y puedes decir "no hace falta" para saltar al modo normal.

## Los tres modos en detalle

### Council — deliberacion multi-perspectiva

Para decisiones con alternativas reales y trade-offs. Antes de deliberar, Claudia te propone quien se sienta en el consejo y espera a que lo valides. Puedes quitar o añadir voces, y elegir solo roles, solo voces reales o una mezcla.

**Roles** — 3-5 segun el tipo de decision (mas los que hayas añadido en `user/behavior.md`):

| Rol | Perspectiva |
|-----|-------------|
| El Pragmatico | Viabilidad, recursos, camino mas corto al resultado |
| El Esceptico | Riesgos, supuestos sin verificar |
| El Visionario | Largo plazo, oportunidades no visibles |
| El Usuario | Experiencia de quien usa el producto |
| El Guardian | Sostenibilidad, precedentes, coste de mantenimiento |
| El Contrario | El argumento opuesto mas fuerte |
| El Experto de dominio | Practica establecida, que ha funcionado antes |

**Voces reales** — si tu vault tiene contenido de autores que han escrito sobre el tema (via `vault-search`), Claudia los ofrece con cuantas entradas tiene de cada uno. Una voz real habla desde lo que ese autor ha escrito, citando la pieza, y no se le atribuye nada que no este en su corpus. Si pides a alguien que no esta en tu vault, entra como **voz inferida**: sale de lo que el modelo sabe de esa persona, y el output lo marca asi.

El output incluye la perspectiva de cada voz, los puntos de acuerdo, la tension central y una recomendacion sintetizada.

**La Sala del Consejo (opcional).** Si le pides a Claudia que te lo enseñe en La Sala, abre una pagina local (`http://localhost:8787`) con una mesa redonda: los miembros entran y toman asiento, quien habla se ilumina, su texto sale en un cuadro de dialogo por paginas y el veredicto aparece sobre la mesa. Tiene modo Rapido (fichas con la postura de cada uno) y Acta (todo el texto), un modo para grabarla y varios temas (Mesa del Rey Arturo, Minimal, 16 bits); puedes crear el tuyo, ver `council-live/THEMES.md`. Para que tus mentores salgan con su cara, pon su foto en `user/config/mentor-photos/<id>.jpg`.

### RedTeam — validacion adversarial

Para cuando ya tienes un plan concreto y quieres encontrar fallos antes de ejecutarlo. Claudia ataca desde cinco vectores:

1. **Supuestos ocultos** — que das por verdad sin verificar
2. **Casos limite** — escenarios no cubiertos que rompen el plan
3. **Dependencias fragiles** — single points of failure
4. **Costes ocultos** — recursos que no aparecen en el plan pero seran necesarios
5. **Reversibilidad** — que decisiones son dificiles de deshacer

Termina con un veredicto de riesgo (BAJO/MEDIO/ALTO/CRITICO), fallos fatales vs. mitigables, y una condicion de go/no-go.

### FirstPrinciples — deconstruccion axiomatica

Para cuando la respuesta convencional no satisface, estas atascado en un optimo local, o quieres cuestionar algo fundamental. Tres fases:

1. **Demolicion** — elimina costumbre, convencion, inercia y analogias heredadas
2. **Axiomas** — identifica que es verdad fundamental, irreducible
3. **Reconstruccion** — partiendo solo de los axiomas, llega a una conclusion

Compara el resultado con la respuesta convencional y explica por que difieren (si difieren).

## Reglas de uso

- **Un modo por vez.** Si durante Council se detectan fallos graves, se termina Council y se sugiere RedTeam.
- **Sin web search.** Estos modos son de razonamiento interno. Si necesitas datos, usa `/research` primero y luego `/thinking`.
- **Prioridad de auto-seleccion:** RedTeam > Council > FirstPrinciples (si la situacion activa mas de uno).
- **Opt-out siempre disponible.** Si Claudia activa un modo y no lo quieres, dile que no.

## Donde se guarda

Los modos de thinking no generan ficheros permanentes por defecto. Tras una deliberacion importante, Claudia puede registrar el resultado en memoria episodica (`memory_reflect.py`) para aprender de los patrones de razonamiento que funcionaron o fallaron.

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Crea `user/behavior.md` dentro del directorio de la skill (o edítalo, si ya existe). También puedes pedírselo a Claudia y lo hace ella. Tienes ideas en `behavior.example.md`:

```
.claude/skills/claudia-thinking/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "En el Council, añade siempre el rol 'El Cliente' enfocado en la experiencia del usuario final"
- "Al final de cualquier modo de thinking, añade una sección '## Próximos pasos' con 2-3 acciones concretas"
- "Usa un umbral más conservador para la auto-detección — solo activa si las señales son muy claras"
- "Escribe los outputs de thinking siempre en inglés"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Skills relacionadas

- **claudia-research** — para investigar datos antes de razonar. Usa `/research` para reunir informacion y luego `/thinking` para deliberar
- **claudia-wisdom** — las extracciones de wisdom pueden alimentar el contexto de un Council o FirstPrinciples
- **vault-search** — de ahi salen las voces reales del Council: los autores con entradas en tu vault sobre el tema
- **memory-search** — para recuperar deliberaciones pasadas registradas en memoria episodica
