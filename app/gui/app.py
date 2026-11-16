#!/usr/bin/env python3
"""
AI-Local-Hub - GUI Interface (Streamlit)
=======================================
Web-based graphical interface for managing AI models.
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
import time

from app.core.model_manager import ModelManager
from app.core.executor import ModelExecutor, InferenceResult
from app.core.github_connector import GitHubConnector
from app.core.resource_detector import ResourceDetector, DeviceSpecs
from app.utils.config import Config
from app.db.database import Database, ModelRecord


# Initialize components
model_manager = ModelManager()
executor = ModelExecutor()
db = Database()


# Page configuration
st.set_page_config(
    page_title="AI-Local-Hub",
    page_icon=str(Config.ICON_DIR / "icon.svg"),
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
st.markdown("""
<style>
    /* Main styling */
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1e293b;
    }
    
    /* Card styling */
    .stCard {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    
    .stButton>button:hover {
        background-color: #2563eb;
    }
    
    /* Input styling */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea {
        background-color: #0e1117;
        color: #fafafa;
        border: 1px solid #334155;
        border-radius: 0.5rem;
    }
    
    /* Selectbox styling */
    .stSelectbox>div>div>select {
        background-color: #0e1117;
        color: #fafafa;
        border: 1px solid #334155;
        border-radius: 0.5rem;
    }
    
    /* Header styling */
    .header {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        font-weight: bold;
        font-size: 1.5rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    /* Model card */
    .model-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s;
    }
    
    .model-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
    }
    
    /* Status indicators */
    .status-online {
        color: #10b981;
        font-weight: bold;
    }
    
    .status-offline {
        color: #ef4444;
        font-weight: bold;
    }
    
    /* Type badges */
    .type-text {
        background-color: #3b82f6;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        display: inline-block;
    }
    
    .type-multimodal {
        background-color: #8b5cf6;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        display: inline-block;
    }
    
    /* Source badges */
    .source-ollama {
        background-color: #06b6d4;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        display: inline-block;
    }
    
    .source-huggingface {
        background-color: #f59e0b;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        display: inline-block;
    }
    
    .source-github {
        background-color: #6b7280;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "device_specs" not in st.session_state:
    st.session_state.device_specs = None
if "github_connected" not in st.session_state:
    st.session_state.github_connected = GitHubConnector.validate_token()


# Logo and title
def show_header():
    """Show the header with logo and title."""
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        st.write("")  # Empty column for spacing
    
    with col2:
        st.markdown("""
        <div class="header">
            <img src="https://raw.githubusercontent.com/JohanCarrion1/AI-Local/main/assets/icon/icon.svg" 
                 style="width: 40px; height: 40px; vertical-align: middle; margin-right: 10px;">
            AI-Local-Hub
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # GitHub connection status
        if st.session_state.github_connected:
            st.markdown('<span class="status-online">✅ GitHub Conectado</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-offline">❌ GitHub Desconectado</span>', unsafe_allow_html=True)


# Sidebar navigation
def show_sidebar():
    """Show the sidebar navigation."""
    st.sidebar.markdown("## 🎯 Navegación")
    
    pages = {
        "🏠 Dashboard": "dashboard",
        "📦 Modelos": "models",
        "🚀 Inferencia": "inference",
        "🔗 GitHub": "github",
        "📊 Estadísticas": "stats",
        "⚙️ Configuración": "settings"
    }
    
    for page_name, page_id in pages.items():
        if st.sidebar.button(page_name, use_container_width=True):
            st.session_state.page = page_id
    
    st.sidebar.markdown("---")
    
    # Device info in sidebar
    st.sidebar.markdown("### 📱 Dispositivo")
    if st.session_state.device_specs:
        specs = st.session_state.device_specs
        st.sidebar.markdown(f"**SO:** {specs.os}")
        st.sidebar.markdown(f"**RAM:** {specs.ram_total_gb:.1f} GB")
        if specs.gpu:
            st.sidebar.markdown(f"**GPU:** {specs.gpu}")
        if specs.gpu_vram_gb:
            st.sidebar.markdown(f"**VRAM:** {specs.gpu_vram_gb:.1f} GB")
    else:
        st.sidebar.markdown("Detectando...")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📖 Ayuda")
    st.sidebar.markdown("""
    - **CLI:** Usa `python -m app.cli.main --help`
    - **Documentación:** [Ver README](https://github.com/JohanCarrion1/AI-Local)
    - **Reportar Bug:** [Issues](https://github.com/JohanCarrion1/AI-Local/issues)
    """)


# Dashboard page
def show_dashboard():
    """Show the dashboard page."""
    st.markdown("## 📊 Dashboard")
    
    # Detect device specs if not already done
    if st.session_state.device_specs is None:
        with st.spinner("Detectando recursos del dispositivo..."):
            st.session_state.device_specs = ResourceDetector.detect()
    
    specs = st.session_state.device_specs
    
    # Show device info
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🖥️ Información del Dispositivo")
        st.info(f"""
        **Sistema Operativo:** {specs.os}  
        **Arquitectura:** {specs.architecture}  
        **RAM Total:** {specs.ram_total_gb:.1f} GB  
        **RAM Disponible:** {specs.ram_available_gb:.1f} GB  
        **Núcleos CPU:** {specs.cpu_cores}
        """)
    
    with col2:
        st.markdown("### 🎯 Tipo de Dispositivo")
        tier = Config.detect_tier()
        tier_info = Config.MODEL_RECOMMENDATIONS.get(tier, {})
        device_type = "📱 Móvil" if specs.is_mobile else "💻 Escritorio"
        st.info(f"""
        **Tipo:** {device_type}  
        **Categoría:** {tier_info.get('name', 'Desconocido')}  
        **VRAM Estimada:** {specs.gpu_vram_gb:.1f} GB""" if specs.gpu_vram_gb else f"""
        **Tipo:** {device_type}  
        **Categoría:** {tier_info.get('name', 'Desconocido')}""")
    
    with col3:
        st.markdown("### 📦 Estadísticas")
        stats = db.get_stats()
        st.info(f"""
        **Modelos Descargados:** {stats['models']}  
        **Repositorios GitHub:** {stats['repositories']}  
        **Inferencias Totales:** {stats['inference_history']}
        """)
    
    # Show recommended models
    st.markdown("### 🎯 Modelos Recomendados")
    recommendations = Config.get_recommendations(tier)
    
    cols = st.columns(3)
    for i, model in enumerate(recommendations):
        with cols[i % 3]:
            model_type = model.get("type", "text")
            type_class = "type-multimodal" if model_type == "multimodal" else "type-text"
            source_class = f"source-{model.get('source', 'ollama')}"
            
            st.markdown(f"""
            <div class="model-card">
                <h4>{model['name']}</h4>
                <p><span class="{type_class}">{'Multimodal' if model_type == 'multimodal' else 'Texto'}</span> 
                   <span class="{source_class}">{model.get('source', 'ollama')}</span></p>
                <p><strong>Tamaño:</strong> {model['size']}</p>
                <p><strong>VRAM:</strong> {model.get('vram', 0)} GB</p>
                <p><small>{model.get('id', '')}</small></p>
            </div>
            """, unsafe_allow_html=True)


# Models page
def show_models():
    """Show the models management page."""
    st.markdown("## 📦 Gestión de Modelos")
    
    tab1, tab2, tab3 = st.tabs(["📥 Descargar", "📦 Locales", "🌐 Disponibles"])
    
    with tab1:
        st.markdown("### Descargar Nuevo Modelo")
        
        col1, col2 = st.columns(2)
        with col1:
            source = st.selectbox(
                "Fuente:",
                Config.SUPPORTED_SOURCES,
                index=0
            )
        with col2:
            if source == "ollama":
                model_id = st.text_input("ID del Modelo (ej: qwen3:8b):")
            elif source == "huggingface":
                model_id = st.text_input("ID del Modelo (ej: Qwen/Qwen2.5-Coder-7B):")
            else:  # github
                model_id = st.text_input("Repositorio (ej: usuario/repo):")
        
        if st.button("🔍 Buscar Modelo", use_container_width=True):
            with st.spinner("Buscando..."):
                results = model_manager.search_models(model_id, source)
            
            if results:
                st.markdown("#### Resultados:")
                for model in results:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**{model['name']}**")
                    with col2:
                        st.markdown(f"{model['size']}")
                    with col3:
                        st.markdown(f"{model.get('vram', 0)} GB VRAM")
            else:
                st.warning("No se encontraron modelos.")
        
        if st.button("⬇️ Descargar Modelo", use_container_width=True):
            if not model_id:
                st.error("Por favor ingresa un ID de modelo.")
            else:
                with st.spinner(f"Descargando {model_id} desde {source}..."):
                    try:
                        model_info = model_manager.download_model(model_id, source)
                        
                        # Save to database
                        record = ModelRecord(
                            name=model_info.name,
                            model_id=model_info.model_id,
                            source=model_info.source,
                            path=str(model_info.path),
                            type=model_info.type,
                            vram_required=model_info.vram_required
                        )
                        db.add_model(record)
                        
                        st.success(f"✅ Modelo descargado: {model_info.name}")
                        st.markdown(f"**Ruta:** `{model_info.path}`")
                    except Exception as e:
                        st.error(f"❌ Error al descargar: {e}")
    
    with tab2:
        st.markdown("### Modelos Locales")
        
        local_models = model_manager.list_local_models()
        
        if not local_models:
            st.info("No hay modelos descargados localmente.")
        else:
            for model in local_models:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.markdown(f"**{model.name}**")
                with col2:
                    st.markdown(f"{model.source}")
                with col3:
                    st.markdown(f"📁 {model.path.name}")
                with col4:
                    if st.button("❌", key=f"delete_{model.model_id}"):
                        try:
                            model_manager.delete_model(model.model_id, model.source)
                            db.delete_model(model.model_id)
                            st.success(f"Modelo {model.name} eliminado.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
    
    with tab3:
        st.markdown("### Modelos Disponibles")
        
        col1, col2 = st.columns(2)
        with col1:
            filter_source = st.selectbox(
                "Filtrar por fuente:",
                ["Todos"] + Config.SUPPORTED_SOURCES
            )
        with col2:
            filter_type = st.selectbox(
                "Filtrar por tipo:",
                ["Todos", "text", "multimodal"]
            )
        
        with st.spinner("Cargando modelos..."):
            available_models = model_manager.list_available_models()
        
        if filter_source != "Todos":
            available_models = [m for m in available_models if m.get("source") == filter_source]
        if filter_type != "Todos":
            available_models = [m for m in available_models if m.get("type") == filter_type]
        
        if not available_models:
            st.info("No se encontraron modelos.")
        else:
            for model in available_models:
                model_type = model.get("type", "text")
                type_class = "type-multimodal" if model_type == "multimodal" else "type-text"
                source_class = f"source-{model.get('source', 'ollama')}"
                
                st.markdown(f"""
                <div class="model-card">
                    <h4>{model['name']}</h4>
                    <p><span class="{type_class}">{'Multimodal' if model_type == 'multimodal' else 'Texto'}</span> 
                       <span class="{source_class}">{model.get('source', 'ollama')}</span></p>
                    <p><strong>Tamaño:</strong> {model['size']} | <strong>VRAM:</strong> {model.get('vram', 0)} GB</p>
                    <p><small>ID: {model.get('id', '')}</small></p>
                </div>
                """, unsafe_allow_html=True)


# Inference page
def show_inference():
    """Show the inference page."""
    st.markdown("## 🚀 Inferencia con Modelos")
    
    # Get local models
    local_models = model_manager.list_local_models()
    
    if not local_models:
        st.warning("No hay modelos descargados. Por favor descarga un modelo primero.")
        if st.button("Ir a Modelos"):
            st.session_state.page = "models"
            st.rerun()
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_model = st.selectbox(
            "Seleccionar Modelo:",
            [f"{m.name} ({m.source})" for m in local_models],
            index=0
        )
    
    with col2:
        model_type = st.selectbox(
            "Tipo de Modelo:",
            ["text", "multimodal"]
        )
    
    # Get selected model
    selected_model_name = selected_model.split(" (")[0]
    selected_model = None
    for m in local_models:
        if m.name == selected_model_name:
            selected_model = m
            break
    
    if not selected_model:
        st.error("Modelo no encontrado.")
        return
    
    # Show model info
    st.markdown(f"""
    **Información del Modelo:**
    - **Ruta:** `{selected_model.path}`
    - **Fuente:** {selected_model.source}
    - **Tipo:** {selected_model.type}
    """)
    
    # Input for inference
    st.markdown("### 📝 Entrada")
    
    if model_type == "text":
        prompt = st.text_area(
            "Prompt:",
            placeholder="Escribe tu prompt aquí...",
            height=150
        )
    else:  # multimodal
        col1, col2 = st.columns([1, 2])
        with col1:
            image_file = st.file_uploader(
                "Imagen (opcional):",
                type=["jpg", "jpeg", "png", "webp"]
            )
        with col2:
            prompt = st.text_area(
                "Prompt:",
                placeholder="Describe la imagen o haz una pregunta...",
                height=150
            )
    
    # Generation parameters
    with st.expander("⚙️ Parámetros de Generación"):
        col1, col2, col3 = st.columns(3)
        with col1:
            temperature = st.slider("Temperatura:", 0.0, 1.0, 0.7, 0.1)
        with col2:
            max_tokens = st.slider("Máximo de Tokens:", 64, 2048, 512, 64)
        with col3:
            top_p = st.slider("Top P:", 0.0, 1.0, 0.95, 0.05)
    
    # Run inference
    if st.button("🚀 Ejecutar Inferencia", use_container_width=True):
        if not prompt:
            st.error("Por favor ingresa un prompt.")
            return
        
        with st.spinner("Ejecutando inferencia..."):
            try:
                start_time = time.time()
                
                # Prepare input
                if model_type == "multimodal" and image_file:
                    # Save uploaded image temporarily
                    temp_image_path = Path(f"temp_{datetime.now().timestamp()}.jpg")
                    with open(temp_image_path, "wb") as f:
                        f.write(image_file.getbuffer())
                    
                    input_data = {
                        "text": prompt,
                        "image": str(temp_image_path)
                    }
                else:
                    input_data = prompt
                
                # Run inference
                result: InferenceResult = executor.run_inference(
                    model_path=selected_model.path,
                    prompt=input_data,
                    model_type=model_type,
                    temperature=temperature,
                    max_new_tokens=max_tokens,
                    top_p=top_p
                )
                
                elapsed_time = time.time() - start_time
                
                # Save to history
                db.add_inference(
                    model_id=selected_model.model_id,
                    prompt=prompt,
                    response=result.text if result.success else f"Error: {result.error}",
                    time_taken=elapsed_time,
                    tokens=result.tokens_generated if result.success else 0
                )
                
                # Clean up temp image
                if model_type == "multimodal" and image_file and temp_image_path.exists():
                    temp_image_path.unlink()
                
                if result.success:
                    st.success("✅ Inferencia completada!")
                    
                    st.markdown("### 📄 Resultado")
                    st.markdown(f"**Tiempo:** {elapsed_time:.2f}s | **Tokens:** {result.tokens_generated}")
                    st.markdown("---")
                    st.markdown(result.text)
                    st.markdown("---")
                else:
                    st.error(f"❌ Error: {result.error}")
                    
            except Exception as e:
                st.error(f"❌ Error al ejecutar inferencia: {e}")


# GitHub page
def show_github():
    """Show the GitHub integration page."""
    st.markdown("## 🔗 Integración con GitHub")
    
    # Check connection status
    st.session_state.github_connected = GitHubConnector.validate_token()
    
    if not st.session_state.github_connected:
        st.markdown("### ⚠️ Conectar con GitHub")
        st.markdown("""
        Para usar las funciones de GitHub, necesitas un **Personal Access Token** con los siguientes scopes:
        - `repo` (para acceder a repositorios privados)
        - `read:org` (para acceder a organizaciones)
        
        **Pasos:**
        1. Ve a [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
        2. Crea un nuevo token con los scopes mencionados
        3. Copia el token y pégalo a continuación
        """)
        
        token = st.text_input("Token de GitHub:", type="password")
        
        if st.button("🔑 Conectar", use_container_width=True):
            if not token:
                st.error("Por favor ingresa un token.")
            else:
                success = GitHubConnector.set_token(token)
                if success:
                    st.session_state.github_connected = GitHubConnector.validate_token()
                    if st.session_state.github_connected:
                        st.success("✅ Conexión exitosa!")
                        st.rerun()
                    else:
                        st.error("❌ Token inválido. Verifica que tenga los scopes correctos.")
                else:
                    st.error("❌ Error al guardar el token.")
    else:
        # Show user info
        user_info = GitHubConnector.get_user_info()
        if user_info:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.image(user_info.get("avatar_url", ""), width=100)
            with col2:
                st.markdown(f"### 👤 {user_info.get('name', user_info.get('login'))}")
                st.markdown(f"**Usuario:** @{user_info.get('login')}")
                st.markdown(f"**Repositorios Públicos:** {user_info.get('public_repos', 0)}")
            with col3:
                if st.button("🔓 Desconectar"):
                    GitHubConnector.remove_token()
                    st.session_state.github_connected = False
                    st.success("Desconectado correctamente.")
                    st.rerun()
        
        # Tabs for different GitHub operations
        tab1, tab2, tab3, tab4 = st.tabs(["📦 Tus Repos", "⭐ Con Estrella", "🔍 Buscar", "📥 Clonar"])
        
        with tab1:
            st.markdown("### Tus Repositorios")
            repos = GitHubConnector.get_user_repos()
            
            if not repos:
                st.info("No tienes repositorios.")
            else:
                for repo in repos:
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.markdown(f"**{repo.full_name}**")
                    with col2:
                        st.markdown(f"{'✅ Privado' if repo.private else '❌ Público'}")
                    with col3:
                        st.markdown(f"⭐ {repo.stars}")
                    with col4:
                        if st.button("Clonar", key=f"clone_{repo.full_name}"):
                            with st.spinner(f"Clonando {repo.full_name}..."):
                                try:
                                    model_info = model_manager.download_model(
                                        repo.full_name, 
                                        "github"
                                    )
                                    record = ModelRecord(
                                        name=model_info.name,
                                        model_id=model_info.model_id,
                                        source="github",
                                        path=str(model_info.path)
                                    )
                                    db.add_model(record)
                                    st.success(f"✅ Repositorio clonado: {repo.full_name}")
                                except Exception as e:
                                    st.error(f"❌ Error: {e}")
        
        with tab2:
            st.markdown("### Repositorios con Estrella")
            repos = GitHubConnector.list_starred_repos()
            
            if not repos:
                st.info("No tienes repositorios con estrella.")
            else:
                for repo in repos:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**{repo.full_name}**")
                    with col2:
                        st.markdown(f"⭐ {repo.stars}")
                    with col3:
                        st.markdown(f"🍴 {repo.forks}")
        
        with tab3:
            st.markdown("### Buscar Repositorios")
            query = st.text_input("Consulta de búsqueda:")
            
            if st.button("🔍 Buscar"):
                with st.spinner("Buscando..."):
                    results = GitHubConnector.search_repos(query, limit=10)
                
                if not results:
                    st.info("No se encontraron resultados.")
                else:
                    for repo in results:
                        st.markdown(f"**{repo.full_name}**")
                        st.markdown(f"{repo.description}")
                        st.markdown(f"⭐ {repo.stars} | 🍴 {repo.forks}")
                        st.markdown("---")
        
        with tab4:
            st.markdown("### Clonar Repositorio")
            
            col1, col2 = st.columns(2)
            with col1:
                repo_url = st.text_input("URL del Repositorio (ej: usuario/repo):")
            with col2:
                branch = st.text_input("Rama:", value="main")
            
            if st.button("📥 Clonar", use_container_width=True):
                if not repo_url:
                    st.error("Por favor ingresa una URL de repositorio.")
                else:
                    with st.spinner(f"Clonando {repo_url}..."):
                        try:
                            model_info = model_manager.download_model(
                                repo_url,
                                "github"
                            )
                            record = ModelRecord(
                                name=model_info.name,
                                model_id=model_info.model_id,
                                source="github",
                                path=str(model_info.path)
                            )
                            db.add_model(record)
                            st.success(f"✅ Repositorio clonado: {repo_url}")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")


# Stats page
def show_stats():
    """Show the statistics page."""
    st.markdown("## 📊 Estadísticas")
    
    stats = db.get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Modelos Descargados", stats["models"])
    with col2:
        st.metric("Repositorios GitHub", stats["repositories"])
    with col3:
        st.metric("Inferencias Totales", stats["inference_history"])
    with col4:
        # Calculate average inference time
        history = db.get_inference_history(limit=100)
        avg_time = sum(h["time_taken"] for h in history) / len(history) if history else 0
        st.metric("Tiempo Promedio", f"{avg_time:.2f}s")
    
    st.markdown("---")
    
    # Model statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📦 Modelos por Fuente")
        if stats["sources"]:
            for source, count in stats["sources"].items():
                st.markdown(f"- **{source}:** {count}")
        else:
            st.info("No hay datos de fuentes.")
    
    with col2:
        st.markdown("### 🏷️ Modelos por Tipo")
        if stats["types"]:
            for model_type, count in stats["types"].items():
                st.markdown(f"- **{model_type}:** {count}")
        else:
            st.info("No hay datos de tipos.")
    
    # Inference history
    st.markdown("### 📜 Historial de Inferencias")
    
    history = db.get_inference_history(limit=20)
    
    if not history:
        st.info("No hay historial de inferencias.")
    else:
        for record in history:
            with st.expander(f"{record['model_id']} - {record['created_at'][:19]}"):
                st.markdown(f"**Prompt:** {record['prompt'][:100]}...")
                st.markdown(f"**Respuesta:** {record['response'][:200]}...")
                st.markdown(f"**Tiempo:** {record['time_taken']:.2f}s | **Tokens:** {record['tokens_generated']}")
    
    # Clear history button
    if st.button("🗑️ Limpiar Historial", use_container_width=True):
        db.clear_inference_history()
        st.success("Historial de inferencias eliminado.")
        st.rerun()


# Settings page
def show_settings():
    """Show the settings page."""
    st.markdown("## ⚙️ Configuración")
    
    st.markdown("### 📁 Directorios")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Directorio de Modelos:**")
        st.code(str(Config.MODELS_DIR))
    
    with col2:
        st.markdown(f"**Directorio de Base de Datos:**")
        st.code(str(Config.DB_DIR))
    
    st.markdown("---")
    
    st.markdown("### 🔧 Configuración de GitHub")
    
    if st.session_state.github_connected:
        st.success("✅ Conectado a GitHub")
        if st.button("🔓 Desconectar GitHub"):
            GitHubConnector.remove_token()
            st.session_state.github_connected = False
            st.success("Desconectado de GitHub.")
            st.rerun()
    else:
        st.warning("⚠️ No conectado a GitHub")
        if st.button("🔑 Conectar GitHub"):
            st.session_state.page = "github"
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("### 🗑️ Limpiar Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Limpiar Historial de Inferencias"):
            db.clear_inference_history()
            st.success("Historial de inferencias eliminado.")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Limpiar Todos los Modelos"):
            local_models = model_manager.list_local_models()
            for model in local_models:
                model_manager.delete_model(model.model_id, model.source)
                db.delete_model(model.model_id)
            st.success("Todos los modelos eliminados.")
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("### ℹ️ Información del Sistema")
    
    if st.session_state.device_specs:
        specs = st.session_state.device_specs
        st.json({
            "Sistema Operativo": specs.os,
            "Versión": specs.os_version,
            "Arquitectura": specs.architecture,
            "RAM Total (GB)": specs.ram_total_gb,
            "RAM Disponible (GB)": specs.ram_available_gb,
            "Núcleos CPU": specs.cpu_cores,
            "Modelo CPU": specs.cpu_model,
            "GPU": specs.gpu,
            "VRAM GPU (GB)": specs.gpu_vram_gb,
            "Es Móvil": specs.is_mobile,
            "Es Termux": specs.is_termux
        })
    else:
        st.info("Detectando información del sistema...")


# Main app
def main():
    """Main application entry point."""
    show_header()
    show_sidebar()
    
    # Show the selected page
    page_handlers = {
        "dashboard": show_dashboard,
        "models": show_models,
        "inference": show_inference,
        "github": show_github,
        "stats": show_stats,
        "settings": show_settings
    }
    
    handler = page_handlers.get(st.session_state.page, show_dashboard)
    handler()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6b7280; padding: 1rem;">
        <p>AI-Local-Hub v0.1.0 | <a href="https://github.com/JohanCarrion1/AI-Local" style="color: #3b82f6;">GitHub</a></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
