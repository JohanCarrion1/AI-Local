# Auren

El usuario eligió el emblema de tres formas curvas en coral, naranja y dorado, sin letras. `auren-master.png` conserva el primer plano transparente preparado con ImageGen a partir de esa imagen.

- `res/drawable-nodpi/auren_artwork.png`: primer plano transparente de 512 × 512. El emblema se recorta por su silueta visible, se reduce proporcionalmente a un máximo de 288 × 288 y se centra con márgenes simétricos. El lienzo de origen no determina su posición en Android.
- `res/drawable/ic_launcher_foreground.xml`: inset uniforme de 4 dp sobre ese lienzo cuadrado; evita anclajes inferiores y mantiene la proporción.
- `res/drawable/ic_launcher_background.xml`: fondo espresso uniforme `#1C0E09`.
- `assets/auren-mark.png`: versión de 160 × 160 del mismo emblema centrado para el chat y menú.
- `res/mipmap-anydpi-v26/ic_launcher.xml`: icono adaptativo para máscaras de launcher.
- `res/mipmap-anydpi-v33/ic_launcher.xml`: incorpora la versión temática monocroma con la misma posición y escala.
- `res/drawable/ic_launcher_monochrome.xml`: misma silueta del primer plano, teñida por Android.
- `res/drawable-nodpi/auren_notification.png`: silueta blanca de 192 × 192, centrada y con margen para notificaciones.
- `res/drawable/ic_launcher.xml`: recurso de notificación que usa esa silueta.

Los PNG de distribución se preparan con ImageMagick: normalización de alfa para quitar píxeles aislados del recorte, escala proporcional, centrado y tamaños de recurso. El emblema no se estira ni se desplaza al fondo. Se comprueban los márgenes y el área segura circular del primer plano.

Las rutas `res/` y `assets/` son relativas a `android/app/src/main/`. Se mantiene el package ID y la clave de firma para actualizar la app existente sin cambiar los modelos o conversaciones.
