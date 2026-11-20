"""AI Provider Base Abstraction and Unified Error Types

Defines common contract for local (Ollama) and remote (Groq) generation providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class AIProviderError(Exception):
    """Base error for all AI provider failures."""
    pass

class AIProviderAuthError(AIProviderError):
    """Raised when authentication with provider fails (e.g. invalid or missing API key)."""
    pass

class AIProviderRateLimitError(AIProviderError):
    """Raised when provider rate limit is exceeded."""
    pass

class AIProviderTimeoutError(AIProviderError):
    """Raised when provider response times out."""
    pass

class AIProviderUnavailableError(AIProviderError):
    """Raised when requested model or provider endpoint is unavailable."""
    pass

class AIProvider(ABC):
    """Abstract interface for generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Normalized provider identifier (e.g. 'ollama', 'groq')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Active or configured default model name."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes text generation and returns a normalized dictionary:
        {
            "response": str,
            "thinking": str,
            "eval_count": int,
            "model": str,
            "provider": str
        }
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Performs a lightweight connectivity / readiness check without printing secrets.
        Returns:
        {
            "status": "connected" | "unreachable" | "unconfigured" | "auth_error" | "error",
            "model": str,
            "available": bool,
            "message": Optional[str]
        }
        """
        pass

    def is_available(self) -> bool:
        """Quick boolean check if provider is responsive."""
        try:
            res = self.health_check()
            return bool(res.get("available", False))
        except Exception:
            return False
