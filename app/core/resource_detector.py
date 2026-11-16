"""
AI-Local-Hub - Resource Detector
===============================
Detects system resources (RAM, VRAM, GPU, OS) to recommend compatible models.
"""

import platform
import psutil
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DeviceSpecs:
    """Device specifications."""
    os: str
    os_version: str
    ram_total_gb: float
    ram_available_gb: float
    cpu_cores: int
    cpu_model: str
    gpu: Optional[str] = None
    gpu_vram_gb: Optional[float] = None
    is_mobile: bool = False
    is_termux: bool = False
    architecture: str = "unknown"


class ResourceDetector:
    """Detects system resources and determines compatible models."""
    
    @staticmethod
    def detect() -> DeviceSpecs:
        """Detect all system resources."""
        return DeviceSpecs(
            os=ResourceDetector._detect_os(),
            os_version=ResourceDetector._detect_os_version(),
            ram_total_gb=ResourceDetector._detect_ram_total(),
            ram_available_gb=ResourceDetector._detect_ram_available(),
            cpu_cores=ResourceDetector._detect_cpu_cores(),
            cpu_model=ResourceDetector._detect_cpu_model(),
            gpu=ResourceDetector._detect_gpu(),
            gpu_vram_gb=ResourceDetector._detect_gpu_vram(),
            is_mobile=ResourceDetector._is_mobile(),
            is_termux=ResourceDetector._is_termux(),
            architecture=ResourceDetector._detect_architecture(),
        )
    
    @staticmethod
    def _detect_os() -> str:
        """Detect operating system."""
        system = platform.system().lower()
        if system == "linux":
            if ResourceDetector._is_termux():
                return "Android (Termux)"
            elif ResourceDetector._is_mobile():
                return "Android"
        return system.capitalize()
    
    @staticmethod
    def _detect_os_version() -> str:
        """Detect OS version."""
        try:
            if platform.system() == "Linux":
                with open("/proc/version", "r") as f:
                    version = f.read()
                    if "Android" in version or "aarch64" in version:
                        return "Android"
            return platform.version()
        except Exception:
            return "Unknown"
    
    @staticmethod
    def _detect_ram_total() -> float:
        """Detect total RAM in GB."""
        try:
            return round(psutil.virtual_memory().total / (1024 ** 3), 2)
        except Exception:
            return 0.0
    
    @staticmethod
    def _detect_ram_available() -> float:
        """Detect available RAM in GB."""
        try:
            return round(psutil.virtual_memory().available / (1024 ** 3), 2)
        except Exception:
            return 0.0
    
    @staticmethod
    def _detect_cpu_cores() -> int:
        """Detect number of CPU cores."""
        try:
            return psutil.cpu_count(logical=False) or 1
        except Exception:
            return 1
    
    @staticmethod
    def _detect_cpu_model() -> str:
        """Detect CPU model."""
        try:
            if platform.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.startswith("model name"):
                            return line.split(":")[1].strip()
                        elif line.startswith("Processor"):
                            return line.split(":")[1].strip()
            return platform.processor() or "Unknown"
        except Exception:
            return "Unknown"
    
    @staticmethod
    def _detect_gpu() -> Optional[str]:
        """Detect GPU model."""
        try:
            if platform.system() == "Linux":
                # Check for Adreno (Qualcomm mobile GPUs)
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read()
                    if "Adreno" in cpuinfo:
                        # Extract Adreno version
                        match = re.search(r"Adreno\s*(\d+)", cpuinfo)
                        if match:
                            return f"Adreno {match.group(1)}"
                        return "Adreno"
                
                # Check for Mali (ARM mobile GPUs)
                if "Mali" in cpuinfo:
                    return "Mali"
                
                # Check for NVIDIA
                if "NVIDIA" in cpuinfo:
                    return "NVIDIA"
                
            # For Windows/Mac
            if platform.system() == "Windows":
                try:
                    import wmi
                    c = wmi.WMI()
                    for gpu in c.Win32_VideoController():
                        if gpu.Name and "Intel" not in gpu.Name:
                            return gpu.Name
                except ImportError:
                    pass
                return "Unknown (Windows)"
            
            if platform.system() == "Darwin":
                try:
                    import subprocess
                    result = subprocess.run(
                        ["system_profiler", "SPDisplaysDataType"],
                        capture_output=True, text=True
                    )
                    for line in result.stdout.split("\n"):
                        if "Chipset Model" in line:
                            return line.split(":")[1].strip()
                except Exception:
                    pass
                return "Unknown (Mac)"
                
            return None
        except Exception:
            return None
    
    @staticmethod
    def _detect_gpu_vram() -> Optional[float]:
        """Detect GPU VRAM in GB."""
        try:
            if platform.system() == "Linux":
                # For mobile devices, estimate based on RAM
                if ResourceDetector._is_mobile():
                    total_ram = ResourceDetector._detect_ram_total()
                    # Mobile devices typically share RAM with GPU
                    return round(total_ram * 0.3, 1)  # Estimate 30% of RAM for GPU
                
                # For desktop Linux with NVIDIA
                try:
                    import subprocess
                    result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        vram_mb = float(result.stdout.strip().split()[0])
                        return round(vram_mb / 1024, 2)
                except Exception:
                    pass
                
                # For AMD/Intel
                try:
                    with open("/sys/class/drm/card0/device/mem_info_vram_total", "r") as f:
                        vram_kb = int(f.read().strip())
                        return round(vram_kb / (1024 ** 2), 2)
                except Exception:
                    pass
                
                return None
            
            if platform.system() == "Windows":
                try:
                    import wmi
                    c = wmi.WMI()
                    for gpu in c.Win32_VideoController():
                        if gpu.AdapterRAM:
                            vram_bytes = int(gpu.AdapterRAM)
                            return round(vram_bytes / (1024 ** 3), 2)
                except ImportError:
                    pass
                return None
            
            if platform.system() == "Darwin":
                try:
                    import subprocess
                    result = subprocess.run(
                        ["system_profiler", "SPDisplaysDataType"],
                        capture_output=True, text=True
                    )
                    for line in result.stdout.split("\n"):
                        if "VRAM" in line:
                            vram_mb = float(line.split(":")[1].strip().split()[0])
                            return round(vram_mb / 1024, 2)
                except Exception:
                    pass
                return None
                
            return None
        except Exception:
            return None
    
    @staticmethod
    def _is_mobile() -> bool:
        """Check if running on a mobile device."""
        try:
            system = platform.system().lower()
            if system == "android":
                return True
            if system == "linux":
                # Check for Android-specific files
                android_files = [
                    "/system/build.prop",
                    "/data",
                    "/sdcard",
                ]
                for f in android_files:
                    if Path(f).exists():
                        return True
                # Check for Adreno in cpuinfo
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        if "Adreno" in f.read() or "Mali" in f.read():
                            return True
                except Exception:
                    pass
            return False
        except Exception:
            return False
    
    @staticmethod
    def _is_termux() -> bool:
        """Check if running in Termux."""
        try:
            return "com.termux" in platform.platform().lower() or \
                   Path("/data/data/com.termux/files").exists() or \
                   "TERMUX_VERSION" in os.environ
        except Exception:
            return False
    
    @staticmethod
    def _detect_architecture() -> str:
        """Detect system architecture."""
        try:
            machine = platform.machine().lower()
            if machine in ["x86_64", "amd64"]:
                return "x86_64"
            elif machine in ["aarch64", "arm64"]:
                return "arm64"
            elif machine in ["armv7l", "armv8l"]:
                return "arm"
            else:
                return machine
        except Exception:
            return "unknown"
    
    @staticmethod
    def get_compatible_models(specs: DeviceSpecs = None) -> list:
        """Get list of compatible models based on device specs."""
        if specs is None:
            specs = ResourceDetector.detect()
        
        from app.utils.config import Config
        
        # Get recommendations based on tier
        tier = Config.detect_tier()
        recommendations = Config.get_recommendations(tier)
        
        # Filter by VRAM if GPU VRAM is known
        if specs.gpu_vram_gb:
            recommendations = [
                m for m in recommendations 
                if m.get("vram", 0) <= specs.gpu_vram_gb
            ]
        
        # Filter by RAM
        if specs.ram_total_gb:
            recommendations = [
                m for m in recommendations 
                if m.get("vram", 0) <= specs.ram_total_gb * 0.8  # Use 80% of RAM as limit
            ]
        
        return recommendations
    
    @staticmethod
    def format_specs(specs: DeviceSpecs = None) -> str:
        """Format device specs as a readable string."""
        if specs is None:
            specs = ResourceDetector.detect()
        
        lines = [
            f"Sistema Operativo: {specs.os} {specs.os_version}",
            f"Arquitectura: {specs.architecture}",
            f"RAM Total: {specs.ram_total_gb} GB",
            f"RAM Disponible: {specs.ram_available_gb} GB",
            f"Núcleos CPU: {specs.cpu_cores}",
            f"Modelo CPU: {specs.cpu_model}",
        ]
        
        if specs.gpu:
            lines.append(f"GPU: {specs.gpu}")
        if specs.gpu_vram_gb:
            lines.append(f"VRAM GPU: {specs.gpu_vram_gb} GB")
        if specs.is_mobile:
            lines.append("Dispositivo: Móvil")
        if specs.is_termux:
            lines.append("Entorno: Termux")
        
        return "\n".join(lines)


# Import Path for compatibility
from pathlib import Path
