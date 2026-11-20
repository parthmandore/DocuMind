"""Local Ollama AI Provider Implementation

Coordinates local Qwen3 4B generation strictly under the OllamaHardwareArbiter.
"""

from typing import Dict, Any, Optional
import time
import httpx

from backend.config import config
from backend.ai.providers.base import (
    AIProvider,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderUnavailableError
)
from backend.ollama_runtime.client import ollama_client
from backend.ollama_runtime.arbiter import OllamaBusyError, MemoryThresholdError

class OllamaProvider(AIProvider):
    """Local Ollama generation provider."""

    def __init__(self):
        self._cached_health: Optional[Dict[str, Any]] = None
        self._cached_health_time: float = 0.0

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return config.llm_model

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        target_model = model or self.default_model
        req_timeout = timeout or config.llm_timeout_seconds

        try:
            res = ollama_client.generate(
                prompt=prompt,
                system=system,
                model=target_model,
                options=options,
                timeout=req_timeout
            )
            return {
                "response": res.get("response", "").strip(),
                "thinking": res.get("thinking", "").strip(),
                "eval_count": res.get("eval_count", 0),
                "model": target_model,
                "provider": "ollama"
            }
        except (OllamaBusyError, MemoryThresholdError):
            raise
        except httpx.TimeoutException:
            raise AIProviderTimeoutError(f"Ollama local generation timed out after {req_timeout}s.")
        except Exception as e:
            raise AIProviderError(f"Ollama local generation error: {e}")

    def health_check(self, force: bool = False) -> Dict[str, Any]:
        """Checks local Ollama daemon connectivity."""
        now = time.time()
        if not force and self._cached_health is not None and (now - self._cached_health_time < 3.0):
            return self._cached_health

        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{config.ollama_host}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    has_model = any(self.default_model in m for m in models)
                    res = {
                        "status": "connected",
                        "model": self.default_model,
                        "available": True,
                        "message": "Local Ollama daemon running" if has_model else f"Ollama connected (model '{self.default_model}' pending download)"
                    }
                else:
                    res = {
                        "status": f"http_{resp.status_code}",
                        "model": self.default_model,
                        "available": False,
                        "message": f"Ollama daemon returned HTTP {resp.status_code}"
                    }
        except Exception:
            res = {
                "status": "unreachable",
                "model": self.default_model,
                "available": False,
                "message": f"Ollama daemon unreachable at {config.ollama_host}"
            }

        self._cached_health = res
        self._cached_health_time = now
        return res
