# AI-Local Gallery

![AI-Local Gallery Icon](assets/icon/icon.svg)

**AI-Local Gallery** es una aplicación para administrar modelos de IA de forma 100% local. Permite buscar, descargar y ejecutar modelos de HuggingFace Hub directamente en tu dispositivo sin necesidad de servidores externos.

## 📱 Características

- ✅ **Búsqueda dinámica**: Busca TODOS los modelos disponibles en HuggingFace Hub
- ✅ **Descarga con un clic**: Descarga modelos directamente desde la aplicación
- ✅ **Ejecución local**: Ejecuta modelos sin servidores (sin Ollama)
- ✅ **Soporte móvil**: Funciona en Android (Termux) y PC
- ✅ **Interfaz profesional**: Diseño tipo Google AI Gallery
- ✅ **Detección de recursos**: Recomienda modelos compatibles con tu dispositivo
- ✅ **Integración GitHub**: Conéctate con token para repositorios privados

## 🚀 Instalación

### Para Android (APK)

1. **Requisitos**:
   - Android 7.0+ (API 24+)
   - Buildozer
   - Python 3.8+

2. **Compilar la APK**:
   ```bash
   # Instalar Buildozer
   pip install buildozer
   
   # Inicializar Buildozer
   buildozer init
   
   # Compilar APK (esto puede tardar 1-2 horas)
   buildozer -v android debug
   
   # La APK se generará en: bin/
   ```

3. **Instalar la APK**:
   - Copia el archivo `bin/AI-Local-Gallery-1.0.0-debug.apk` a tu Android
   - Instálalo como cualquier otra APK

### Para PC (Desktop)

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/JohanCarrion1/AI-Local.git
   cd AI-Local
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar la aplicación**:
   ```bash
   # Opción 1: Usar el script principal (detecta plataforma automáticamente)
   python main.py
   
   # Opción 2: Ejecutar Streamlit directamente
   streamlit run app/gui/app.py
   ```

### Para Termux (Android)

1. **Actualizar paquetes**:
   ```bash
   pkg update && pkg upgrade
   ```

2. **Instalar dependencias**:
   ```bash
   pkg install python git
   pip install -r requirements.txt
   ```

3. **Ejecutar**:
   ```bash
   python main.py
   ```

## 📁 Estructura del Proyecto

```
AI-Local/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── model_manager.py      # Búsqueda y descarga de modelos
│   │   ├── executor.py           # Ejecución de modelos
│   │   ├── github_connector.py  # Conexión con GitHub
│   │   └── resource_detector.py # Detección de recursos
│   ├── gui/
│   │   ├── __init__.py
│   │   └── app.py                # Interfaz Streamlit (Desktop)
│   ├── mobile/
│   │   ├── __init__.py
│   │   └── main.py              # Interfaz Kivy (Mobile)
│   └── db/
│       ├── __init__.py
│       └── database.py           # Base de datos SQLite
├── assets/
│   └── icon/
│       └── icon.svg             # Icono de la aplicación
├── main.py                      # Punto de entrada principal
├── buildozer.spec               # Configuración para Buildozer
├── requirements.txt             # Dependencias Python
├── .github/
│   └── workflows/
│       └── ci.yml               # CI/CD Pipeline
└── README.md
```

## 🎨 Interfaz de Usuario

### Desktop (Streamlit)
- **Página de Galería**: Busca modelos con filtros por tarea, framework, lenguaje
- **Mis Modelos**: Lista de modelos descargados
- **Ejecutar**: Interfaz para ejecutar modelos con prompts
- **GitHub**: Conexión con token y navegación de repositorios
- **Configuración**: Información del sistema y limpieza

### Mobile (Kivy)
- **Pantalla de Galería**: Tarjetas de modelos con botones de descarga y ejecución
- **Mis Modelos**: Modelos descargados localmente
- **Ejecutar**: Interfaz para interactuar con modelos
- **Configuración**: Información del dispositivo

## 🔧 Configuración

### Token de HuggingFace
Para descargar modelos privados, configura tu token:
```python
from huggingface_hub import login
login(token="tu_token_aqui")
```

### Token de GitHub
Para acceder a repositorios privados:
```python
from app.core.github_connector import GitHubConnector
github = GitHubConnector(token="tu_github_token")
```

## 📦 Dependencias

Las dependencias principales incluyen:
- `huggingface_hub`: Para buscar y descargar modelos
- `transformers`: Para cargar y ejecutar modelos
- `torch`: Backend para modelos PyTorch
- `streamlit`: Interfaz web para desktop
- `kivy`: Interfaz nativa para móvil
- `psutil`: Detección de recursos del sistema
- `sqlite3`: Base de datos local

## 🤖 Modelos Recomendados

### Para dispositivos con 4-6GB RAM (como Samsung A36):
- `TinyLlama/TinyLlama-1.1B`
- `Qwen/Qwen2.5-Coder-0.5B`
- `distilbert-base-uncased`
- `google/mobilebert-uncased`

### Para dispositivos con 8GB+ RAM:
- `Qwen/Qwen2.5-Coder-1.5B`
- `Qwen/Qwen2.5-Coder-3B`
- `mistralai/Mistral-7B` (requiere ~14GB RAM)

## 📊 Detección de Recursos

La aplicación detecta automáticamente:
- Tipo de dispositivo (móvil/PC)
- RAM disponible
- Almacenamiento disponible
- GPU disponible (si hay)

Y recomienda modelos compatibles con tus recursos.

## 🔒 Privacidad

- Todos los modelos se descargan y ejecutan localmente
- No se envía información a servidores externos
- Los tokens se guardan localmente de forma segura

## 📜 Licencia

MIT License - © 2024 JohanCarrion1

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor abre un Issue o Pull Request en GitHub.

## 📞 Soporte

Si tienes problemas o preguntas, abre un Issue en el repositorio de GitHub.

---

**¡Disfruta de tu IA local!** 🎉
