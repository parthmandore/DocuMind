"""Retrieval Base Models and Interfaces"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.chunking.base import DocumentChunk

class ScoredChunk(BaseModel):
    chunk: DocumentChunk
    score: float
    score_type: str = "hybrid"  # "dense", "sparse", "hybrid"
    explanation: Optional[Dict[str, Any]] = None

class Retriever(ABC):
    """Abstract interface for document chunk retrieval."""
    
    @abstractmethod
    def index(self, chunks: List[DocumentChunk]) -> None:
        """Index a collection of document chunks."""
        pass

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[ScoredChunk]:
        """Retrieve top_k most relevant chunks for a user query."""
        pass
