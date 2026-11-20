"""Controlled Local File Storage Service

Stores uploaded files within the designated local upload directory using internal IDs.
Provides safe deletion when documents are removed.
"""

import os
from pathlib import Path
from backend.config import config

def save_uploaded_file(doc_id: str, safe_filename: str, content: bytes) -> str:
    """
    Saves document bytes locally under data/uploads/{doc_id}_{safe_filename}.
    Returns the absolute path to the stored file.
    """
    os.makedirs(config.upload_dir, exist_ok=True)
    target_filename = f"{doc_id}_{safe_filename}"
    target_path = Path(config.upload_dir) / target_filename

    with open(target_path, "wb") as f:
        f.write(content)

    return str(target_path.resolve())

def delete_stored_file(storage_path: str) -> bool:
    """
    Safely deletes a stored document file from disk.
    Returns True if file was deleted, False if file did not exist.
    """
    if not storage_path:
        return False

    try:
        path = Path(storage_path)
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception:
        pass
    return False
