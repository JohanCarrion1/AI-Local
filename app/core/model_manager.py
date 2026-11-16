"""
AI-Local-Hub - Model Manager
============================
Handles downloading and managing AI models from various sources.
"""

import os
import shutil
import subprocess
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

from app.utils.config import Config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a model."""
    name: str
    size: str
    source: str
    model_id: str
    path: Path
    type: str = "text"  # "text" or "multimodal"
    vram_required: float = 0.0
    downloaded: bool = False


class ModelManager:
    """Manages downloading and organizing AI models."""
    
    def __init__(self):
        self.models_dir = Config.MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Source handlers
        self._source_handlers = {
            "ollama": self._download_from_ollama,
            "huggingface": self._download_from_huggingface,
            "github": self._download_from_github,
        }
    
    def list_local_models(self) -> List[ModelInfo]:
        """List all locally downloaded models."""
        models = []
        
        if not self.models_dir.exists():
            return models
        
        for model_dir in self.models_dir.iterdir():
            if model_dir.is_dir():
                # Check for model files
                model_files = list(model_dir.glob("*"))
                if model_files:
                    models.append(ModelInfo(
                        name=model_dir.name,
                        size="Unknown",
                        source="local",
                        model_id=model_dir.name,
                        path=model_dir,
                        downloaded=True
                    ))
        
        return models
    
    def list_available_models(self, source: str = None) -> List[Dict[str, Any]]:
        """List available models from all sources or a specific source."""
        if source:
            handler = self._source_handlers.get(source)
            if handler:
                return handler(list_only=True)
            return []
        
        # Return all available models from all sources
        all_models = []
        for source_name in self._source_handlers:
            try:
                models = self._source_handlers[source_name](list_only=True)
                if models:
                    all_models.extend(models)
            except Exception as e:
                logger.warning(f"Failed to list models from {source_name}: {e}")
        
        return all_models
    
    def download_model(
        self, 
        model_id: str, 
        source: str = "ollama",
        output_dir: Optional[Path] = None
    ) -> ModelInfo:
        """Download a model from a specific source."""
        if source not in self._source_handlers:
            raise ValueError(f"Unsupported source: {source}. Supported: {self._source_handlers.keys()}")
        
        handler = self._source_handlers[source]
        
        if output_dir is None:
            output_dir = self.models_dir / source / model_id
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading {model_id} from {source}...")
        
        try:
            model_info = handler(model_id, output_dir)
            logger.info(f"Successfully downloaded {model_id} to {output_dir}")
            return model_info
        except Exception as e:
            logger.error(f"Failed to download {model_id}: {e}")
            raise
    
    def _download_from_ollama(
        self, 
        model_id: str, 
        output_dir: Path = None,
        list_only: bool = False
    ) -> Optional[ModelInfo]:
        """Download model using Ollama."""
        if list_only:
            # For now, return a list of popular Ollama models
            return [
                {"name": "Qwen3 8B", "size": "8B", "source": "ollama", "id": "qwen3:8b", "type": "text", "vram": 6},
                {"name": "Qwen3 27B", "size": "27B", "source": "ollama", "id": "qwen3:27b", "type": "text", "vram": 24},
                {"name": "Phi-3.5-mini", "size": "3.8B", "source": "ollama", "id": "phi3.5:mini", "type": "text", "vram": 3},
                {"name": "Llama 3.2 7B", "size": "7B", "source": "ollama", "id": "llama3.2:7b", "type": "text", "vram": 6},
            ]
        
        # Check if Ollama is installed
        try:
            result = subprocess.run(["ollama", "--version"], capture_output=True)
            if result.returncode != 0:
                raise RuntimeError("Ollama is not installed. Please install Ollama first.")
        except FileNotFoundError:
            raise RuntimeError("Ollama is not installed. Please install Ollama first.")
        
        # Pull the model
        result = subprocess.run(
            ["ollama", "pull", model_id],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to pull model: {result.stderr}")
        
        # Get model path (Ollama stores models in ~/.ollama/models)
        ollama_models_dir = Path.home() / ".ollama" / "models"
        model_path = ollama_models_dir / model_id.replace("/", "--")
        
        if not model_path.exists():
            # Try to find the model
            for model_dir in ollama_models_dir.glob("*"):
                if model_id.replace("/", "--") in model_dir.name or model_id in model_dir.name:
                    model_path = model_dir
                    break
        
        # Copy to our models directory
        if output_dir and model_path.exists():
            shutil.copytree(model_path, output_dir, dirs_exist_ok=True)
        
        return ModelInfo(
            name=model_id,
            size="Unknown",
            source="ollama",
            model_id=model_id,
            path=output_dir or model_path,
            downloaded=True
        )
    
    def _download_from_huggingface(
        self,
        model_id: str,
        output_dir: Path = None,
        list_only: bool = False
    ) -> Optional[ModelInfo]:
        """Download model from HuggingFace Hub."""
        if list_only:
            # Return popular models from HuggingFace
            return [
                {"name": "Qwen2.5-Coder-7B", "size": "7B", "source": "huggingface", "id": "Qwen/Qwen2.5-Coder-7B", "type": "text", "vram": 5},
                {"name": "Qwen2.5-VL-7B", "size": "7B", "source": "huggingface", "id": "Qwen/Qwen2.5-VL-7B", "type": "multimodal", "vram": 8},
                {"name": "DeepSeek-Coder-7B", "size": "7B", "source": "huggingface", "id": "deepseek-ai/DeepSeek-Coder-7B", "type": "text", "vram": 5},
                {"name": "MobileVLM-7B", "size": "7B", "source": "huggingface", "id": "VisualGLM/MobileVLM-7B", "type": "multimodal", "vram": 5},
                {"name": "PaliGemma-3B", "size": "3B", "source": "huggingface", "id": "google/paligemma-3b-mix-224", "type": "multimodal", "vram": 4},
            ]
        
        try:
            from huggingface_hub import snapshot_download, HfApi
        except ImportError:
            raise RuntimeError("huggingface_hub is not installed. Run: pip install huggingface_hub")
        
        # Check if model exists
        try:
            api = HfApi()
            model_info = api.model_info(model_id)
        except Exception as e:
            raise ValueError(f"Model {model_id} not found on HuggingFace: {e}")
        
        # Download the model
        logger.info(f"Downloading {model_id} from HuggingFace...")
        
        snapshot_download(
            repo_id=model_id,
            local_dir=str(output_dir),
            local_dir_use_symlinks=False,
            ignore_patterns=["*.msgpack", "*.h5", "*.tflite", "*.safetensors.index.json"],
        )
        
        return ModelInfo(
            name=model_id.split("/")[-1],
            size=f"{model_info.siblings[0].size / (1024**3):.2f} GB" if model_info.siblings else "Unknown",
            source="huggingface",
            model_id=model_id,
            path=output_dir,
            downloaded=True
        )
    
    def _download_from_github(
        self,
        repo: str,
        output_dir: Path = None,
        list_only: bool = False,
        branch: str = "main"
    ) -> Optional[ModelInfo]:
        """Download model from a GitHub repository."""
        if list_only:
            # For now, return empty list (GitHub repos are dynamic)
            return []
        
        try:
            import git
        except ImportError:
            raise RuntimeError("GitPython is not installed. Run: pip install gitpython")
        
        # Get GitHub token
        from app.core.github_connector import GitHubConnector
        token = GitHubConnector.get_token()
        
        # Clone the repository
        repo_url = f"https://github.com/{repo}.git"
        
        logger.info(f"Cloning {repo} (branch: {branch})...")
        
        try:
            if token:
                repo_url = f"https://{token}@github.com/{repo}.git"
            
            git.Repo.clone_from(
                repo_url,
                to_path=str(output_dir),
                branch=branch,
                depth=1
            )
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {e}")
        
        return ModelInfo(
            name=repo.split("/")[-1],
            size="Unknown",
            source="github",
            model_id=repo,
            path=output_dir,
            downloaded=True
        )
    
    def delete_model(self, model_id: str, source: str = None) -> bool:
        """Delete a downloaded model."""
        if source:
            model_path = self.models_dir / source / model_id
        else:
            # Search for the model in all sources
            model_path = None
            for source_dir in self.models_dir.iterdir():
                if source_dir.is_dir():
                    potential_path = source_dir / model_id
                    if potential_path.exists():
                        model_path = potential_path
                        break
        
        if model_path and model_path.exists():
            shutil.rmtree(model_path)
            logger.info(f"Deleted model: {model_id}")
            return True
        
        logger.warning(f"Model {model_id} not found")
        return False
    
    def get_model_info(self, model_id: str, source: str = None) -> Optional[ModelInfo]:
        """Get information about a specific model."""
        models = self.list_local_models()
        for model in models:
            if model.model_id == model_id or model.name == model_id:
                return model
        return None
    
    def search_models(self, query: str, source: str = None) -> List[Dict[str, Any]]:
        """Search for models by name."""
        available_models = self.list_available_models(source)
        
        return [
            m for m in available_models 
            if query.lower() in m.get("name", "").lower() or 
               query.lower() in m.get("id", "").lower()
        ]
