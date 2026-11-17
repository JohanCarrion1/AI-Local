# AI Local · Android

Asistente Android con inferencia **dentro de la aplicación**, sin Termux, Python, Ollama ni servidores. La nueva app nativa se encuentra en `android/`; el prototipo Python se conserva para escritorio.

## Instalar

En **Actions → Android APK Build**, abre una ejecución de tu rama y descarga `ai-local-android-arm64`. Descomprime e instala `app-debug.apk` en un teléfono **Android 8+ de 64 bits (ARM64)**. Es una compilación de prueba firmada con clave debug, no una versión para Play Store. El paquete nuevo es `com.ailocal.app`; no reemplaza automáticamente el antiguo prototipo Kivy.

## Uso

1. Biblioteca: revisa RAM y espacio, pulsa Descargar y confirma el tamaño. Android mantiene la descarga al salir y reintenta interrupciones de red. Usa Cancelar para detenerla.
2. Cada archivo se verifica por tamaño y SHA-256 antes de habilitar Usar modelo. La verificación de varios GB puede tardar.
3. Pulsa Usar modelo. El motor llama.cpp integrado carga el GGUF y abre Chat local.
4. Escribe y pulsa Enviar. Puedes detener la generación. Las conversaciones permanecen en el teléfono hasta iniciar un chat nuevo o borrar los datos de la app.
5. Para fotos, carga **SmolVLM 500M**, pulsa Imagen y selecciona una imagen con el selector de Android. Qwen Coder admite texto, no imágenes. Se usa una foto por turno, reducida a un máximo de 1024 píxeles; el historial conserva texto, no las imágenes anteriores.
6. GitHub: conecta un token de acceso personal, selecciona un repositorio y rama, abre una carpeta o archivo, edita el texto y revisa antes de guardar un commit. Si el archivo cambió remotamente, recárgalo: no se sobrescriben conflictos silenciosamente. No se ejecutan comandos del modelo ni se publican sus respuestas automáticamente. Pulsa Desconectar para borrar el token.

## Modelos incluidos

| Modelo | Descarga aproximada | RAM total orientativa | Entrada |
|---|---:|---:|---|
| Qwen2.5-Coder 0.5B Instruct Q4_K_M | 0.49 GB | 2–3 GB | Texto |
| Qwen2.5-Coder 3B Instruct Q4_K_M | 2.10 GB | 5–6 GB | Texto |
| Qwen2.5-Coder 7B Instruct Q4_K_M | 4.68 GB | 8–12 GB | Texto |
| Qwen2.5-Coder 7B Instruct abliterated Q4_K_M (bartowski) | 4.68 GB | 8–12 GB | Texto |
| SmolVLM 500M Instruct Q8_0 + proyector Q8_0 | 0.55 GB | 3–4 GB | Texto + imagen |

Las referencias y hashes se fijan en `android/app/src/main/assets/models.json`. Los modelos oficiales Qwen son de Qwen; la variante abliterated es comunitaria. Consulta licencias y fichas en los repositorios Hugging Face enlazados en el catálogo. La variante abliterated no mejora necesariamente la calidad. Las recomendaciones de RAM son estimaciones, no garantías: el sistema operativo y otras apps consumen memoria. Se muestra también RAM libre; empezar por 0.5B es prudente. El motor usa CPU, hasta 4 hilos, contexto 4096 y hasta 512 tokens de respuesta. En teléfonos básicos los modelos grandes pueden ser lentos o Android puede cerrar el proceso por falta de memoria.

## Privacidad y GitHub

Inferencia offline tras descargar y verificar el modelo. Solo las descargas (Hugging Face) y las operaciones explícitas con GitHub requieren red. El token se cifra con AES-GCM y una clave de Android Keystore; las copias de seguridad de la app están deshabilitadas. Nunca se guarda en JavaScript ni se entrega al modelo. Utiliza un token fine-grained limitado a los repositorios necesarios, con **Contents: Read and write** y Metadata de lectura. La app lista hasta 100 repositorios recientes y permite editar texto de hasta 512 KB. No hay sincronización automática ni edición autónoma de repositorios: los cambios se envían al confirmar Guardar.

## Compilar

JDK 17, Gradle 8.11.1, Android SDK 35, NDK 28.0.13004108 y CMake 3.22.1:

```sh
sdkmanager 'platforms;android-35' 'build-tools;35.0.0' 'ndk;28.0.13004108' 'cmake;3.22.1'
gradle -p android assembleDebug lintDebug
```

CMake obtiene llama.cpp del commit fijo `9581154a2250cc9e6948e4c2a2fc4b4e19d1a57e`, con soporte multimodal mtmd. APK contiene JNI, llama y mtmd; modelos se descargan separadamente. No requiere permisos generales de almacenamiento: los modelos están en almacenamiento propio de la app y las imágenes se abren con el selector del sistema.

Actions compila el motor real, ejecuta lint, exige un APK, verifica la firma y comprueba la biblioteca JNI dentro del paquete. Un workflow en verde demuestra compilación, **no** una prueba física de rendimiento o inferencia en cada teléfono.

## Prueba en teléfono

- Descargar 0.5B, verificar y cargar; desconectar internet y conversar, detener y crear nuevo chat.
- Descargar SmolVLM y su proyector; comparar respuestas sobre dos fotos distintas.
- Interrumpir red en una descarga, reabrir la app y comprobar recuperación; cancelar y reintentar.
- Crear una rama de prueba en GitHub, editar un archivo y verificar el commit; modificar el mismo archivo remotamente para comprobar el rechazo de SHA obsoleto.
- Probar 3B/7B solo con memoria suficiente y observar consumo/temperatura.

El icono vectorial original combina un monograma arquitectónico, un núcleo vertical y una estrella de cuatro puntas. Los archivos Python y su CI heredado siguen siendo independientes del APK.
