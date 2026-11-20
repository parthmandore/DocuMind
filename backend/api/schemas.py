"""Pydantic Schemas for DocuMind API Request and Response Payloads"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Re-export generation models for query API
from backend.generation.schemas import (
    CitationItem,
    SupportingClaim,
    GroundedAnswer
)

class BoundingBoxSchema(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    page: int

class SectionSchema(BaseModel):
    id: str
    title: str
    section_level: int
    page_number: int
    order_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChunkSchema(BaseModel):
    id: str
    chunk_index: int
    page_number: int
    text: str
    token_count: int
    bboxes: List[Dict[str, Any]] = Field(default_factory=list)

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    filename: str
    mime_type: str
    file_size_bytes: int
    file_hash: str
    status: str
    error_message: Optional[str] = None
    quality_warnings: List[str] = Field(default_factory=list)
    total_pages: int
    total_words: int
    total_sections: int
    total_chunks: int
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    job_id: str
    is_duplicate: bool
    message: str

class DocumentContentResponse(BaseModel):
    document_id: str
    title: str
    total_pages: int
    total_words: int
    quality_warnings: List[str] = Field(default_factory=list)
    sections: List[SectionSchema] = Field(default_factory=list)
    chunks: List[ChunkSchema] = Field(default_factory=list)

class IndexingStatusResponse(BaseModel):
    document_id: str
    status: str
    total_chunks: int
    embedded_chunks: int
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    indexed_at: Optional[str] = None
    is_indexed: bool
    percent_complete: Optional[float] = None
    is_lexical_ready: bool = False

class ReindexResponse(BaseModel):
    document_id: str
    job_id: str
    status: str
    message: str

class SearchHitSchema(BaseModel):
    chunk_id: str
    document_id: str
    section_id: Optional[str] = None
    page_number: int
    text: str
    bboxes: List[Dict[str, Any]] = Field(default_factory=list)
    dense_score: Optional[float] = None
    lexical_score: Optional[float] = None
    fused_score: float
    rank: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResponse(BaseModel):
    query: str
    mode: str
    effective_mode: Optional[str] = None
    total_results: int
    results: List[SearchHitSchema]

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    job_type: str
    status: str
    attempts: int
    error_details: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class HealthResponse(BaseModel):
    status: str
    app_name: str
    database: str
    ollama_status: str
    free_disk_gb: float
    active_provider: str = "ollama"
    generation_provider_status: str = "connected"
    embedding_provider_status: str = "connected"
    groq_configured: bool = False
    arbiter_status: Optional[str] = "idle"
    ram_total_gb: Optional[float] = None
    ram_available_gb: Optional[float] = None
    ram_used_percent: Optional[float] = None
    cpu_count: Optional[int] = None

class AIProviderHealthSchema(BaseModel):
    status: str
    model: str
    available: bool
    message: Optional[str] = None

class AIProviderSettingsResponse(BaseModel):
    active_provider: str
    available_providers: List[str]
    generation_model: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    embedding_available: bool
    groq_configured: bool
    provider_health: AIProviderHealthSchema
    warning: Optional[str] = None

class UpdateAIProviderRequest(BaseModel):
    provider: str = Field(..., description="Target AI provider ('ollama' or 'groq')")

# --- Phase 4 Query & Conversation Schemas ---

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Natural language user question")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional document IDs to scope search")
    conversation_id: Optional[str] = Field(default=None, description="Optional conversation ID for context persistence")

    @field_validator("question")
    @classmethod
    def validate_question_not_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace only.")
        return v.strip()

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)

class UpdateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class MessageCitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    chunk_id: str
    document_id: Optional[str] = None
    document_filename: Optional[str] = None
    page_number: int
    exact_quote: str
    bbox: Optional[Dict[str, Any]] = None
    is_verified: bool
    grounding_score: float
    created_at: datetime

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    thinking_trace: Optional[str] = None
    message_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    citations: List[MessageCitationResponse] = Field(default_factory=list)

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime

class ConversationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)

class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=150)
    category: str = Field(default="feedback")
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)
    website: Optional[str] = Field(default=None)  # Anti-spam honeypot field

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Invalid email address format.")
        if "\r" in clean or "\n" in clean:
            raise ValueError("Email contains illegal control characters.")
        return clean

    @field_validator("subject", "name")
    @classmethod
    def sanitize_single_line(cls, v: str) -> str:
        clean = v.strip()
        if "\r" in clean or "\n" in clean:
            raise ValueError("Input cannot contain newline characters.")
        return clean

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        clean = v.strip().lower()
        allowed = {"bug", "feedback", "feature", "general"}
        if clean not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(sorted(allowed))}")
        return clean

class ContactResponse(BaseModel):
    status: str
    message: str
    reference_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

