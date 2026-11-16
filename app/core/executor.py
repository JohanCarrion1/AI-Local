"""
AI-Local-Hub - Model Executor
=============================
Handles loading and running AI models for inference.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoModelForImageTextToText,
    AutoTokenizer,
    AutoProcessor,
    pipeline,
    GenerationConfig
)

from app.utils.config import Config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """Result of an inference operation."""
    text: str
    model: str
    time_taken: float = 0.0
    tokens_generated: int = 0
    success: bool = True
    error: Optional[str] = None


class ModelExecutor:
    """Executes AI models for inference."""
    
    def __init__(self):
        self.models_dir = Config.MODELS_DIR
        self.loaded_models: Dict[str, Any] = {}
        self.loaded_tokenizers: Dict[str, Any] = {}
        self.loaded_processors: Dict[str, Any] = {}
    
    def run_inference(
        self,
        model_path: Union[str, Path],
        prompt: str,
        model_type: str = "text",
        **kwargs
    ) -> InferenceResult:
        """
        Run inference on a model.
        
        Args:
            model_path: Path to the model directory or identifier
            prompt: Input text for the model
            model_type: "text" for text-only models, "multimodal" for vision models
            **kwargs: Additional arguments for generation
        
        Returns:
            InferenceResult with the generated text
        """
        import time
        start_time = time.time()
        
        model_path = Path(model_path)
        model_key = str(model_path)
        
        try:
            if model_type == "text":
                result = self._run_text_model(model_path, prompt, **kwargs)
            elif model_type == "multimodal":
                # For multimodal, prompt should contain both text and image
                result = self._run_multimodal_model(model_path, prompt, **kwargs)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            time_taken = time.time() - start_time
            
            return InferenceResult(
                text=result,
                model=str(model_path.name),
                time_taken=time_taken,
                tokens_generated=len(result.split()),
                success=True
            )
        except Exception as e:
            logger.error(f"Error running inference: {e}")
            return InferenceResult(
                text="",
                model=str(model_path.name),
                time_taken=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    def _run_text_model(
        self,
        model_path: Path,
        prompt: str,
        **kwargs
    ) -> str:
        """Run inference on a text-only model."""
        model_key = str(model_path)
        
        # Load model and tokenizer if not already loaded
        if model_key not in self.loaded_models:
            logger.info(f"Loading text model from {model_path}...")
            
            # Try to load with different configurations
            try:
                # Check if it's a quantized model
                if any(f.name.endswith('.gguf') for f in model_path.glob('*')):
                    # Use a different approach for GGUF models
                    return self._run_gguf_model(model_path, prompt, **kwargs)
                
                # Standard HuggingFace model
                tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
                
                # Determine device
                device = self._get_device()
                
                # Load model with appropriate settings
                model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                    device_map="auto" if device == "cuda" else None,
                    low_cpu_mem_usage=True
                )
                
                self.loaded_models[model_key] = model
                self.loaded_tokenizers[model_key] = tokenizer
                
            except Exception as e:
                logger.error(f"Failed to load text model: {e}")
                raise
        
        model = self.loaded_models[model_key]
        tokenizer = self.loaded_tokenizers[model_key]
        
        # Generate text
        inputs = tokenizer(prompt, return_tensors="pt")
        if "cuda" in str(next(model.parameters()).device):
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Generation config
        gen_config = GenerationConfig(
            temperature=kwargs.get("temperature", 0.7),
            max_new_tokens=kwargs.get("max_new_tokens", 512),
            do_sample=kwargs.get("do_sample", True),
            top_k=kwargs.get("top_k", 50),
            top_p=kwargs.get("top_p", 0.95),
            **kwargs
        )
        
        # Generate
        outputs = model.generate(**inputs, generation_config=gen_config)
        
        # Decode and return
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    def _run_multimodal_model(
        self,
        model_path: Path,
        prompt: Union[str, Dict[str, Any]],
        **kwargs
    ) -> str:
        """Run inference on a multimodal model (text + image)."""
        model_key = str(model_path)
        
        if model_key not in self.loaded_models:
            logger.info(f"Loading multimodal model from {model_path}...")
            
            try:
                processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
                
                device = self._get_device()
                
                model = AutoModelForImageTextToText.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                    device_map="auto" if device == "cuda" else None
                )
                
                self.loaded_models[model_key] = model
                self.loaded_processors[model_key] = processor
                
            except Exception as e:
                logger.error(f"Failed to load multimodal model: {e}")
                raise
        
        model = self.loaded_models[model_key]
        processor = self.loaded_processors[model_key]
        
        # Handle prompt (can be text or dict with image and text)
        if isinstance(prompt, str):
            # Text-only prompt for multimodal models
            inputs = processor(text=prompt, return_tensors="pt")
        else:
            # Dict with image and text
            image = prompt.get("image")
            text = prompt.get("text", "")
            
            if image:
                # Load image
                from PIL import Image
                if isinstance(image, str):
                    image = Image.open(image)
                inputs = processor(images=image, text=text, return_tensors="pt")
            else:
                inputs = processor(text=text, return_tensors="pt")
        
        # Move to device
        if "cuda" in str(next(model.parameters()).device):
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Generate
        outputs = model.generate(**inputs, max_new_tokens=kwargs.get("max_new_tokens", 512))
        
        # Decode and return
        return processor.decode(outputs[0], skip_special_tokens=True)
    
    def _run_gguf_model(
        self,
        model_path: Path,
        prompt: str,
        **kwargs
    ) -> str:
        """Run inference on a GGUF model using llama-cpp."""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise RuntimeError("llama-cpp is not installed. Run: pip install llama-cpp-python")
        
        # Find GGUF file
        gguf_file = None
        for f in model_path.glob("*"):
            if f.name.endswith('.gguf'):
                gguf_file = f
                break
        
        if not gguf_file:
            raise ValueError(f"No GGUF file found in {model_path}")
        
        # Load model
        llm = Llama(
            model_path=str(gguf_file),
            n_ctx=kwargs.get("max_new_tokens", 512),
            n_threads=4,
            n_gpu_layers=-1  # Use all available GPU layers
        )
        
        # Generate
        output = llm(
            prompt=prompt,
            max_tokens=kwargs.get("max_new_tokens", 512),
            temperature=kwargs.get("temperature", 0.7),
            top_p=kwargs.get("top_p", 0.95),
            **kwargs
        )
        
        return output["choices"][0]["text"]
    
    def _get_device(self) -> str:
        """Get the best available device for inference."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def unload_model(self, model_path: Union[str, Path]) -> bool:
        """Unload a model from memory."""
        model_key = str(Path(model_path))
        
        if model_key in self.loaded_models:
            del self.loaded_models[model_key]
        if model_key in self.loaded_tokenizers:
            del self.loaded_tokenizers[model_key]
        if model_key in self.loaded_processors:
            del self.loaded_processors[model_key]
        
        logger.info(f"Unloaded model: {model_key}")
        return True
    
    def clear_memory(self) -> None:
        """Clear all loaded models from memory."""
        self.loaded_models.clear()
        self.loaded_tokenizers.clear()
        self.loaded_processors.clear()
        
        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Cleared all models from memory")
    
    def get_supported_models(self) -> Dict[str, List[str]]:
        """Get list of supported model types and frameworks."""
        return {
            "text": [
                "Qwen", "Qwen2", "Qwen3",
                "Llama", "Mistral", "Phi",
                "DeepSeek", "CodeQwen"
            ],
            "multimodal": [
                "Qwen-VL", "Qwen2.5-VL",
                "PaliGemma", "LLaVA",
                "MobileVLM", "Pixtral"
            ],
            "frameworks": [
                "PyTorch", "TensorFlow", 
                "ONNX", "GGUF (llama-cpp)"
            ]
        }
    
    def check_model_compatibility(self, model_path: Path) -> Dict[str, Any]:
        """Check if a model is compatible with the current system."""
        from app.core.resource_detector import ResourceDetector
        
        specs = ResourceDetector.detect()
        
        # Check if model directory exists
        if not model_path.exists():
            return {"compatible": False, "reason": "Model not found"}
        
        # Check disk space
        model_size = sum(f.stat().st_size for f in model_path.glob('*') if f.is_file())
        disk_free = psutil.disk_usage(model_path.parent).free
        
        if model_size > disk_free:
            return {
                "compatible": False,
                "reason": f"Not enough disk space. Need {model_size / (1024**3):.2f} GB, have {disk_free / (1024**3):.2f} GB"
            }
        
        # Check RAM
        if specs.ram_total_gb < 4:
            return {
                "compatible": False,
                "reason": f"Not enough RAM. Have {specs.ram_total_gb:.1f} GB, need at least 4 GB"
            }
        
        return {"compatible": True, "reason": "Model is compatible"}
