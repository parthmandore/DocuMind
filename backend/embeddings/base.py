"""Embedding Service Base Interfaces"""

from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel

class EmbeddingVector(BaseModel):
    vector: List[float]
    dimension: int

class EmbeddingService(ABC):
    """Abstract interface for local embedding generation."""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate vector embedding for a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a batch of text strings."""
        pass
