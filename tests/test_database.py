"""
Tests for Database
==================
"""

import pytest
import tempfile
from pathlib import Path
from app.db.database import Database, ModelRecord, GitHubRepoRecord


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    db_path.unlink()


def test_add_and_get_model(temp_db):
    """Test adding and retrieving a model."""
    model = ModelRecord(
        name="Test Model",
        model_id="test-model",
        source="ollama",
        path="/path/to/model",
        type="text",
        vram_required=6.0
    )
    
    temp_db.add_model(model)
    retrieved = temp_db.get_model("test-model")
    
    assert retrieved is not None
    assert retrieved.name == "Test Model"
    assert retrieved.source == "ollama"


def test_get_models(temp_db):
    """Test getting multiple models."""
    model1 = ModelRecord(
        name="Model 1",
        model_id="model-1",
        source="ollama",
        path="/path/to/model1"
    )
    model2 = ModelRecord(
        name="Model 2",
        model_id="model-2",
        source="huggingface",
        path="/path/to/model2",
        type="multimodal"
    )
    
    temp_db.add_model(model1)
    temp_db.add_model(model2)
    
    models = temp_db.get_models()
    assert len(models) == 2


def test_update_model(temp_db):
    """Test updating a model."""
    model = ModelRecord(
        name="Original",
        model_id="test-model",
        source="ollama",
        path="/path/to/model"
    )
    
    temp_db.add_model(model)
    
    model.name = "Updated"
    model.vram_required = 8.0
    temp_db.update_model(model)
    
    retrieved = temp_db.get_model("test-model")
    assert retrieved.name == "Updated"
    assert retrieved.vram_required == 8.0


def test_delete_model(temp_db):
    """Test deleting a model."""
    model = ModelRecord(
        name="Test Model",
        model_id="test-model",
        source="ollama",
        path="/path/to/model"
    )
    
    temp_db.add_model(model)
    assert temp_db.get_model("test-model") is not None
    
    temp_db.delete_model("test-model")
    assert temp_db.get_model("test-model") is None


def test_github_repo_crud(temp_db):
    """Test GitHub repo CRUD operations."""
    repo = GitHubRepoRecord(
        repo_name="test-repo",
        repo_url="https://github.com/user/test-repo",
        local_path="/path/to/repo"
    )
    
    temp_db.add_github_repo(repo)
    retrieved = temp_db.get_github_repo("https://github.com/user/test-repo")
    
    assert retrieved is not None
    assert retrieved.repo_name == "test-repo"
    
    repo.local_path = "/new/path"
    temp_db.update_github_repo(repo)
    
    retrieved = temp_db.get_github_repo("https://github.com/user/test-repo")
    assert retrieved.local_path == "/new/path"
    
    temp_db.delete_github_repo("https://github.com/user/test-repo")
    assert temp_db.get_github_repo("https://github.com/user/test-repo") is None


def test_settings(temp_db):
    """Test settings operations."""
    temp_db.set_setting("test_key", "test_value")
    value = temp_db.get_setting("test_key")
    
    assert value == "test_value"
    
    temp_db.set_setting("test_key", "new_value")
    value = temp_db.get_setting("test_key")
    assert value == "new_value"
    
    temp_db.delete_setting("test_key")
    value = temp_db.get_setting("test_key", default="default")
    assert value == "default"


def test_inference_history(temp_db):
    """Test inference history operations."""
    temp_db.add_inference(
        model_id="test-model",
        prompt="Test prompt",
        response="Test response",
        time_taken=1.5,
        tokens=100
    )
    
    history = temp_db.get_inference_history()
    assert len(history) == 1
    assert history[0]["model_id"] == "test-model"
    assert history[0]["prompt"] == "Test prompt"


def test_stats(temp_db):
    """Test statistics."""
    temp_db.add_model(ModelRecord(
        name="Model 1",
        model_id="model-1",
        source="ollama",
        path="/path/to/model1",
        type="text"
    ))
    temp_db.add_model(ModelRecord(
        name="Model 2",
        model_id="model-2",
        source="huggingface",
        path="/path/to/model2",
        type="multimodal"
    ))
    temp_db.add_github_repo(GitHubRepoRecord(
        repo_name="test-repo",
        repo_url="https://github.com/user/test-repo"
    ))
    temp_db.add_inference(
        model_id="model-1",
        prompt="Test",
        response="Response",
        time_taken=1.0,
        tokens=50
    )
    
    stats = temp_db.get_stats()
    assert stats["models"] == 2
    assert stats["repositories"] == 1
    assert stats["inference_history"] == 1
    assert stats["sources"]["ollama"] == 1
    assert stats["sources"]["huggingface"] == 1
    assert stats["types"]["text"] == 1
    assert stats["types"]["multimodal"] == 1
