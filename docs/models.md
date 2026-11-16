# Lista de Modelos Soportados - AI-Local-Hub

## 🎯 Categorías de Modelos

AI-Local-Hub soporta los siguientes tipos de modelos:

1. **Modelos de Texto (LLMs)** - Para generación de código, chat, análisis de texto
2. **Modelos Multimodales (VLMs)** - Para análisis de imágenes + texto, OCR, visión por computadora

---

## 📝 Modelos de Texto (LLMs)

### Para Dispositivos Móviles (4-8GB RAM)

| Modelo | Tamaño | VRAM Requerida | Fuente | Especialidad | Descarga |
|--------|--------|----------------|--------|--------------|----------|
| **Phi-3.5-mini** | 3.8B | 3GB | Ollama | Rápido, eficiente | `ollama run phi3.5:mini` |
| **Qwen2.5-Coder-7B** | 7B | 5GB | HuggingFace | Programación (Python, Java) | [HF Link](https://huggingface.co/Qwen/Qwen2.5-Coder-7B) |
| **DeepSeek-Coder-7B** | 7B | 5GB | HuggingFace | Backend, múltiples lenguajes | [HF Link](https://huggingface.co/deepseek-ai/DeepSeek-Coder-7B) |
| **CodeQwen1.5-7B** | 7B | 5GB | HuggingFace | Programación | [HF Link](https://huggingface.co/Qwen/CodeQwen1.5-7B) |
| **Qwen3 8B** | 8B | 6GB | Ollama | Generalista, buen equilibrio | `ollama run qwen3:8b` |
| **Llama 3.2 7B** | 7B | 6GB | Ollama | Chat, general | `ollama run llama3.2:7b` |

### Para PC (16-24GB RAM)

| Modelo | Tamaño | VRAM Requerida | Fuente | Especialidad | Descarga |
|--------|--------|----------------|--------|--------------|----------|
| **Qwen3.8-27B** | 27B | 24GB | Ollama | Mejor para programación | `ollama run qwen3:27b` |
| **Qwen2.5-Coder-14B** | 14B | 12GB | HuggingFace | Programación avanzada | [HF Link](https://huggingface.co/Qwen/Qwen2.5-Coder-14B) |
| **DeepSeek-Coder-14B** | 14B | 12GB | HuggingFace | Backend | [HF Link](https://huggingface.co/deepseek-ai/DeepSeek-Coder-14B) |
| **Llama 3.2 14B** | 14B | 12GB | Ollama | Chat avanzado | `ollama run llama3.2:14b` |
| **Mistral 7B** | 7B | 6GB | Ollama | Generalista | `ollama run mistral:7b` |
| **Gemma 7B** | 7B | 6GB | Ollama | Generalista (Google) | `ollama run gemma:7b` |

### Para PC Potente (24GB+ RAM)

| Modelo | Tamaño | VRAM Requerida | Fuente | Especialidad | Descarga |
|--------|--------|----------------|--------|--------------|----------|
| **Qwen3.8-27B** | 27B | 24GB | Ollama | El mejor equilibrio | `ollama run qwen3:27b` |
| **Qwen2.5-Coder-32B** | 32B | 24GB | HuggingFace | Programación profesional | [HF Link](https://huggingface.co/Qwen/Qwen2.5-Coder-32B) |
| **Llama 3.2 70B** | 70B | 40GB | Ollama | Chat de alta calidad | `ollama run llama3.2:70b` |
| **Mistral 8x7B** | 47B | 32GB | Ollama | Mixture of Experts | `ollama run mistral:8x7b` |
| **DeepSeek-Coder-33B** | 33B | 24GB | HuggingFace | Programación | [HF Link](https://huggingface.co/deepseek-ai/DeepSeek-Coder-33B) |

### Para Servidores (48GB+ RAM)

| Modelo | Tamaño | VRAM Requerida | Fuente | Especialidad | Descarga |
|--------|--------|----------------|--------|--------------|----------|
| **Qwen3-Coder-480B** | 480B | 80GB+ | HuggingFace | Coding agentico | [HF Link](https://huggingface.co/Qwen/Qwen3-Coder-480B) |
| **Qwen2.5-72B** | 72B | 48GB | HuggingFace | Generalista de alta capacidad | [HF Link](https://huggingface.co/Qwen/Qwen2.5-72B) |
| **Kimi-Dev-72B** | 72B | 48GB | HuggingFace | Ingeniería de software | [HF Link](https://huggingface.co/kimichat/Kimi-Dev-72B) |
| **Llama 3.2 90B** | 90B | 60GB | Ollama | Chat de alta calidad | `ollama run llama3.2:90b` |
| **Mixtral 8x22B** | 141B | 80GB | Ollama | Mixture of Experts | `ollama run mixtral:8x22b` |

---

## 🖼️ Modelos Multimodales (VLMs)

### Para Dispositivos Móviles (4-8GB RAM)

| Modelo | Tamaño | VRAM Requerida | Fuente | Especialidad | Descarga |
|--------|--------|----------------|--------|--------------|----------|
| **MobileVLM-7B** | 7B | 5GB | HuggingFace | Optimizado para móvil | [HF Link](https://huggingface.co/VisualGLM/MobileVLM-7B) |
| **PaliGemma-3B** | 3B | 4GB | HuggingFace | Visión + Lenguaje | [HF Link](https://huggingface.co/google/paligemma-3b-mix-224) |
| **MiniCPM-V-2.5** | 2.5B | 3GB | HuggingFace | Chat + Visión | [HF Link](https://huggingface.co/OpenCPI/MiniCPM-V-2_5) |

### Para PC (16-24GB RAM)

| Modelo | Tamaño | VRAM Requerida | Fuente | Especialidad | Descarga |
|--------|--------|----------------|--------|--------------|----------|
| **Qwen2.5-VL-7B** | 7B | 8GB | HuggingFace | Visión + Lenguaje | [HF Link](https://huggingface.co/Qwen/Qwen2.5-VL-7B) |
| **LLaVA-1.5-7B** | 7B | 8GB | HuggingFace | Chat visual | [HF Link](https://huggingface.co/liuhaotian/llava-1.5-7b) |
| **BakLLaVA-7B** | 7B | 8GB | HuggingFace | Visión + Lenguaje | [HF Link](https://huggingface.co/SkyWorkAI/BakLLaVA-7B) |

### Para PC Potente (24GB+ RAM)

| Modelo | Tamaño | VRAM Requerida | Fuente | Especialidad | Descarga |
|--------|--------|----------------|--------|--------------|----------|
| **Qwen2.5-VL-32B** | 32B | 24GB | HuggingFace | Visión + Lenguaje avanzado | [HF Link](https://huggingface.co/Qwen/Qwen2.5-VL-32B) |
| **LLaVA-1.5-13B** | 13B | 16GB | HuggingFace | Chat visual | [HF Link](https://huggingface.co/liuhaotian/llava-1.5-13b) |
| **Pixtral-Large** | 12B | 24GB | HuggingFace | Razonamiento visual | [HF Link](https://huggingface.co/mistralai/Pixtral-12B) |
| **GLM-4V-9B** | 9B | 12GB | HuggingFace | Razonamiento espacial 3D | [HF Link](https://huggingface.co/THUDM/glm-4v-9b) |

### Para Servidores (48GB+ RAM)

| Modelo | Tamaño | VRAM Requerida | Fuente | Especialidad | Descarga |
|--------|--------|----------------|--------|--------------|----------|
| **Qwen2.5-VL-72B** | 72B | 48GB | HuggingFace | Visión + Lenguaje de alta capacidad | [HF Link](https://huggingface.co/Qwen/Qwen2.5-VL-72B) |
| **LLaVA-1.5-70B** | 70B | 48GB | HuggingFace | Chat visual | [HF Link](https://huggingface.co/liuhaotian/llava-1.5-70b) |
| **InternVL2.5** | Varios | 48GB+ | HuggingFace | Comprensión visual avanzada | [HF Link](https://huggingface.co/OpenGVLab/InternVL2-5) |

---

## 🏆 Benchmarks de Modelos

### Modelos de Programación (SWE-bench)

| Modelo | SWE-bench (%) | HumanEval (%) | Especialidad |
|--------|---------------|---------------|--------------|
| **Qwen3-Coder-480B** | 69.6% | - | Coding agentico |
| **Kimi-Dev-72B** | 68.5% | - | Ingeniería de software |
| **DeepSeek-Coder-V3** | - | 89.4% | Backend |
| **Qwen3.8-27B** | - | 90.3% | General |
| **Qwen2.5-Coder-32B** | 61.8% | 85.2% | Programación |

### Modelos Multimodales

| Modelo | MMLU | DocVQA | MathVista | ChartQA |
|--------|------|--------|-----------|---------|
| **Qwen2.5-VL-72B** | 85.2% | 92.1% | 65.4% | 88.3% |
| **Pixtral-Large** | - | 91.5% | 69.4% | - |
| **GLM-4V-9B** | 84.3% | 90.2% | 68.1% | 87.2% |
| **LLaVA-1.5-7B** | 80.1% | 88.5% | 60.2% | 85.1% |

---

## 🎨 Comparación por Caso de Uso

### Para Programación

| Caso de Uso | Modelo Recomendado | Tamaño | VRAM |
|-------------|-------------------|--------|------|
| Autocompletado de código | Qwen2.5-Coder-7B | 7B | 5GB |
| Generación de funciones | DeepSeek-Coder-7B | 7B | 5GB |
| Resolver issues de GitHub | Qwen3-Coder-480B | 480B | 80GB+ |
| Explicación de código | Qwen3.8-27B | 27B | 24GB |
| Refactorización | Kimi-Dev-72B | 72B | 48GB |

### Para Análisis de Imágenes

| Caso de Uso | Modelo Recomendado | Tamaño | VRAM |
|-------------|-------------------|--------|------|
| OCR (Texto en imágenes) | MobileVLM-7B | 7B | 5GB |
| Descripción de imágenes | Qwen2.5-VL-7B | 7B | 8GB |
| Preguntas sobre imágenes | PaliGemma-3B | 3B | 4GB |
| Análisis de diagramas | Pixtral-Large | 12B | 24GB |
| Razonamiento visual complejo | Qwen2.5-VL-72B | 72B | 48GB |

### Para Chat General

| Caso de Uso | Modelo Recomendado | Tamaño | VRAM |
|-------------|-------------------|--------|------|
| Chat básico | Phi-3.5-mini | 3.8B | 3GB |
| Chat avanzado | Qwen3 8B | 8B | 6GB |
| Chat técnico | Qwen3.8-27B | 27B | 24GB |
| Chat con contexto largo | Llama 3.2 70B | 70B | 40GB |

---

## 🔍 Cómo Elegir un Modelo

### 1. **Verifica tus recursos**
Ejecuta el comando para detectar los recursos de tu dispositivo:
```bash
ailocal detect
```

### 2. **Selecciona según tu caso de uso**
- **Programación:** Modelos con "Coder" en el nombre (Qwen-Coder, DeepSeek-Coder)
- **Análisis de imágenes:** Modelos con "VL" o "Vision" (Qwen-VL, LLaVA)
- **Chat general:** Modelos sin especialización (Qwen3, Llama, Mistral)

### 3. **Considera el tamaño**
- **Móvil (4-6GB RAM):** Modelos de 3B-7B
- **PC (16GB RAM):** Modelos de 7B-14B
- **PC Potente (24GB+ RAM):** Modelos de 24B-72B
- **Servidor (48GB+ RAM):** Modelos de 70B+

### 4. **Prueba y compara**
Descarga varios modelos y prueba cuál se adapta mejor a tus necesidades:
```bash
# Descargar modelo
ailocal download qwen3:8b --source=ollama

# Probar con un prompt
ailocal run qwen3:8b --prompt="Hola, ¿cómo estás?"
```

---

## 📦 Formatos de Modelos Soportados

AI-Local-Hub soporta los siguientes formatos:

1. **PyTorch (.pt, .bin)** - Modelos nativos de PyTorch
2. **Safetensors (.safetensors)** - Formato seguro para tensores
3. **GGUF (.gguf)** - Formato cuantizado para CPU/GPU (usando llama-cpp)
4. **ONNX (.onnx)** - Formato abierto para inferencia
5. **HuggingFace Hub** - Descarga directa desde el hub
6. **Ollama** - Gestión simplificada de modelos

---

## 🔄 Cuantización

Para reducir el uso de memoria y VRAM, puedes usar modelos cuantizados:

| Tipo de Cuantización | Tamaño Relativo | VRAM Requerida | Calidad |
|---------------------|-----------------|----------------|---------|
| FP16 | 100% | 100% | ⭐⭐⭐⭐⭐ |
| BF16 | 100% | 100% | ⭐⭐⭐⭐⭐ |
| INT8 (Q8) | 50% | 50% | ⭐⭐⭐⭐ |
| INT4 (Q4) | 25% | 25% | ⭐⭐⭐ |
| INT4_K_M (Q4_K_M) | 25% | 25% | ⭐⭐⭐⭐ |

**Ejemplo con Ollama:**
```bash
# Descargar modelo en Q4 (4-bit)
ollama pull qwen3:8b-q4_K_M

# Usar el modelo
ailocal run qwen3:8b-q4_K_M --prompt="Hola"
```

---

## 🌍 Fuentes de Modelos

### 1. **Ollama** (Recomendado para principiantes)
- Fácil de usar
- Gestión automática de modelos
- Cuantización incorporada
- [Sitio web](https://ollama.ai)

### 2. **HuggingFace Hub** (Recomendado para modelos específicos)
- Mayor variedad de modelos
- Modelos de investigación
- Requiere más espacio en disco
- [Sitio web](https://huggingface.co/models)

### 3. **GitHub** (Para repositorios privados)
- Acceso a repositorios privados
- Modelos personalizados
- Requiere token de autenticación
- [Documentación](https://docs.github.com/en)

---

## 📚 Recursos Adicionales

- [HuggingFace Model Hub](https://huggingface.co/models) - Explora miles de modelos
- [Ollama Model Library](https://ollama.ai/library) - Modelos listos para usar
- [Qwen Models](https://github.com/QwenLM/Qwen) - Modelos de Alibaba
- [LLaVA Models](https://github.com/haotian-liu/LLaVA) - Modelos multimodales
- [DeepSeek Models](https://github.com/deepseek-ai/DeepSeek-Coder) - Modelos para programación
