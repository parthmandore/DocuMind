"""Unified Ollama Client Coordinated by Hardware Arbiter

Guarantees that all LLM generation, embedding requests, and model calls
are routed strictly through the OllamaHardwareArbiter, using persistent
HTTP keep-alive transport without redundant Windows SSL/proxy initialization.
"""

import json
import logging
import re
import threading
from typing import List, Dict, Any, Optional
import httpx
from backend.config import config
from backend.ollama_runtime.arbiter import arbiter

logger = logging.getLogger(__name__)

_DOT_LEADER_RE = re.compile(r"\.{4,}")


def prepare_embedding_text(text: str) -> str:
    """Normalizes pathological character runs (e.g. TOC dot leaders) before tokenization."""
    if not text:
        return ""
    if "...." in text:
        return _DOT_LEADER_RE.sub("...", text)
    return text


class OllamaClient:
    def __init__(self, host: Optional[str] = None):
        self.host = (host or config.ollama_host).rstrip("/")
        self._client_lock = threading.Lock()
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Returns a reusable persistent httpx.Client with fast local transport."""
        with self._client_lock:
            if self._client is None or getattr(self._client, "is_closed", False):
                use_ssl = self.host.startswith("https://")
                self._client = httpx.Client(
                    timeout=120.0,
                    trust_env=False,
                    verify=use_ssl,
                    limits=httpx.Limits(max_keepalive_connections=4, max_connections=8),
                )
            return self._client

    def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        timeout: float = 60.0
    ) -> List[List[float]]:
        """
        Embeds a batch of texts via Ollama /api/embed (or sequential fallback),
        strictly governed by the hardware arbiter and persistent keep-alive connection.
        """
        target_model = model or config.embedding_model
        if not texts:
            return []

        prepared_texts = [prepare_embedding_text(t) for t in texts]
        results: List[List[float]] = []

        with arbiter.acquire_sync(operation=f"embedding_batch[{len(prepared_texts)}]", timeout=timeout * 2):
            client = self._get_client()
            # Primary: Ollama native batched /api/embed with keep_alive="2h"
            try:
                resp = client.post(
                    f"{self.host}/api/embed",
                    json={"model": target_model, "input": prepared_texts, "keep_alive": "2h"},
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embeddings = data.get("embeddings", [])
                    if len(embeddings) == len(prepared_texts):
                        return embeddings
            except Exception as batch_err:
                logger.debug("Batched /api/embed failed, falling back to /api/embeddings: %s", batch_err)

            # Fallback to sequential legacy /api/embeddings (safely bounded to context window)
            for t in prepared_texts:
                safe_t = t[:6000] if len(t) > 6000 else t
                resp = client.post(
                    f"{self.host}/api/embeddings",
                    json={"model": target_model, "prompt": safe_t, "keep_alive": "2h"},
                    timeout=timeout,
                )
                resp.raise_for_status()
                results.append(resp.json().get("embedding", []))

        return results

    def embed_single(
        self,
        text: str,
        model: Optional[str] = None,
        timeout: float = 30.0
    ) -> List[float]:
        """Embeds a single query string under the arbiter."""
        res = self.embed([text], model=model, timeout=timeout)
        return res[0] if res else []

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        Executes streaming generation under the arbiter.
        Collects response and thinking streams safely.
        """
        target_model = model or config.llm_model
        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": system or "",
            "stream": True,
            "options": options or {
                "temperature": config.llm_temperature,
                "num_predict": config.llm_num_predict
            }
        }

        with arbiter.acquire_sync(operation="llm_generation", timeout=timeout):
            accumulated_response = []
            accumulated_thinking = []
            eval_count = 0

            client = self._get_client()
            with client.stream("POST", f"{self.host}/api/generate", json=payload, timeout=timeout) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if "thinking" in chunk and chunk["thinking"]:
                            accumulated_thinking.append(chunk["thinking"])
                        if "response" in chunk and chunk["response"]:
                            accumulated_response.append(chunk["response"])
                        if chunk.get("done", False):
                            eval_count = chunk.get("eval_count", 0)
                    except Exception:
                        continue

            return {
                "response": "".join(accumulated_response).strip(),
                "thinking": "".join(accumulated_thinking).strip(),
                "eval_count": eval_count,
                "model": target_model
            }

    def unload_model(self, model: str) -> bool:
        """Explicitly unloads a model from host RAM by requesting keep_alive: 0."""
        try:
            client = self._get_client()
            resp = client.post(
                f"{self.host}/api/generate",
                json={"model": model, "keep_alive": 0},
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to unload model {model}: {e}")
            return False

    def unload_all(self) -> bool:
        """Unloads both generation and embedding models to maximize free physical RAM."""
        u1 = self.unload_model(config.embedding_model)
        u2 = self.unload_model(config.llm_model)
        return u1 or u2


ollama_client = OllamaClient()
