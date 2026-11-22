"""Ingest Evaluation Dataset Documents and Chunks into Database

Populates data/documind.db with the genuine ground-truth documents and chunks
from data/evaluation_dataset.json, computing and persisting real 768-dim nomic-embed-text
vectors for all chunks.
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
    DocumentStatus,
    JobStatus,
    ProcessingJob
)
from backend.config import config
from backend.ollama_runtime.client import ollama_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_eval")

def parse_page_number(loc_str: str) -> int:
    """Extracts integer page number from expected_source_location string."""
    m = re.search(r"Page\s+(\d+)", loc_str, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 1

def ingest_evaluation_corpus(dataset_path: str = "data/evaluation_dataset.json"):
    init_db()
    db: Session = SessionLocal()

    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        cases = dataset.get("cases", [])
        logger.info("Loaded %d cases from %s", len(cases), dataset_path)

        # Group cases by document_id
        docs_map: Dict[str, Dict[str, Any]] = {}
        for c in cases:
            doc_id = c["document_id"]
            if doc_id not in docs_map:
                docs_map[doc_id] = {
                    "document_id": doc_id,
                    "document_title": c["document_title"],
                    "passages": []
                }
            docs_map[doc_id]["passages"].append(c)

        for doc_id, doc_info in docs_map.items():
            logger.info("Processing document: %s (%s)", doc_id, doc_info["document_title"])

            # 1. Upsert Document record
            doc_record = db.query(Document).filter(Document.id == doc_id).first()
            if not doc_record:
                doc_record = Document(
                    id=doc_id,
                    title=doc_info["document_title"],
                    filename=f"{doc_id.lower()}.pdf",
                    storage_path=f"data/uploads/{doc_id.lower()}.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=65536,
                    file_hash=f"eval_hash_{doc_id.lower()}",
                    status=DocumentStatus.PROCESSING.value,
                    total_pages=50,
                    total_words=0,
                    total_sections=0,
                    total_chunks=0,
                    doc_metadata={"benchmark_document": True}
                )
                db.add(doc_record)
                db.commit()
                db.refresh(doc_record)

            # 2. Extract unique passages to create distinct chunks
            unique_passages: Dict[str, Dict[str, Any]] = {}
            for p in doc_info["passages"]:
                text = p["relevant_source_passage"].strip()
                if text and text not in unique_passages:
                    unique_passages[text] = p

            # 3. Create or update chunks
            chunks_to_embed: List[DocumentChunk] = []
            chunk_texts: List[str] = []

            for idx, (passage_text, meta) in enumerate(unique_passages.items()):
                chunk_id = f"eval_{doc_id}_{idx:03d}"
                existing_chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
                page = parse_page_number(meta.get("expected_source_location", "Page 1"))

                if not existing_chunk:
                    chunk = DocumentChunk(
                        id=chunk_id,
                        document_id=doc_id,
                        chunk_index=idx,
                        page_number=page,
                        text=passage_text,
                        token_count=len(passage_text.split()),
                        bboxes=[{"page": page, "x0": 50, "y0": 100, "x1": 550, "y1": 200}],
                        chunk_metadata={
                            "case_ids": [p["case_id"] for p in doc_info["passages"] if p["relevant_source_passage"].strip() == passage_text],
                            "expected_source_location": meta.get("expected_source_location")
                        }
                    )
                    db.add(chunk)
                    db.commit()
                    db.refresh(chunk)
                    existing_chunk = chunk

                # Check if embedding needed
                if not existing_chunk.embedding or existing_chunk.embedding_model != config.embedding_model:
                    chunks_to_embed.append(existing_chunk)
                    chunk_texts.append(passage_text)

            # 4. Generate embeddings in batches via OllamaHardwareArbiter
            if chunks_to_embed:
                logger.info("Generating embeddings for %d chunks in %s...", len(chunks_to_embed), doc_id)
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
                logger.info("Finished embedding chunks for %s.", doc_id)

            # Update Document stats
            all_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
            doc_record.total_chunks = len(all_chunks)
            doc_record.total_words = sum(c.token_count for c in all_chunks)
            doc_record.status = DocumentStatus.COMPLETED.value
            doc_record.doc_metadata = {
                "benchmark_document": True,
                "embedding_model": config.embedding_model,
                "embedding_dimension": config.embedding_dimension
            }
            db.commit()

        logger.info("All evaluation corpus documents and chunks successfully ingested and embedded!")

    finally:
        db.close()

if __name__ == "__main__":
    ingest_evaluation_corpus()
