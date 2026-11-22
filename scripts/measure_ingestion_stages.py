import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

"""Measure separately:
1. Upload and validation.
2. Text extraction.
3. Structural section extraction.
4. Chunk creation.
5. Embedding generation.
6. SQLite writes.
7. Index completion.
Record actual timings.
"""
import time
import os
from pathlib import Path
from backend.ingestion.validator import validate_file_upload, compute_file_hash
from backend.extraction.router import extract_document
from backend.chunking.layout_chunker import LayoutAwareChunker
from backend.config import config
from backend.ollama_runtime.client import ollama_client
from backend.db.base import SessionLocal
from backend.db.models import Document, DocumentSection, DocumentChunk, ProcessingJob, DocumentStatus, JobStatus

pdf_path = Path("data/uploads/doc-hr-pol-2026.pdf")
if not pdf_path.exists():
    # pick first pdf
    for f in Path("data/uploads").glob("*.pdf"):
        if f.stat().st_size > 1000:
            pdf_path = f
            break

print(f"Target document for benchmark: {pdf_path.name} ({pdf_path.stat().st_size / 1024:.1f} KB)")

with open(pdf_path, "rb") as f:
    content = f.read()

# 1. Upload and validation
t0 = time.perf_counter()
safe_name = validate_file_upload(pdf_path.name, len(content), content)
file_hash = compute_file_hash(content)
t_val = time.perf_counter() - t0
print(f"1. Upload and validation: {t_val*1000:.2f} ms")

# 2 & 3. Text extraction & Structural section extraction
t0 = time.perf_counter()
extracted_doc = extract_document(str(pdf_path))
t_extract = time.perf_counter() - t0
print(f"2. Text extraction: {t_extract*1000:.2f} ms ({extracted_doc.word_count} words, {extracted_doc.total_pages} pages)")
print(f"3. Structural section extraction: {len(extracted_doc.sections)} sections extracted")

# 4. Chunk creation
t0 = time.perf_counter()
chunker = LayoutAwareChunker(
    target_words_per_chunk=config.chunk_size_tokens,
    overlap_words=config.chunk_overlap_tokens
)
chunks = chunker.chunk(extracted_doc)
t_chunk = time.perf_counter() - t0
print(f"4. Chunk creation: {t_chunk*1000:.2f} ms ({len(chunks)} chunks created)")

# 5. Embedding generation (using current ollama_client.embed)
t0 = time.perf_counter()
batch_size = config.embedding_batch_size
all_texts = [c.text for c in chunks]
embeddings = []
for i in range(0, len(all_texts), batch_size):
    batch = all_texts[i:i+batch_size]
    embs = ollama_client.embed(batch, model=config.embedding_model)
    embeddings.extend(embs)
t_embed = time.perf_counter() - t0
print(f"5. Embedding generation: {t_embed:.3f} s ({len(embeddings)} vectors of dim {len(embeddings[0]) if embeddings else 0})")

# 6. SQLite writes
t0 = time.perf_counter()
# Measure time to insert chunks and sections
db = SessionLocal()
try:
    test_doc_id = "bench_temp_" + str(int(time.time()))
    doc = Document(
        id=test_doc_id,
        title="Benchmark Test",
        filename="benchmark_test.pdf",
        storage_path=str(pdf_path),
        mime_type="application/pdf",
        file_size_bytes=len(content),
        file_hash="bench_" + file_hash[:20],
        status=DocumentStatus.PROCESSING.value
    )
    db.add(doc)
    for idx, c in enumerate(chunks):
        db_chunk = DocumentChunk(
            id=f"{test_doc_id}_c{idx}",
            document_id=test_doc_id,
            section_id="sec_0",
            chunk_index=idx,
            page_number=c.page_numbers[0] if c.page_numbers else 1,
            text=c.text,
            token_count=c.token_count or len(c.text.split()),
            bboxes=[b.model_dump() for b in c.bboxes] if c.bboxes else [],
            chunk_metadata=c.metadata
        )
        if idx < len(embeddings):
            db_chunk.set_embedding(embeddings[idx], model_name=config.embedding_model, expected_dim=config.embedding_dimension)
        db.add(db_chunk)
    db.commit()
    t_db = time.perf_counter() - t0
    print(f"6. SQLite writes: {t_db*1000:.2f} ms")

    # 7. Index completion
    t0 = time.perf_counter()
    doc.status = DocumentStatus.COMPLETED.value
    db.commit()
    t_complete = time.perf_counter() - t0
    print(f"7. Index completion: {t_complete*1000:.2f} ms")
    
    # Cleanup test doc
    db.query(DocumentChunk).filter(DocumentChunk.document_id == test_doc_id).delete()
    db.query(Document).filter(Document.id == test_doc_id).delete()
    db.commit()
finally:
    db.close()

total_pipeline_time = t_val + t_extract + t_chunk + t_embed + t_db + t_complete
print(f"\nTOTAL PIPELINE TIME: {total_pipeline_time:.3f} s")
