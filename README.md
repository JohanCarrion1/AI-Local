# AI Local · Android 2.1

Asistente Android con inferencia **dentro de la aplicación**, sin Termux, Python, Ollama ni servidores. La nueva app nativa se encuentra en `android/`; el prototipo Python se conserva para escritorio.

## Instalar

En **Actions → Android APK Build**, abre una ejecución de tu rama y descarga `ai-local-android-arm64`. Descomprime e instala `app-debug.apk` en un teléfono **Android 8+ de 64 bits (ARM64)**. Es una compilación de prueba, no una versión para Play Store. Desde 2.1 se usa una clave debug pública y estable para que las siguientes actualizaciones de prueba mantengan la firma. Las versiones 2.0 anteriores usaban claves generadas en cada runner: Android puede exigir desinstalarlas antes de instalar 2.1, lo que elimina sus datos y modelos locales. Una publicación de producción debe usar una clave privada diferente. El paquete nuevo es `com.ailocal.app`; no reemplaza automáticamente el antiguo prototipo Kivy.

## Uso

1. Biblioteca: revisa RAM y espacio, pulsa Descargar y confirma el tamaño. Android mantiene la descarga al salir y reintenta interrupciones de red. Usa Cancelar para detenerla.
2. Cada archivo se verifica por tamaño y SHA-256 antes de habilitar Usar modelo. La verificación de varios GB puede tardar.
3. Pulsa Usar modelo. El motor llama.cpp integrado carga el GGUF y abre Chat local.
4. Escribe y pulsa Enviar. Puedes detener la generación. Las conversaciones permanecen en el teléfono hasta iniciar un chat nuevo o borrar los datos de la app.
5. Para fotos, carga un modelo de **Visión** (SmolVLM 500M o Qwen2.5-VL 7B si hay recursos), pulsa Imagen y selecciona una imagen con el selector de Android. Qwen Coder admite texto, no imágenes. Se usa una foto por turno, reducida a un máximo de 1024 píxeles; el historial conserva texto, no las imágenes anteriores.
6. GitHub: conecta un token de acceso personal, selecciona un repositorio y rama, abre una carpeta o archivo, edita el texto y revisa antes de guardar un commit. Puedes llevar el archivo al chat para pedir una revisión y copiar una respuesta al editor; revisa el resultado antes del commit. Si el archivo cambió remotamente, recárgalo: no se sobrescriben conflictos silenciosamente. No se ejecutan comandos del modelo ni se publican sus respuestas automáticamente. Pulsa Desconectar para borrar el token.

## Modelos incluidos (20 modelos; 17 de 5B o más)

| Modelo | Parámetros | Descarga aprox. | RAM total mínima / presupuesto IA estimado | Entrada |
|---|---:|---:|---:|---|
| Qwen3 · 8B | 8B | 5.03 GB | 8 / 6.5 GB | Texto |
| Qwen3 · 14B | 14B | 9.00 GB | 16 / 11 GB | Texto |
| Qwen3 · 32B | 32B | 19.76 GB | 32 / 24 GB | Texto |
| Qwen2.5 Instruct · 14B | 14B | 8.99 GB | 16 / 11 GB | Texto |
| Qwen2.5 Coder · 14B | 14B | 8.99 GB | 16 / 11 GB | Texto |
| Qwen2.5 Coder · 32B | 32B | 19.85 GB | 32 / 24 GB | Texto |
| DeepSeek R1 Distill Qwen · 7B | 7B | 4.68 GB | 8 / 6 GB | Texto |
| DeepSeek R1 Distill Qwen · 14B | 14B | 8.99 GB | 16 / 11 GB | Texto |
| DeepSeek R1 Distill Llama · 8B | 8B | 4.92 GB | 10 / 7 GB | Texto |
| Llama 3.1 Instruct · 8B | 8B | 4.92 GB | 10 / 7 GB | Texto |
| Mistral Instruct v0.3 · 7B | 7B | 4.37 GB | 8 / 6 GB | Texto |
| Mistral NeMo Instruct · 12B | 12B | 7.48 GB | 16 / 10.5 GB | Texto |
| Gemma 2 Instruct · 9B | 9B | 5.76 GB | 12 / 8.5 GB | Texto |
| Phi-4 · 14B | 14B | 9.05 GB | 16 / 12 GB | Texto |
| Qwen2.5-VL Instruct · 7B | 7B | 5.54 GB | 12 / 8 GB | Texto + imagen |
| Qwen Coder · 7B | 7B | 4.68 GB | 8 / 6 GB | Texto |
| Qwen Coder · 7B Abliterated | 7B | 4.68 GB | 8 / 6 GB | Texto |
| Qwen Coder · 0.5B | 0.5B | 0.49 GB | 2 / 1.5 GB | Texto |
| Qwen Coder · 3B | 3B | 2.10 GB | 5 / 3.5 GB | Texto |
| SmolVLM · 500M | 0.5B | 0.55 GB | 3 / 2.2 GB | Texto + imagen |

Las referencias y hashes se fijan en `android/app/src/main/assets/models.json`. Los modelos oficiales Qwen son de Qwen; la variante abliterated es comunitaria. Consulta licencias y fichas en los repositorios Hugging Face enlazados en el catálogo. La variante abliterated no mejora necesariamente la calidad. Las recomendaciones de RAM son estimaciones, no garantías: el sistema operativo y otras apps consumen memoria. La vista inicial prioriza los modelos de 5B o más; Todos conserva también las opciones ligeras. El buscador y los filtros separan código, razonamiento, conversación y visión. «No recomendado» se muestra con el motivo cuando falta RAM total, presupuesto utilizable o almacenamiento. Descargar no garantiza que un teléfono pueda cargar el modelo. El motor usa CPU, hasta 4 hilos, contexto 4096 y hasta 512 tokens de respuesta. En teléfonos básicos los modelos grandes pueden ser lentos o Android puede cerrar el proceso por falta de memoria.


## Recursos reales y barras del dispositivo

La RAM total física se muestra separada de la RAM libre del sistema y del **presupuesto IA estimado**. El presupuesto nunca se calcula suponiendo que toda la RAM física está disponible.

Se consulta `ActivityManager.MemoryInfo` y se contrasta `MemAvailable` en `/proc/meminfo` cuando puede leerse. Se reserva el mayor de 512 MiB, el 8% de la RAM total o 1.25 veces el umbral de memoria baja. Además, se aplica un techo prudente del 60% de la RAM total para dejar margen a Android y otras apps. Ese techo es una política de la aplicación, no un límite garantizado del sistema operativo. Si existen límites cgroup v2, se utiliza también el margen restante de sus ancestros. Con presión PSI de memoria se reduce la estimación; con `lowMemory` el presupuesto es cero. La lectura de procfs/cgroup/PSI puede estar restringida en Android: se informa del fallback y no se inventan mediciones.

Ejemplo: 7.2 GiB totales y 2.5 GiB libres dan alrededor de 1.9 GiB de presupuesto IA, dependiendo del umbral de Android. En un equipo de esa clase nunca se presupuestan los 7.2 GiB para inferencia, ni más de 4.5 GiB incluso si el sistema informa de mucha memoria recuperable. Se muestran también PSS y heap nativo de la app en los detalles.

Las cifras se actualizan cada 10 segundos y antes de cargar un modelo, después de liberar el anterior. Si el presupuesto actual no cubre la estimación del modelo, se conserva la descarga y se rechaza la carga con una explicación. Los requisitos de cada modelo son estimaciones conservadoras para contexto 4096, no garantías de ejecución.

La interfaz está dentro de un `FrameLayout` nativo que reserva los insets de barras, recortes y teclado, con 8 dp adicionales sobre el encabezado. No se usa padding del WebView como sustituto del área segura. Las pruebas Android verifican los límites del viewport en retrato y paisaje en un emulador Android 15.

## Privacidad y GitHub

Inferencia offline tras descargar y verificar el modelo. Solo las descargas (Hugging Face) y las operaciones explícitas con GitHub requieren red. El token se cifra con AES-GCM y una clave de Android Keystore; las copias de seguridad de la app están deshabilitadas. Nunca se guarda en JavaScript ni se entrega al modelo. Utiliza un token fine-grained limitado a los repositorios necesarios, con **Contents: Read and write** y Metadata de lectura. La app lista hasta 100 repositorios recientes y permite editar texto de hasta 512 KB. No hay sincronización automática ni edición autónoma de repositorios: los cambios se envían al confirmar Guardar.

## Compilar

JDK 17, Gradle 8.11.1, Android SDK 35, NDK 28.0.13004108 y CMake 3.22.1:

```sh
sdkmanager 'platforms;android-35' 'build-tools;35.0.0' 'ndk;28.0.13004108' 'cmake;3.22.1'
cd android
./gradlew testDebugUnitTest assembleDebug lintDebug
```

CMake obtiene llama.cpp del commit fijo `9581154a2250cc9e6948e4c2a2fc4b4e19d1a57e`, con soporte multimodal mtmd. APK contiene JNI, llama y mtmd; modelos se descargan separadamente. No requiere permisos generales de almacenamiento: los modelos están en almacenamiento propio de la app y las imágenes se abren con el selector del sistema.

Actions compila el motor real, ejecuta lint, exige un APK, verifica la firma y comprueba la biblioteca JNI dentro del paquete. Un workflow en verde demuestra compilación, **no** una prueba física de rendimiento o inferencia en cada teléfono.

## Pruebas

Actions ejecuta pruebas de presupuesto de RAM, catálogo e interfaz; el job `android-insets-test` compila para x86_64 y usa un emulador Android 15 para verificar que el WebView queda fuera de las barras del sistema. El APK de distribución sigue siendo ARM64. Los nuevos archivos de modelos se verifican por revisión, tamaño y SHA-256, pero no se ha ejecutado inferencia con cada modelo grande en un teléfono.

### Prueba en teléfono

- Descargar 0.5B, verificar y cargar; desconectar internet y conversar, detener y crear nuevo chat.
- Descargar SmolVLM y su proyector; comparar respuestas sobre dos fotos distintas.
- Interrumpir red en una descarga, reabrir la app y comprobar recuperación; cancelar y reintentar.
- Crear una rama de prueba en GitHub, editar un archivo y verificar el commit; modificar el mismo archivo remotamente para comprobar el rechazo de SHA obsoleto.
- Probar 3B/7B solo con memoria suficiente y observar consumo/temperatura.

El icono vectorial original combina un monograma arquitectónico, un núcleo vertical y una estrella de cuatro puntas. Los archivos Python y su CI heredado siguen siendo independientes del APK.
