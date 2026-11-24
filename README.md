# Auren · Android 2.9.2

Auren es el nuevo nombre de AI Local. Mantiene `com.ailocal.app`, la firma de actualización, los modelos descargados, el historial y los ajustes. Su icono conserva el diseño elegido: tres formas curvas en coral, naranja y dorado, centradas sobre fondo espresso. Incluye recursos adaptativos y una variante monocroma para iconos temáticos y notificaciones.

Asistente Android con inferencia **dentro de la aplicación**, sin Termux, Python, Ollama ni servidores. La nueva app nativa se encuentra en `android/`; el antiguo prototipo Python de escritorio se eliminó del repositorio.

## Instalar

**[Descargar Auren-2.9.2.apk directamente](https://github.com/JohanCarrion1/AI-Local/releases/download/v2.9.2/Auren-2.9.2.apk)**

Abre ese archivo `.apk` en un teléfono **Android 8+ de 64 bits (ARM64)** e instálalo sobre la versión anterior. No hace falta descomprimirlo. Android debe identificarlo como **Auren 2.9.2**.

El antiguo `ai-local-hub-package.zip` era el proyecto Python de escritorio y no se instala en Android; ya no forma parte del repositorio.

Desde 2.1 se usa una clave debug pública y estable para que las siguientes actualizaciones mantengan la firma. Las versiones 2.0 anteriores usaban claves generadas en cada runner: Android puede exigir desinstalarlas antes de instalar 2.1, lo que elimina sus datos y modelos locales. Una publicación de producción debe usar una clave privada diferente. El paquete es `com.ailocal.app`; no reemplaza automáticamente el antiguo prototipo Kivy.

## Interfaz y personalización

La app abre directamente el chat. El menú hamburguesa contiene **Chat predeterminado**, **Conectar a GitHub** y **Descargar modelos**, con historial y búsqueda de conversaciones debajo. Nuevo chat conserva las conversaciones anteriores; cada una puede reabrirse desde el historial. La conversación única de 2.2 se migra automáticamente al historial local.

El perfil al pie del menú despliega los ajustes: nombre local, tema oscuro/claro/sistema, naranja predeterminado y otros acentos (azul, violeta, rosa, neutro y color personalizado), modelo preferido, carga automática opcional, contexto, máximo de respuesta e instrucciones del asistente. La opción de estadísticas y los recursos del dispositivo están en esos ajustes. Los colores y preferencias se guardan en el teléfono, y las barras del sistema siguen el tema claro u oscuro. Se conserva el paquete de actualización; no se conecta con Claude ni utiliza su servicio.

El historial se guarda en el almacenamiento local del WebView. No se sincroniza con cuentas externas y se elimina si se borran los datos de la app. Eliminar una conversación o todo el historial requiere confirmación; los modelos descargados y el token de GitHub se conservan. Solo hay una generación activa; cambiar de conversación o borrarla se bloquea mientras responde para evitar mezclar mensajes.

La carga muestra el progreso de los pesos y la preparación del contexto. Antes del primer token se muestra el procesamiento del mensaje y el tiempo transcurrido. Los errores de inferencia y las respuestas vacías quedan visibles con Reintentar; el mensaje enviado se conserva sin duplicarlo. Si Android interrumpe una respuesta, al reabrir se permite reintentar. El compositor no incluye una advertencia fija; las estadísticas son opcionales desde el perfil.

## Segundo plano y velocidad

El modelo y la generación pertenecen a `InferenceService`, independiente de la Activity y del WebView. Al cargar un modelo se inicia un servicio en primer plano de tipo `specialUse`, con notificación visible y acciones para volver, detener la generación o liberar el modelo de la RAM. Se solicita el permiso de notificaciones en Android 13+; denegarlo no impide la inferencia, aunque Android puede ocultar esa notificación del panel. El perfil también permite liberar la RAM sin borrar los archivos descargados.

Cambiar de app, volver o recrear la pantalla reconecta al mismo trabajo. El servicio guarda periódicamente la respuesta en un archivo atómico privado y sincroniza el resultado por identificador de conversación y petición, sin duplicarlo. Un bloqueo parcial de CPU mantiene el cálculo con la pantalla apagada solo mientras hay una carga o respuesta activa, con liberación al terminar, fallar o detenerse. El modelo queda disponible sin mantener despierta la CPU cuando está inactivo. No se reinicia una carga de varios GB sin intervención del usuario después de un cierre de proceso. Si Android reclama el proceso del WebView (la pantalla) mientras estás en otra app, la interfaz se reconstruye sola al volver y se reconecta a la respuesta en curso; el modelo y el servicio no se detienen. Android todavía puede finalizar la app por memoria insuficiente o por un cierre forzado; en ese caso se recupera el texto guardado, se indica la causa que reporta Android (memoria baja, error interno o cierre desde Recientes) y se ofrece reintentar.

Para reducir la espera entre turnos, el motor conserva la caché KV del prefijo exacto de tokens y procesa solo la parte nueva. Si cambian el historial, las instrucciones o el modelo se invalida la parte incompatible; en arquitecturas sin recorte parcial se vuelve al procesamiento completo. La caché visual se reutiliza solo si coinciden los píxeles, el tamaño y el prefijo de conversación; cambiar de foto obliga a codificarla de nuevo. La transmisión a pantalla se agrupa a un máximo de 20 actualizaciones por segundo, no se redibuja el WebView mientras está oculto y PSS se muestrea cada dos segundos. Se conservan los pesos completos y la cuantización elegida. El perfil permite respuestas directas o detalladas y visión ágil (256 tokens visuales) o detallada (512); más detalle visual consume más tiempo y memoria. Las ediciones Qwen3 con razonamiento reciben /no_think en modo directo para evitar razonamiento interno prolongado, y permite pensar en modo detallado.

El APK 2.6 incluye las variantes CPU oficiales de llama.cpp para ARM64: NEON básico, dot-product, FP16 e i8mm, además de variantes ARMv9. El motor selecciona por capacidades reales del procesador; no ejecuta instrucciones incompatibles ni requiere instalar dependencias en Termux. El pool deja de hacer espera activa y limita los hilos por afinidad/cuota CPU cuando el sistema la publica. El perfil muestra las capacidades del backend utilizado.

La lectura de imágenes utiliza selección determinista de tokens para evitar variaciones aleatorias en colores y texto. El proyector visual de Qwen2.5-VL (aprox. 0.85 GB) se abre únicamente al procesar una foto y se libera antes de generar texto. Los chats de texto con modelos visuales no mantienen ese proyector en RAM. Esto reduce presión de memoria y lecturas repetidas de pesos; la velocidad final sigue dependiendo del SoC, memoria disponible y temperatura.

## Uso

1. Menú → Descargar modelos: revisa RAM y espacio, pulsa Descargar y confirma el tamaño. Android mantiene la descarga al salir y reintenta interrupciones de red. Usa Cancelar para detenerla.
2. Cada archivo se verifica por tamaño y SHA-256 antes de habilitar Usar modelo. La verificación de varios GB puede tardar.
3. Pulsa Usar modelo. El motor llama.cpp integrado carga el GGUF y abre el chat.
4. Escribe y pulsa Enviar. Puedes detener la generación. Las conversaciones permanecen en el teléfono hasta eliminarlas desde el perfil o borrar los datos de la app. Nuevo chat conserva el historial.
5. Para fotos, carga un modelo de **Visión** (SmolVLM 500M o Qwen2.5-VL 7B si hay recursos), pulsa Imagen y selecciona una imagen con el selector de Android. Qwen Coder admite texto, no imágenes. Espera la miniatura con nombre y dimensiones antes de enviar. La foto se corrige por orientación EXIF y se reduce a un máximo de 1024 píxeles. Las copias privadas sobreviven al cambio de pantalla y permiten preguntar de nuevo por la última foto del chat; se conservan hasta 24 fotos y después se eliminan las más antiguas. Si falta el archivo se solicita adjuntarlo de nuevo, sin enviar silenciosamente un turno sin imagen. Borrar todo el historial elimina esas copias.
6. Menú → Conectar a GitHub: conecta un token de acceso personal, selecciona un repositorio y rama, abre una carpeta o archivo, edita el texto y revisa antes de guardar un commit. Puedes llevar el archivo al chat para pedir una revisión y copiar una respuesta al editor; revisa el resultado antes del commit. Si el archivo cambió remotamente, recárgalo: no se sobrescriben conflictos silenciosamente. No se ejecutan comandos del modelo ni se publican sus respuestas automáticamente. Pulsa Desconectar para borrar el token.

## Catálogo de descarga (37 opciones)

| Modelo | Cuantización | Descarga aprox. | Entrada |
|---|---|---:|---|
| Qwen3 Instruct 2507 · 4B | Q4_K_M | 2.50 GB | Texto |
| Qwen2.5‑VL Instruct · 3B | Q4_K_M | 2.77 GB | Texto + imagen |
| Qwen3‑VL Instruct · 4B | Q4_K_M | 2.95 GB | Texto + imagen |
| Phi‑4 Mini Instruct · 3.8B | Q4_K_M | 2.49 GB | Texto |
| MiniCPM‑V 4 · 4.1B | Q4_K_M | 3.15 GB | Texto + imagen |
| Qwen3 · 4B | Q4_K_M | 2.50 GB | Texto |
| Qwen Coder · 3B · precisión Q5 | Q5_K_M | 2.22 GB | Texto |
| Qwen Coder · 3B · precisión Q6 | Q6_K | 2.54 GB | Texto |
| Qwen3 Instruct 2507 · 4B · precisión Q5 | Q5_K_M | 2.89 GB | Texto |
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
| Qwen3 · 4B Abliterated (sin filtros) | Q4_K_M | 2.50 GB | Texto |
| Dolphin 3.0 · Qwen2.5 3B (sin censura) | Q4_K_M | 1.93 GB | Texto |
| Llama 3.2 · 3B Uncensored | Q4_K_M | 2.24 GB | Texto |
| Qwen Coder · 0.5B | Q4_K_M | 0.49 GB | Texto |
| Qwen Coder · 3B | Q4_K_M | 2.10 GB | Texto |
| SmolVLM · 500M | Q8_0 | 0.55 GB | Texto + imagen |

Las referencias y hashes se fijan en `android/app/src/main/assets/models.json`. Los modelos oficiales Qwen son de Qwen; la variante abliterated es comunitaria. Consulta licencias y fichas en los repositorios Hugging Face enlazados en el catálogo. La variante abliterated no mejora necesariamente la calidad. Las estimaciones de memoria no son garantías: el sistema operativo y otras apps consumen memoria. La vista inicial **Para tu celular · 2–6B** incluye los modelos ligeros nuevos, los modelos/versiones de 3B a 6B y variantes adicionales Q5/Q6. Q5 y Q6 aumentan precisión de cuantización, tamaño y RAM; no son modelos con más parámetros. **Grandes · 7B+** mantiene los modelos mayores y Todos conserva el catálogo completo. El anterior filtro 5B+ ocultaba el Coder 3B; ahora queda visible desde el inicio. El buscador y los filtros separan código, razonamiento, conversación y visión. Las tarjetas distinguen margen suficiente, margen ajustado, posible necesidad de más RAM libre y tamaños superiores a la RAM física visible. Descargar no garantiza que un teléfono pueda cargar el modelo. El motor usa CPU, hasta 4 hilos, contexto inicial de texto de 2048 (configurable hasta 4096), respuestas de hasta 4096 tokens y continuación automática acotada para respuestas más largas. En teléfonos básicos los modelos grandes pueden ser lentos o Android puede cerrar el proceso por falta de memoria.


## Recursos, estimación y prueba en el teléfono

**7B/8B son parámetros, no gigabytes de RAM requeridos.** Tampoco se exige un mínimo nominal de 8 GB: un teléfono de 8 GB puede mostrar alrededor de 7.2 GiB físicos por unidades y reservas del sistema. La versión 2.2 elimina los mínimos estáticos de RAM, el techo del 60% y el bloqueo por presupuesto estimado de 2.1.

Se muestran RAM física y disponibilidad actual por separado. Se consulta ActivityManager y, si es accesible, MemAvailable en procfs; se muestra también PSI, PSS y límites cgroup v2 legibles. El margen orientativo resta únicamente el mayor de 256 MiB y 1.10 veces el umbral de memoria baja, y respeta límites cgroup medidos. No recorta artificialmente la cifra según un porcentaje de RAM total ni sustituye la memoria libre por el máximo que pueda alcanzar tras cerrar otras apps. Presión/lowMemory se informan como señales; no se convierten en una deducción porcentual inventada. Se actualiza cada 10 segundos y antes de cargar.

Cada archivo tiene una estimación de pesos GGUF + caché KV por arquitectura y contexto + un intervalo de búferes. El catálogo registra los elementos de KV por token y su arquitectura de origen. Qwen, DeepSeek, Mistral, Phi y SmolVLM se calcularon a partir de sus configs de texto; Llama 3.1 8B y Gemma 2 9B usan las dimensiones publicadas de arquitectura. El cálculo es orientativo: mmap, páginas recuperables, repacking y el backend pueden variar el consumo real. `memoryEstimate` no representa una garantía ni un límite impuesto por Android.

El contexto de texto inicial es 1024 tokens y se puede elegir 512, 1024, 2048 o 4096; visión usa como mínimo 2048. El motor utiliza mmap, sin mlock, batch 128 y microbatch 64. Desactiva los buffers extra de repacking de pesos para evitar copias adicionales del modelo; esto prioriza memoria sobre posibles aceleraciones de ese backend. Intenta caché K Q8_0 y V F16; si el motor no admite esa configuración recurre a K/V F16 y lo informa. El intervalo de la tarjeta contempla este fallback. Se ofrecen Qwen Coder 7B Q3_K_M (3.81 GB) y Qwen3 8B Q3_K_M (4.12 GB), además de Q4; Q3 reduce tamaño con posible pérdida de precisión.

Con 5 GiB disponibles y un umbral bajo típico, el margen orientativo es aproximadamente 4.75 GiB. Qwen Coder 7B Q4 tiene unos 4.36 GiB solo en archivo: puede quedar justo con búferes; Q3 deja más margen. Ninguna estimación garantiza que cualquier 7B/8B funcione holgadamente en un teléfono concreto.

**Cargar modelo** abre directamente el chat con los pesos completos. No hay una prueba previa obligatoria, ni un modo demo, ni una generación sintética de 16 tokens. La estimación no bloquea un 7B/8B; si el motor no consigue asignar memoria se muestra su error real. Los archivos cuyo tamaño estimado supera toda la RAM física visible conservan una advertencia con la posibilidad de intentar la carga manualmente.

Las estadísticas se miden durante tus respuestas reales: tokens, tiempo hasta el primer token, velocidad de generación separada de la preparación visual y PSS máximo muestreado. Se puede elegir un máximo de respuesta de 256 a 2048 tokens, sujeto al espacio restante del contexto. Esto es una configuración de inferencia, no una restricción de prueba del modelo. Una respuesta corta que funcione no garantiza más memoria para todos los contextos o imágenes. Si una carga se interrumpe se informa al reabrir; solo se atribuye a memoria baja cuando Android lo confirma mediante ApplicationExitInfo.

La interfaz sigue dentro del contenedor nativo que reserva barras del sistema, recortes y teclado. Las pruebas Android 15 verifican retrato, paisaje e insets del teclado.

## Privacidad y GitHub

El chat distingue la conexión de GitHub de las capacidades del modelo. Una petición para conectar la cuenta muestra una guía con acceso directo al campo de token, incluso antes de cargar un modelo. **Sin token todavía no hay una cuenta conectada.** El botón Crear un token abre los ajustes oficiales de GitHub; selecciona los repositorios y los permisos Contents de lectura/escritura. Tras validarlo, se muestra la cuenta configurada. Los tokens rechazados y los permisos insuficientes se explican en la app.

Abre un archivo y pulsa **Usar archivo en el chat**. Se adjunta una copia local de hasta 10 000 caracteres, identificada por repositorio, rama, ruta y SHA; su tamaño debe caber en el contexto elegido del modelo. La app aporta al modelo su estado real de conexión y sus capacidades de lectura, propuesta y edición mediante la interfaz. El código se trata como material de referencia. La respuesta puede copiarse al editor tras revisarla; una propuesta asociada a un archivo no sustituye otro archivo ni una revisión distinta. Guardar en GitHub sigue requiriendo confirmar un commit y el servidor comprueba el SHA.

Un token pegado por accidente en el chat pasa al campo privado, sin guardarse como mensaje ni enviarse a inferencia. También se ocultan patrones de tokens de GitHub en las instrucciones, historial y código enviados al modelo. La copia seleccionada puede conservarse con la conversación y retirarse con × junto al compositor; no se consulta el repositorio en vivo durante cada respuesta.

Inferencia offline tras descargar y verificar el modelo. Solo las descargas (Hugging Face) y las operaciones explícitas con GitHub requieren red. El token se cifra con AES-GCM y una clave de Android Keystore; las copias de seguridad de la app están deshabilitadas. Se introduce en un campo privado transitorio, no se guarda en el historial ni en localStorage y no se entrega al modelo. Utiliza un token fine-grained limitado a los repositorios necesarios, con **Contents: Read and write** y Metadata de lectura. La app lista hasta 100 repositorios recientes y permite editar texto de hasta 512 KB. No hay sincronización automática ni edición autónoma de repositorios: los cambios se envían al confirmar Guardar.

## Compilar

JDK 17, Gradle 8.11.1, Android SDK 35, NDK 28.0.13004108 y CMake 3.22.1:

```sh
sdkmanager 'platforms;android-35' 'build-tools;35.0.0' 'ndk;28.0.13004108' 'cmake;3.22.1'
cd android
./gradlew testDebugUnitTest assembleDebug lintDebug
```

CMake obtiene llama.cpp del commit fijo `9581154a2250cc9e6948e4c2a2fc4b4e19d1a57e`, con soporte multimodal mtmd. APK contiene JNI, llama y mtmd; modelos se descargan separadamente. No requiere permisos generales de almacenamiento: los modelos están en almacenamiento propio de la app y las imágenes se abren con el selector del sistema.

Los kernels nativos se compilan con optimización `-O3` también en el APK debug. La preparación de texto y visión respeta `llama_n_batch(ctx)`; no se envían bloques de 256 tokens a un contexto configurado con batch 128. Detener también interrumpe el procesamiento CPU del contexto, además del bucle de generación.

Actions compila el motor real, ejecuta lint, exige un APK, verifica la firma y comprueba JNI, bibliotecas compartidas y plugins ARM64 dentro del paquete. Un workflow en verde demuestra compilación, **no** una prueba física de rendimiento o inferencia en cada teléfono.

## Pruebas

Actions ejecuta pruebas de disponibilidad real, estimación por cuantización/contexto, carga directa, catálogo y flujo completo de la interfaz, incluyendo temas, migración de historial, conversaciones y GitHub; el job `android-insets-test` compila para x86_64 y usa un emulador Android 15 para verificar el área segura, el botón Atrás con el menú abierto y que el tema claro también cambia el contenedor nativo. El APK de distribución sigue siendo ARM64. Los archivos se verifican por revisión, tamaño y SHA-256; no se ha probado cada modelo grande en un teléfono físico.

Ese job también instala un GGUF Qwen Coder 0.5B fijado y verificado por SHA-256 únicamente como fixture de ingeniería. `NativeChatTest` usa el WebView y el puente Java/JNI reales para cargarlo, responder al saludo reportado, procesar más de 128 tokens, mostrar un error de contexto y volver a responder. No se añade ningún modelo al APK ni una prueba obligatoria a la carga del usuario. `android/tests/native/InferenceRegression.java` permite repetir las regresiones JNI en host con los GGUF de 7B del catálogo.

La prueba Android también vuelve a Inicio durante la generación, espera su finalización sin recibir tokens en el WebView, vuelve al chat y recrea la Activity durante otra respuesta. Comprueba que se conserva la misma instancia del servicio y el modelo, que cada respuesta se importa una sola vez, que se reutilizan tokens y que el bloqueo de CPU se libera. `CacheRegression.java` verifica prefijo reutilizado, invalidación de sufijos y limpieza al volver a cargar el modelo en JNI de host. Las pruebas de interfaz cubren reconexión a respuestas en curso o completas, snapshots fuera de orden y recuperación de texto parcial tras un cierre de proceso.

### Prueba en teléfono

- Descargar 0.5B, verificar y cargar; desconectar internet y conversar, detener y crear nuevo chat.
- Descargar SmolVLM y su proyector; comparar respuestas sobre dos fotos distintas.
- Interrumpir red en una descarga, reabrir la app y comprobar recuperación; cancelar y reintentar.
- Crear una rama de prueba en GitHub, editar un archivo y verificar el commit; modificar el mismo archivo remotamente para comprobar el rechazo de SHA obsoleto.
- Probar 3B/7B solo con memoria suficiente y observar consumo/temperatura.

La identidad gráfica se documenta en `android/branding/README.md`.

La regresión visual de 2.6 usa el selector Android real con respuestas interceptadas de MediaStore: miniatura, recreación de Activity, envío al servicio y JNI, dos imágenes con píxeles distintos y reutilización de la misma foto en una pregunta posterior. En 2.7 la matriz ARM64 usa **los modelos móviles completos**: Qwen2.5‑VL 3B, Qwen3‑VL 4B y MiniCPM‑V 4. Exige respuestas diferentes a objetos rojos/azules sin dar colores en el prompt, además de comprobar la caché visual. Otro caso genera código Python con Qwen3 Instruct 2507 4B y valida su sintaxis y comportamiento como función pura. Las fixtures pequeñas del emulador son exclusivamente pruebas de integración y no sustituyen los modelos elegidos por el usuario. Los tiempos del runner no constituyen una medición del Samsung SM-A366E.

En 2.7 se incorporan Qwen3 Instruct 2507 4B, Qwen3 4B, Phi‑4 Mini 3.8B, Qwen2.5‑VL 3B, Qwen3‑VL 4B y MiniCPM‑V 4 (4.1B totales), además de tres variantes de precisión Q5/Q6. Las descargas visuales incluyen el proyector correspondiente y se verifican con SHA‑256. MiniCPM usa nombres locales propios para sus archivos. Las ediciones Instruct sin pensamiento no reciben `/no_think`. Las advertencias de memoria siguen basadas en recursos medidos; ser de 3B/4B no garantiza que todos los contextos o imágenes quepan. Gemma 3 4B se dejó fuera de la selección visual móvil porque su validación completa en CPU no terminó en un tiempo razonable; se priorizaron los tres modelos visuales que sí pasaron.

## Auren 2.8 — chat y continuidad

Saludo compacto y centrado; paleta HSV táctil con controles accesibles de tono, saturación y brillo y entrada HEX de 24 bits. La elección se aplica al instante y se conserva. El código de las respuestas se presenta en bloques desplazables y se copia sin alterar el original; el texto del modelo nunca se interpreta como HTML.

La inferencia sigue en el servicio de primer plano con bloqueo de CPU durante la generación. La pantalla se vuelve a conectar al reanudarse, al recuperar foco y mediante un refresco ligero independiente de las descargas y GitHub. Solo se actualiza el bloque que se está escribiendo, evitando reconstruir el historial por cada fragmento. En Personalización → Segundo plano se pueden abrir los ajustes de batería del teléfono; se muestra si Android restringe el proceso.

El motor informa si termina por EOS, cancelación, límite de respuesta o contexto. El contexto textual se desplaza cuando el modelo permite mover su KV: conserva el prefijo inicial y el texto más reciente en lugar de detener la generación al llenar la ventana. Cuando el historial excede la ventana se conservan su inicio y su tramo reciente; las referencias de archivos GitHub se mantienen completas y muestran un error si no caben; un mensaje nuevo demasiado grande sigue mostrando un error y puede requerir aumentar el contexto. Las imágenes y los modelos que no admiten desplazar KV conservan su límite de contexto. Una respuesta limitada por longitud ofrece Continuar; si se llena un contexto que no se puede desplazar, ofrece Ampliar contexto; no se presenta como una interrupción de Android. Las instalaciones nuevas usan un máximo de 1024 tokens; se respetan los ajustes guardados. Cerrar forzosamente el proceso o su eliminación por falta de memoria interrumpe la inferencia: se conserva la parte escrita y la opción de reintentar.

## Respuestas largas

El límite por respuesta sube a 2048 tokens por defecto (hasta 4096) y el contexto a 2048. Si una respuesta aún se corta por longitud, Auren continúa sola hasta 3 veces y une el texto en un único mensaje, de modo que el bloque de código no se parte. El botón "Continuar" sigue disponible si hace falta más.

## Cambios integrados en la compilación 2.9

Se reúne el catálogo ampliado, los modelos ligeros y las variantes comunitarias, la recomendación según los recursos del teléfono, la exportación de respuestas a PDF/DOCX/Markdown/HTML/TXT, la continuación automática de respuestas y la vista plegada del razonamiento. El icono conserva el diseño coral, naranja y dorado elegido por el usuario.

## Compilación y publicación

Un solo flujo, `.github/workflows/android.yml`, hace todo. Cada cambio en `main` compila el APK, ejecuta las pruebas de interfaz y publica ese mismo APK como Release (`Auren-<versión>.apk`). En ramas y compilaciones manuales solo se guarda el APK como artefacto; las pruebas pesadas de emulador y ARM64 corren en los pull requests. Ya no hay un segundo flujo de publicación.

## Pensar antes de responder

En Ajustes hay un interruptor. Apagado (por defecto), los Qwen3 híbridos reciben el bloque de razonamiento ya cerrado y responden directo, mucho más rápido. Encendido, razonan primero y el razonamiento aparece en un desplegable "Pensamiento". La velocidad (tokens por segundo) se muestra bajo cada respuesta.

## Archivos de código desde cualquier modelo

Cada bloque de código de una respuesta tiene su botón "Guardar nombre.ext" (por ejemplo `Guardar admin_store.py` o `Guardar index.html`). El nombre sale del archivo que el modelo menciona entre comillas invertidas o, si no lo menciona, del lenguaje del bloque; el texto se guarda tal cual, con la extensión correcta. Auren le indica a todos los modelos que entreguen los archivos así. "Guardar como…" sigue disponible para exportar la respuesta completa como .pdf, .docx, .md, .html o .txt.
