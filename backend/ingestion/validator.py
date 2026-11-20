"""File Upload Validation and Sanitization

Validates file extensions, MIME signatures, file sizes, and cleans filenames
to prevent directory traversal attacks.
"""

import os
import re
import hashlib
from typing import Optional
from backend.config import config

# Magic signatures for binary formats
FILE_SIGNATURES = {
    ".pdf": b"%PDF",
    ".docx": b"PK\x03\x04",
}

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes filename to prevent directory traversal and filesystem errors:
    - Removes path separators (/ and \\)
    - Replaces illegal Windows/Unix characters
    - Limits base filename length
    """
    if not filename:
        return "untitled_document"

    # Extract base name only
    clean = os.path.basename(filename)
    
    # Remove control characters and path traversal patterns
    clean = clean.replace("..", "").replace("/", "").replace("\\", "")
    
    # Replace illegal characters with underscore: < > : " / \ | ? *
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean)
    
    # Collapse multiple underscores/spaces
    clean = re.sub(r'[_ ]+', '_', clean).strip("._ ")
    
    if not clean:
        clean = "document"

    # Retain extension while shortening name if necessary
    name, ext = os.path.splitext(clean)
    if len(name) > 60:
        name = name[:60]

    return f"{name}{ext.lower()}"

def compute_file_hash(content: bytes) -> str:
    """Computes SHA-256 digest hex string for content-based duplicate detection."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()

def validate_file_upload(filename: str, file_size: int, content: Optional[bytes] = None) -> str:
    """
    Validates file against security policies:
    1. Rejects zero-byte files.
    2. Rejects files exceeding max size limit.
    3. Rejects unsupported file extensions explicitly.
    4. Verifies magic signature for binary files.
    
    Returns the sanitized safe filename.
    """
    if file_size <= 0:
        raise ValueError("File is empty (0 bytes). Upload a valid non-empty document.")

    if file_size > config.max_upload_size_bytes:
        max_mb = config.max_upload_size_bytes / (1024 * 1024)
        raise ValueError(f"File size exceeds maximum permitted limit of {max_mb:.0f} MB.")

    safe_name = sanitize_filename(filename)
    ext = os.path.splitext(safe_name)[1].lower()

    if ext not in config.allowed_extensions:
        allowed = ", ".join(sorted(config.allowed_extensions))
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: {allowed}"
        )

    # Magic byte verification if content is provided
    if content and ext in FILE_SIGNATURES:
        expected_sig = FILE_SIGNATURES[ext]
        if not content.startswith(expected_sig):
            raise ValueError(
                f"File content does not match the '{ext}' signature. Corrupted or mislabeled file."
            )

    return safe_name
