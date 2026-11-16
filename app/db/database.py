"""
AI-Local-Hub - Database
=======================
SQLite database for tracking models, repositories, and settings.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from app.utils.config import Config


# Database schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    model_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,  -- 'ollama', 'huggingface', 'github'
    path TEXT NOT NULL,
    size_bytes INTEGER,
    type TEXT DEFAULT 'text',  -- 'text' or 'multimodal'
    framework TEXT,  -- 'pytorch', 'tensorflow', etc.
    vram_required REAL DEFAULT 0.0,
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    description TEXT
);

CREATE TABLE IF NOT EXISTS github_repos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_name TEXT NOT NULL,
    repo_url TEXT NOT NULL UNIQUE,
    local_path TEXT,
    last_pulled TIMESTAMP,
    auto_update BOOLEAN DEFAULT FALSE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inference_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT,
    time_taken REAL,
    tokens_generated INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES models(model_id)
);

CREATE INDEX IF NOT EXISTS idx_models_source ON models(source);
CREATE INDEX IF NOT EXISTS idx_models_type ON models(type);
CREATE INDEX IF NOT EXISTS idx_models_downloaded ON models(downloaded_at);
CREATE INDEX IF NOT EXISTS idx_inference_model ON inference_history(model_id);
CREATE INDEX IF NOT EXISTS idx_inference_created ON inference_history(created_at);
"""


@dataclass
class ModelRecord:
    """Database record for a model."""
    id: Optional[int] = None
    name: str = ""
    model_id: str = ""
    source: str = ""
    path: str = ""
    size_bytes: int = 0
    type: str = "text"
    framework: str = ""
    vram_required: float = 0.0
    downloaded_at: str = ""
    last_used: str = ""
    description: str = ""


@dataclass
class GitHubRepoRecord:
    """Database record for a GitHub repository."""
    id: Optional[int] = None
    repo_name: str = ""
    repo_url: str = ""
    local_path: str = ""
    last_pulled: str = ""
    auto_update: bool = False
    description: str = ""


class Database:
    """SQLite database manager."""
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Config.DB_PATH
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database and create tables."""
        with self._get_connection() as conn:
            conn.executescript(SCHEMA)
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(str(self.db_path))
    
    # Models CRUD
    def add_model(self, model: ModelRecord) -> ModelRecord:
        """Add a new model to the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO models (
                    name, model_id, source, path, size_bytes, type, framework,
                    vram_required, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model.name,
                    model.model_id,
                    model.source,
                    model.path,
                    model.size_bytes,
                    model.type,
                    model.framework,
                    model.vram_required,
                    model.description
                )
            )
            conn.commit()
            model.id = cursor.lastrowid
            return model
    
    def get_model(self, model_id: str) -> Optional[ModelRecord]:
        """Get a model by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM models WHERE model_id = ?",
                (model_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_model(row)
            return None
    
    def get_models(
        self,
        source: str = None,
        model_type: str = None,
        limit: int = None
    ) -> List[ModelRecord]:
        """Get all models with optional filters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM models"
            params = []
            
            conditions = []
            if source:
                conditions.append("source = ?")
                params.append(source)
            if model_type:
                conditions.append("type = ?")
                params.append(model_type)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def update_model(self, model: ModelRecord) -> bool:
        """Update a model in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE models SET
                    name = ?,
                    source = ?,
                    path = ?,
                    size_bytes = ?,
                    type = ?,
                    framework = ?,
                    vram_required = ?,
                    last_used = CURRENT_TIMESTAMP,
                    description = ?
                WHERE model_id = ?
                """,
                (
                    model.name,
                    model.source,
                    model.path,
                    model.size_bytes,
                    model.type,
                    model.framework,
                    model.vram_required,
                    model.description,
                    model.model_id
                )
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_model(self, model_id: str) -> bool:
        """Delete a model from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM models WHERE model_id = ?",
                (model_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def _row_to_model(self, row: tuple) -> ModelRecord:
        """Convert a database row to a ModelRecord."""
        return ModelRecord(
            id=row[0],
            name=row[1],
            model_id=row[2],
            source=row[3],
            path=row[4],
            size_bytes=row[5],
            type=row[6],
            framework=row[7],
            vram_required=row[8],
            downloaded_at=row[9],
            last_used=row[10],
            description=row[11]
        )
    
    # GitHub Repos CRUD
    def add_github_repo(self, repo: GitHubRepoRecord) -> GitHubRepoRecord:
        """Add a GitHub repository to the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO github_repos (
                    repo_name, repo_url, local_path, auto_update, description
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    repo.repo_name,
                    repo.repo_url,
                    repo.local_path,
                    repo.auto_update,
                    repo.description
                )
            )
            conn.commit()
            repo.id = cursor.lastrowid
            return repo
    
    def get_github_repo(self, repo_url: str) -> Optional[GitHubRepoRecord]:
        """Get a GitHub repository by its URL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM github_repos WHERE repo_url = ?",
                (repo_url,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_github_repo(row)
            return None
    
    def get_github_repos(self) -> List[GitHubRepoRecord]:
        """Get all GitHub repositories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM github_repos")
            rows = cursor.fetchall()
            return [self._row_to_github_repo(row) for row in rows]
    
    def update_github_repo(self, repo: GitHubRepoRecord) -> bool:
        """Update a GitHub repository in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE github_repos SET
                    repo_name = ?,
                    local_path = ?,
                    last_pulled = CURRENT_TIMESTAMP,
                    auto_update = ?,
                    description = ?
                WHERE repo_url = ?
                """,
                (
                    repo.repo_name,
                    repo.local_path,
                    repo.auto_update,
                    repo.description,
                    repo.repo_url
                )
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_github_repo(self, repo_url: str) -> bool:
        """Delete a GitHub repository from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM github_repos WHERE repo_url = ?",
                (repo_url,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def _row_to_github_repo(self, row: tuple) -> GitHubRepoRecord:
        """Convert a database row to a GitHubRepoRecord."""
        return GitHubRepoRecord(
            id=row[0],
            repo_name=row[1],
            repo_url=row[2],
            local_path=row[3],
            last_pulled=row[4],
            auto_update=bool(row[5]),
            description=row[6]
        )
    
    # Settings CRUD
    def set_setting(self, key: str, value: Any) -> bool:
        """Set a setting value."""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (key, value_str)
            )
            conn.commit()
            return True
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return default
    
    def delete_setting(self, key: str) -> bool:
        """Delete a setting."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM settings WHERE key = ?",
                (key,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    # Inference History
    def add_inference(self, model_id: str, prompt: str, response: str, time_taken: float, tokens: int) -> bool:
        """Add an inference record to the history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO inference_history (
                    model_id, prompt, response, time_taken, tokens_generated
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (model_id, prompt, response, time_taken, tokens)
            )
            conn.commit()
            return True
    
    def get_inference_history(self, model_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get inference history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT model_id, prompt, response, time_taken, tokens_generated, created_at
                FROM inference_history
            """
            params = []
            
            if model_id:
                query += " WHERE model_id = ?"
                params.append(model_id)
            
            query += " ORDER BY created_at DESC"
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    def clear_inference_history(self) -> bool:
        """Clear all inference history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inference_history")
            conn.commit()
            return True
    
    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM models")
            model_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM github_repos")
            repo_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM inference_history")
            history_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT source, COUNT(*) FROM models GROUP BY source")
            sources = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute("SELECT type, COUNT(*) FROM models GROUP BY type")
            types = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                "models": model_count,
                "repositories": repo_count,
                "inference_history": history_count,
                "sources": sources,
                "types": types
            }


# Create a global database instance
db = Database()
