"""AI Providers Package for DocuMind Dual-Provider Inference"""

from backend.ai.providers.base import (
    AIProvider,
    AIProviderError,
    AIProviderAuthError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError
)
from backend.ai.providers.ollama_provider import OllamaProvider
from backend.ai.providers.groq_provider import GroqProvider
from backend.ai.providers.factory import (
    get_provider,
    set_active_provider,
    get_available_providers,
    get_ollama_provider,
    get_groq_provider,
    get_provider_capabilities
)

__all__ = [
    "AIProvider",
    "AIProviderError",
    "AIProviderAuthError",
    "AIProviderRateLimitError",
    "AIProviderTimeoutError",
    "AIProviderUnavailableError",
    "OllamaProvider",
    "GroqProvider",
    "get_provider",
    "set_active_provider",
    "get_available_providers",
    "get_ollama_provider",
    "get_groq_provider",
    "get_provider_capabilities"
]
