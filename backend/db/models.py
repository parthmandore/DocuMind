"""SQLAlchemy ORM Models for DocuMind

Implements the initial schema for:
- Documents
- Document sections
- Document chunks
- Conversations
- Messages
- Citations
- Processing jobs
- Evaluation records

Includes embedding model version tracking, cascade deletion, and vector safety.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SAEnum
)
from sqlalchemy.orm import relationship
from backend.db.base import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    CHUNKED = "CHUNKED"
    EMBEDDING = "EMBEDDING"
    INDEXED = "INDEXED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for duplicate detection
    
    status = Column(String(32), default=DocumentStatus.PENDING.value, nullable=False)
    error_message = Column(Text, nullable=True)
    quality_warnings = Column(JSON, default=list, nullable=False)  # Warnings: sparse, empty, order
    
    total_pages = Column(Integer, default=0, nullable=False)
    total_words = Column(Integer, default=0, nullable=False)
    total_sections = Column(Integer, default=0, nullable=False)
    total_chunks = Column(Integer, default=0, nullable=False)
    doc_metadata = Column(JSON, default=dict, nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships with CASCADE deletion
    sections = relationship(
        "DocumentSection",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    jobs = relationship(
        "ProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class DocumentSection(Base):
    __tablename__ = "document_sections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String(255), nullable=False, default="Untitled Section")
    section_level = Column(Integer, default=1, nullable=False)  # 1=H1, 2=H2, etc.
    page_number = Column(Integer, default=1, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    content = Column(Text, nullable=False)
    section_metadata = Column(JSON, default=dict, nullable=False)

    document = relationship("Document", back_populates="sections")
    chunks = relationship(
        "DocumentChunk",
        back_populates="section",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    section_id = Column(
        String(36),
        ForeignKey("document_sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, default=1, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    bboxes = Column(JSON, default=list, nullable=False)  # Bounding box coordinates
    
    # Embedding version tracking
    embedding_model = Column(String(64), nullable=True, index=True)
    embedding_dim = Column(Integer, nullable=True)
    embedding = Column(JSON, nullable=True)  # List[float] stored portably
    chunk_metadata = Column(JSON, default=dict, nullable=False)

    document = relationship("Document", back_populates="chunks")
    section = relationship("DocumentSection", back_populates="chunks")
    citations = relationship(
        "Citation",
        back_populates="chunk",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def set_embedding(self, vector: List[float], model_name: str, expected_dim: int):
        """Strictly validates vector dimensionality and model version to prevent vector mixing."""
        if len(vector) != expected_dim:
            raise ValueError(
                f"Incompatible embedding vector dimension: expected {expected_dim}, got {len(vector)}"
            )
        self.embedding = vector
        self.embedding_model = model_name
        self.embedding_dim = expected_dim

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), default="New Conversation", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(String(32), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    thinking_trace = Column(Text, nullable=True)
    message_metadata = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    citations = relationship(
        "Citation",
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class Citation(Base):
    __tablename__ = "citations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_id = Column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    page_number = Column(Integer, default=1, nullable=False)
    exact_quote = Column(Text, nullable=False)
    bbox = Column(JSON, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    grounding_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    message = relationship("Message", back_populates="citations")
    chunk = relationship("DocumentChunk", back_populates="citations")

    @property
    def document_id(self) -> Optional[str]:
        return self.chunk.document_id if self.chunk else None

    @property
    def document_filename(self) -> Optional[str]:
        return self.chunk.document.filename if (self.chunk and self.chunk.document) else None

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_type = Column(String(64), default="document_ingestion", nullable=False)
    status = Column(String(32), default=JobStatus.PENDING.value, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="jobs")

class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), nullable=False, index=True)
    category = Column(String(64), nullable=False)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=False)
    actual_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    grounding_score = Column(Float, default=0.0, nullable=False)
    latency_seconds = Column(Float, default=0.0, nullable=False)
    evaluated_at = Column(DateTime, default=utc_now, nullable=False)
    eval_metadata = Column(JSON, default=dict, nullable=False)
