"""DocuMind - Global Configuration

Local-first configuration settings managing dual AI providers (Ollama & Groq),
endpoints, storage paths, upload limits, and hardware execution thresholds.
"""

import os
import json
from pathlib import Path
from typing import Optional, Set
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def load_env_file(env_path: Path) -> None:
    """Lightweight .env parser that populates os.environ without external dependencies."""
    if not env_path.exists():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

# Populate environment variables from local .env if present
load_env_file(PROJECT_ROOT / ".env")

SETTINGS_FILE = PROJECT_ROOT / "data" / "ai_settings.json"

def get_persisted_ai_provider() -> str:
    """Reads runtime provider preference if saved, falling back to env."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                prov = data.get("active_provider")
                if prov in ("ollama", "groq"):
                    return prov
        except Exception:
            pass
    return os.getenv("AI_PROVIDER", "groq").lower()

class DocuMindConfig(BaseModel):
    # Environment & Host
    app_name: str = "DocuMind"
    debug: bool = False
    project_root: Path = PROJECT_ROOT
    data_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data")
    upload_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "uploads")
    
    # Upload Limits & Validation
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    allowed_extensions: Set[str] = {".pdf", ".docx", ".txt", ".md", ".markdown"}
    allowed_mime_types: Set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "application/octet-stream"  # Checked with extension validation
    }
    
    # Extraction Quality Thresholds
    min_doc_char_count: int = 10
    sparse_page_char_threshold: int = 30  # Pages with fewer chars flagged as sparse/scanned
    
    # Dual AI Provider Configuration
    # Supported: 'ollama' (local inference), 'groq' (temporary cloud inference)
    ai_provider: str = Field(default_factory=get_persisted_ai_provider)
    
    # Groq Cloud Configuration
    groq_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip() or None)
    groq_base_url: str = Field(default_factory=lambda: os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"))
    groq_model: str = Field(default_factory=lambda: os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"))
    groq_timeout_seconds: float = Field(default_factory=lambda: float(os.getenv("GROQ_TIMEOUT_SECONDS", "120.0")))
    
    # Local Ollama Inference (Permanent)
    ollama_host: str = Field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
    llm_model: str = Field(default_factory=lambda: os.getenv("OLLAMA_GENERATION_MODEL", "qwen3:4b"))
    embedding_model: str = Field(default_factory=lambda: os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"))
    embedding_dimension: int = 768
    embedding_batch_size: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_BATCH_SIZE", "8")))
    
    # Generation parameters tuned for hardware
    llm_temperature: float = 0.2
    llm_num_predict: int = Field(default_factory=lambda: int(os.getenv("LLM_NUM_PREDICT", "2400")))
    llm_timeout_seconds: float = 120.0
    min_free_ram_mb: int = 200
    
    # Document Extraction & Chunking
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 50
    preserve_bounding_boxes: bool = True
    
    # Security, CORS & Network Policies
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            orig.strip()
            for orig in os.getenv(
                "CORS_ALLOWED_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
            ).split(",")
            if orig.strip()
        ]
    )
    enable_hsts: bool = Field(default_factory=lambda: os.getenv("ENABLE_HSTS", "false").lower() in ("true", "1", "yes"))

    # Support & Contact Email Configuration (Optional SMTP)
    smtp_host: Optional[str] = Field(default_factory=lambda: os.getenv("SMTP_HOST", "").strip() or None)
    smtp_port: int = Field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: Optional[str] = Field(default_factory=lambda: os.getenv("SMTP_USER", "").strip() or None)
    smtp_password: Optional[str] = Field(default_factory=lambda: os.getenv("SMTP_PASSWORD", "").strip() or None)
    smtp_sender: str = Field(default_factory=lambda: os.getenv("SMTP_SENDER", "noreply@documind.local"))
    support_email_recipient: str = Field(default_factory=lambda: os.getenv("SUPPORT_EMAIL_RECIPIENT", "support@documind.local"))

    # Database / Storage (Local only)
    db_type: str = "sqlite"
    sqlite_db_path: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "documind.db")
    pg_dsn: str = os.getenv("DOCUMIND_PG_DSN", "postgresql+psycopg://documind:documind@localhost:5432/documind")

    @property
    def database_url(self) -> str:
        if self.db_type == "postgresql":
            return self.pg_dsn
        os.makedirs(self.sqlite_db_path.parent, exist_ok=True)
        return f"sqlite:///{self.sqlite_db_path}"

    @property
    def is_groq_configured(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key.strip())

    def persist_ai_provider(self, provider: str) -> None:
        """Persists runtime choice of AI provider."""
        if provider not in ("ollama", "groq"):
            raise ValueError(f"Invalid AI provider '{provider}'. Must be 'ollama' or 'groq'.")
        self.ai_provider = provider
        os.makedirs(self.data_dir, exist_ok=True)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"active_provider": provider}, f, indent=2)
        except Exception:
            pass

config = DocuMindConfig()
# Ensure directories exist
os.makedirs(config.data_dir, exist_ok=True)
os.makedirs(config.upload_dir, exist_ok=True)
