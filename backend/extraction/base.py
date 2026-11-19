"""Document Extraction Base Interfaces and Data Models"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    page: int

class ExtractedBlock(BaseModel):
    block_id: str
    page: int
    text: str
    bbox: Optional[BoundingBox] = None
    block_type: str = "text"  # 'text', 'heading', 'list', 'code', 'table'
    section_id: Optional[str] = None
    table_id: Optional[str] = None

class ExtractedSection(BaseModel):
    section_id: str
    title: str
    section_level: int = 1  # 1 for H1, 2 for H2, etc.
    page_number: int = 1
    order_index: int = 0
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExtractedTable(BaseModel):
    table_id: str
    page: int
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    bbox: Optional[BoundingBox] = None

class ExtractedDocument(BaseModel):
    doc_id: str
    source_path: str
    total_pages: int
    blocks: List[ExtractedBlock] = Field(default_factory=list)
    sections: List[ExtractedSection] = Field(default_factory=list)
    tables: List[ExtractedTable] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    quality_warnings: List[str] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks if b.text.strip())

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())

class DocumentParser(ABC):
    """Abstract interface for document parsers."""
    
    @abstractmethod
    def parse(self, file_path: str) -> ExtractedDocument:
        """Parse a local document file into a structured ExtractedDocument."""
        pass
