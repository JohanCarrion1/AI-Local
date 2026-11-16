"""
Tests for ResourceDetector
=========================
"""

import pytest
from app.core.resource_detector import ResourceDetector, DeviceSpecs


def test_detect_returns_device_specs():
    """Test that detect returns a DeviceSpecs object."""
    specs = ResourceDetector.detect()
    assert isinstance(specs, DeviceSpecs)


def test_detect_returns_valid_ram():
    """Test that RAM values are positive."""
    specs = ResourceDetector.detect()
    assert specs.ram_total_gb > 0
    assert specs.ram_available_gb >= 0


def test_detect_returns_valid_cpu():
    """Test that CPU values are valid."""
    specs = ResourceDetector.detect()
    assert specs.cpu_cores > 0
    assert len(specs.cpu_model) > 0


def test_detect_returns_os():
    """Test that OS is detected."""
    specs = ResourceDetector.detect()
    assert len(specs.os) > 0


def test_format_specs():
    """Test that format_specs returns a string."""
    specs = ResourceDetector.detect()
    formatted = ResourceDetector.format_specs(specs)
    assert isinstance(formatted, str)
    assert len(formatted) > 0


def test_get_compatible_models():
    """Test that get_compatible_models returns a list."""
    models = ResourceDetector.get_compatible_models()
    assert isinstance(models, list)


def test_detect_tier():
    """Test that detect_tier returns a valid tier."""
    from app.utils.config import Config
    tier = ResourceDetector.detect_tier()
    assert tier in Config.MODEL_RECOMMENDATIONS.keys()
