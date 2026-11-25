"""Background Processing Worker

Manages the database-backed job queue for document extraction, layout chunking,
and dense vector embedding ingestion.
Coordinates with OllamaHardwareArbiter to guarantee single-operation mutual exclusion
while deduplicating identical chunk contents and caching valid embeddings by content hash.
"""

import asyncio
import hashlib
import logging
import threading
import time
import traceback
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import config
from backend.db.base import SessionLocal
from backend.db.models import (
    Document,
    DocumentSection,
    DocumentChunk,
    ProcessingJob,
    DocumentStatus,
    JobStatus
)
from backend.extraction.router import extract_document
from backend.chunking.layout_chunker import LayoutAwareChunker
from backend.ollama_runtime.client import ollama_client, prepare_embedding_text
from backend.ollama_runtime.arbiter import arbiter

logger = logging.getLogger("documind.worker")

_AUTO_RESUME_LOCK = threading.Lock()
_LAST_AUTO_RESUME_CHECK = 0.0
_AUTO_RESUME_COOLDOWN_SEC = 15.0


def _check_ollama_embedding_ready() -> Tuple[bool, str]:
    """
    Checks if local Ollama daemon is reachable and has the configured embedding model available.
    Uses a short connect timeout (0.5s) to avoid stalling on closed Windows loopback ports.
    """
    try:
        with httpx.Client(
            timeout=httpx.Timeout(2.0, connect=0.5),
            trust_env=False,
            verify=config.ollama_host.startswith("https://")
        ) as check_client:
            resp = check_client.get(f"{config.ollama_host}/api/tags")
            if resp.status_code != 200:
                return (
                    False,
                    f"Local embedding provider (Ollama) returned HTTP {resp.status_code}. Document is searchable in lexical mode."
                )
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            target_base = config.embedding_model.split(":")[0]
            has_model = any(
                m == config.embedding_model or m.split(":")[0] == target_base
                for m in models
            )
            if not has_model:
                return (
                    False,
                    f"Embedding model '{config.embedding_model}' is not installed in Ollama. Run 'ollama pull {config.embedding_model}'. Document is searchable in lexical mode."
                )
            return True, ""
    except Exception:
        return (
            False,
            "Semantic indexing is waiting for local embedding provider (Ollama unreachable). Document is searchable in lexical mode."
        )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_content_hash(text: str) -> str:
    """Computes a deterministic SHA-256 hash of normalized embedding input text."""
    normalized = prepare_embedding_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _lookup_cached_embeddings_by_hash(
    db: Session,
    needed_hashes: List[str],
    model_name: str,
    expected_dim: int
) -> Dict[str, List[float]]:
    """
    Safely queries persisted DocumentChunk embeddings matching exact content hashes,
    model version, and vector dimensionality to avoid redundant Ollama inference.
    """
    cached: Dict[str, List[float]] = {}
    if not needed_hashes:
        return cached
    try:
        rows = (
            db.query(DocumentChunk.chunk_metadata, DocumentChunk.embedding)
            .filter(
                DocumentChunk.embedding.isnot(None),
                DocumentChunk.embedding_model == model_name,
                DocumentChunk.embedding_dim == expected_dim,
                func.json_extract(DocumentChunk.chunk_metadata, "$.content_hash").in_(needed_hashes)
            )
            .all()
        )
        for meta, emb in rows:
            if not emb or len(emb) != expected_dim or not isinstance(meta, dict):
                continue
            h = meta.get("content_hash")
            if h and h not in cached:
                cached[h] = emb
    except Exception:
        # Gracefully fall back if database backend does not support json_extract
        return {}
    return cached


def process_job_sync(
    doc_id: str,
    job_id: str,
    db: Optional[Session] = None,
    skip_embedding: bool = False,
    stage_a_only: bool = False
) -> bool:
    """
    Synchronous execution of document extraction, cleaning, sectioning,
    chunking, and embedding generation.
    Supports idempotent resumption, content-hash vector reuse, and safe batch persistence.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        doc = db.query(Document).filter(Document.id == doc_id).first()

        if not job or not doc:
            return False

        # Preserve prior status before transitioning to PROCESSING
        prior_doc_status = doc.status

        # Mark as RUNNING
        job.status = JobStatus.RUNNING.value
        job.started_at = utc_now()
        job.attempts += 1
        doc.status = DocumentStatus.PROCESSING.value
        doc.error_message = None
        db.commit()

        # Step 1: Check if chunks already exist (e.g. resumption or reindexing)
        existing_chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        # Full re-extraction on explicit reindex unless we are resuming/completing embeddings for CHUNKED/EMBEDDING docs
        if job.job_type == "reindex" and prior_doc_status not in (
            DocumentStatus.CHUNKED.value,
            DocumentStatus.EMBEDDING.value,
        ):
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
            db.query(DocumentSection).filter(DocumentSection.document_id == doc.id).delete()
            db.commit()
            existing_chunks = []

        if not existing_chunks:
            # Step 1-A: Execute extraction & chunking in a savepoint (nested transaction)
            try:
                with db.begin_nested():
                    # Clean any partial sections left by prior failed attempts
                    db.query(DocumentSection).filter(DocumentSection.document_id == doc.id).delete()

                    extracted_doc = extract_document(doc.storage_path)
                    extracted_doc.doc_id = doc.id

                    # Persist Document Sections with doc-scoped IDs to prevent unique constraint collisions
                    section_id_map = {}
                    for sec in extracted_doc.sections:
                        scoped_sec_id = f"{doc.id}_{sec.section_id}"
                        section_id_map[sec.section_id] = scoped_sec_id
                        db_sec = DocumentSection(
                            id=scoped_sec_id,
                            document_id=doc.id,
                            title=sec.title,
                            section_level=sec.section_level,
                            page_number=sec.page_number,
                            order_index=sec.order_index,
                            content=sec.content,
                            section_metadata=sec.metadata
                        )
                        db.add(db_sec)

                    # Run Layout-Aware Chunking
                    chunker = LayoutAwareChunker(
                        target_words_per_chunk=config.chunk_size_tokens,
                        overlap_words=config.chunk_overlap_tokens
                    )
                    chunks = chunker.chunk(extracted_doc)

                    # Persist Document Chunks with precomputed content hashes
                    for idx, c in enumerate(chunks):
                        primary_page = c.page_numbers[0] if c.page_numbers else 1
                        bbox_dicts = [b.model_dump() for b in c.bboxes] if c.bboxes else []
                        scoped_chunk_sec_id = section_id_map.get(c.section_id, c.section_id)
                        c_meta = dict(c.metadata or {})
                        c_meta["content_hash"] = compute_content_hash(c.text)

                        db_chunk = DocumentChunk(
                            id=c.chunk_id,
                            document_id=doc.id,
                            section_id=scoped_chunk_sec_id,
                            chunk_index=idx,
                            page_number=primary_page,
                            text=c.text,
                            token_count=c.token_count or len(c.text.split()),
                            bboxes=bbox_dicts,
                            chunk_metadata=c_meta
                        )
                        db.add(db_chunk)

                # Stage A committed successfully: document is structurally parsed,
                # sectioned, chunked, and immediately searchable via lexical/BM25 retrieval.
                doc.status = DocumentStatus.CHUNKED.value
                doc.total_pages = extracted_doc.total_pages
                doc.total_words = extracted_doc.word_count
                doc.total_sections = len(extracted_doc.sections)
                doc.total_chunks = len(chunks)
                doc.quality_warnings = extracted_doc.quality_warnings
                doc.error_message = None
                doc_meta = dict(doc.doc_metadata or {})
                doc_meta["lexical_ready"] = True
                doc_meta["stage"] = "lexical_ready"
                doc_meta["stage_a_completed_at"] = utc_now().isoformat()
                doc_meta["embedding_progress"] = {
                    "completed": 0,
                    "total": len(chunks),
                    "percent": 0.0
                }
                doc.doc_metadata = doc_meta
                db.commit()

                if stage_a_only:
                    return True

            except Exception as extraction_err:
                error_trace = traceback.format_exc()
                doc.status = DocumentStatus.FAILED.value
                doc.error_message = f"Extraction failed: {extraction_err}"
                job.status = JobStatus.FAILED.value
                job.error_details = error_trace
                job.completed_at = utc_now()
                db.commit()
                return False

        # Step 2: Dense Embedding Generation (unless explicitly skipped)
        if not skip_embedding:
            try:
                all_chunks = (
                    db.query(DocumentChunk)
                    .filter(DocumentChunk.document_id == doc.id)
                    .order_by(DocumentChunk.chunk_index.asc())
                    .all()
                )

                # Identify chunks needing embedding (missing or outdated model/dim)
                to_embed: List[DocumentChunk] = []
                hash_cache: Dict[str, List[float]] = {}

                for c in all_chunks:
                    meta = c.chunk_metadata if isinstance(c.chunk_metadata, dict) else {}
                    c_hash = meta.get("content_hash") or compute_content_hash(c.text)
                    if (
                        c.embedding
                        and c.embedding_model == config.embedding_model
                        and len(c.embedding) == config.embedding_dimension
                    ):
                        hash_cache[c_hash] = c.embedding
                    else:
                        to_embed.append(c)

                total_chunks_count = len(all_chunks)
                already_embedded_count = total_chunks_count - len(to_embed)

                if to_embed:
                    # Stage B: Transition to EMBEDDING with live incremental progress
                    doc.status = DocumentStatus.EMBEDDING.value
                    doc_meta = dict(doc.doc_metadata or {})
                    doc_meta["embedding_progress"] = {
                        "completed": already_embedded_count,
                        "total": total_chunks_count,
                        "percent": round((already_embedded_count / max(1, total_chunks_count)) * 100, 1)
                    }
                    doc.doc_metadata = doc_meta
                    db.commit()

                    # Pre-check local embedding provider availability without SSL cert overhead
                    embedding_online, embedding_reason = _check_ollama_embedding_ready()

                    if not embedding_online:
                        doc.status = DocumentStatus.CHUNKED.value
                        doc.error_message = embedding_reason
                        job.status = JobStatus.FAILED.value
                        job.error_details = f"{embedding_reason} Document is extracted, chunked, and searchable via BM25."
                        job.completed_at = utc_now()
                        db.commit()
                        return False

                    # Reuse valid embeddings from DB matching content_hash + model + dimension (skip on explicit reindex)
                    chunk_hashes: List[str] = []
                    for c in to_embed:
                        meta = c.chunk_metadata if isinstance(c.chunk_metadata, dict) else {}
                        chunk_hashes.append(meta.get("content_hash") or compute_content_hash(c.text))

                    if job.job_type != "reindex":
                        missing_from_local = list({h for h in chunk_hashes if h not in hash_cache})
                        if missing_from_local:
                            db_hits = _lookup_cached_embeddings_by_hash(
                                db=db,
                                needed_hashes=missing_from_local,
                                model_name=config.embedding_model,
                                expected_dim=config.embedding_dimension
                            )
                            hash_cache.update(db_hits)

                    completed_count = already_embedded_count
                    now_iso = utc_now().isoformat()

                    # Separate cache hits from unique texts actually requiring Ollama inference
                    unique_reps: List[tuple] = []  # (hash, representative_chunk)
                    hash_to_chunks: Dict[str, List[DocumentChunk]] = {}
                    cache_hit_applied = False

                    for c, h in zip(to_embed, chunk_hashes):
                        if h in hash_cache:
                            c.set_embedding(
                                hash_cache[h],
                                model_name=config.embedding_model,
                                expected_dim=config.embedding_dimension
                            )
                            meta = dict(c.chunk_metadata or {})
                            meta["content_hash"] = h
                            meta["indexed_at"] = now_iso
                            c.chunk_metadata = meta
                            completed_count += 1
                            cache_hit_applied = True
                        else:
                            if h not in hash_to_chunks:
                                hash_to_chunks[h] = []
                                unique_reps.append((h, c))
                            hash_to_chunks[h].append(c)

                    if cache_hit_applied:
                        doc_meta = dict(doc.doc_metadata or {})
                        doc_meta["embedding_progress"] = {
                            "completed": completed_count,
                            "total": total_chunks_count,
                            "percent": round((completed_count / max(1, total_chunks_count)) * 100, 1)
                        }
                        doc.doc_metadata = doc_meta
                        db.commit()

                    batch_size = max(1, config.embedding_batch_size)
                    for i in range(0, len(unique_reps), batch_size):
                        batch_pairs = unique_reps[i : i + batch_size]
                        batch_texts = [pair[1].text for pair in batch_pairs]

                        # Generates embeddings in batched /api/embed calls under the hardware arbiter
                        embeddings = ollama_client.embed(
                            batch_texts,
                            model=config.embedding_model,
                            timeout=config.llm_timeout_seconds
                        )

                        batch_ts = utc_now().isoformat()
                        for (h, _), vec in zip(batch_pairs, embeddings):
                            target_chunks = hash_to_chunks.get(h, [])
                            for chunk_obj in target_chunks:
                                chunk_obj.set_embedding(
                                    vec,
                                    model_name=config.embedding_model,
                                    expected_dim=config.embedding_dimension
                                )
                                meta = dict(chunk_obj.chunk_metadata or {})
                                meta["content_hash"] = h
                                meta["indexed_at"] = batch_ts
                                chunk_obj.chunk_metadata = meta
                            completed_count += len(target_chunks)

                        doc_meta = dict(doc.doc_metadata or {})
                        doc_meta["embedding_progress"] = {
                            "completed": completed_count,
                            "total": total_chunks_count,
                            "percent": round((completed_count / max(1, total_chunks_count)) * 100, 1)
                        }
                        doc.doc_metadata = doc_meta
                        # Commit per batch to preserve progress and prevent RAM accumulation
                        db.commit()

            except Exception as embed_err:
                error_trace = traceback.format_exc()
                # Preserve lexical readiness when chunks already exist in DB
                doc.status = DocumentStatus.CHUNKED.value if total_chunks_count > 0 else DocumentStatus.FAILED.value
                doc.error_message = (
                    f"Semantic indexing paused ({embed_err}). Document is searchable in lexical mode."
                    if total_chunks_count > 0
                    else f"Embedding generation failed: {embed_err}"
                )
                job.status = JobStatus.FAILED.value
                job.error_details = error_trace
                job.completed_at = utc_now()
                db.commit()
                return False

        # Step 3: Mark as Indexed & Completed
        doc.status = DocumentStatus.COMPLETED.value
        doc_meta = dict(doc.doc_metadata or {})
        doc_meta["embedding_model"] = config.embedding_model
        doc_meta["embedding_dimension"] = config.embedding_dimension
        doc_meta["indexed_at"] = utc_now().isoformat()
        total_chunks_final = doc.total_chunks or len(doc.chunks)
        doc_meta["embedding_progress"] = {
            "completed": total_chunks_final,
            "total": total_chunks_final,
            "percent": 100.0
        }
        doc.doc_metadata = doc_meta
        doc.error_message = None

        job.status = JobStatus.COMPLETED.value
        job.completed_at = utc_now()
        job.error_details = None

        db.commit()
        return True

    except Exception as exc:
        logger.error(
            "Unhandled exception in document processing worker for doc_id=%s, job_id=%s: %s\n%s",
            doc_id,
            job_id,
            exc,
            traceback.format_exc()
        )
        db.rollback()
        try:
            fail_doc = db.query(Document).filter(Document.id == doc_id).first()
            fail_job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if fail_doc:
                fail_doc.status = DocumentStatus.FAILED.value
                fail_doc.error_message = f"Processing failed: {str(exc)[:300]}"
            if fail_job:
                fail_job.status = JobStatus.FAILED.value
                fail_job.error_details = traceback.format_exc()
                fail_job.completed_at = utc_now()
            db.commit()
        except Exception as persist_err:
            logger.error("Failed to persist failure status for job_id=%s: %s", job_id, persist_err)
            db.rollback()
        return False
    finally:
        if close_db:
            db.close()


def reconcile_orphaned_jobs(db: Optional[Session] = None) -> int:
    """
    Reconciles orphaned processing jobs and documents that were left in
    RUNNING, PROCESSING, or EMBEDDING status due to a process crash or restart.
    Marks them as FAILED so they do not remain permanently stuck.
    Returns the count of reconciled jobs and documents.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        orphaned_jobs = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.status.in_([JobStatus.RUNNING.value, JobStatus.PENDING.value]))
            .all()
        )
        orphaned_docs = (
            db.query(Document)
            .filter(Document.status.in_([DocumentStatus.PROCESSING.value, DocumentStatus.EMBEDDING.value]))
            .all()
        )

        reconciled_count = len(orphaned_jobs) + len(orphaned_docs)
        if reconciled_count > 0:
            now = utc_now()
            for job in orphaned_jobs:
                job.status = JobStatus.FAILED.value
                job.error_details = (
                    "Processing interrupted by backend restart. Document can be re-indexed or re-uploaded."
                )
                job.completed_at = now

            for doc in orphaned_docs:
                if doc.status == DocumentStatus.EMBEDDING.value and (doc.total_chunks or 0) > 0:
                    doc.status = DocumentStatus.CHUNKED.value
                    doc.error_message = (
                        "Semantic indexing interrupted by backend restart. Document is searchable in lexical mode."
                    )
                else:
                    doc.status = DocumentStatus.FAILED.value
                    doc.error_message = (
                        "Processing interrupted by backend restart. Document can be re-indexed or re-uploaded."
                    )

            db.commit()
            logger.warning(
                "Reconciled %d orphaned job(s) and %d orphaned document(s) on startup.",
                len(orphaned_jobs),
                len(orphaned_docs)
            )
        return reconciled_count
    except Exception as exc:
        logger.error("Failed to reconcile orphaned jobs on startup: %s", exc)
        db.rollback()
        return 0
    finally:
        if close_db:
            db.close()


async def run_document_processing_job(
    doc_id: str,
    job_id: str,
    db: Optional[Session] = None,
    skip_embedding: bool = False
) -> bool:
    """
    Asynchronously executes a document processing job in a background thread.
    Prevents blocking the FastAPI event loop.
    """
    return await asyncio.to_thread(process_job_sync, doc_id, job_id, db, skip_embedding)


def _resume_waiting_embeddings_worker() -> int:
    """Finds CHUNKED documents waiting for embeddings and processes them when Ollama is online."""
    embedding_ready, _ = _check_ollama_embedding_ready()
    if not embedding_ready:
        return 0

    db = SessionLocal()
    resumed = 0
    try:
        waiting_docs = (
            db.query(Document)
            .filter(
                Document.status == DocumentStatus.CHUNKED.value,
                Document.error_message.isnot(None),
                Document.total_chunks > 0,
            )
            .all()
        )
        for doc in waiting_docs:
            active_job = (
                db.query(ProcessingJob)
                .filter(
                    ProcessingJob.document_id == doc.id,
                    ProcessingJob.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
                )
                .first()
            )
            if active_job:
                continue

            import uuid as _uuid
            job = ProcessingJob(
                id=str(_uuid.uuid4()),
                document_id=doc.id,
                job_type="reindex",
                status=JobStatus.PENDING.value,
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            logger.info("Auto-resuming pending embeddings for CHUNKED document '%s' (job=%s)", doc.id, job.id)
            process_job_sync(doc.id, job.id, db=db)
            resumed += 1
        return resumed
    except Exception as exc:
        logger.warning("Failed during waiting embeddings auto-resume: %s", exc)
        db.rollback()
        return resumed
    finally:
        db.close()


def schedule_waiting_embeddings_resume(force: bool = False) -> bool:
    """
    Schedules non-blocking background resumption for CHUNKED documents waiting on Ollama.
    Rate-limited so repeated health checks never spawn overlapping sweeps.
    """
    global _LAST_AUTO_RESUME_CHECK
    now = time.monotonic()
    with _AUTO_RESUME_LOCK:
        if not force and (now - _LAST_AUTO_RESUME_CHECK) < _AUTO_RESUME_COOLDOWN_SEC:
            return False
        _LAST_AUTO_RESUME_CHECK = now

    t = threading.Thread(
        target=_resume_waiting_embeddings_worker,
        name="documind-auto-resume",
        daemon=True,
    )
    t.start()
    return True
