"""
AI-Local-Hub - Model Manager (Advanced Version)
================================================
Search and download models from HuggingFace Hub with advanced features.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from huggingface_hub import (
    snapshot_download,
    login,
    whoami,
    list_models,
    ModelFilter,
    ModelSearchArguments,
    model_info
)
from transformers import AutoConfig

from app.utils.config import Config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a model from HuggingFace Hub."""
    id: str
    name: str
    author: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    likes: int = 0
    size: str = "0 MB"
    last_modified: str = ""
    pipeline_tag: str = ""
    framework: List[str] = field(default_factory=list)
    task: str = ""
    is_downloaded: bool = False
    local_path: Optional[Path] = None


class ModelManager:
    """Advanced model manager for searching and downloading from HuggingFace Hub."""
    
    def __init__(self):
        self.models_dir = Config.MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._cached_models: Dict[str, ModelInfo] = {}
    
    def search_models(
        self,
        query: str = "",
        task: str = None,
        framework: str = None,
        language: str = None,
        sort_by: str = "downloads",
        limit: int = 50,
        pipeline_tag: str = None
    ) -> List[ModelInfo]:
        """
        Search for models on HuggingFace Hub with advanced filters.
        
        Args:
            query: Search query (model name, description, etc.)
            task: Filter by task (text-generation, text-classification, etc.)
            framework: Filter by framework (pytorch, tensorflow, etc.)
            language: Filter by language
            sort_by: Sort by (downloads, likes, last_modified)
            limit: Maximum number of results
            pipeline_tag: Filter by pipeline tag
        
        Returns:
            List of ModelInfo objects
        """
        try:
            # Build search arguments
            search_args = ModelSearchArguments(
                search=query,
                filter=ModelFilter(
                    task=task,
                    framework=framework,
                    language=language,
                    pipeline_tag=pipeline_tag
                )
            )
            
            # Search models
            models = list_models(
                search=search_args,
                sort=sort_by,
                limit=limit
            )
            
            # Convert to ModelInfo
            results = []
            for model in models:
                try:
                    model_info = ModelInfo(
                        id=model.id,
                        name=model.id.split("/")[-1] if "/" in model.id else model.id,
                        author=model.id.split("/")[0] if "/" in model.id else "",
                        description=model.description or "",
                        tags=model.tags or [],
                        downloads=model.downloads,
                        likes=model.likes,
                        size=self._format_size(model.sha) if hasattr(model, 'sha') else "Unknown",
                        last_modified=model.lastModified or "",
                        pipeline_tag=model.pipeline_tag or "",
                        framework=model.framework or [],
                        task=model.task or ""
                    )
                    results.append(model_info)
                except Exception as e:
                    logger.warning(f"Error processing model {model.id}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            return []
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get detailed information about a specific model."""
        try:
            if model_id in self._cached_models:
                return self._cached_models[model_id]
            
            model = model_info(model_id)
            
            model_info = ModelInfo(
                id=model.id,
                name=model.id.split("/")[-1] if "/" in model.id else model.id,
                author=model.id.split("/")[0] if "/" in model.id else "",
                description=model.cardData.get("description", "") if model.cardData else "",
                tags=model.tags or [],
                downloads=model.downloads,
                likes=model.likes,
                size=self._format_size(model.siblings[0].size) if model.siblings else "Unknown",
                last_modified=model.lastModified or "",
                pipeline_tag=model.pipeline_tag or "",
                framework=model.framework or [],
                task=model.task or ""
            )
            
            self._cached_models[model_id] = model_info
            return model_info
            
        except Exception as e:
            logger.error(f"Error getting model info for {model_id}: {e}")
            return None
    
    def download_model(
        self,
        model_id: str,
        output_dir: Optional[Path] = None,
        ignore_patterns: List[str] = None,
        resume_download: bool = True
    ) -> Optional[Path]:
        """
        Download a model from HuggingFace Hub.
        
        Args:
            model_id: Model identifier (ej: "Qwen/Qwen2.5-Coder-7B")
            output_dir: Output directory (defaults to models_dir/model_id)
            ignore_patterns: Patterns to ignore during download
            resume_download: Whether to resume partial downloads
        
        Returns:
            Path to the downloaded model, or None if failed
        """
        try:
            if output_dir is None:
                output_dir = self.models_dir / model_id.replace("/", "--")
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading {model_id} to {output_dir}...")
            
            # Download with snapshot_download
            snapshot_download(
                repo_id=model_id,
                local_dir=str(output_dir),
                local_dir_use_symlinks=False,
                ignore_patterns=ignore_patterns or ["*.msgpack", "*.h5", "*.tflite", "*.safetensors.index.json"],
                resume_download=resume_download,
                force_download=False
            )
            
            logger.info(f"Successfully downloaded {model_id}")
            return output_dir
            
        except Exception as e:
            logger.error(f"Failed to download {model_id}: {e}")
            return None
    
    def download_multiple_models(self, model_ids: List[str]) -> Dict[str, bool]:
        """Download multiple models concurrently."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_model = {
                executor.submit(self.download_model, model_id): model_id 
                for model_id in model_ids
            }
            
            for future in as_completed(future_to_model):
                model_id = future_to_model[future]
                try:
                    result = future.result()
                    results[model_id] = result is not None
                except Exception as e:
                    logger.error(f"Error downloading {model_id}: {e}")
                    results[model_id] = False
        
        return results
    
    def list_local_models(self) -> List[ModelInfo]:
        """List all locally downloaded models."""
        models = []
        
        if not self.models_dir.exists():
            return models
        
        for model_dir in self.models_dir.iterdir():
            if model_dir.is_dir():
                # Try to find model info
                model_id = model_dir.name.replace("--", "/")
                model_info = self.get_model_info(model_id)
                
                if model_info:
                    model_info.is_downloaded = True
                    model_info.local_path = model_dir
                    models.append(model_info)
                else:
                    # Create basic info from directory
                    models.append(ModelInfo(
                        id=model_id,
                        name=model_dir.name,
                        is_downloaded=True,
                        local_path=model_dir
                    ))
        
        return models
    
    def delete_model(self, model_id: str) -> bool:
        """Delete a downloaded model."""
        try:
            # Find the model directory
            model_path = self.models_dir / model_id.replace("/", "--")
            
            if model_path.exists():
                shutil.rmtree(model_path)
                logger.info(f"Deleted model: {model_id}")
                
                # Remove from cache
                if model_id in self._cached_models:
                    del self._cached_models[model_id]
                
                return True
            
            # Try to find by name
            for model_dir in self.models_dir.iterdir():
                if model_dir.is_dir() and model_id in str(model_dir):
                    shutil.rmtree(model_dir)
                    logger.info(f"Deleted model: {model_id}")
                    return True
            
            logger.warning(f"Model {model_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting model {model_id}: {e}")
            return False
    
    def get_popular_models(self, task: str = None, limit: int = 20) -> List[ModelInfo]:
        """Get popular models, optionally filtered by task."""
        try:
            if task:
                models = list_models(
                    filter=ModelFilter(task=task),
                    sort="downloads",
                    limit=limit
                )
            else:
                models = list_models(
                    sort="downloads",
                    limit=limit
                )
            
            return [
                ModelInfo(
                    id=m.id,
                    name=m.id.split("/")[-1],
                    author=m.id.split("/")[0] if "/" in m.id else "",
                    description=m.description or "",
                    downloads=m.downloads,
                    likes=m.likes
                )
                for m in models
            ]
        except Exception as e:
            logger.error(f"Error getting popular models: {e}")
            return []
    
    def get_recent_models(self, limit: int = 20) -> List[ModelInfo]:
        """Get recently updated models."""
        try:
            models = list_models(
                sort="last_modified",
                limit=limit
            )
            
            return [
                ModelInfo(
                    id=m.id,
                    name=m.id.split("/")[-1],
                    author=m.id.split("/")[0] if "/" in m.id else "",
                    description=m.description or "",
                    last_modified=m.lastModified or ""
                )
                for m in models
            ]
        except Exception as e:
            logger.error(f"Error getting recent models: {e}")
            return []
    
    def search_by_capability(self, capability: str, limit: int = 20) -> List[ModelInfo]:
        """Search models by capability (task)."""
        return self.search_models(task=capability, limit=limit)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def get_model_config(self, model_path: Path) -> Optional[Dict[str, Any]]:
        """Get model configuration."""
        try:
            config = AutoConfig.from_pretrained(str(model_path))
            return config.to_dict()
        except Exception as e:
            logger.error(f"Error getting model config: {e}")
            return None
    
    def check_model_compatibility(self, model_id: str) -> Dict[str, Any]:
        """Check if a model is compatible with the current system."""
        from app.core.resource_detector import ResourceDetector
        
        specs = ResourceDetector.detect()
        model_info = self.get_model_info(model_id)
        
        if not model_info:
            return {"compatible": False, "reason": "Model not found"}
        
        # Check disk space
        try:
            model_size = self._get_model_size(model_id)
            disk_free = shutil.disk_usage(self.models_dir).free
            
            if model_size > disk_free:
                return {
                    "compatible": False,
                    "reason": f"Not enough disk space. Need {self._format_size(model_size)}, have {self._format_size(disk_free)}"
                }
        except Exception:
            pass
        
        # Check RAM
        if specs.ram_total_gb < 4:
            return {
                "compatible": False,
                "reason": f"Not enough RAM. Have {specs.ram_total_gb:.1f} GB, need at least 4 GB"
            }
        
        return {"compatible": True, "reason": "Model is compatible"}
    
    def _get_model_size(self, model_id: str) -> int:
        """Get model size in bytes."""
        try:
            model = model_info(model_id)
            if model.siblings:
                return sum(s.size for s in model.siblings)
            return 0
        except Exception:
            return 0
    
    def get_suggested_models(self, task: str = None) -> List[ModelInfo]:
        """Get suggested models based on task."""
        # Common tasks and their popular models
        task_models = {
            "text-generation": [
                "Qwen/Qwen2.5-7B-Instruct",
                "Qwen/Qwen2.5-Coder-7B",
                "deepseek-ai/DeepSeek-Coder-7B",
                "phi-3.5-mini-instruct",
                "llama3.2-7b-instruct"
            ],
            "text-classification": [
                "distilbert-base-uncased",
                "bert-base-uncased",
                "Qwen/Qwen2.5-7B"
            ],
            "text2text-generation": [
                "t5-small",
                "t5-base",
                "facebook/bart-base"
            ],
            "image-classification": [
                "google/vit-base-patch16-224",
                "microsoft/resnet-50",
                "convnext-tiny"
            ],
            "image-to-text": [
                "Qwen/Qwen2.5-VL-7B",
                "PaliGemma/paligemma-3b-mix-224",
                "llava-hf/llava-1.5-7b-hf"
            ],
            "automatic-speech-recognition": [
                "facebook/wav2vec2-base-960h",
                "openai/whisper-tiny",
                "openai/whisper-base"
            ]
        }
        
        if task and task in task_models:
            return [self.get_model_info(mid) for mid in task_models[task] if self.get_model_info(mid)]
        
        # Return popular models for text generation by default
        return [self.get_model_info(mid) for mid in task_models.get("text-generation", []) if self.get_model_info(mid)]
