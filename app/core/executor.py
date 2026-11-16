"""
AI-Local-Hub - Model Executor (Advanced Version)
===============================================
Load and run models directly using HuggingFace Transformers.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple
from dataclasses import dataclass, field
import time
import torch

from transformers import (
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    AutoModelForQuestionAnswering,
    AutoModelForImageClassification,
    AutoModelForImageTextToText,
    AutoModelForVisualQuestionAnswering,
    AutoModelForObjectDetection,
    AutoTokenizer,
    AutoProcessor,
    AutoImageProcessor,
    pipeline,
    GenerationConfig,
    Pipeline
)

from app.utils.config import Config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """Result of an inference operation."""
    text: str
    model_id: str
    task: str = ""
    time_taken: float = 0.0
    tokens_generated: int = 0
    success: bool = True
    error: Optional[str] = None
    raw_output: Optional[Dict[str, Any]] = None


@dataclass
class ModelLoader:
    """Helper class to load and manage models."""
    model: Any = None
    tokenizer: Any = None
    processor: Any = None
    pipeline: Optional[Pipeline] = None
    model_path: Optional[Path] = None
    model_id: str = ""
    task: str = ""
    device: str = "cpu"
    loaded: bool = False


class ModelExecutor:
    """Advanced executor for running AI models directly."""
    
    def __init__(self):
        self.loaded_models: Dict[str, ModelLoader] = {}
        self.device = self._get_device()
        self.max_memory = self._get_max_memory()
    
    def _get_device(self) -> str:
        """Get the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    def _get_max_memory(self) -> Dict[str, Any]:
        """Get max memory for each device."""
        max_memory = {}
        
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                max_memory[f"cuda:{i}"] = torch.cuda.get_device_properties(i).total_memory
                max_memory["cuda"] = torch.cuda.get_device_properties(0).total_memory
        
        return max_memory
    
    def load_model(
        self,
        model_path: Union[str, Path],
        task: str = "text-generation",
        model_id: str = None
    ) -> Optional[ModelLoader]:
        """
        Load a model for inference.
        
        Args:
            model_path: Path to the model directory
            task: Task type (text-generation, text-classification, etc.)
            model_id: Optional model identifier
        
        Returns:
            ModelLoader with loaded model, or None if failed
        """
        model_path = Path(model_path)
        model_key = str(model_path)
        
        # Check if already loaded
        if model_key in self.loaded_models:
            loader = self.loaded_models[model_key]
            if loader.loaded:
                return loader
        
        try:
            logger.info(f"Loading model from {model_path} for task: {task}")
            
            loader = ModelLoader(
                model_path=model_path,
                model_id=model_id or model_path.name,
                task=task,
                device=self.device
            )
            
            # Load based on task type
            if task == "text-generation":
                self._load_text_generation(loader)
            elif task == "text2text-generation":
                self._load_text2text(loader)
            elif task == "text-classification":
                self._load_classification(loader)
            elif task == "token-classification":
                self._load_token_classification(loader)
            elif task == "question-answering":
                self._load_qa(loader)
            elif task in ["image-classification", "image-to-text", "visual-question-answering", "object-detection"]:
                self._load_vision(loader, task)
            else:
                # Try to auto-detect task
                self._load_auto(loader, task)
            
            loader.loaded = True
            self.loaded_models[model_key] = loader
            logger.info(f"Successfully loaded model: {model_path.name}")
            return loader
            
        except Exception as e:
            logger.error(f"Error loading model {model_path}: {e}")
            return None
    
    def _load_text_generation(self, loader: ModelLoader) -> None:
        """Load text generation model."""
        loader.tokenizer = AutoTokenizer.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True
        )
        
        loader.model = AutoModelForCausalLM.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True,
            torch_dtype=torch.float16 if loader.device == "cuda" else torch.float32,
            device_map="auto" if loader.device == "cuda" else None
        )
    
    def _load_text2text(self, loader: ModelLoader) -> None:
        """Load text2text generation model."""
        loader.tokenizer = AutoTokenizer.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True
        )
        
        loader.model = AutoModelForSeq2SeqLM.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True,
            torch_dtype=torch.float16 if loader.device == "cuda" else torch.float32
        )
    
    def _load_classification(self, loader: ModelLoader) -> None:
        """Load text classification model."""
        loader.tokenizer = AutoTokenizer.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True
        )
        
        loader.model = AutoModelForSequenceClassification.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True
        )
    
    def _load_token_classification(self, loader: ModelLoader) -> None:
        """Load token classification model."""
        loader.tokenizer = AutoTokenizer.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True
        )
        
        loader.model = AutoModelForTokenClassification.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True
        )
    
    def _load_qa(self, loader: ModelLoader) -> None:
        """Load question answering model."""
        loader.tokenizer = AutoTokenizer.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True
        )
        
        loader.model = AutoModelForQuestionAnswering.from_pretrained(
            str(loader.model_path),
            trust_remote_code=True
        )
    
    def _load_vision(self, loader: ModelLoader, task: str) -> None:
        """Load vision model."""
        if task == "image-classification":
            loader.processor = AutoImageProcessor.from_pretrained(
                str(loader.model_path),
                trust_remote_code=True
            )
            loader.model = AutoModelForImageClassification.from_pretrained(
                str(loader.model_path),
                trust_remote_code=True
            )
        else:
            # For multimodal models (image + text)
            loader.processor = AutoProcessor.from_pretrained(
                str(loader.model_path),
                trust_remote_code=True
            )
            
            if task == "image-to-text":
                loader.model = AutoModelForImageTextToText.from_pretrained(
                    str(loader.model_path),
                    trust_remote_code=True
                )
            elif task == "visual-question-answering":
                loader.model = AutoModelForVisualQuestionAnswering.from_pretrained(
                    str(loader.model_path),
                    trust_remote_code=True
                )
            elif task == "object-detection":
                loader.model = AutoModelForObjectDetection.from_pretrained(
                    str(loader.model_path),
                    trust_remote_code=True
                )
    
    def _load_auto(self, loader: ModelLoader, task: str) -> None:
        """Try to auto-load model based on config."""
        try:
            # Try to create a pipeline
            loader.pipeline = pipeline(
                task=task,
                model=str(loader.model_path),
                tokenizer=str(loader.model_path),
                device=0 if loader.device == "cuda" else -1,
                trust_remote_code=True
            )
        except Exception:
            # Fallback to text generation
            self._load_text_generation(loader)
    
    def run_inference(
        self,
        model_path: Union[str, Path],
        inputs: Union[str, Dict[str, Any]],
        task: str = "text-generation",
        model_id: str = None,
        **kwargs
    ) -> InferenceResult:
        """
        Run inference on a model.
        
        Args:
            model_path: Path to the model directory
            inputs: Input data (string for text, dict for multimodal)
            task: Task type
            model_id: Optional model identifier
            **kwargs: Additional arguments for generation
        
        Returns:
            InferenceResult with the generated output
        """
        start_time = time.time()
        model_path = Path(model_path)
        
        try:
            # Load model if not already loaded
            loader = self.load_model(model_path, task, model_id)
            
            if not loader or not loader.loaded:
                return InferenceResult(
                    text="",
                    model_id=model_id or str(model_path),
                    task=task,
                    success=False,
                    error=f"Failed to load model from {model_path}"
                )
            
            # Run inference based on loader type
            if loader.pipeline:
                # Use pipeline if available
                result = self._run_pipeline(loader.pipeline, inputs, **kwargs)
            elif loader.model and loader.tokenizer:
                # Use model + tokenizer
                result = self._run_model_tokenizer(loader, inputs, task, **kwargs)
            elif loader.model and loader.processor:
                # Use model + processor (for vision)
                result = self._run_model_processor(loader, inputs, task, **kwargs)
            else:
                return InferenceResult(
                    text="",
                    model_id=model_id or str(model_path),
                    task=task,
                    success=False,
                    error="No valid model loader found"
                )
            
            elapsed_time = time.time() - start_time
            
            return InferenceResult(
                text=result.get("text", "") if isinstance(result, dict) else str(result),
                model_id=model_id or str(model_path),
                task=task,
                time_taken=elapsed_time,
                tokens_generated=len(result.get("text", "").split()) if isinstance(result, dict) else 0,
                success=True,
                raw_output=result
            )
            
        except Exception as e:
            logger.error(f"Error running inference: {e}")
            return InferenceResult(
                text="",
                model_id=model_id or str(model_path),
                task=task,
                time_taken=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    def _run_pipeline(self, pipe: Pipeline, inputs: Any, **kwargs) -> Any:
        """Run inference using a pipeline."""
        return pipe(inputs, **kwargs)
    
    def _run_model_tokenizer(self, loader: ModelLoader, inputs: Any, task: str, **kwargs) -> Dict[str, Any]:
        """Run inference using model + tokenizer."""
        model = loader.model.to(loader.device) if hasattr(loader.model, 'to') else loader.model
        
        if isinstance(inputs, str):
            encoded_inputs = loader.tokenizer(inputs, return_tensors="pt").to(loader.device)
        else:
            encoded_inputs = inputs
        
        # Generate based on task
        if task == "text-generation":
            gen_config = GenerationConfig(
                temperature=kwargs.get("temperature", 0.7),
                max_new_tokens=kwargs.get("max_new_tokens", 512),
                do_sample=kwargs.get("do_sample", True),
                top_k=kwargs.get("top_k", 50),
                top_p=kwargs.get("top_p", 0.95)
            )
            outputs = model.generate(**encoded_inputs, generation_config=gen_config)
            return {"text": loader.tokenizer.decode(outputs[0], skip_special_tokens=True)}
        else:
            outputs = model(**encoded_inputs)
            return outputs
    
    def _run_model_processor(self, loader: ModelLoader, inputs: Any, task: str, **kwargs) -> Dict[str, Any]:
        """Run inference using model + processor (for vision)."""
        model = loader.model.to(loader.device) if hasattr(loader.model, 'to') else loader.model
        
        if isinstance(inputs, dict):
            # Handle multimodal input
            if "image" in inputs and "text" in inputs:
                # For vision-language models
                images = inputs["image"]
                texts = inputs["text"]
                
                from PIL import Image
                if isinstance(images, str):
                    images = Image.open(images)
                
                encoded_inputs = loader.processor(images=images, text=texts, return_tensors="pt").to(loader.device)
            else:
                encoded_inputs = loader.processor(inputs, return_tensors="pt").to(loader.device)
        else:
            encoded_inputs = loader.processor(inputs, return_tensors="pt").to(loader.device)
        
        outputs = model(**encoded_inputs)
        
        if task == "image-to-text":
            return {"text": loader.processor.decode(outputs[0], skip_special_tokens=True)}
        else:
            return outputs
    
    def unload_model(self, model_path: Union[str, Path]) -> bool:
        """Unload a model from memory."""
        model_key = str(Path(model_path))
        
        if model_key in self.loaded_models:
            del self.loaded_models[model_key]
            
            # Clear GPU cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"Unloaded model: {model_key}")
            return True
        
        return False
    
    def unload_all(self) -> None:
        """Unload all models from memory."""
        self.loaded_models.clear()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Unloaded all models")
    
    def get_supported_tasks(self) -> List[str]:
        """Get list of supported tasks."""
        return [
            "text-generation",
            "text2text-generation",
            "text-classification",
            "token-classification",
            "question-answering",
            "image-classification",
            "image-to-text",
            "visual-question-answering",
            "object-detection",
            "automatic-speech-recognition",
            "fill-mask",
            "summarization",
            "translation",
            "conversational"
        ]
    
    def detect_task(self, model_path: Path) -> str:
        """Auto-detect task from model config."""
        try:
            config = AutoConfig.from_pretrained(str(model_path))
            
            if hasattr(config, 'task_specific_params'):
                return list(config.task_specific_params.keys())[0]
            
            if hasattr(config, 'model_type'):
                model_type = config.model_type
                if model_type in ["bert", "roberta", "distilbert"]:
                    return "text-classification"
                elif model_type in ["t5", "bart", "marian"]:
                    return "text2text-generation"
                elif model_type == "gpt2":
                    return "text-generation"
                elif model_type == "vit":
                    return "image-classification"
            
            return "text-generation"
            
        except Exception:
            return "text-generation"
    
    def get_model_capabilities(self, model_path: Path) -> Dict[str, Any]:
        """Get model capabilities and metadata."""
        try:
            config = AutoConfig.from_pretrained(str(model_path))
            
            return {
                "model_type": getattr(config, "model_type", "unknown"),
                "vocab_size": getattr(config, "vocab_size", 0),
                "hidden_size": getattr(config, "hidden_size", 0),
                "num_layers": getattr(config, "num_hidden_layers", 0),
                "num_attention_heads": getattr(config, "num_attention_heads", 0),
                "max_position_embeddings": getattr(config, "max_position_embeddings", 0)
            }
        except Exception as e:
            logger.error(f"Error getting model capabilities: {e}")
            return {}
