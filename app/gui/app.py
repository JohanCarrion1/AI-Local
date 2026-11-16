#!/usr/bin/env python3
"""AI-Local-Hub GUI - Streamlit Interface"""
import streamlit as st
from pathlib import Path
import time
from app.core.model_manager import ModelManager
from app.core.executor import ModelExecutor
from app.core.github_connector import GitHubConnector
from app.core.resource_detector import ResourceDetector
from app.utils.config import Config
from app.db.database import Database

model_manager = ModelManager()
executor = ModelExecutor()
db = Database()

st.set_page_config(page_title="AI-Local-Hub", page_icon=str(Config.ICON_DIR / "icon.svg"), layout="wide")

# Session state
if "page" not in st.session_state:
    st.session_state.page = "catalog"
if "device_specs" not in st.session_state:
    st.session_state.device_specs = ResourceDetector.detect()
if "github_connected" not in st.session_state:
    st.session_state.github_connected = GitHubConnector.validate_token()

# Navigation
st.sidebar.title("AI-Local-Hub")
st.sidebar.markdown("---")
for label, page in [("📦 Catálogo", "catalog"), ("🚀 Inferencia", "inference"), ("🔗 GitHub", "github"), ("📊 Stats", "stats")]:
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.page = page

# Device specs in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### 📱 Tu Dispositivo")
specs = st.session_state.device_specs
st.sidebar.info(f"**SO:** {specs.os}\n**RAM:** {specs.ram_total_gb:.1f} GB\n**GPU:** {specs.gpu or 'N/A'}")

# Pages
if st.session_state.page == "catalog":
    st.title("📦 Catálogo de Modelos de IA")
    
    # Excellent programming models
    MODELS = [
        {"id": "qwen3:8b", "name": "Qwen3 8B", "size": "8B", "vram": 6, "source": "ollama", "type": "text", "category": "programming", "languages": ["Python", "JS", "Java", "C++", "Go"], "desc": "Excelente para programación y chat general"},
        {"id": "Qwen/Qwen3-Coder-7B", "name": "Qwen3-Coder 7B", "size": "7B", "vram": 5, "source": "huggingface", "type": "text", "category": "programming", "languages": ["Python", "Java", "JS"], "desc": "Especializado en generación de código"},
        {"id": "deepseek-ai/DeepSeek-Coder-7B", "name": "DeepSeek Coder 7B", "size": "7B", "vram": 5, "source": "huggingface", "type": "text", "category": "programming", "languages": ["Python", "TypeScript", "Java", "Go", "Rust"], "desc": "Mejor modelo open-source para backend"},
        {"id": "phi3.5:mini", "name": "Phi-3.5 Mini", "size": "3.8B", "vram": 3, "source": "ollama", "type": "text", "category": "programming", "languages": ["Python", "JS"], "desc": "Ultra-eficiente, ideal para móvil"},
        {"id": "VisualGLM/MobileVLM-7B", "name": "MobileVLM 7B", "size": "7B", "vram": 5, "source": "huggingface", "type": "multimodal", "category": "vision", "desc": "Modelo multimodal optimizado para móvil"},
        {"id": "google/paligemma-3b-mix-224", "name": "PaliGemma 3B", "size": "3B", "vram": 4, "source": "huggingface", "type": "multimodal", "category": "vision", "desc": "Visión + Lenguaje, perfecto para móvil"},
    ]
    
    # Filter by device compatibility
    compatible_models = [m for m in MODELS if m["vram"] <= (specs.ram_total_gb * 0.8)]
    
    st.markdown(f"**{len(compatible_models)} modelos compatibles con tu dispositivo**")
    
    # Category filters
    categories = ["all"] + list(set(m["category"] for m in MODELS))
    cols = st.columns(len(categories))
    for i, cat in enumerate(categories):
        with cols[i]:
            if st.button(cat.capitalize(), use_container_width=True):
                st.session_state.filter_category = cat
    
    # Display models
    filter_cat = st.session_state.get("filter_category", "all")
    filtered = [m for m in compatible_models if filter_cat == "all" or m["category"] == filter_cat]
    
    for model in filtered:
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"### {model['name']}")
            st.markdown(f"**Tamaño:** {model['size']} | **VRAM:** {model['vram']} GB | **Tipo:** {model['type']}")
            if 'languages' in model:
                st.markdown(f"**Lenguajes:** {', '.join(model['languages'])}")
            st.markdown(f"*{model['desc']}*")
        with cols[1]:
            # Check if already downloaded
            local_models = [m.name for m in model_manager.list_local_models()]
            is_downloaded = model['name'] in local_models
            
            if is_downloaded:
                st.success("✅ Descargado")
                if st.button(f"Eliminar", key=f"del_{model['id']}", use_container_width=True):
                    for m in model_manager.list_local_models():
                        if m.name == model['name']:
                            model_manager.delete_model(m.model_id, m.source)
                            db.delete_model(m.model_id)
                            st.rerun()
            else:
                if st.button(f"⬇️ Descargar", key=f"dl_{model['id']}", use_container_width=True):
                    with st.spinner(f"Descargando {model['name']}..."):
                        try:
                            model_info = model_manager.download_model(model['id'], model['source'])
                            db.add_model(ModelRecord(
                                name=model['name'], model_id=model['id'],
                                source=model['source'], path=str(model_info.path),
                                type=model['type'], vram_required=model['vram']
                            ))
                            st.success(f"✅ {model['name']} descargado!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
        st.markdown("---")

elif st.session_state.page == "inference":
    st.title("🚀 Inferencia")
    local_models = model_manager.list_local_models()
    if not local_models:
        st.warning("No hay modelos descargados. Ve al catálogo para descargar.")
        if st.button("Ir a Catálogo"):
            st.session_state.page = "catalog"
            st.rerun()
    else:
        selected = st.selectbox("Modelo:", [m.name for m in local_models])
        prompt = st.text_area("Prompt:")
        if st.button("Ejecutar"):
            model = next(m for m in local_models if m.name == selected)
            with st.spinner("Ejecutando..."):
                result = executor.run_inference(model.path, prompt, model.type)
                if result.success:
                    st.success("✅ Resultado:")
                    st.write(result.text)
                else:
                    st.error(f"❌ Error: {result.error}")

elif st.session_state.page == "github":
    st.title("🔗 GitHub")
    if not st.session_state.github_connected:
        token = st.text_input("Token:", type="password")
        if st.button("Conectar"):
            GitHubConnector.set_token(token)
            st.session_state.github_connected = GitHubConnector.validate_token()
            st.rerun()
    else:
        st.success("✅ Conectado")
        if st.button("Desconectar"):
            GitHubConnector.remove_token()
            st.session_state.github_connected = False
            st.rerun()
        repos = GitHubConnector.get_user_repos()
        for repo in repos:
            st.markdown(f"**{repo.full_name}** - ⭐ {repo.stars}")
            if st.button(f"Clonar {repo.name}"):
                with st.spinner("Clonando..."):
                    model_info = model_manager.download_model(repo.full_name, "github")
                    db.add_model(ModelRecord(name=repo.name, model_id=repo.full_name, source="github", path=str(model_info.path)))
                    st.success("✅ Clonado!")

elif st.session_state.page == "stats":
    st.title("📊 Estadísticas")
    stats = db.get_stats()
    st.metric("Modelos", stats["models"])
    st.metric("Inferencias", stats["inference_history"])
    history = db.get_inference_history(limit=10)
    for h in history:
        with st.expander(f"{h['model_id']} - {h['created_at'][:10]}"):
            st.write(f"Prompt: {h['prompt'][:50]}...")
            st.write(f"Respuesta: {h['response'][:100]}...")

st.markdown("---")
st.markdown("💙 AI-Local-Hub v0.1.0")
