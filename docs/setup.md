# Guía de Instalación - AI-Local-Hub

## 📋 Requisitos Previos

### Para PC (Windows/Linux/Mac)
- Python 3.10 o superior
- Git
- 4GB+ de RAM (recomendado 8GB+ para modelos de 7B)
- GPU con CUDA (opcional, para mejor rendimiento)

### Para Android (Termux)
- Aplicación Termux (desde F-Droid)
- Termux:PR (para instalar paquetes de Python)
- Al menos 4GB de RAM
- 2GB+ de espacio libre

---

## 💻 Instalación en PC

### 1. Clonar el repositorio
```bash
git clone https://github.com/JohanCarrion1/AI-Local.git
cd AI-Local
```

### 2. Crear entorno virtual
```bash
# Linux/Mac
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. (Opcional) Instalar Ollama para gestión de modelos
```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Descargar desde https://ollama.ai
```

### 5. Probar la instalación
```bash
# Usar CLI
python -m app.cli.main --help

# O usar GUI
streamlit run app/gui/app.py
```

---

## 📱 Instalación en Android (Termux)

### 1. Instalar Termux y Termux:PR
- Descarga **Termux** desde [F-Droid](https://f-droid.org/packages/com.termux/)
- Descarga **Termux:PR** desde [F-Droid](https://f-droid.org/packages/com.termux.termux_pr/)

### 2. Actualizar paquetes
```bash
pkg update && pkg upgrade
```

### 3. Instalar dependencias
```bash
pkg install git python python-pip wget
pip install --upgrade pip
```

### 4. Instalar Ollama (opcional, para gestión de modelos)
```bash
wget https://ollama.ai/install.sh
bash install.sh
```

### 5. Clonar el repositorio
```bash
git clone https://github.com/JohanCarrion1/AI-Local.git
cd AI-Local
```

### 6. Instalar dependencias de Python
```bash
pip install -r requirements.txt
```

### 7. Probar la instalación
```bash
python -m app.cli.main detect
```

---

## 🚀 Uso Básico

### Con la CLI

```bash
# Detectar recursos del dispositivo
ailocal detect

# Listar modelos disponibles
ailocal models --list

# Descargar un modelo (ej: Qwen3 8B)
ailocal download qwen3:8b --source=ollama

# Ejecutar inferencia
ailocal run qwen3:8b --prompt="Explica qué es Python"

# Conectar con GitHub
ailocal github connect --token=ghp_xxxxx

# Clonar un repositorio de GitHub
ailocal github clone usuario/repo
```

### Con la GUI

```bash
# Iniciar la interfaz web
streamlit run app/gui/app.py
```

Abre tu navegador en `http://localhost:8501`

---

## 🎯 Modelos Recomendados por Dispositivo

### Para Móvil (4-6GB RAM) - Ejemplo: A36
- **Qwen3 8B** (6GB VRAM) - Mejor para código
- **Phi-3.5-mini** (3GB VRAM) - Más rápido
- **MobileVLM-7B** (5GB VRAM) - Multimodal
- **PaliGemma-3B** (4GB VRAM) - Multimodal ligero

### Para PC (16GB RAM)
- **Qwen3.8-27B** (24GB VRAM) - Excelente para código
- **Qwen2.5-VL-7B** (8GB VRAM) - Multimodal
- **DeepSeek-Coder-7B** (5GB VRAM) - Especializado en código

### Para PC (24GB+ RAM)
- **Qwen3.8-27B** (24GB VRAM)
- **Qwen2.5-VL-32B** (24GB VRAM) - Multimodal avanzado
- **Llama 3.2 70B** (40GB VRAM) - Generalista

### Para Servidor (48GB+ RAM)
- **Qwen3-Coder-480B** (80GB VRAM) - El mejor para código
- **Qwen2.5-VL-72B** (48GB VRAM) - Multimodal de alta capacidad
- **Kimi-Dev-72B** (48GB VRAM) - Especializado en desarrollo

---

## 🔐 Configuración de GitHub Token

### 1. Generar un Personal Access Token (PAT)
1. Ve a [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Haz clic en "Generate new token" > "Fine-grained tokens"
3. Configura:
   - **Token name:** AI-Local-Hub
   - **Expiration:** Selecciona una fecha de expiración
   - **Description:** Token para AI-Local-Hub
4. **Scopes:**
   - Repository permissions: **Read and Write** (para repositorios privados)
   - Organization permissions: **Read** (opcional)
5. Haz clic en "Generate token"
6. **Copia el token** (solo se muestra una vez)

### 2. Guardar el token en la aplicación

#### Usando CLI
```bash
ailocal github connect --token=ghp_xxxxxxxxxxxxxxxxxxx
```

#### Usando GUI
1. Ve a la pestaña "GitHub"
2. Ingresa tu token en el campo correspondiente
3. Haz clic en "Conectar"

---

## 📦 Descarga de Modelos

### Desde Ollama (recomendado para principiantes)
```bash
# Descargar Qwen3 8B
ailocal download qwen3:8b --source=ollama

# Descargar Phi-3.5-mini
ailocal download phi3.5:mini --source=ollama

# Ver modelos disponibles
ailocal models --list
```

### Desde HuggingFace
```bash
# Descargar Qwen2.5-Coder-7B
ailocal download Qwen/Qwen2.5-Coder-7B --source=huggingface

# Descargar MobileVLM-7B (multimodal)
ailocal download VisualGLM/MobileVLM-7B --source=huggingface
```

### Desde GitHub
```bash
# Primero conecta con GitHub
ailocal github connect --token=ghp_xxxxx

# Clonar un repositorio
ailocal github clone usuario/repo-con-modelos
```

---

## 🚀 Ejecución de Inferencia

### Ejemplo básico
```bash
# Ejecutar con Qwen3 8B
ailocal run qwen3:8b --prompt="Explica qué es la programación"
```

### Con parámetros personalizados
```bash
# Con temperatura y máximo de tokens
ailocal run qwen3:8b --prompt="Escribe una función en Python para calcular factorial" \
    --temperature=0.3 --max-tokens=1024
```

### Con modelos multimodales
```bash
# Usar un modelo multimodal (requiere imagen)
# Primero descarga un modelo multimodal
ailocal download VisualGLM/MobileVLM-7B --source=huggingface

# Luego ejecuta (la GUI tiene mejor soporte para imágenes)
streamlit run app/gui/app.py
```

---

## ⚙️ Solución de Problemas

### Error: "Ollama is not installed"
**Solución:** Instala Ollama siguiendo las instrucciones en [ollama.ai](https://ollama.ai)

### Error: "Not enough memory"
**Solución:** 
- Usa modelos más pequeños (ej: Phi-3.5-mini en lugar de Qwen3 8B)
- Cierra otras aplicaciones para liberar memoria
- Usa cuantización (Q4, Q5) para reducir el uso de VRAM

### Error: "Model not found"
**Solución:** Verifica que el ID del modelo sea correcto. Usa `ailocal models --list` para ver modelos disponibles.

### Error: "GitHub token invalid"
**Solución:** 
1. Verifica que el token tenga los scopes correctos
2. Genera un nuevo token y vuelve a conectar
3. Asegúrate de que el token no haya expirado

### Error en Termux: "Module not found"
**Solución:** 
```bash
pip install nombre-del-modulo
```

---

## 📊 Verificar Recursos

Para ver qué modelos son compatibles con tu dispositivo:
```bash
ailocal detect
```

Esto mostrará:
- Sistema operativo
- RAM total y disponible
- CPU (núcleos y modelo)
- GPU y VRAM (si disponible)
- Lista de modelos recomendados

---

## 🔄 Actualización

Para actualizar la aplicación:
```bash
cd AI-Local
git pull origin main
pip install -r requirements.txt
```

---

## 🗑️ Desinstalación

### PC
```bash
# Eliminar entorno virtual
rm -rf venv/

# Eliminar repositorio
cd ..
rm -rf AI-Local/
```

### Android (Termux)
```bash
# Eliminar repositorio
cd ..
rm -rf AI-Local/

# (Opcional) Desinstalar Ollama
rm -rf ~/.ollama/
```

---

## 📚 Recursos Adicionales

- [Documentación de Ollama](https://github.com/jmorganca/ollama)
- [HuggingFace Model Hub](https://huggingface.co/models)
- [Qwen Models](https://github.com/QwenLM/Qwen)
- [PyTorch](https://pytorch.org/)
- [Streamlit](https://streamlit.io/)
