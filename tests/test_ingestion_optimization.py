"""Tests for Ingestion Optimizations and Robust Failure Handling.

Covers:
- PDF table detection quality preservation and drawing analysis skipping.
- Worker unhandled exception trapping and failure status persistence.
- Startup reconciliation of orphaned processing jobs and documents.
"""

import os
import uuid
from pathlib import Path
from unittest.mock import patch

from backend.db.models import Document, ProcessingJob, DocumentStatus, JobStatus
from backend.extraction.router import extract_document
from backend.extraction.pdf_parser import PyMuPDFParser, page_has_table_indicator
from backend.jobs.worker import process_job_sync, reconcile_orphaned_jobs

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
PDF_DIR = os.path.join(FIXTURES_DIR, "pdfs")


def test_pdf_table_detection_quality_preservation():
    """Verify that table detection correctly extracts real tables while avoiding false positives."""
    table_pdf = os.path.join(PDF_DIR, "table_dense_spec.pdf")
    doc_tables = extract_document(table_pdf)
    assert len(doc_tables.tables) == 1, "Expected exactly 1 table from table_dense_spec.pdf"
    tab = doc_tables.tables[0]
    assert "Model" in tab.headers
    assert len(tab.rows) == 4

    single_col_pdf = os.path.join(PDF_DIR, "single_column_report.pdf")
    doc_single = extract_document(single_col_pdf)
    assert len(doc_single.tables) == 0, "Expected 0 tables from single_column_report.pdf"

    multi_col_pdf = os.path.join(PDF_DIR, "multi_column_article.pdf")
    doc_multi = extract_document(multi_col_pdf)
    assert len(doc_multi.tables) == 0, "Expected 0 tables from multi_column_article.pdf"


def test_drawing_analysis_skip_on_sparse_drawings():
    """Verify drawing analysis skips when page has fewer than 2 vector drawings."""
    import pymupdf
    pdf_path = os.path.join(PDF_DIR, "single_column_report.pdf")
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    drawings = page.get_drawings()
    assert len(drawings) < 2
    # Table indicator should be False
    assert not page_has_table_indicator(page, drawings=drawings)
    doc.close()


def test_worker_unhandled_failure_records_failed_status(db_session):
    """Verify unhandled exceptions in process_job_sync record FAILED on document and job."""
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    doc = Document(
        id=doc_id,
        title="test_crash.pdf",
        filename="test_crash.pdf",
        mime_type="application/pdf",
        file_hash="dummy_hash_crash",
        file_size_bytes=1024,
        storage_path="non_existent_file_path.pdf",
        status=DocumentStatus.PENDING.value
    )
    job = ProcessingJob(
        id=job_id,
        document_id=doc_id,
        job_type="extraction_and_chunking",
        status=JobStatus.PENDING.value
    )
    db_session.add(doc)
    db_session.add(job)
    db_session.commit()

    success = process_job_sync(doc_id, job_id, db=db_session)
    assert not success, "Expected worker to return False on failure"

    db_session.refresh(doc)
    db_session.refresh(job)

    assert doc.status == DocumentStatus.FAILED.value
    assert doc.error_message is not None
    assert "failed" in doc.error_message.lower() or "no such file" in doc.error_message.lower()

    assert job.status == JobStatus.FAILED.value
    assert job.error_details is not None
    assert job.completed_at is not None


def test_startup_reconciliation_orphans(db_session):
    """Verify orphaned RUNNING/PROCESSING jobs left from a prior crash are marked FAILED."""
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    doc = Document(
        id=doc_id,
        title="orphaned.pdf",
        filename="orphaned.pdf",
        mime_type="application/pdf",
        file_hash="dummy_hash_orphan",
        file_size_bytes=2048,
        storage_path="dummy_orphan.pdf",
        status=DocumentStatus.PROCESSING.value
    )
    job = ProcessingJob(
        id=job_id,
        document_id=doc_id,
        job_type="extraction_and_chunking",
        status=JobStatus.RUNNING.value
    )
    db_session.add(doc)
    db_session.add(job)
    db_session.commit()

    reconciled = reconcile_orphaned_jobs(db=db_session)
    assert reconciled >= 2

    db_session.refresh(doc)
    db_session.refresh(job)

    assert doc.status == DocumentStatus.FAILED.value
    assert "interrupted by backend restart" in doc.error_message

    assert job.status == JobStatus.FAILED.value
    assert "interrupted by backend restart" in job.error_details
    assert job.completed_at is not None
