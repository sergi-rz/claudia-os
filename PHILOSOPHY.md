# Filosofía de Claudia OS

## El problema

Los asistentes de IA actuales tienen un defecto de fondo: no te conocen. Cada conversación empieza de cero. No saben a qué te dedicas, cómo trabajas, qué tienes pendiente, ni qué decidiste la semana pasada. Y los que sí guardan contexto, lo guardan en la nube de otra empresa, bajo sus condiciones, con su modelo de negocio.

El resultado es que tienes quince herramientas que no se hablan entre sí, y un asistente de IA que es brillante pero amnésico.

## La idea central

Tu asistente debería vivir donde tú controlas. En un repositorio tuyo, con tus datos, bajo tus reglas.

Te conoce porque lo tiene escrito, en ficheros que tú posees, que puedes leer, editar y llevar contigo si cambias de herramienta.

## Principios de diseño

**1. Tus datos son tuyos.**
La identidad, la memoria, los workspaces, las credenciales... todo vive en `user/`, que nunca se toca en actualizaciones del core. Tu instancia es tuya. El proyecto es el framework; lo personal es tuyo.

**2. Continuidad real.**
El asistente recuerda porque tiene memoria persistente en ficheros. No es una ilusión de continuidad dentro de una ventana de contexto, es un sistema de memoria que sobrevive entre conversaciones.

**3. Un único asistente.**
Correo, calendario, tareas, investigación, brainstorming, generación de contenido... todo desde una sola conversación, con el mismo asistente que ya te conoce. Sin cambiar de pestaña.

**4. Extendible sin romper lo que funciona.**
La separación estricta entre `core/` y `user/` garantiza que puedes actualizar el núcleo de Claudia OS sin perder tu configuración ni tu contexto. Y puedes añadir skills propias sin tocar el core y puedes integrar skills nuevas personalizadas para tu contexto a través del sistema de blueprints.

**5. No es un producto cerrado, es un sistema vivo.**
Este repositorio tiene funcionalidades básicas que puedes utilizar desde el primer momento, pero a partir de ese punto inicial tu Claudia va a ir mutando a medida que la utilices. Cada corrección que le haces, cada skill que añades, cada preferencia que aprende, cada workspace que configuras... todo eso va convirtiendo tu instancia en algo que ya no se parece a la de nadie más.

Y eso es exactamente lo que tiene que pasar. Un asistente que te conoce de verdad no puede ser igual que el de otro. Tus proyectos son distintos, tus clientes son distintos, tu forma de trabajar es distinta. Un sistema que intenta ser el mismo para todos acaba sin ser realmente útil para ninguno.

Las divergencias entre las versiones de un usuario y otro son la norma general, no la excepción. Dos personas que instalen Claudia OS hoy y la usen durante un mes van a acabar con sistemas que comparten el mismo core pero que funcionan de forma completamente diferente. Eso no es un problema de fragmentación: es la prueba de que el sistema está haciendo lo que tiene que hacer.

No tengas miedo de adaptar Claudia a tus necesidades. Mientras mantengas la separación entre `core/` y `user/`, puedes moldearla todo lo que quieras sin que las actualizaciones del framework rompan nada.

## Inspiración

Varias funcionalidades de Claudia OS beben de la metodología de [PAI (Personal AI Infrastructure)](https://github.com/danielmiessler/Personal_AI_Infrastructure) de Daniel Miessler. La idea de fondo (que cada persona debería tener su propia infraestructura de IA, no depender de la de otra empresa) viene de ahí.

Claude Code como plataforma lo hace posible: un LLM con acceso real al sistema de ficheros, con memoria de contexto larga, con capacidad de ejecutar código y llamar a APIs. No es un chatbot con plugins: es una CLI con agentes reales.

## Lo que Claudia no intenta ser

- **Una app cerrada.** Si necesitas una interfaz pulida lista para usar, hay productos mejores. Claudia es un repo que tú configuras.
- **Un sistema para equipos.** Es deliberadamente personal. Un asistente, un usuario, un contexto.
- **Una plataforma en la nube de otro.** Tus datos viven en tu máquina o tu servidor, no en el nuestro.
- **Cero mantenimiento.** Las integraciones requieren credenciales, las skills evolucionan, el sistema es tuyo y lo cuidas tú.

## Objetivo a largo plazo

Que cualquier profesional autónomo pueda tener un asistente de IA que le conozca de verdad: su trabajo, sus clientes, sus proyectos, sus preferencias. No un chatbot genérico, sino un sistema personalizado, que crezca con él, y que no dependa de que ninguna empresa decida cambiar su modelo de negocio.

Claudia OS es la versión inicial de eso. Funcionalmente es útil hoy. El objetivo es que mejore con cada versión sin dejar de ser tuyo.
