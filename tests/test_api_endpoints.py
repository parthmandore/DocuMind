"""Integration Tests for FastAPI Endpoints"""

import os
import pytest
from unittest.mock import patch
from backend.jobs.worker import process_job_sync

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
PDF_DIR = os.path.join(FIXTURES_DIR, "pdfs")

def test_health_endpoint(client):
    """GET /api/health returns system and database status."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app_name"] == "DocuMind"
    assert "status" in data
    assert "database" in data

def test_upload_and_retrieve_document_lifecycle(client, db_session):
    """
    End-to-end lifecycle:
    1. Upload PDF
    2. Process extraction
    3. Retrieve content with source metadata
    4. Delete document
    5. Verify 404 on subsequent lookups
    """
    pdf_path = os.path.join(PDF_DIR, "single_column_report.pdf")
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    # 1. Upload
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("report.pdf", file_bytes, "application/pdf")}
    )
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()
    assert not upload_data["is_duplicate"]
    doc_id = upload_data["document"]["id"]
    job_id = upload_data["job_id"]
    assert doc_id is not None

    # 2. Process extraction synchronously using the active test DB session
    success = process_job_sync(doc_id, job_id, db=db_session, skip_embedding=True)
    assert success is True

    # 3. Retrieve document metadata
    get_resp = client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 200
    doc_data = get_resp.json()
    assert doc_data["status"] == "COMPLETED"
    assert doc_data["total_pages"] >= 1
    assert doc_data["total_chunks"] > 0

    # 4. Retrieve extracted content with source metadata & bounding boxes
    content_resp = client.get(f"/api/documents/{doc_id}/content")
    assert content_resp.status_code == 200
    content_data = content_resp.json()
    assert content_data["document_id"] == doc_id
    assert len(content_data["chunks"]) > 0
    # Verify chunks have bounding boxes and page numbers
    first_chunk = content_data["chunks"][0]
    assert first_chunk["page_number"] >= 1
    assert len(first_chunk["bboxes"]) > 0

    # 5. List documents
    list_resp = client.get("/api/documents")
    assert list_resp.status_code == 200
    assert any(d["id"] == doc_id for d in list_resp.json())

    # 6. Delete document
    del_resp = client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200

    # 7. Confirm 404
    get_after_del = client.get(f"/api/documents/{doc_id}")
    assert get_after_del.status_code == 404

def test_upload_duplicate_detection(client, db_session):
    """Uploading the exact same file twice returns duplicate notification."""
    txt_path = os.path.join(FIXTURES_DIR, "sample.txt")
    with open(txt_path, "rb") as f:
        file_bytes = f.read()

    # First upload
    res1 = client.post(
        "/api/documents/upload",
        files={"file": ("sample1.txt", file_bytes, "text/plain")}
    )
    assert res1.status_code == 201
    doc_id = res1.json()["document"]["id"]
    job_id = res1.json()["job_id"]
    
    # Process first upload to COMPLETED
    process_job_sync(doc_id, job_id, db=db_session, skip_embedding=True)

    # Second upload with identical bytes
    res2 = client.post(
        "/api/documents/upload",
        files={"file": ("sample2.txt", file_bytes, "text/plain")}
    )
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["is_duplicate"] is True
    assert data2["document"]["id"] == doc_id

def test_upload_unsupported_format(client):
    """Uploading an unsupported format must return 400 Bad Request."""
    res = client.post(
        "/api/documents/upload",
        files={"file": ("payload.exe", b"MZ binaries are not allowed", "application/octet-stream")}
    )
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]

def test_analytics_insights_endpoint(client, db_session):
    """GET /api/analytics/insights returns corpus metrics and grounding distributions."""
    resp = client.get("/api/analytics/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert "overview" in data
    assert "quality" in data
    assert "claim_distribution" in data
    assert "top_cited_documents" in data
    assert "contradiction_logs" in data
    assert "daily_activity" in data
    assert isinstance(data["overview"]["total_documents"], int)
    assert isinstance(data["overview"]["total_chunks"], int)
    assert isinstance(data["claim_distribution"], list)

def test_conversation_rename_and_search(client, db_session):
    """PATCH /api/conversations/{id} renames thread and GET /api/conversations?search= filters by title."""
    # Create thread
    c_res = client.post("/api/conversations", json={"title": "Original Title"})
    assert c_res.status_code == 201
    c_id = c_res.json()["id"]

    # Rename thread
    patch_res = client.patch(f"/api/conversations/{c_id}", json={"title": "Updated Audit Title"})
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Audit Title"

    # Search with matching substring
    s_res = client.get("/api/conversations?search=Audit")
    assert s_res.status_code == 200
    assert any(c["id"] == c_id for c in s_res.json())

    # Search with non-matching substring
    s_none = client.get("/api/conversations?search=NonExistentKeywordXYZ")
    assert s_none.status_code == 200
    assert not any(c["id"] == c_id for c in s_none.json())

    # Clean up
    del_res = client.delete(f"/api/conversations/{c_id}")
    assert del_res.status_code == 200
