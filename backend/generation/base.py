"""Generation Base Models and Interfaces"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.retrieval.base import ScoredChunk

class CitationRef(BaseModel):
    chunk_id: str
    doc_id: str
    page: int
    quote: str

class GenerationResponse(BaseModel):
    answer: str
    thinking: Optional[str] = None
    citations: List[CitationRef] = Field(default_factory=list)
    abstained: bool = False
    tokens_used: int = 0
    latency_seconds: float = 0.0
    model: str = ""

class Generator(ABC):
    """Abstract interface for local language generation."""
    
    @abstractmethod
    def generate(
        self,
        query: str,
        context_chunks: List[ScoredChunk],
        system_instruction: Optional[str] = None
    ) -> GenerationResponse:
        """Generate a grounded response citing provided chunks."""
        pass
