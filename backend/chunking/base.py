"""Chunking Base Models and Interfaces"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.extraction.base import BoundingBox, ExtractedDocument

class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    section_id: Optional[str] = None
    table_id: Optional[str] = None
    page_numbers: List[int]
    text: str
    bboxes: List[BoundingBox] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    token_count: Optional[int] = None

class Chunker(ABC):
    """Abstract interface for document chunking."""
    
    @abstractmethod
    def chunk(self, doc: ExtractedDocument) -> List[DocumentChunk]:
        """Split an extracted document into grounded chunks."""
        pass
