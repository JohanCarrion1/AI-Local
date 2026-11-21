# AI Local · Android 2.3

Asistente Android con inferencia **dentro de la aplicación**, sin Termux, Python, Ollama ni servidores. La nueva app nativa se encuentra en `android/`; el prototipo Python se conserva para escritorio.

## Instalar

En **Actions → Android APK Build**, abre una ejecución de tu rama y descarga `ai-local-android-arm64`. Descomprime e instala `app-debug.apk` en un teléfono **Android 8+ de 64 bits (ARM64)**. Es una compilación de prueba, no una versión para Play Store. Desde 2.1 se usa una clave debug pública y estable para que las siguientes actualizaciones de prueba mantengan la firma. Las versiones 2.0 anteriores usaban claves generadas en cada runner: Android puede exigir desinstalarlas antes de instalar 2.1, lo que elimina sus datos y modelos locales. Una publicación de producción debe usar una clave privada diferente. El paquete nuevo es `com.ailocal.app`; no reemplaza automáticamente el antiguo prototipo Kivy.

## Interfaz y personalización

La app abre directamente el chat. El menú hamburguesa contiene **Chat predeterminado**, **Conectar a GitHub** y **Descargar modelos**, con historial y búsqueda de conversaciones debajo. Nuevo chat conserva las conversaciones anteriores; cada una puede reabrirse desde el historial. La conversación única de 2.2 se migra automáticamente al historial local.

El perfil al pie del menú despliega los ajustes: nombre local, tema oscuro/claro/sistema, naranja predeterminado y otros acentos (azul, violeta, rosa, neutro y color personalizado), modelo preferido, carga automática opcional, contexto, máximo de respuesta e instrucciones del asistente. La opción de estadísticas y los recursos del dispositivo están en esos ajustes. Los colores y preferencias se guardan en el teléfono, y las barras del sistema siguen el tema claro u oscuro. Se conserva la marca AI Local; no se conecta con Claude ni utiliza su servicio.

El historial se guarda en el almacenamiento local del WebView. No se sincroniza con cuentas externas y se elimina si se borran los datos de la app. Eliminar una conversación o todo el historial requiere confirmación; los modelos descargados y el token de GitHub se conservan. Solo hay una generación activa; cambiar de conversación o borrarla se bloquea mientras responde para evitar mezclar mensajes.

## Uso

1. Menú → Descargar modelos: revisa RAM y espacio, pulsa Descargar y confirma el tamaño. Android mantiene la descarga al salir y reintenta interrupciones de red. Usa Cancelar para detenerla.
2. Cada archivo se verifica por tamaño y SHA-256 antes de habilitar Usar modelo. La verificación de varios GB puede tardar.
3. Pulsa Usar modelo. El motor llama.cpp integrado carga el GGUF y abre el chat.
4. Escribe y pulsa Enviar. Puedes detener la generación. Las conversaciones permanecen en el teléfono hasta eliminarlas desde el perfil o borrar los datos de la app. Nuevo chat conserva el historial.
5. Para fotos, carga un modelo de **Visión** (SmolVLM 500M o Qwen2.5-VL 7B si hay recursos), pulsa Imagen y selecciona una imagen con el selector de Android. Qwen Coder admite texto, no imágenes. Se usa una foto por turno, reducida a un máximo de 1024 píxeles; el historial conserva texto, no las imágenes anteriores.
6. Menú → Conectar a GitHub: conecta un token de acceso personal, selecciona un repositorio y rama, abre una carpeta o archivo, edita el texto y revisa antes de guardar un commit. Puedes llevar el archivo al chat para pedir una revisión y copiar una respuesta al editor; revisa el resultado antes del commit. Si el archivo cambió remotamente, recárgalo: no se sobrescriben conflictos silenciosamente. No se ejecutan comandos del modelo ni se publican sus respuestas automáticamente. Pulsa Desconectar para borrar el token.

## Modelos incluidos (22 modelos; 19 de 5B o más)

| Modelo | Cuantización | Descarga aprox. | Entrada |
|---|---|---:|---|
| Qwen3 · 8B | Q4_K_M | 5.03 GB | Texto |
| Qwen3 · 8B · compacto Q3 | Q3_K_M | 4.12 GB | Texto |
| Qwen3 · 14B | Q4_K_M | 9.00 GB | Texto |
| Qwen3 · 32B | Q4_K_M | 19.76 GB | Texto |
| Qwen2.5 Instruct · 14B | Q4_K_M | 8.99 GB | Texto |
| Qwen2.5 Coder · 14B | Q4_K_M | 8.99 GB | Texto |
| Qwen2.5 Coder · 32B | Q4_K_M | 19.85 GB | Texto |
| DeepSeek R1 Distill Qwen · 7B | Q4_K_M | 4.68 GB | Texto |
| DeepSeek R1 Distill Qwen · 14B | Q4_K_M | 8.99 GB | Texto |
| DeepSeek R1 Distill Llama · 8B | Q4_K_M | 4.92 GB | Texto |
| Llama 3.1 Instruct · 8B | Q4_K_M | 4.92 GB | Texto |
| Mistral Instruct v0.3 · 7B | Q4_K_M | 4.37 GB | Texto |
| Mistral NeMo Instruct · 12B | Q4_K_M | 7.48 GB | Texto |
| Gemma 2 Instruct · 9B | Q4_K_M | 5.76 GB | Texto |
| Phi-4 · 14B | Q4_K_M | 9.05 GB | Texto |
| Qwen2.5-VL Instruct · 7B | Q4_K_M | 5.54 GB | Texto + imagen |
| Qwen Coder · 7B | Q4_K_M | 4.68 GB | Texto |
| Qwen Coder · 7B · compacto Q3 | Q3_K_M | 3.81 GB | Texto |
| Qwen Coder · 7B Abliterated | Q4_K_M | 4.68 GB | Texto |
| Qwen Coder · 0.5B | Q4_K_M | 0.49 GB | Texto |
| Qwen Coder · 3B | Q4_K_M | 2.10 GB | Texto |
| SmolVLM · 500M | Q8_0 | 0.55 GB | Texto + imagen |

Las referencias y hashes se fijan en `android/app/src/main/assets/models.json`. Los modelos oficiales Qwen son de Qwen; la variante abliterated es comunitaria. Consulta licencias y fichas en los repositorios Hugging Face enlazados en el catálogo. La variante abliterated no mejora necesariamente la calidad. Las estimaciones de memoria no son garantías: el sistema operativo y otras apps consumen memoria. La vista inicial prioriza los modelos de 5B o más; Todos conserva también las opciones ligeras. El buscador y los filtros separan código, razonamiento, conversación y visión. Las tarjetas distinguen margen suficiente, margen ajustado, posible necesidad de más RAM libre y tamaños superiores a la RAM física visible. Descargar no garantiza que un teléfono pueda cargar el modelo. El motor usa CPU, hasta 4 hilos, contexto inicial de texto 1024 (configurable hasta 4096) y un máximo configurable de respuesta hasta 2048 tokens, limitado por el contexto restante. En teléfonos básicos los modelos grandes pueden ser lentos o Android puede cerrar el proceso por falta de memoria.


## Recursos, estimación y prueba en el teléfono

**7B/8B son parámetros, no gigabytes de RAM requeridos.** Tampoco se exige un mínimo nominal de 8 GB: un teléfono de 8 GB puede mostrar alrededor de 7.2 GiB físicos por unidades y reservas del sistema. La versión 2.2 elimina los mínimos estáticos de RAM, el techo del 60% y el bloqueo por presupuesto estimado de 2.1.

Se muestran RAM física y disponibilidad actual por separado. Se consulta ActivityManager y, si es accesible, MemAvailable en procfs; se muestra también PSI, PSS y límites cgroup v2 legibles. El margen orientativo resta únicamente el mayor de 256 MiB y 1.10 veces el umbral de memoria baja, y respeta límites cgroup medidos. No recorta artificialmente la cifra según un porcentaje de RAM total ni sustituye la memoria libre por el máximo que pueda alcanzar tras cerrar otras apps. Presión/lowMemory se informan como señales; no se convierten en una deducción porcentual inventada. Se actualiza cada 10 segundos y antes de cargar.

Cada archivo tiene una estimación de pesos GGUF + caché KV por arquitectura y contexto + un intervalo de búferes. El catálogo registra los elementos de KV por token y su arquitectura de origen. Qwen, DeepSeek, Mistral, Phi y SmolVLM se calcularon a partir de sus configs de texto; Llama 3.1 8B y Gemma 2 9B usan las dimensiones publicadas de arquitectura. El cálculo es orientativo: mmap, páginas recuperables, repacking y el backend pueden variar el consumo real. `memoryEstimate` no representa una garantía ni un límite impuesto por Android.

El contexto de texto inicial es 1024 tokens y se puede elegir 512, 1024, 2048 o 4096; visión usa como mínimo 2048. El motor utiliza mmap, sin mlock, batch 128 y microbatch 64. Desactiva los buffers extra de repacking de pesos para evitar copias adicionales del modelo; esto prioriza memoria sobre posibles aceleraciones de ese backend. Intenta caché K Q8_0 y V F16; si el motor no admite esa configuración recurre a K/V F16 y lo informa. El intervalo de la tarjeta contempla este fallback. Se ofrecen Qwen Coder 7B Q3_K_M (3.81 GB) y Qwen3 8B Q3_K_M (4.12 GB), además de Q4; Q3 reduce tamaño con posible pérdida de precisión.

Con 5 GiB disponibles y un umbral bajo típico, el margen orientativo es aproximadamente 4.75 GiB. Qwen Coder 7B Q4 tiene unos 4.36 GiB solo en archivo: puede quedar justo con búferes; Q3 deja más margen. Ninguna estimación garantiza que cualquier 7B/8B funcione holgadamente en un teléfono concreto.

**Cargar modelo** abre directamente el chat con los pesos completos. No hay una prueba previa obligatoria, ni un modo demo, ni una generación sintética de 16 tokens. La estimación no bloquea un 7B/8B; si el motor no consigue asignar memoria se muestra su error real. Los archivos cuyo tamaño estimado supera toda la RAM física visible conservan una advertencia con la posibilidad de intentar la carga manualmente.

Las estadísticas se miden durante tus respuestas reales: tokens, tiempo incluyendo preparación y PSS máximo muestreado. Se puede elegir un máximo de respuesta de 256 a 2048 tokens, sujeto al espacio restante del contexto. Esto es una configuración de inferencia, no una restricción de prueba del modelo. Una respuesta corta que funcione no garantiza más memoria para todos los contextos o imágenes. Si una carga se interrumpe se informa al reabrir; solo se atribuye a memoria baja cuando Android lo confirma mediante ApplicationExitInfo.

La interfaz sigue dentro del contenedor nativo que reserva barras del sistema, recortes y teclado. Las pruebas Android 15 verifican retrato, paisaje e insets del teclado.

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

Actions ejecuta pruebas de disponibilidad real, estimación por cuantización/contexto, carga directa, catálogo y flujo completo de la interfaz, incluyendo temas, migración de historial, conversaciones y GitHub; el job `android-insets-test` compila para x86_64 y usa un emulador Android 15 para verificar el área segura, el botón Atrás con el menú abierto y que el tema claro también cambia el contenedor nativo. El APK de distribución sigue siendo ARM64. Los archivos se verifican por revisión, tamaño y SHA-256; no se ha probado cada modelo grande en un teléfono físico.

### Prueba en teléfono

- Descargar 0.5B, verificar y cargar; desconectar internet y conversar, detener y crear nuevo chat.
- Descargar SmolVLM y su proyector; comparar respuestas sobre dos fotos distintas.
- Interrumpir red en una descarga, reabrir la app y comprobar recuperación; cancelar y reintentar.
- Crear una rama de prueba en GitHub, editar un archivo y verificar el commit; modificar el mismo archivo remotamente para comprobar el rechazo de SHA obsoleto.
- Probar 3B/7B solo con memoria suficiente y observar consumo/temperatura.

El icono vectorial original combina un monograma arquitectónico, un núcleo vertical y una estrella de cuatro puntas. Los archivos Python y su CI heredado siguen siendo independientes del APK.
