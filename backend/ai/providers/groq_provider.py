"""Groq Cloud AI Provider Implementation (Temporary Inference Alternative)

Connects to Groq's official OpenAI-compatible chat completions endpoint.
Enforces strict secret masking, normalized responses, and error translation.
Does NOT hold local Ollama hardware locks.
"""

from typing import Dict, Any, Optional
import time
import httpx

from backend.config import config
from backend.ai.providers.base import (
    AIProvider,
    AIProviderError,
    AIProviderAuthError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError
)

class GroqProvider(AIProvider):
    """Temporary remote Groq generation provider."""

    def __init__(self):
        self._cached_health: Optional[Dict[str, Any]] = None
        self._cached_health_time: float = 0.0

    @property
    def name(self) -> str:
        return "groq"

    @property
    def default_model(self) -> str:
        return config.groq_model

    def _get_headers(self) -> Dict[str, str]:
        if not config.is_groq_configured:
            raise AIProviderAuthError("Groq API key is not configured in backend environment.")
        return {
            "Authorization": f"Bearer {config.groq_api_key}",
            "Content-Type": "application/json"
        }

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        target_model = model or self.default_model
        req_timeout = timeout or config.groq_timeout_seconds
        headers = self._get_headers()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        opts = options or {}
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": opts.get("temperature", 0.0),
            "max_tokens": opts.get("num_predict", config.llm_num_predict)
        }

        url = f"{config.groq_base_url}/chat/completions"

        try:
            with httpx.Client(timeout=req_timeout) as client:
                resp = client.post(url, headers=headers, json=payload)

                if resp.status_code == 401 or resp.status_code == 403:
                    raise AIProviderAuthError("Groq authentication failed: invalid API key or permission denied.")
                elif resp.status_code == 429:
                    retry_after = resp.headers.get("retry-after", "")
                    reset_tokens = resp.headers.get("x-ratelimit-reset-tokens", "")
                    remaining_tokens = resp.headers.get("x-ratelimit-remaining-tokens", "0")
                    msg = f"Groq rate limit exceeded (429). Remaining tokens: {remaining_tokens}, Reset: {reset_tokens}, Retry-After: {retry_after}s"
                    raise AIProviderRateLimitError(msg)
                elif resp.status_code == 404:
                    raise AIProviderUnavailableError(f"Groq model '{target_model}' not found or unavailable.")
                elif resp.status_code >= 500:
                    raise AIProviderError(f"Groq API remote server error (HTTP {resp.status_code}).")
                elif resp.status_code != 200:
                    raise AIProviderError(f"Groq API returned unexpected HTTP status {resp.status_code}.")

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise AIProviderError("Groq returned empty choices in completion response.")

                msg = choices[0].get("message", {})
                content = (msg.get("content") or "").strip()
                reasoning = (msg.get("reasoning") or "").strip()

                # Extract reasoning if enclosed in standard <think> tags
                thinking = reasoning
                if "<think>" in content and "</think>" in content:
                    parts = content.split("</think>", 1)
                    thinking = parts[0].replace("<think>", "").strip()
                    content = parts[1].strip()

                usage = data.get("usage", {})
                eval_count = usage.get("completion_tokens", 0)
                prompt_tokens = usage.get("prompt_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                ratelimit_info = {
                    "remaining_tokens": resp.headers.get("x-ratelimit-remaining-tokens"),
                    "limit_tokens": resp.headers.get("x-ratelimit-limit-tokens"),
                    "reset_tokens": resp.headers.get("x-ratelimit-reset-tokens"),
                    "remaining_requests": resp.headers.get("x-ratelimit-remaining-requests"),
                    "reset_requests": resp.headers.get("x-ratelimit-reset-requests"),
                }

                return {
                    "response": content,
                    "thinking": thinking,
                    "eval_count": eval_count,
                    "prompt_tokens": prompt_tokens,
                    "total_tokens": total_tokens,
                    "ratelimit": ratelimit_info,
                    "model": target_model,
                    "provider": "groq"
                }

        except (AIProviderAuthError, AIProviderRateLimitError, AIProviderUnavailableError, AIProviderError):
            raise
        except httpx.TimeoutException:
            raise AIProviderTimeoutError(f"Groq request timed out after {req_timeout}s.")
        except httpx.RequestError as req_err:
            raise AIProviderError(f"Network error communicating with Groq API: {type(req_err).__name__}")
        except Exception as e:
            raise AIProviderError(f"Unexpected Groq generation error: {e}")

    def health_check(self, force: bool = False) -> Dict[str, Any]:
        """Performs a lightweight connectivity check to Groq without exposing credentials."""
        now = time.time()
        if not force and self._cached_health is not None and (now - self._cached_health_time < 5.0):
            return self._cached_health

        if not config.is_groq_configured:
            res = {
                "status": "unconfigured",
                "model": self.default_model,
                "available": False,
                "message": "GROQ_API_KEY is not configured in backend environment."
            }
            self._cached_health = res
            self._cached_health_time = now
            return res

        try:
            with httpx.Client(timeout=3.0) as client:
                headers = {"Authorization": f"Bearer {config.groq_api_key}"}
                resp = client.get(f"{config.groq_base_url}/models", headers=headers)
                if resp.status_code == 200:
                    res = {
                        "status": "connected",
                        "model": self.default_model,
                        "available": True,
                        "message": "Groq Cloud API connected"
                    }
                elif resp.status_code in (401, 403):
                    res = {
                        "status": "auth_error",
                        "model": self.default_model,
                        "available": False,
                        "message": "Invalid or expired Groq API key"
                    }
                else:
                    res = {
                        "status": f"http_{resp.status_code}",
                        "model": self.default_model,
                        "available": False,
                        "message": f"Groq endpoint returned HTTP {resp.status_code}"
                    }
        except httpx.TimeoutException:
            res = {
                "status": "timeout",
                "model": self.default_model,
                "available": False,
                "message": "Groq endpoint health check timed out"
            }
        except Exception:
            res = {
                "status": "unreachable",
                "model": self.default_model,
                "available": False,
                "message": "Groq endpoint unreachable"
            }

        self._cached_health = res
        self._cached_health_time = now
        return res
