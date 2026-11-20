"""Structured Answer and Citation Schemas (Phase 4 & 4.3)"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ClaimSupportState(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"

class CitationItem(BaseModel):
    citation_id: str
    document_id: str
    document_filename: str
    chunk_id: str
    page_number: int
    section_title: str = "General Section"
    exact_quote: str
    bounding_boxes: List[Dict[str, Any]] = Field(default_factory=list)
    verification_status: str = "unverified"  # "verified", "quote_mismatch", "page_mismatch", "source_missing"
    claim_support_status: str = "unverified"  # "supported", "unsupported", "partial"

class SupportingClaim(BaseModel):
    claim_id: str
    claim_text: str
    supporting_chunk_ids: List[str] = Field(default_factory=list)
    citation_ids: List[str] = Field(default_factory=list)
    verification_status: str = "unverified"  # "verified", "unverified", "partially_verified"
    support_state: ClaimSupportState = ClaimSupportState.INSUFFICIENT_EVIDENCE
    numerical_verified: Optional[bool] = None
    entities_verified: Optional[bool] = None
    temporal_verified: Optional[bool] = None
    reasoning: str = ""

class GroundedAnswer(BaseModel):
    answer_id: str
    conversation_id: Optional[str] = None
    question: str
    answer: str
    status: str = "answered"  # "answered", "partially_answered", "abstained"
    abstained: bool = False
    confidence: float = 0.0
    evidence_assessment: str = ""
    supporting_claims: List[SupportingClaim] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)
    unsupported_parts: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
