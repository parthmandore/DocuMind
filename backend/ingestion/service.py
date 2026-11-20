"""Document Ingestion Service

Coordinates validation, duplicate detection, storage, and database persistence.
Enforces that document deletion removes all associated chunks, sections,
citations, processing jobs, and the physical file.
"""

import os
import uuid
from typing import Tuple, Optional, List
from sqlalchemy.orm import Session

from backend.db.models import Document, ProcessingJob, DocumentStatus, JobStatus
from backend.ingestion.validator import validate_file_upload, compute_file_hash
from backend.ingestion.storage import save_uploaded_file, delete_stored_file

class IngestionService:
    @staticmethod
    def ingest_file(
        db: Session,
        filename: str,
        content: bytes,
        mime_type: Optional[str] = None
    ) -> Tuple[Document, ProcessingJob, bool]:
        """
        Validates, stores, and registers a document file.
        Returns:
            (Document, ProcessingJob, is_duplicate)
        """
        file_size = len(content)
        safe_name = validate_file_upload(filename, file_size, content)
        file_hash = compute_file_hash(content)

        # Duplicate detection: check if a document with identical hash already exists
        existing_doc = (
            db.query(Document)
            .filter(Document.file_hash == file_hash)
            .first()
        )
        if existing_doc and existing_doc.status == DocumentStatus.COMPLETED.value:
            # Found existing completed document
            # Find its last job or create a reference
            last_job = (
                db.query(ProcessingJob)
                .filter(ProcessingJob.document_id == existing_doc.id)
                .order_by(ProcessingJob.created_at.desc())
                .first()
            )
            return existing_doc, last_job, True

        doc_id = str(uuid.uuid4())
        ext = os.path.splitext(safe_name)[1].lower()
        derived_mime = mime_type or {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".markdown": "text/markdown"
        }.get(ext, "application/octet-stream")

        storage_path = save_uploaded_file(doc_id, safe_name, content)

        # Title defaults to base filename without extension
        title = os.path.splitext(safe_name)[0].replace("_", " ").title()

        doc = Document(
            id=doc_id,
            title=title,
            filename=safe_name,
            storage_path=storage_path,
            mime_type=derived_mime,
            file_size_bytes=file_size,
            file_hash=file_hash,
            status=DocumentStatus.PENDING.value,
            quality_warnings=[]
        )
        db.add(doc)

        job = ProcessingJob(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            job_type="document_ingestion",
            status=JobStatus.PENDING.value
        )
        db.add(job)
        db.commit()
        db.refresh(doc)
        db.refresh(job)

        return doc, job, False

    @staticmethod
    def delete_document(db: Session, doc_id: str) -> bool:
        """
        Deletes a document by ID.
        Cascade foreign keys ensure associated sections, chunks, citations,
        and processing jobs are removed from the database.
        The physical file is also removed from storage.
        """
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return False

        storage_path = doc.storage_path
        db.delete(doc)
        db.commit()

        # Remove physical file from disk
        if storage_path:
            delete_stored_file(storage_path)

        return True
