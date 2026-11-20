"""Ollama Embedding Service Implementation

Communicates with the local Ollama daemon for dense vector embeddings,
coordinated strictly through the centralized OllamaHardwareArbiter.
"""

from typing import List, Optional
from backend.embeddings.base import EmbeddingService
from backend.config import config
from backend.ollama_runtime.client import ollama_client

class OllamaEmbeddingService(EmbeddingService):
    def __init__(self, host: str = None, model: str = None, timeout: float = 60.0):
        self.host = (host or config.ollama_host).rstrip("/")
        self.model = model or config.embedding_model
        self.timeout = timeout

    def embed_text(self, text: str) -> List[float]:
        return ollama_client.embed_single(text, model=self.model, timeout=self.timeout)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return ollama_client.embed(texts, model=self.model, timeout=self.timeout)
