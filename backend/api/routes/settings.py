"""Settings API Route

Manages runtime dual-provider configuration (Ollama vs Groq)
without exposing secrets or modifying core retrieval architecture.
"""

from fastapi import APIRouter, HTTPException, status
from backend.config import config
from backend.ai.providers import (
    get_provider,
    set_active_provider,
    get_available_providers,
    get_ollama_provider,
    get_groq_provider
)
from backend.api.schemas import (
    AIProviderSettingsResponse,
    AIProviderHealthSchema,
    UpdateAIProviderRequest
)

router = APIRouter(prefix="/settings", tags=["settings"])

def _build_settings_response() -> AIProviderSettingsResponse:
    provider = get_provider()
    health = provider.health_check()
    ollama_prov = get_ollama_provider()
    ollama_health = ollama_prov.health_check()

    warning_msg = None
    if provider.name == "groq":
        warning_msg = (
            "Cloud inference active: Document excerpts for queries are processed via Groq API. "
            "Switch to Ollama for 100% local, air-gapped operation."
        )

    return AIProviderSettingsResponse(
        active_provider=provider.name,
        available_providers=get_available_providers(),
        generation_model=provider.default_model,
        embedding_provider="ollama",
        embedding_model=config.embedding_model,
        embedding_dimension=config.embedding_dimension,
        embedding_available=ollama_health.get("available", False),
        groq_configured=config.is_groq_configured,
        provider_health=AIProviderHealthSchema(
            status=health.get("status", "unknown"),
            model=health.get("model", provider.default_model),
            available=health.get("available", False),
            message=health.get("message")
        ),
        warning=warning_msg
    )

@router.get("/ai-provider", response_model=AIProviderSettingsResponse)
def get_ai_provider_settings():
    """Returns current AI provider configuration and capability status."""
    return _build_settings_response()

@router.put("/ai-provider", response_model=AIProviderSettingsResponse)
def update_ai_provider_settings(payload: UpdateAIProviderRequest):
    """
    Switches active generation provider between 'ollama' and 'groq'.
    Validates credentials and connectivity before persisting.
    """
    target = payload.provider.lower().strip()
    if target not in get_available_providers():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider '{payload.provider}'. Must be one of: {get_available_providers()}"
        )

    if target == "groq":
        if not config.is_groq_configured:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot switch to Groq: GROQ_API_KEY is not configured in backend environment (.env)."
            )
        # Verify connectivity
        groq_prov = get_groq_provider()
        health = groq_prov.health_check()
        if not health.get("available", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot switch to Groq: {health.get('message', 'Groq endpoint unreachable')}."
            )

    set_active_provider(target)
    return _build_settings_response()
