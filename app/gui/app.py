#!/usr/bin/env python3
"""
AI-Local-Hub - AI Gallery (Like Google AI Gallery)
===================================================
Professional GUI for browsing, downloading, and running AI models locally.
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
import time
from typing import Optional, List

from app.core.model_manager import ModelManager, ModelInfo
from app.core.executor import ModelExecutor, InferenceResult
from app.core.github_connector import GitHubConnector
from app.core.resource_detector import ResourceDetector
from app.utils.config import Config
from app.db.database import Database, ModelRecord


# Initialize components
model_manager = ModelManager()
executor = ModelExecutor()
db = Database()


# Page configuration
st.set_page_config(
    page_title="AI Gallery - Local Hub",
    page_icon=str(Config.ICON_DIR / "icon.svg"),
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS for professional look
st.markdown("""
<style>
    /* Main background */
    .main {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
        color: #e0e0e0;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #16213e 0%, #0f3460 100%);
        border-right: 1px solid #2a2a3e;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    
    .download-btn {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
    }
    
    .download-btn:hover {
        background: linear-gradient(135deg, #0ea98c 0%, #30e06d 100%) !important;
    }
    
    .run-btn {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
    }
    
    .run-btn:hover {
        background: linear-gradient(135deg, #e083eb 0%, #e5465c 100%) !important;
    }
    
    .delete-btn {
        background: linear-gradient(135deg, #ff4757 0%, #cc0000 100%) !important;
    }
    
    .delete-btn:hover {
        background: linear-gradient(135deg, #ff3742 0%, #aa0000 100%) !important;
    }
    
    /* Header */
    .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        font-weight: 700;
        font-size: 2rem;
        margin-bottom: 20px;
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
        text-align: center;
    }
    
    /* Model card */
    .model-card {
        background: linear-gradient(135deg, #1e2749 0%, #2d3748 100%);
        border: 1px solid #3a4a5c;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        transition: all 0.3s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .model-card:hover {
        border-color: #667eea;
        transform: translateY(-4px);
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.2);
    }
    
    /* Model header */
    .model-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        flex-wrap: wrap;
        gap: 10px;
    }
    
    /* Model name */
    .model-name {
        font-size: 1.3rem;
        font-weight: 700;
        color: #fff;
        margin: 0;
    }
    
    /* Model author */
    .model-author {
        color: #a0aec0;
        font-size: 0.9rem;
    }
    
    /* Model stats */
    .model-stats {
        display: flex;
        gap: 15px;
        margin: 12px 0;
        flex-wrap: wrap;
    }
    
    .stat-badge {
        background: rgba(102, 126, 234, 0.2);
        color: #a5b4fc;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    
    .stat-downloads {
        background: rgba(17, 153, 142, 0.2);
        color: #4fd1c7;
    }
    
    .stat-likes {
        background: rgba(240, 147, 251, 0.2);
        color: #ed8936;
    }
    
    .stat-size {
        background: rgba(255, 71, 87, 0.2);
        color: #f56565;
    }
    
    /* Model description */
    .model-desc {
        color: #a0aec0;
        font-size: 0.9rem;
        line-height: 1.6;
        margin: 12px 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    /* Model tags */
    .model-tags {
        display: flex;
        gap: 8px;
        margin: 12px 0;
        flex-wrap: wrap;
    }
    
    .tag {
        background: rgba(102, 126, 234, 0.2);
        color: #a5b4fc;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Button container */
    .button-container {
        display: flex;
        gap: 10px;
        margin-top: 15px;
        flex-wrap: wrap;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #1a202c;
        color: #e0e0e0;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 10px;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Select boxes */
    .stSelectbox > div > div > select {
        background: #1a202c;
        color: #e0e0e0;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 10px;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #fff;
        margin: 30px 0 20px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid #667eea;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    /* Filter chips */
    .filter-chip {
        background: rgba(102, 126, 234, 0.2);
        color: #a5b4fc;
        padding: 8px 16px;
        border-radius: 20px;
        border: 1px solid #3a4a5c;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s;
        display: inline-block;
        margin: 4px;
    }
    
    .filter-chip:hover {
        background: rgba(102, 126, 234, 0.4);
        border-color: #667eea;
    }
    
    .filter-chip.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
    }
    
    /* Loading spinner */
    .loading {
        border: 3px solid #2d3748;
        border-top: 3px solid #667eea;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Success/Error messages */
    .success-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin: 10px 0;
        font-weight: 500;
    }
    
    .error-box {
        background: linear-gradient(135deg, #ff4757 0%, #cc0000 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin: 10px 0;
        font-weight: 500;
    }
    
    /* Result box */
    .result-box {
        background: #1a202c;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 20px;
        margin: 15px 0;
        color: #e0e0e0;
    }
    
    /* Code blocks */
    .code-block {
        background: #0a0a0a;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "gallery"
if "device_specs" not in st.session_state:
    st.session_state.device_specs = ResourceDetector.detect()
if "github_connected" not in st.session_state:
    st.session_state.github_connected = GitHubConnector.validate_token()
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "selected_task" not in st.session_state:
    st.session_state.selected_task = "text-generation"
if "downloading" not in st.session_state:
    st.session_state.downloading = {}


# Common tasks for filtering
POPULAR_TASKS = [
    {"name": "Text Generation", "value": "text-generation", "icon": "📝"},
    {"name": "Coding", "value": "text-generation", "icon": "💻"},
    {"name": "Chat", "value": "conversational", "icon": "💬"},
    {"name": "Image to Text", "value": "image-to-text", "icon": "🖼️"},
    {"name": "Classification", "value": "text-classification", "icon": "🏷️"},
    {"name": "Translation", "value": "translation", "icon": "🌍"},
    {"name": "Summarization", "value": "summarization", "icon": "📄"},
    {"name": "Question Answering", "value": "question-answering", "icon": "❓"},
]


def show_header():
    """Show the header with logo and title."""
    st.markdown("""
    <div class="header">
        <img src="https://raw.githubusercontent.com/JohanCarrion1/AI-Local/main/assets/icon/icon.svg" 
             style="width: 40px; height: 40px; vertical-align: middle; margin-right: 12px;">
        AI Gallery - Local Hub
    </div>
    """, unsafe_allow_html=True)


def show_sidebar():
    """Show the sidebar navigation."""
    st.sidebar.markdown("## 🎯 Navigation")
    st.sidebar.markdown("---")
    
    pages = [
        ("🏛️ Gallery", "gallery"),
        ("📦 My Models", "my_models"),
        ("🚀 Run Model", "run"),
        ("🔗 GitHub", "github"),
        ("⚙️ Settings", "settings"),
    ]
    
    for label, page_id in pages:
        if st.sidebar.button(label, use_container_width=True):
            st.session_state.page = page_id
            st.rerun()
    
    st.sidebar.markdown("---")
    
    # Device info
    st.sidebar.markdown("### 📱 Your Device")
    specs = st.session_state.device_specs
    st.sidebar.info(f"""
    **OS:** {specs.os}  
    **RAM:** {specs.ram_total_gb:.1f} GB  
    **CPU:** {specs.cpu_cores} cores  
    **GPU:** {specs.gpu or 'None'}  
    **VRAM:** {specs.gpu_vram_gb:.1f} GB""" if specs.gpu_vram_gb else f"""
    **OS:** {specs.os}  
    **RAM:** {specs.ram_total_gb:.1f} GB  
    **CPU:** {specs.cpu_cores} cores  
    **GPU:** {specs.gpu or 'None'}""")
    
    st.sidebar.markdown("---")
    
    # Quick stats
    stats = db.get_stats()
    st.sidebar.markdown("### 📊 Quick Stats")
    st.sidebar.markdown(f"**Models:** {stats['models']}")
    st.sidebar.markdown(f"**Inferences:** {stats['inference_history']}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📖 Help")
    st.sidebar.markdown("""
    - **Search:** Find models from HuggingFace Hub
    - **Download:** Download models directly to the app
    - **Run:** Execute models locally without servers
    """)


def gallery_page():
    """Main gallery page with model search and display."""
    st.markdown('<div class="section-header">🏛️ AI Model Gallery</div>', unsafe_allow_html=True)
    
    # Search bar
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        search_query = st.text_input(
            "🔍 Search models",
            placeholder="Try: Qwen, Llama, coding, text-generation...",
            value=st.session_state.search_query,
            key="search_input"
        )
        st.session_state.search_query = search_query
    
    with col2:
        selected_task = st.selectbox(
            "Task",
            ["All"] + [t["value"] for t in POPULAR_TASKS],
            index=0,
            key="task_filter"
        )
        st.session_state.selected_task = selected_task
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["downloads", "likes", "last_modified"],
            index=0,
            key="sort_filter"
        )
    
    # Task filters as chips
    st.markdown("**Quick Filters:**")
    cols = st.columns(len(POPULAR_TASKS))
    for i, task in enumerate(POPULAR_TASKS):
        with cols[i]:
            if st.button(f"{task['icon']} {task['name']}", use_container_width=True):
                st.session_state.search_query = ""
                st.session_state.selected_task = task["value"]
                st.rerun()
    
    st.markdown("---")
    
    # Search models
    if search_query or st.session_state.selected_task != "All":
        with st.spinner("🔍 Searching HuggingFace Hub..."):
            task_filter = None if st.session_state.selected_task == "All" else st.session_state.selected_task
            st.session_state.search_results = model_manager.search_models(
                query=search_query,
                task=task_filter,
                sort_by=sort_by,
                limit=20
            )
    else:
        # Show popular models
        with st.spinner("Loading popular models..."):
            st.session_state.search_results = model_manager.get_popular_models(
                task="text-generation",
                limit=20
            )
    
    # Display results
    if st.session_state.search_results:
        st.markdown(f"**Found {len(st.session_state.search_results)} models**")
        
        # Display in grid
        for model in st.session_state.search_results:
            display_model_card(model)
    else:
        st.info("No models found. Try a different search query.")


def display_model_card(model: ModelInfo):
    """Display a model card with download and run buttons."""
    # Check if already downloaded
    local_models = model_manager.list_local_models()
    is_downloaded = any(m.model_id == model.id for m in local_models)
    
    # Check compatibility
    specs = st.session_state.device_specs
    compatible = model_manager.check_model_compatibility(model.id)["compatible"]
    
    with st.container():
        st.markdown(f"""
        <div class="model-card">
            <div class="model-header">
                <div>
                    <h3 class="model-name">{model.name}</h3>
                    <p class="model-author">by {model.author}</p>
                </div>
            </div>
            <p class="model-desc">{model.description[:200]}{'...' if len(model.description) > 200 else ''}</p>
            <div class="model-stats">
                <span class="stat-badge stat-downloads">⬇️ {model.downloads:,}</span>
                <span class="stat-badge stat-likes">❤️ {model.likes:,}</span>
                <span class="stat-badge stat-size">💾 {model.size}</span>
                {'<span class="stat-badge" style="background: rgba(17, 153, 142, 0.2); color: #4fd1c7;">✅ Compatible</span>' if compatible else ''}
                {'<span class="stat-badge" style="background: rgba(255, 71, 87, 0.2); color: #f56565;">⚠️ Not Compatible</span>' if not compatible else ''}
            </div>
            <div class="model-tags">
                {''.join(f'<span class="tag">{tag}</span>' for tag in model.tags[:5])}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if is_downloaded:
                st.success("✅ Downloaded")
            else:
                if st.button(
                    "⬇️ Download",
                    key=f"download_{model.id}",
                    use_container_width=True,
                    disabled=not compatible
                ):
                    download_model_with_progress(model)
        
        with col2:
            if is_downloaded:
                if st.button(
                    "▶️ Run",
                    key=f"run_{model.id}",
                    use_container_width=True,
                    class_="run-btn"
                ):
                    run_model(model)
            else:
                st.markdown("")  # Empty space
        
        with col3:
            if is_downloaded:
                if st.button(
                    "🗑️ Delete",
                    key=f"delete_{model.id}",
                    use_container_width=True,
                    class_="delete-btn"
                ):
                    delete_model(model)
            else:
                st.markdown("")  # Empty space
        
        st.markdown("---")


def download_model_with_progress(model: ModelInfo):
    """Download a model with progress indication."""
    if model.id in st.session_state.downloading:
        st.warning("Already downloading...")
        return
    
    st.session_state.downloading[model.id] = True
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text(f"Downloading {model.name}...")
        
        # Download the model
        output_dir = model_manager.download_model(model.id)
        
        if output_dir:
            # Save to database
            record = ModelRecord(
                name=model.name,
                model_id=model.id,
                source="huggingface",
                path=str(output_dir),
                type="text",  # Can be detected later
                vram_required=0
            )
            db.add_model(record)
            
            progress_bar.progress(100)
            status_text.text(f"✅ Successfully downloaded {model.name}!")
            time.sleep(1)
            st.rerun()
        else:
            status_text.text(f"❌ Failed to download {model.name}")
            
    except Exception as e:
        status_text.text(f"❌ Error: {e}")
    finally:
        st.session_state.downloading[model.id] = False
        progress_bar.empty()
        status_text.empty()


def run_model(model: ModelInfo):
    """Run inference with a model."""
    # Find the local model
    local_models = model_manager.list_local_models()
    local_model = next((m for m in local_models if m.model_id == model.id), None)
    
    if not local_model:
        st.error(f"Model {model.id} not found locally")
        return
    
    # Detect task
    task = executor.detect_task(local_model.path)
    
    st.session_state.running_model = model.id
    st.session_state.running_task = task
    st.session_state.page = "run"
    st.rerun()


def delete_model(model: ModelInfo):
    """Delete a downloaded model."""
    try:
        success = model_manager.delete_model(model.id)
        if success:
            db.delete_model(model.id)
            st.success(f"✅ Deleted {model.name}")
            st.rerun()
        else:
            st.error(f"❌ Failed to delete {model.name}")
    except Exception as e:
        st.error(f"❌ Error: {e}")


def my_models_page():
    """Page showing downloaded models."""
    st.markdown('<div class="section-header">📦 My Models</div>', unsafe_allow_html=True)
    
    local_models = model_manager.list_local_models()
    
    if not local_models:
        st.info("No models downloaded yet. Go to the Gallery to download some!")
        if st.button("🏛️ Go to Gallery"):
            st.session_state.page = "gallery"
            st.rerun()
        return
    
    # Show models in cards
    for model in local_models:
        model_info = model_manager.get_model_info(model.model_id)
        if model_info:
            model_info.is_downloaded = True
            model_info.local_path = model.path
            display_model_card(model_info)
        else:
            # Show basic info
            with st.container():
                st.markdown(f"""
                <div class="model-card">
                    <h3 class="model-name">{model.name}</h3>
                    <p class="model-author">Local model</p>
                    <p class="model-desc">Path: {model.path}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("▶️ Run", key=f"run_local_{model.model_id}", use_container_width=True):
                        st.session_state.running_model = model.model_id
                        st.session_state.running_task = "text-generation"
                        st.session_state.page = "run"
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_local_{model.model_id}", use_container_width=True):
                        delete_model(ModelInfo(id=model.model_id, name=model.name))
                
                st.markdown("---")


def run_page():
    """Page for running inference with a model."""
    st.markdown('<div class="section-header">🚀 Run Model</div>', unsafe_allow_html=True)
    
    # Get the model to run
    model_id = st.session_state.get("running_model")
    task = st.session_state.get("running_task", "text-generation")
    
    if not model_id:
        st.info("Select a model from the Gallery or My Models page to run.")
        
        # Show popular models to select
        st.markdown("### Or select from popular models:")
        popular = model_manager.get_suggested_models(task)
        cols = st.columns(min(3, len(popular)))
        for i, model in enumerate(popular):
            with cols[i % 3]:
                if st.button(model.name, use_container_width=True):
                    st.session_state.running_model = model.id
                    st.session_state.running_task = task
                    st.rerun()
        return
    
    # Get model info
    model_info = model_manager.get_model_info(model_id)
    local_models = model_manager.list_local_models()
    local_model = next((m for m in local_models if m.model_id == model_id), None)
    
    if not local_model:
        st.error(f"Model {model_id} not found. Please download it first.")
        if st.button("🏛️ Go to Gallery"):
            st.session_state.page = "gallery"
            st.rerun()
        return
    
    # Show model info
    if model_info:
        st.markdown(f"""
        <div class="model-card">
            <h3 class="model-name">{model_info.name}</h3>
            <p class="model-author">by {model_info.author}</p>
            <p class="model-desc">{model_info.description[:200]}{'...' if len(model_info.description) > 200 else ''}</p>
            <div class="model-stats">
                <span class="stat-badge">📦 {model_info.size}</span>
                <span class="stat-badge">⬇️ {model_info.downloads:,}</span>
                <span class="stat-badge">❤️ {model_info.likes:,}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"**Model:** {model_id}")
        st.markdown(f"**Path:** {local_model.path}")
    
    # Input for the model
    st.markdown("### 📝 Input")
    
    # Different input based on task
    if task in ["image-to-text", "visual-question-answering", "object-detection", "image-classification"]:
        col1, col2 = st.columns([1, 2])
        with col1:
            image_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png", "webp"])
        with col2:
            text_input = st.text_input("Optional text/prompt")
    else:
        text_input = st.text_area(
            "Enter your prompt",
            placeholder="Type your question or prompt here...",
            height=150
        )
    
    # Generation parameters
    with st.expander("⚙️ Generation Parameters"):
        col1, col2, col3 = st.columns(3)
        with col1:
            temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        with col2:
            max_tokens = st.slider("Max Tokens", 64, 2048, 512, 64)
        with col3:
            top_p = st.slider("Top P", 0.0, 1.0, 0.95, 0.05)
    
    # Run button
    if st.button("▶️ Run Inference", use_container_width=True, key="run_inference"):
        if not text_input and task not in ["image-classification", "object-detection"]:
            st.error("Please enter a prompt")
            return
        
        with st.spinner("Running inference..."):
            try:
                start_time = time.time()
                
                # Prepare input
                if image_file:
                    from PIL import Image
                    image = Image.open(image_file)
                    inputs = {"image": image, "text": text_input} if text_input else {"image": image}
                else:
                    inputs = text_input
                
                # Run inference
                result: InferenceResult = executor.run_inference(
                    model_path=local_model.path,
                    inputs=inputs,
                    task=task,
                    temperature=temperature,
                    max_new_tokens=max_tokens,
                    top_p=top_p
                )
                
                elapsed_time = time.time() - start_time
                
                # Save to history
                db.add_inference(
                    model_id=model_id,
                    prompt=str(inputs) if isinstance(inputs, dict) else inputs,
                    response=result.text if result.success else f"Error: {result.error}",
                    time_taken=elapsed_time,
                    tokens=result.tokens_generated if result.success else 0
                )
                
                if result.success:
                    st.success(f"✅ Inference completed in {elapsed_time:.2f}s")
                    
                    st.markdown("### 📄 Result")
                    if task in ["image-classification", "object-detection"]:
                        # Show structured output
                        st.json(result.raw_output)
                    else:
                        st.markdown(f"**Output:**")
                        st.markdown(f"""
                        <div class="result-box">
                            {result.text}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Copy button
                    if st.button("📋 Copy to clipboard"):
                        st.code(result.text)
                else:
                    st.error(f"❌ Error: {result.error}")
                    
            except Exception as e:
                st.error(f"❌ Error running inference: {e}")


def github_page():
    """GitHub integration page."""
    st.markdown('<div class="section-header">🔗 GitHub Integration</div>', unsafe_allow_html=True)
    
    if not st.session_state.github_connected:
        st.markdown("### Connect to GitHub")
        st.markdown("""
        To download private repositories, connect your GitHub account.
        """)
        
        token = st.text_input("GitHub Token", type="password")
        if st.button("🔑 Connect"):
            if token:
                GitHubConnector.set_token(token)
                st.session_state.github_connected = GitHubConnector.validate_token()
                if st.session_state.github_connected:
                    st.success("✅ Connected successfully!")
                    st.rerun()
                else:
                    st.error("❌ Invalid token")
            else:
                st.error("Please enter a token")
    else:
        st.success("✅ Connected to GitHub")
        
        if st.button("🔓 Disconnect"):
            GitHubConnector.remove_token()
            st.session_state.github_connected = False
            st.success("Disconnected")
            st.rerun()
        
        # Show user repos
        st.markdown("### Your Repositories")
        repos = GitHubConnector.get_user_repos()
        
        if repos:
            for repo in repos:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**{repo.full_name}**")
                with col2:
                    st.markdown(f"⭐ {repo.stars}")
                with col3:
                    if st.button("Clone", key=f"clone_{repo.full_name}"):
                        with st.spinner(f"Cloning {repo.full_name}..."):
                            output_dir = Config.MODELS_DIR / "github" / repo.name
                            model_info = model_manager.download_model(repo.full_name, output_dir=output_dir)
                            if model_info:
                                db.add_model(ModelRecord(
                                    name=repo.name,
                                    model_id=repo.full_name,
                                    source="github",
                                    path=str(output_dir)
                                ))
                                st.success("✅ Cloned!")
                                st.rerun()
        else:
            st.info("No repositories found")


def settings_page():
    """Settings page."""
    st.markdown('<div class="section-header">⚙️ Settings</div>', unsafe_allow_html=True)
    
    st.markdown("### 📁 Directories")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Models Directory:**")
        st.code(str(Config.MODELS_DIR))
    with col2:
        st.markdown(f"**Database Directory:**")
        st.code(str(Config.DB_DIR))
    
    st.markdown("---")
    
    st.markdown("### 🔧 GitHub")
    if st.session_state.github_connected:
        st.success("✅ Connected to GitHub")
        if st.button("🔓 Disconnect"):
            GitHubConnector.remove_token()
            st.session_state.github_connected = False
            st.success("Disconnected")
            st.rerun()
    else:
        st.info("Not connected to GitHub")
        if st.button("🔑 Connect"):
            st.session_state.page = "github"
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("### 🗑️ Clean Data")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Inference History"):
            db.clear_inference_history()
            st.success("Inference history cleared")
            st.rerun()
    with col2:
        if st.button("🗑️ Delete All Models"):
            for m in model_manager.list_local_models():
                model_manager.delete_model(m.model_id, m.source)
                db.delete_model(m.model_id)
            st.success("All models deleted")
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("### ℹ️ System Info")
    specs = st.session_state.device_specs
    st.json({
        "OS": specs.os,
        "OS Version": specs.os_version,
        "Architecture": specs.architecture,
        "RAM Total (GB)": specs.ram_total_gb,
        "RAM Available (GB)": specs.ram_available_gb,
        "CPU Cores": specs.cpu_cores,
        "CPU Model": specs.cpu_model,
        "GPU": specs.gpu,
        "GPU VRAM (GB)": specs.gpu_vram_gb,
        "Is Mobile": specs.is_mobile,
        "Is Termux": specs.is_termux
    })


# Main app
def main():
    """Main application entry point."""
    show_header()
    show_sidebar()
    
    # Show the selected page
    page_handlers = {
        "gallery": gallery_page,
        "my_models": my_models_page,
        "run": run_page,
        "github": github_page,
        "settings": settings_page
    }
    
    handler = page_handlers.get(st.session_state.page, gallery_page)
    handler()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #718096; padding: 20px;">
        <p><strong>AI Gallery - Local Hub</strong> v0.1.0 | 
        <a href="https://github.com/JohanCarrion1/AI-Local" style="color: #667eea;">GitHub</a></p>
        <p>✨ Browse, download, and run AI models locally</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
