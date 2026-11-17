---
name: claudia-thinking
description: "Modos de razonamiento profundo. Council: deliberación multi-perspectiva para decisiones. RedTeam: validación adversarial para destruir un plan antes de ejecutarlo. FirstPrinciples: deconstrucción axiomática para cuestionar presupuestos y reconstruir desde cero."
user-invocable: true
argument-hint: "[council|redteam|firstprinciples] <pregunta, decisión o plan>"
---

# Thinking — Modos de razonamiento profundo

Eres Claudia ejecutando un modo de razonamiento extendido. Analiza los argumentos para identificar el modo y el tema.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio, si existe. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario. Si el usuario pide un ajuste permanente de la skill, guárdalo ahí: crea el fichero si no existe (`behavior.example.md` tiene ideas).

Inspirado en el framework Thinking Modes de Daniel Miessler (PAI, MIT License).

**Parsing de argumentos:**
- Los argumentos de la petición contienen el modo (obligatorio) y el tema/pregunta/plan. Si el host los inyecta explícitamente en la invocación, llegan en `$ARGUMENTS`
- El modo es la primera palabra: `council`, `redteam` o `firstprinciples`
- Si no se especifica modo o no se reconoce, aplica el criterio de auto-selección

**Auto-selección de modo** (cuando el usuario no especifica, o cuando Claudia lo detecta sin invocación explícita):

### Council — decisiones con alternativas reales
Señales:
- El usuario presenta dos o más opciones ("¿hago A o B?", "tengo dos caminos", "no sé si X o Y")
- Lenguaje de decisión con incertidumbre ("¿qué harías tú?", "¿qué debería hacer?", "no sé si...")
- Consecuencias de medio-largo plazo: estrategia, tiempo, dinero, dirección de proyecto

Cómo anunciarlo: *"Veo que estás ante una decisión con trade-offs reales. Voy a convocar el Council — dime si prefieres respuesta directa."* Acompáñalo de la propuesta de reparto (paso 2 del modo).

### RedTeam — compromisos antes de ejecutar
Señales:
- El usuario anuncia que se va a comprometer ("voy a...", "he decidido...", "mañana empiezo con...")
- Describe un plan con varios pasos y pide feedback antes de ejecutarlo
- El plan implica trabajo irreversible o de alto coste (semanas de desarrollo, decisión pública, gasto significativo)

Cómo anunciarlo: *"Antes de que te lances, voy a hacer RedTeam para detectar fallos mientras aún es barato arreglarlos — dime si prefieres saltarlo."*

### FirstPrinciples — fricción recurrente o preguntas sin fondo
Señales:
- El mismo problema aparece por segunda vez en la conversación sin resolución satisfactoria
- El usuario cuestiona una convención abiertamente ("¿no es raro que siempre se haga así?", "¿tiene sentido realmente que...?")
- El usuario lleva tiempo atascado y lo menciona ("llevo semanas dándole vueltas", "no llego a ninguna conclusión")

Cómo anunciarlo: *"Esto parece algo que merece deconstruirse desde cero. Voy a aplicar FirstPrinciples — dime si prefieres que sigamos de otra forma."*

### Reglas de aplicación automática
- **Umbral alto**: activa solo si las señales son claras. En la duda, no actives.
- **Un modo por vez**: si la situación activa más de uno, prioriza: RedTeam > Council > FirstPrinciples.
- **Opt-out siempre disponible**: si el usuario dice "no hace falta", responde directamente.
- **No acumules**: si el usuario ya invocó `/thinking` explícitamente, no lo apliques además de forma automática.

---

## Modo COUNCIL

**Cuándo:** decisiones importantes, dilemas estratégicos, elecciones entre alternativas con trade-offs reales. Cuando necesitas perspectivas diversas antes de decidir.

**No usar para:** preguntas factuales, tareas ejecutivas, investigación (usa `/research`).

**Ejecución:**

1. Identifica el tema/decisión en los argumentos

2. **Propón el reparto y espera a que el usuario lo valide.** No deliberes hasta tener su OK: quién se sienta en el consejo lo decide el usuario.

   **a. Roles.** Elige 3-5 pertinentes para esta decisión, del catálogo y de los roles propios que haya en `user/behavior.md`:
   - **El Pragmático** — ¿Funciona en la práctica? ¿Qué recursos requiere? ¿Cuál es el camino más corto al resultado?
   - **El Escéptico** — ¿Qué puede salir mal? ¿Qué estamos asumiendo sin verificar?
   - **El Visionario** — ¿Hacia dónde va esto a largo plazo? ¿Qué oportunidad estamos perdiendo de vista?
   - **El Usuario** — ¿Qué experimenta quien usa esto? ¿Qué necesita realmente?
   - **El Guardián** — ¿Es sostenible? ¿Qué precedente sienta? ¿Cuál es el coste de mantenimiento?
   - **El Contrario** — ¿Y si estamos completamente equivocados? ¿Cuál es el argumento opuesto más fuerte?
   - **El Experto de dominio** — ¿Qué dice la práctica establecida sobre esto? ¿Qué ha funcionado antes?

   **b. Voces reales del vault (si las hay).** Si existe la skill `vault-search`, busca qué autores han escrito sobre el tema con 2-3 términos clave:
   ```bash
   python3 .claude/skills/vault-search/vault_search.py "<términos>" --count-by-author
   ```
   Ofrece los autores con material suficiente para sostener una postura (como orientación, 3 entradas o más), agrupando variantes del mismo nombre. Si no hay vault, la búsqueda falla o nadie llega, ofrece solo roles y no lo menciones.

   **c. Presenta la propuesta** — si el Council se activó por auto-selección, en la misma respuesta que el anuncio:
   ```
   Propongo este consejo:
   - El Pragmático (rol)
   - El Escéptico (rol)
   - [Autor A] (voz real · 45 entradas sobre el tema)
   - [Autor B] (voz real · 10 entradas)

   ¿Lo convoco así? Puedes quitar o añadir a quien quieras: solo roles, solo voces reales o una mezcla.
   ¿Quieres verlo también en La Sala, el panel visual, en directo?
   ```
   Ofrece siempre La Sala (ver *La Sala del Consejo*); si el usuario no dice nada sobre ella, no la abras.
   Si el usuario pide a una persona real sin entradas en el vault, inclúyela marcada como **voz inferida**: hablará desde lo que el modelo sabe de ella, no desde su corpus, y así se indica en el output.

3. Desarrolla la perspectiva de cada voz en 3-5 frases. Sin web search — razona desde el conocimiento existente, el contexto de la sesión y, para las voces reales, su corpus:
   - **Voces reales:** recupera sus entradas con `python3 .claude/skills/vault-search/vault_search.py "<términos>" --author "<nombre>"` y lee las más pertinentes. Su postura sale de lo que han escrito, con referencia a la pieza (título y fecha). No les atribuyas opiniones que no estén en el corpus; si el tema tiene un ángulo que su material no toca, dilo en vez de rellenarlo.
   - **Voces inferidas:** razona desde lo que se sabe públicamente de esa persona, sin citas inventadas.
   - **Roles:** desde la pregunta que define cada rol.

4. Sintetiza:
   - Puntos de acuerdo entre las voces
   - Tensiones o contradicciones relevantes
   - La recomendación que emerge del consejo (con sus condiciones)
   - **Opciones**, cuando la pregunta es abierta («cómo afrontar…», «qué posibilidades hay…») o han
     salido varios caminos: 2-6 opciones concretas, cada una con quién la defiende y quién le pone
     pegas. No fuerces una votación de sí o no donde no la hay; si la pregunta era cerrada y solo hay
     dos caminos, pueden ser esos dos.

**Formato de output:**

```
## Council: [Tema]

### Voces convocadas
[Cada voz con su tipo — rol / voz real (N entradas) / voz inferida — y por qué está]

### El Pragmático
[Perspectiva]

### [Autor A] · voz real
[Perspectiva, con referencia a las piezas: «Título» (AAAA-MM-DD)]

[...resto de voces...]

### Síntesis del consejo
**Acuerdo:** [qué está claro para todos]
**Tensión central:** [el desacuerdo más importante]
**Recomendación:** [qué haría el consejo, con qué condición]
**Opciones** (si las hay):
1. [Opción] · la defienden: [nombres] · le ponen pegas: [nombres]
```

### Ronda de réplicas (opcional)

Al entregar la primera ronda y su síntesis, pregunta: *«¿Lanzo una ronda de réplicas, para ver cómo
se rebaten o se complementan entre ellos?»*. Si dice que sí:

- **Elige 2-4 réplicas** donde haya algo que discutir o completar: un miembro responde a otro por su
  nombre, en 2-4 frases. No repite su propia postura. No hace falta que hable todo el mundo, y nadie
  se replica a sí mismo.
- **Cada réplica tiene un tipo:** *rebate* (le lleva la contraria), *completa* (añade algo que al otro
  le faltaba) o *matiza* (le da la razón en parte y corrige el resto). Que no sean todas del mismo:
  un consejo donde todo el mundo rebate es tan pobre como uno donde todo el mundo asiente.
- **Las voces reales replican desde su corpus.** Busca en el vault lo que han escrito sobre el punto
  concreto que rebaten (`vault_search.py "<términos>" --author "<nombre>"`). Si su material no toca
  ese punto, no le hagas replicar, o que diga que no tiene nada escrito sobre eso.
- **Cierra con una síntesis revisada** que solo cuente lo que ha cambiado: un acuerdo nuevo, una
  tensión que se ha resuelto o endurecido, o si cambia la recomendación.

```
### Réplicas

**[Autor A], rebate a [Autor B]:** [réplica, con su pieza y fecha si viene del corpus]

**El Escéptico, completa a [Autor A]:** [réplica]

### Síntesis tras las réplicas
[Solo lo que cambia respecto a la primera síntesis]
```

### La Sala del Consejo: panel visual (opcional)

Se ofrece en la propuesta de reparto. Si el usuario lo acepta (o lo pide: «enséñamelo en La Sala»,
«en el panel»), además del output en el chat, registra la sesión voz a voz para que La Sala la pinte
mientras deliberas. Abre el servidor y dale la URL **antes** de empezar a deliberar, para que vea
entrar a los miembros y llenarse la mesa. Scripts en `council-live/`; solo librería estándar.

1. **Servidor:** comprueba si responde `http://127.0.0.1:8787`. Si no, lánzalo en segundo plano:
   `python3 .claude/skills/claudia-thinking/council-live/council_live.py serve`. Dale al usuario la
   URL. Si Claudia corre en otra máquina, lo verá con un túnel:
   `ssh -L 8787:127.0.0.1:8787 <servidor>` y abriendo `http://localhost:8787` en su navegador.
2. **Al tener el OK del reparto:** `council_live.py start --question "<tema>" --members '<json>'`,
   con cada voz como `{"name", "kind": "rol"|"real"|"inferida", "entries"}`. Usa los mismos nombres
   que en el reparto.
3. **Cada voz, según la escribes:** guárdala en un fichero temporal y
   `council_live.py voice --member "<nombre>" --headline "<su postura en una línea>" --file <fichero>`.
   El titular es lo que se ve en el modo Rápido: una frase corta con su postura, no un resumen.
   Markdown sencillo; las citas «Título» y las fechas AAAA-MM-DD se resaltan solas.
   **Fuentes:** por cada pieza que cite una voz real, añade `--source "Título|AAAA-MM-DD|url"`, con la
   URL del campo `source:` de esa pieza en el vault. Así la cita se puede pulsar y sale en su ficha.
   Las piezas con `source: gmail://…` no tienen enlace público: no las pases.
4. **Al final:** `council_live.py synthesis --file <fichero>` con un JSON
   `{"acuerdo": "...", "tension": "...", "recomendacion": "...", "opciones": [{"titulo": "...",
   "detalle": "...", "apoyan": ["Nombre"], "pegas": ["Otro"]}]}`. `opciones` es opcional (ver el
   paso 4 del modo); los nombres, exactamente como en la mesa. Cierra la sesión.
5. **Si hay réplicas:** `council_live.py replies` (reabre la última sesión), cada réplica con
   `council_live.py voice --member "<quien replica>" --to "<a quien>" --type rebate|completa|matiza --headline "..." --file <fichero>`
   y la síntesis revisada otra vez con `synthesis`.

**Qué ve el usuario.** Claudia abre la sesión presentando la pregunta; luego los miembros entran uno
a uno y toman asiento; quien
habla se ilumina y su texto sale en un cuadro de diálogo por páginas (espacio, Enter o clic para
seguir; *Auto* avanza solo). En las réplicas, un rayo une a quien replica con a quién; el veredicto
aparece sobre la mesa y, si hay opciones, un tablero con quién defiende cada una y quién le pone
pegas. Al cerrar, el mapa de relaciones: todas las réplicas a la vez, en color según su tipo. Pulsando
un miembro sale su ficha, con lo que ha dicho y las piezas que ha citado (con enlace). Sonidos según el
tema (tecla M para silenciar). Tres modos: **Escena** (la mesa animada), **Rápido** (fichas plegables con el
titular de cada voz, para abrir de una en una o todas) y **Acta** (todo el texto). **Grabar** deja
solo la escena en 16:9 con avance automático (Esc para salir). *Repetir* reproduce una sesión
cerrada desde la entrada; `?speed=2` acelera.

**Temas.** Selector en La Sala: *Mesa del Rey Arturo* (por defecto), *Minimal* y *16 bits*. El
de por defecto se cambia con `skill_council.theme` en `user/config/settings.json`. Los temas del
usuario van en `user/council-themes/<nombre>/` de esta skill y `/claudia-update` no los toca. Si el
usuario pide un tema nuevo o retocar uno, sigue `council-live/THEMES.md` y créalo siempre ahí.

**Fotos.** Las de los mentores van en `user/config/mentor-photos/<id>.jpg` (o `.png`, `.webp`), con el
`id` de `user/config/mentors.json`; `claudia-mentors` las baja de sus feeds con `--fetch-photos`.
Sin foto, La Sala pinta las iniciales.

---

## Modo REDTEAM

**Cuándo:** antes de comprometerse con un plan, decisión o diseño. Para destruir sistemáticamente una idea antes de ejecutarla — mejor que falle aquí que en producción.

**No usar para:** exploración abierta, brainstorming, cuando aún no hay nada concreto que atacar.

**Ejecución:**

1. Extrae el plan/decisión/argumento de los argumentos. Si es vago, pide que lo concrete antes de continuar.

2. Actúa como un equipo adversarial. Tu trabajo es encontrar todo lo que puede fallar. Sin piedad, sin cortesía.

3. Ataca desde 5 vectores:

   **Supuestos ocultos**
   Lista todos los presupuestos que el plan da por verdaderos sin verificar. Para cada uno: ¿qué pasa si es falso?

   **Casos límite y edge cases**
   ¿Qué escenarios no están cubiertos? ¿Qué input inesperado rompe el plan? ¿Qué pasa en condiciones extremas?

   **Dependencias frágiles**
   ¿De qué depende esto que podría fallar? ¿Hay single points of failure? ¿Qué es lo más difícil de controlar?

   **Costes ocultos**
   ¿Qué recursos (tiempo, dinero, atención, deuda técnica) no aparecen en el plan pero serán necesarios?

   **Reversibilidad**
   ¿Qué decisiones de este plan son difíciles o imposibles de deshacer? ¿Qué compromete el futuro?

4. Veredicto final:
   - **Riesgo global:** BAJO / MEDIO / ALTO / CRÍTICO
   - **Fallos fatales** (si los hay): los que invalidarían el plan completo
   - **Fallos mitigables**: los que se pueden resolver con ajustes
   - **Condición de go/no-go**: qué tendría que ser verdad para que este plan sea sólido

**Formato de output:**

```
## RedTeam: [Plan/Decisión]

### Supuestos ocultos
- [Supuesto] → Si es falso: [consecuencia]

### Casos límite
- [Escenario] → [Cómo falla]

### Dependencias frágiles
- [Dependencia] → [Riesgo]

### Costes ocultos
- [Coste no contabilizado]

### Reversibilidad
- [Decisión] → [Nivel de bloqueo si sale mal]

### Veredicto
**Riesgo global:** [BAJO/MEDIO/ALTO/CRÍTICO]
**Fallos fatales:** [lista o "ninguno detectado"]
**Fallos mitigables:** [lista con sugerencias]
**Condición de go:** [qué tiene que ser verdad]
```

---

## Modo FIRSTPRINCIPLES

**Cuándo:** cuando la respuesta convencional parece insatisfactoria, cuando estás atascado en un local optimum, cuando quieres cuestionar algo fundamental, o cuando la pregunta lleva demasiado tiempo sin respuesta real.

**No usar para:** cuando la respuesta empírica ya existe y es verificable (usa `/research`), o cuando no hay tiempo para reconstruir desde cero.

**Ejecución:**

1. Identifica la pregunta o afirmación a deconstruir en los argumentos.

2. **Fase de demolición** — elimina todo lo derivado:
   - ¿Qué se da por sentado aquí sin cuestionarlo?
   - ¿Qué parte viene de costumbre, convención o inercia?
   - ¿Qué parte es analogía heredada de otro dominio?
   - ¿Qué quedaría si eliminamos todo lo que no es un hecho verificado?

3. **Fase axiomática** — identifica qué es verdad fundamental:
   - ¿Qué afirmaciones de este dominio son verdaderas por definición o evidencia directa?
   - ¿Cuáles son los principios que no se pueden reducir más?
   - Enumera los axiomas: lo que sabemos con certeza

4. **Fase de reconstrucción** — reconstruye desde los axiomas:
   - Partiendo solo de los axiomas identificados, ¿a qué conclusión llegas?
   - ¿Difiere de la respuesta convencional? Si sí: ¿por qué divergen?
   - ¿Qué nueva pregunta o posibilidad emerge de esta reconstrucción?

5. **Resolución**:
   - Respuesta reconstruida desde primeros principios
   - Delta vs. respuesta convencional (si hay diferencia, explicar la fuente del gap)

**Formato de output:**

```
## FirstPrinciples: [Pregunta/Afirmación]

### Demolición
**Presupuestos detectados:**
- [Presupuesto] — origen: [costumbre / analogía / autoridad / etc.]

**Lo que queda tras la demolición:**
[Lo que es verificable directamente]

### Axiomas
1. [Hecho fundamental verificable]
2. [...]

### Reconstrucción
**Desde los axiomas anteriores:**
[Razonamiento paso a paso]

**Conclusión reconstruida:**
[Respuesta desde primeros principios]

### Delta con la respuesta convencional
[Sin diferencia / Diferencia en X / Contradicción en Y]
**Fuente del gap:** [por qué la convención difiere]
```

---

## Reglas generales

1. **Sin web search.** Estos modos son de razonamiento interno, no investigación externa. Si se necesitan datos, usar `/research` primero y luego `/thinking`.
2. **Sé implacable.** La utilidad de estos modos depende de no suavizar las conclusiones. Un council que solo dice lo que el usuario quiere oír no sirve. Un redteam que no encuentra fallos es un redteam que no ha trabajado.
3. **No mezcles modos.** Cada modo tiene una función específica. Si durante Council detectas que el plan tiene fallos graves, termina Council y sugiere hacer RedTeam.
4. **Puedes declinar.** Si el tema es demasiado vago para Council o RedTeam, pide que se concrete antes de continuar.
5. **Loguea en episódico.** Tras completar un modo de thinking en una decisión importante, registra con `memory_reflect.py` — los patrones de razonamiento que funcionan o fallan son lecciones valiosas.
