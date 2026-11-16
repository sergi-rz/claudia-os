# Personalizar claudia-scrape

Para ajustar cómo funciona esta skill, crea el fichero `user/behavior.md` dentro de esta carpeta y
escribe ahí lo que quieres cambiar, en lenguaje natural. También puedes pedírselo a Claudia y lo
crea ella.

Lo que escribas se aplica sobre el comportamiento por defecto; si choca con él, gana lo tuyo.
Las actualizaciones de Claudia (`claudia-update`) no tocan nunca la carpeta `user/`.

Este fichero es solo de ejemplo: la skill no lo lee.

## Ideas

- Cambiar el formato de presentación de tweets (sin métricas, solo texto y autor)
- Activar siempre el modo full-thread para URLs de X por defecto
- Añadir el idioma detectado al encabezado del contenido extraído
- Truncar artículos largos a los primeros N caracteres cuando se usan como librería
