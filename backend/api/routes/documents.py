"""Document API Routes

Endpoints for document upload, content retrieval, status inspection,
and cascade deletion.
"""

import os
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import Document, DocumentSection, DocumentChunk, ProcessingJob, JobStatus
from backend.config import config
from backend.ingestion.service import IngestionService
from backend.jobs.worker import run_document_processing_job
from backend.api.schemas import (
    DocumentResponse,
    DocumentUploadResponse,
    DocumentContentResponse,
    SectionSchema,
    ChunkSchema,
    IndexingStatusResponse,
    ReindexResponse
)

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a document (PDF, DOCX, TXT, MD).
    Validates file format and size, detects duplicates, creates records,
    and enqueues background processing.
    """
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {e}"
        )

    try:
        doc, job, is_duplicate = IngestionService.ingest_file(
            db=db,
            filename=file.filename or "uploaded_file",
            content=content,
            mime_type=file.content_type
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )

    if not is_duplicate:
        # Enqueue background processing job
        background_tasks.add_task(run_document_processing_job, doc.id, job.id)
        msg = "File uploaded and scheduled for extraction."
    else:
        msg = "Duplicate document detected: matching SHA-256 hash already exists."

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(doc),
        job_id=job.id if job else "",
        is_duplicate=is_duplicate,
        message=msg
    )

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all registered documents ordered by creation time."""
    docs = (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [DocumentResponse.model_validate(d) for d in docs]

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Retrieve document metadata, status, and quality warnings."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )
    return DocumentResponse.model_validate(doc)

@router.get("/{doc_id}/file")
def get_document_file(doc_id: str, db: Session = Depends(get_db)):
    """
    Serves the original document binary file for PDF.js preview or download.
    Validates document existence in SQLite and enforces path containment
    within the configured upload directory to prevent path traversal attacks.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )

    # Resolve and validate storage path against allowed upload directory
    uploads_dir = os.path.realpath(str(config.upload_dir))
    file_path = os.path.realpath(str(doc.storage_path))

    # Path traversal guard: ensure file_path is strictly within uploads_dir
    try:
        common = os.path.commonpath([uploads_dir, file_path])
        if common != uploads_dir:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path configuration."
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File path verification failed."
        )

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document binary file does not exist on disk."
        )

    return FileResponse(
        path=file_path,
        media_type=doc.mime_type or "application/octet-stream",
        filename=doc.filename,
        content_disposition_type="inline"
    )

@router.get("/{doc_id}/content", response_model=DocumentContentResponse)
def get_document_content(doc_id: str, db: Session = Depends(get_db)):
    """Retrieve extracted sections and chunks with source metadata and bounding boxes."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )

    sections = (
        db.query(DocumentSection)
        .filter(DocumentSection.document_id == doc_id)
        .order_by(DocumentSection.order_index.asc())
        .all()
    )

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    sec_schemas = [
        SectionSchema(
            id=s.id,
            title=s.title,
            section_level=s.section_level,
            page_number=s.page_number,
            order_index=s.order_index,
            content=s.content,
            metadata=s.section_metadata or {}
        )
        for s in sections
    ]

    chunk_schemas = [
        ChunkSchema(
            id=c.id,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            text=c.text,
            token_count=c.token_count,
            bboxes=c.bboxes or []
        )
        for c in chunks
    ]

    return DocumentContentResponse(
        document_id=doc.id,
        title=doc.title,
        total_pages=doc.total_pages,
        total_words=doc.total_words,
        quality_warnings=doc.quality_warnings or [],
        sections=sec_schemas,
        chunks=chunk_schemas
    )

@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """
    Deletes a document by ID.
    Cascade foreign keys remove all associated sections, chunks, citations,
    and processing jobs from the database. The physical file is also deleted.
    """
    deleted = IngestionService.delete_document(db, doc_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )
    return {"message": f"Document '{doc_id}' and all associated data successfully deleted."}

@router.get("/{doc_id}/indexing-status", response_model=IndexingStatusResponse)
def get_indexing_status(doc_id: str, db: Session = Depends(get_db)):
    """Inspect embedding and vector indexing status for a document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )

    total_c = (
        db.query(func.count(DocumentChunk.id))
        .filter(DocumentChunk.document_id == doc_id)
        .scalar()
        or 0
    )
    embedded_chunks = (
        db.query(func.count(DocumentChunk.id))
        .filter(
            DocumentChunk.document_id == doc_id,
            DocumentChunk.embedding.isnot(None),
            DocumentChunk.embedding_model == config.embedding_model,
        )
        .scalar()
        or 0
    )

    doc_meta = doc.doc_metadata or {}
    indexed_at = doc_meta.get("indexed_at")
    model_name = doc_meta.get("embedding_model") or config.embedding_model
    dim = doc_meta.get("embedding_dimension") or config.embedding_dimension

    is_indexed = (total_c > 0) and (embedded_chunks == total_c)
    percent = round((embedded_chunks / max(1, total_c)) * 100, 1) if total_c > 0 else 0.0
    lexical_ready = bool(doc_meta.get("lexical_ready") or total_c > 0)

    return IndexingStatusResponse(
        document_id=doc.id,
        status=doc.status,
        total_chunks=total_c,
        embedded_chunks=embedded_chunks,
        embedding_model=model_name if embedded_chunks > 0 else None,
        embedding_dimension=dim if embedded_chunks > 0 else None,
        indexed_at=indexed_at,
        is_indexed=is_indexed,
        percent_complete=percent,
        is_lexical_ready=lexical_ready
    )

@router.post("/{doc_id}/reindex", response_model=ReindexResponse, status_code=status.HTTP_202_ACCEPTED)
def reindex_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger a re-indexing job for an existing document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )

    # Prevent concurrent duplicate jobs for the same document
    running_job = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.document_id == doc.id,
            ProcessingJob.status.in_([JobStatus.RUNNING.value, JobStatus.PENDING.value])
        )
        .first()
    )
    if running_job:
        return ReindexResponse(
            document_id=doc.id,
            job_id=running_job.id,
            status=running_job.status,
            message=f"A processing job ({running_job.id}) is already active for document '{doc.id}'."
        )

    job = ProcessingJob(
        document_id=doc.id,
        job_type="reindex",
        status=JobStatus.PENDING.value
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_document_processing_job, doc.id, job.id)

    return ReindexResponse(
        document_id=doc.id,
        job_id=job.id,
        status=job.status,
        message=f"Re-indexing scheduled for document '{doc.id}'."
    )

