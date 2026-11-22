# Auren

Identidad minimalista: un monograma A de dos trazos afinados sobre negro carbón, con un corte central de espacio negativo. La referencia de estilo elegida por el usuario fue la sencillez monocroma de Grok. El monograma mantiene una construcción propia.

- `auren-master.png`: arte maestro generado con ImageGen; se conserva a alta resolución.
- `res/drawable-nodpi/auren_artwork.png`: primer plano transparente 512 × 512 para el launcher; derivado del arte maestro con la misma silueta.
- `assets/auren-mark.png`: versión 160 × 160 para el chat y el menú.
- `res/mipmap-anydpi-v26/ic_launcher.xml`: icono adaptativo; el primer plano tiene margen para las máscaras del launcher.
- `res/mipmap-anydpi-v33/ic_launcher.xml`: añade la variante temática monocroma.
- `res/drawable/ic_launcher_monochrome.xml`: misma silueta y escala del primer plano, para iconos temáticos.
- `res/drawable-nodpi/auren_notification.png`: silueta blanca con margen propio para tamaños pequeños.
- `res/drawable/ic_launcher.xml`: recurso de notificación que usa esa silueta.

El monograma queda dentro del área central del icono adaptativo, con margen para recortes circulares y esquinas redondeadas. Los PNG de distribución se obtienen del maestro con ImageMagick: máscara de luminancia, transparencia y tamaños de recurso; no se añaden elementos nuevos al emblema.

Las rutas `res/` y `assets/` son relativas a `android/app/src/main/`. El package ID y la clave de firma permanecen iguales para actualizar la app existente.
