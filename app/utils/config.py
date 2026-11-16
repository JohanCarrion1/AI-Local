"""
AI-Local-Hub - Configuration
============================
"""

from pathlib import Path
from typing import Dict, Any
import platform
import psutil


class Config:
    """Configuration manager for AI-Local-Hub."""
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent
    MODELS_DIR = BASE_DIR / "models"
    DB_DIR = BASE_DIR / "app" / "db"
    DB_PATH = DB_DIR / "models.db"
    ASSETS_DIR = BASE_DIR / "assets"
    ICON_DIR = ASSETS_DIR / "icon"
    
    # GitHub
    GITHUB_TOKEN_KEY = "github_token"
    GITHUB_TOKEN_SERVICE = "AI-Local-Hub"
    
    # Model Sources
    SUPPORTED_SOURCES = ["ollama", "huggingface", "github"]
    
    # Default Models by Resource Tier
    MODEL_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {
        "mobile_low": {  # 4-6GB RAM (A36)
            "name": "Mobile (Low-End)",
            "max_vram": 6,
            "recommended": [
                {"name": "Phi-3.5-mini", "size": "3.8B", "vram": 3, "source": "ollama", "id": "phi3.5:mini"},
                {"name": "Qwen2.5-Coder-7B", "size": "7B", "vram": 5, "source": "huggingface", "id": "Qwen/Qwen2.5-Coder-7B"},
                {"name": "DeepSeek-Coder-7B", "size": "7B", "vram": 5, "source": "huggingface", "id": "deepseek-ai/DeepSeek-Coder-7B"},
                {"name": "MobileVLM-7B", "size": "7B", "vram": 5, "source": "huggingface", "id": "VisualGLM/MobileVLM-7B", "type": "multimodal"},
                {"name": "PaliGemma-3B", "size": "3B", "vram": 4, "source": "huggingface", "id": "google/paligemma-3b-mix-224", "type": "multimodal"},
            ],
        },
        "mobile_high": {  # 6-8GB RAM
            "name": "Mobile (High-End)",
            "max_vram": 8,
            "recommended": [
                {"name": "Qwen3 8B", "size": "8B", "vram": 6, "source": "ollama", "id": "qwen3:8b"},
                {"name": "Llama 3.2 7B", "size": "7B", "vram": 6, "source": "ollama", "id": "llama3.2:7b"},
                {"name": "Qwen2.5-VL-7B", "size": "7B", "vram": 8, "source": "huggingface", "id": "Qwen/Qwen2.5-VL-7B", "type": "multimodal"},
            ],
        },
        "pc_low": {  # 16GB RAM
            "name": "PC (Low-End)",
            "max_vram": 16,
            "recommended": [
                {"name": "Qwen3.8-27B", "size": "27B", "vram": 24, "source": "ollama", "id": "qwen3:27b"},
                {"name": "Qwen2.5-Coder-14B", "size": "14B", "vram": 12, "source": "huggingface", "id": "Qwen/Qwen2.5-Coder-14B"},
                {"name": "DeepSeek-Coder-14B", "size": "14B", "vram": 12, "source": "huggingface", "id": "deepseek-ai/DeepSeek-Coder-14B"},
            ],
        },
        "pc_high": {  # 24GB+ RAM
            "name": "PC (High-End)",
            "max_vram": 24,
            "recommended": [
                {"name": "Qwen3.8-27B", "size": "27B", "vram": 24, "source": "ollama", "id": "qwen3:27b"},
                {"name": "Qwen2.5-VL-32B", "size": "32B", "vram": 24, "source": "huggingface", "id": "Qwen/Qwen2.5-VL-32B", "type": "multimodal"},
                {"name": "Llama 3.2 70B", "size": "70B", "vram": 40, "source": "ollama", "id": "llama3.2:70b"},
            ],
        },
        "server": {  # 48GB+ RAM
            "name": "Server",
            "max_vram": 80,
            "recommended": [
                {"name": "Qwen3-Coder-480B", "size": "480B", "vram": 80, "source": "huggingface", "id": "Qwen/Qwen3-Coder-480B"},
                {"name": "Qwen2.5-VL-72B", "size": "72B", "vram": 48, "source": "huggingface", "id": "Qwen/Qwen2.5-VL-72B", "type": "multimodal"},
                {"name": "Kimi-Dev-72B", "size": "72B", "vram": 48, "source": "huggingface", "id": "kimichat/Kimi-Dev-72B"},
            ],
        },
    }
    
    @classmethod
    def detect_tier(cls) -> str:
        """Detect the appropriate resource tier based on system specs."""
        try:
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            is_mobile = platform.system() == "Linux" and "Android" in platform.platform()
            
            # For mobile devices
            if is_mobile:
                if ram_gb <= 6:
                    return "mobile_low"
                else:
                    return "mobile_high"
            
            # For desktop
            if ram_gb <= 8:
                return "mobile_low"
            elif ram_gb <= 16:
                return "mobile_high"
            elif ram_gb <= 24:
                return "pc_low"
            elif ram_gb <= 48:
                return "pc_high"
            else:
                return "server"
        except Exception:
            return "mobile_low"  # Default to lowest tier
    
    @classmethod
    def get_recommendations(cls, tier: str = None) -> list:
        """Get recommended models for a specific tier."""
        if tier is None:
            tier = cls.detect_tier()
        return cls.MODEL_RECOMMENDATIONS.get(tier, cls.MODEL_RECOMMENDATIONS["mobile_low"])["recommended"]


# Create necessary directories
Config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
Config.DB_DIR.mkdir(parents=True, exist_ok=True)
