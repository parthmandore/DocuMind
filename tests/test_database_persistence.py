"""Tests for Database Persistence, Model Constraints, and Cascade Deletion"""

import pytest
import uuid
from backend.db.models import (
    Document,
    DocumentSection,
    DocumentChunk,
    Conversation,
    Message,
    Citation,
    ProcessingJob,
    EvaluationRecord,
    DocumentStatus,
    JobStatus
)

def test_document_and_section_persistence(db_session):
    """Test creating a document and linked sections."""
    doc = Document(
        id=str(uuid.uuid4()),
        title="Test Doc",
        filename="test.pdf",
        storage_path="/data/test.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        file_hash="mock_hash_12345",
        status=DocumentStatus.PENDING.value
    )
    db_session.add(doc)
    db_session.commit()

    sec = DocumentSection(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        title="Section 1",
        section_level=1,
        page_number=1,
        order_index=0,
        content="Section content goes here."
    )
    db_session.add(sec)
    db_session.commit()

    # Query back
    saved_doc = db_session.query(Document).filter(Document.id == doc.id).first()
    assert saved_doc is not None
    assert len(saved_doc.sections) == 1
    assert saved_doc.sections[0].title == "Section 1"

def test_embedding_model_version_and_dimension_safety(db_session):
    """Ensure vector dimensionality is verified and prevents mixing incompatible vectors."""
    doc = Document(
        id=str(uuid.uuid4()),
        title="Vector Test Doc",
        filename="vec.pdf",
        storage_path="/data/vec.pdf",
        mime_type="application/pdf",
        file_size_bytes=512,
        file_hash="mock_hash_vec"
    )
    db_session.add(doc)
    db_session.commit()

    chunk = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        chunk_index=0,
        page_number=1,
        text="Sample chunk for embedding test"
    )

    # 1. Compatible vector setting (dim=4)
    valid_vec = [0.1, 0.2, 0.3, 0.4]
    chunk.set_embedding(valid_vec, model_name="bge-m3", expected_dim=4)
    assert chunk.embedding_dim == 4
    assert chunk.embedding_model == "bge-m3"
    assert chunk.embedding == valid_vec

    # 2. Incompatible vector setting (expected_dim=1024, got len 4) must fail
    with pytest.raises(ValueError) as exc:
        chunk.set_embedding(valid_vec, model_name="bge-m3", expected_dim=1024)
    assert "Incompatible embedding vector dimension" in str(exc.value)

def test_cascade_deletion(db_session):
    """Deleting a document must cascade and delete its sections, chunks, citations, and jobs."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        title="Cascade Test Doc",
        filename="cascade.pdf",
        storage_path="/data/cascade.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        file_hash="mock_cascade_hash"
    )
    db_session.add(doc)

    sec_id = str(uuid.uuid4())
    sec = DocumentSection(
        id=sec_id,
        document_id=doc_id,
        title="Cascade Section",
        content="Section text"
    )
    db_session.add(sec)

    chunk_id = str(uuid.uuid4())
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        section_id=sec_id,
        chunk_index=0,
        page_number=1,
        text="Chunk text"
    )
    db_session.add(chunk)

    job_id = str(uuid.uuid4())
    job = ProcessingJob(
        id=job_id,
        document_id=doc_id,
        status=JobStatus.COMPLETED.value
    )
    db_session.add(job)

    # Conversation, Message, and Citation
    conv_id = str(uuid.uuid4())
    conv = Conversation(id=conv_id, title="Test Conv")
    db_session.add(conv)

    msg_id = str(uuid.uuid4())
    msg = Message(id=msg_id, conversation_id=conv_id, role="assistant", content="Answer with citation")
    db_session.add(msg)

    cit_id = str(uuid.uuid4())
    cit = Citation(
        id=cit_id,
        message_id=msg_id,
        chunk_id=chunk_id,
        page_number=1,
        exact_quote="Chunk text"
    )
    db_session.add(cit)
    db_session.commit()

    # Confirm all exist
    assert db_session.query(DocumentSection).filter(DocumentSection.id == sec_id).first() is not None
    assert db_session.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first() is not None
    assert db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first() is not None
    assert db_session.query(Citation).filter(Citation.id == cit_id).first() is not None

    # Delete the document
    db_session.delete(doc)
    db_session.commit()

    # Verify all linked entities were removed
    assert db_session.query(Document).filter(Document.id == doc_id).first() is None
    assert db_session.query(DocumentSection).filter(DocumentSection.id == sec_id).first() is None
    assert db_session.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first() is None
    assert db_session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first() is None
    assert db_session.query(Citation).filter(Citation.id == cit_id).first() is None

def test_evaluation_record_persistence(db_session):
    """Test creating and querying an evaluation record."""
    rec = EvaluationRecord(
        id=str(uuid.uuid4()),
        case_id="case_01",
        category="direct_factual",
        question="What is the SLA uptime?",
        expected_answer="99.95%",
        actual_answer="99.95% monthly uptime",
        is_correct=True,
        grounding_score=1.0,
        latency_seconds=1.23
    )
    db_session.add(rec)
    db_session.commit()

    saved = db_session.query(EvaluationRecord).filter(EvaluationRecord.case_id == "case_01").first()
    assert saved is not None
    assert saved.is_correct is True
