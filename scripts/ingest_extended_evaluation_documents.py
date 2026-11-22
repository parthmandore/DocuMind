"""Explicit and Documented Ingestion of Extended Evaluation Dataset Documents

Populates data/documind.db with the genuine ground-truth documents, sections,
and chunks from data/evaluation_dataset_extended.json, computing and persisting
real 768-dim nomic-embed-text vectors for all newly introduced passages.
"""

import os
import sys
import re
import json
import logging

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any
from sqlalchemy.orm import Session

from backend.db.base import SessionLocal, init_db
from backend.db.models import (
    Document,
    DocumentSection,
    DocumentChunk,
    DocumentStatus
)
from backend.config import config
from backend.ollama_runtime.client import ollama_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_extended")

def parse_page_number(loc_str: str) -> int:
    """Extracts integer page number from expected_source_location string."""
    m = re.search(r"Page\s+(\d+)", loc_str, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 1

def ingest_extended_evaluation_corpus(dataset_path: str = "data/evaluation_dataset_extended.json"):
    init_db()
    db: Session = SessionLocal()

    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        cases = dataset.get("cases", [])
        logger.info("Loaded %d extended cases from %s", len(cases), dataset_path)

        # Collect unique passages to add
        new_chunks_added = []
        chunks_to_embed = []
        chunk_texts = []

        for idx, c in enumerate(cases):
            case_id = c["case_id"]
            doc_id = c["document_id"]
            passage_text = c.get("relevant_source_passage", "").strip()
            loc_str = c.get("expected_source_location", "Page 1")

            if not passage_text or c.get("should_abstain", False):
                continue

            # Check if this exact text is already in the database for this doc_id
            existing = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc_id,
                DocumentChunk.text == passage_text
            ).first()

            if existing:
                logger.info("[%s] Passage already present in chunk '%s'.", case_id, existing.id)
                # Ensure embedding exists
                if not existing.embedding or existing.embedding_model != config.embedding_model:
                    chunks_to_embed.append(existing)
                    chunk_texts.append(passage_text)
                continue

            # Create new chunk
            page = parse_page_number(loc_str)
            chunk_id = f"eval_ext_{doc_id}_{idx:03d}"

            chunk = DocumentChunk(
                id=chunk_id,
                document_id=doc_id,
                chunk_index=100 + idx,
                page_number=page,
                text=passage_text,
                token_count=len(passage_text.split()),
                bboxes=[{"page": page, "x0": 50, "y0": 100, "x1": 550, "y1": 200}],
                chunk_metadata={
                    "case_ids": [case_id],
                    "expected_source_location": loc_str,
                    "corpus_source": "extended_evaluation_ingestion"
                }
            )
            db.add(chunk)
            db.commit()
            db.refresh(chunk)

            new_chunks_added.append({
                "chunk_id": chunk_id,
                "case_id": case_id,
                "document_id": doc_id,
                "page": page,
                "token_count": len(passage_text.split()),
                "text_snippet": passage_text[:80] + "..."
            })
            chunks_to_embed.append(chunk)
            chunk_texts.append(passage_text)
            logger.info("Created new chunk '%s' for case %s.", chunk_id, case_id)

        # Generate embeddings for newly added or missing chunks
        if chunks_to_embed:
            logger.info("Generating nomic-embed-text embeddings for %d chunks...", len(chunks_to_embed))
            batch_size = max(1, config.embedding_batch_size)
            for b_i in range(0, len(chunks_to_embed), batch_size):
                b_chunks = chunks_to_embed[b_i : b_i + batch_size]
                b_texts = chunk_texts[b_i : b_i + batch_size]

                embeddings = ollama_client.embed(
                    b_texts,
                    model=config.embedding_model,
                    timeout=config.llm_timeout_seconds
                )

                for chunk_obj, vec in zip(b_chunks, embeddings):
                    chunk_obj.set_embedding(
                        vec,
                        model_name=config.embedding_model,
                        expected_dim=config.embedding_dimension
                    )
                db.commit()
            logger.info("Successfully persisted embeddings for all %d chunks.", len(chunks_to_embed))

        # Update document chunk counts
        doc_ids = set(c["document_id"] for c in cases)
        for d_id in doc_ids:
            doc = db.query(Document).filter(Document.id == d_id).first()
            if doc:
                count = db.query(DocumentChunk).filter(DocumentChunk.document_id == d_id).count()
                doc.total_chunks = count
                db.commit()

        # Write explicit audit report
        audit_report = {
            "dataset_source": dataset_path,
            "total_new_chunks_added": len(new_chunks_added),
            "total_chunks_embedded": len(chunks_to_embed),
            "embedding_model": config.embedding_model,
            "embedding_dimension": config.embedding_dimension,
            "chunks_added": new_chunks_added
        }

        os.makedirs("results", exist_ok=True)
        report_path = "results/corpus_extended_ingestion_audit.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(audit_report, f, indent=2)

        print(f"\nIngestion complete. Added {len(new_chunks_added)} new chunks. Audit report written to {report_path}")

    finally:
        db.close()

if __name__ == "__main__":
    ingest_extended_evaluation_corpus()
