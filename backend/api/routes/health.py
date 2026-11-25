"""Health Check API Routes

Monitors local daemon connectivity (Ollama), remote inference provider (Groq),
database responsiveness, hardware arbiter state, and local disk space.
"""

import shutil
import time
import psutil
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.config import config
from backend.db.base import get_db
from backend.api.schemas import HealthResponse
from backend.ai.providers import get_provider, get_groq_provider
from backend.ollama_runtime.arbiter import arbiter

router = APIRouter(prefix="/health", tags=["health"])

_OLLAMA_PROBE_CACHE = {"status": "unreachable", "checked_at": 0.0}
_OLLAMA_PROBE_TTL_SEC = 3.0


def _probe_ollama_status() -> str:
    """Probes Ollama /api/tags with short connect timeout and brief caching."""
    now = time.monotonic()
    if (now - _OLLAMA_PROBE_CACHE["checked_at"]) < _OLLAMA_PROBE_TTL_SEC:
        return _OLLAMA_PROBE_CACHE["status"]

    status_val = "connected"
    try:
        with httpx.Client(
            timeout=httpx.Timeout(2.0, connect=0.5),
            trust_env=False,
            verify=config.ollama_host.startswith("https://")
        ) as client:
            resp = client.get(f"{config.ollama_host}/api/tags")
            if resp.status_code != 200:
                status_val = f"http_{resp.status_code}"
    except Exception:
        status_val = "unreachable"

    _OLLAMA_PROBE_CACHE["status"] = status_val
    _OLLAMA_PROBE_CACHE["checked_at"] = now
    return status_val

@router.get("", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Performs real-time health verification of local backend and AI provider dependencies."""
    # 1. DB check
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e}"

    # 2. Ollama check (Required for local embeddings and local generation)
    prev_ollama = _OLLAMA_PROBE_CACHE["status"]
    ollama_status = _probe_ollama_status()
    if ollama_status == "connected" and prev_ollama != "connected":
        from backend.jobs.worker import schedule_waiting_embeddings_resume
        schedule_waiting_embeddings_resume()

    # 3. Active generation provider check
    active_prov = get_provider()
    active_health = active_prov.health_check()
    generation_status = active_health.get("status", "unknown")

    # 4. Arbiter state
    arb_status = arbiter.get_status().get("status", "idle")

    # 5. Disk space check
    try:
        total, used, free = shutil.disk_usage(str(config.project_root))
        free_gb = round(free / (1024 ** 3), 2)
    except Exception:
        free_gb = 0.0

    # 6. Host RAM and CPU diagnostics
    ram_total_gb = None
    ram_available_gb = None
    ram_used_percent = None
    cpu_count = None
    try:
        mem = psutil.virtual_memory()
        ram_total_gb = round(mem.total / (1024 ** 3), 2)
        ram_available_gb = round(mem.available / (1024 ** 3), 2)
        ram_used_percent = round(mem.percent, 1)
        cpu_count = psutil.cpu_count(logical=True)
    except Exception:
        pass

    # Overall health determination:
    # DB must be connected, and the active generation provider must be available.
    is_healthy = (db_status == "connected") and bool(active_health.get("available", False))

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        app_name=config.app_name,
        database=db_status,
        ollama_status=ollama_status,
        free_disk_gb=free_gb,
        active_provider=active_prov.name,
        generation_provider_status=generation_status,
        embedding_provider_status=ollama_status,
        groq_configured=config.is_groq_configured,
        arbiter_status=arb_status,
        ram_total_gb=ram_total_gb,
        ram_available_gb=ram_available_gb,
        ram_used_percent=ram_used_percent,
        cpu_count=cpu_count
    )
