"""Tests for File Upload Validation and Sanitization"""

import pytest
from backend.ingestion.validator import (
    sanitize_filename,
    validate_file_upload,
    compute_file_hash
)

def test_sanitize_filename_traversal():
    """Ensure directory traversal patterns and slashes are removed."""
    raw = "../../../etc/passwd.txt"
    cleaned = sanitize_filename(raw)
    assert ".." not in cleaned
    assert "/" not in cleaned
    assert "\\" not in cleaned
    assert cleaned.endswith(".txt")

def test_sanitize_filename_illegal_characters():
    """Ensure illegal Windows characters (< > : \" / \\ | ? *) are sanitized."""
    raw = 'report<v1>:final|draft?.pdf'
    cleaned = sanitize_filename(raw)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert ":" not in cleaned
    assert "|" not in cleaned
    assert "?" not in cleaned
    assert cleaned.endswith(".pdf")

def test_validate_file_upload_supported_formats():
    """Supported formats (.pdf, .docx, .txt, .md) must pass validation."""
    for fname in ["doc.pdf", "report.docx", "notes.txt", "README.md", "spec.markdown"]:
        # Mock valid PDF bytes
        content = b"%PDF-1.4 sample content" if fname.endswith(".pdf") else b"PK\x03\x04 sample" if fname.endswith(".docx") else b"Sample text"
        clean = validate_file_upload(fname, len(content), content)
        assert clean.endswith(fname.split(".")[-1].lower())

def test_validate_file_upload_unsupported_formats():
    """Unsupported formats (.exe, .zip, .png, etc.) must be explicitly rejected."""
    for fname in ["malware.exe", "archive.zip", "photo.png", "script.sh"]:
        with pytest.raises(ValueError) as exc:
            validate_file_upload(fname, 100, b"some content")
        assert "Unsupported file format" in str(exc.value)

def test_validate_file_upload_zero_bytes():
    """Zero-byte files must be rejected."""
    with pytest.raises(ValueError) as exc:
        validate_file_upload("empty.txt", 0, b"")
    assert "File is empty" in str(exc.value)

def test_validate_file_upload_oversized():
    """Files exceeding size limit must be rejected."""
    oversized = 60 * 1024 * 1024  # 60 MB
    with pytest.raises(ValueError) as exc:
        validate_file_upload("large.txt", oversized, b"")
    assert "exceeds maximum permitted limit" in str(exc.value)

def test_validate_file_upload_mislabeled_magic_signature():
    """A .pdf file that does not start with %PDF must be rejected as corrupted/mislabeled."""
    corrupt_content = b"THIS IS NOT A PDF HEADER"
    with pytest.raises(ValueError) as exc:
        validate_file_upload("fake.pdf", len(corrupt_content), corrupt_content)
    assert "does not match the '.pdf' signature" in str(exc.value)

def test_compute_file_hash():
    """SHA-256 hash must be deterministic and correct."""
    data = b"DocuMind local document intelligence"
    h1 = compute_file_hash(data)
    h2 = compute_file_hash(data)
    assert h1 == h2
    assert len(h1) == 64
