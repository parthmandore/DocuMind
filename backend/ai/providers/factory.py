"""AI Provider Factory and Registry

Provides single point of resolution and dynamic runtime switching for AI providers.
"""

from typing import Dict, List, Optional, Any
from backend.config import config
from backend.ai.providers.base import AIProvider
from backend.ai.providers.ollama_provider import OllamaProvider
from backend.ai.providers.groq_provider import GroqProvider

_ollama_instance: Optional[OllamaProvider] = None
_groq_instance: Optional[GroqProvider] = None

def get_ollama_provider() -> OllamaProvider:
    global _ollama_instance
    if _ollama_instance is None:
        _ollama_instance = OllamaProvider()
    return _ollama_instance

def get_groq_provider() -> GroqProvider:
    global _groq_instance
    if _groq_instance is None:
        _groq_instance = GroqProvider()
    return _groq_instance

def get_available_providers() -> List[str]:
    return ["ollama", "groq"]

def get_provider(name: Optional[str] = None) -> AIProvider:
    """Returns the requested provider or the currently active configured provider."""
    target_name = (name or config.ai_provider).lower().strip()
    if target_name == "groq":
        return get_groq_provider()
    elif target_name == "ollama":
        return get_ollama_provider()
    else:
        raise ValueError(
            f"Unsupported AI provider '{target_name}'. Available providers: {get_available_providers()}"
        )

def set_active_provider(name: str) -> AIProvider:
    """Dynamically switches active generation provider and persists choice."""
    target_name = name.lower().strip()
    if target_name not in get_available_providers():
        raise ValueError(
            f"Cannot switch to '{name}'. Must be one of {get_available_providers()}"
        )
    config.persist_ai_provider(target_name)
    return get_provider(target_name)

def get_provider_capabilities() -> Dict[str, Any]:
    """
    Returns non-sensitive report of generation and embedding capabilities.
    Explicitly reports that embeddings are local-only via Ollama nomic-embed-text.
    """
    active_prov = get_provider()
    active_health = active_prov.health_check()
    ollama_prov = get_ollama_provider()
    ollama_health = ollama_prov.health_check()

    return {
        "active_provider": active_prov.name,
        "available_providers": get_available_providers(),
        "generation_model": active_prov.default_model,
        "generation_status": active_health.get("status", "unknown"),
        "generation_available": active_health.get("available", False),
        "embedding_provider": "ollama",
        "embedding_model": config.embedding_model,
        "embedding_dimension": config.embedding_dimension,
        "embedding_available": ollama_health.get("available", False),
        "groq_configured": config.is_groq_configured
    }
