"""Tests for BM25 Lexical Search and DatabaseRetriever (Phase 3 Stage 5)"""

import pytest
from sqlalchemy.orm import Session
from backend.retrieval.bm25 import BM25, tokenize
from backend.retrieval.db_retriever import DatabaseRetriever, SearchResult
from backend.db.models import Document, DocumentChunk, DocumentStatus
from backend.config import config

def test_bm25_tokenization_technical_terms():
    """Verify that BM25 tokenizer preserves technical codes, units, and versions."""
    raw = "The RS-485 interface has an IP-67 rating at 0.75 MPa, 1200 RPM, and HTTP API v2.1."
    tokens = tokenize(raw)

    assert "rs-485" in tokens
    assert "ip-67" in tokens
    assert "0.75" in tokens
    assert "mpa" in tokens
    assert "1200" in tokens
    assert "rpm" in tokens
    assert "http" in tokens
    assert "api" in tokens
    assert "v2.1" in tokens

def test_bm25_scoring_logic():
    """Verify BM25 ranking based on term frequency and document frequency."""
    corpus_ids = ["doc_1", "doc_2", "doc_3"]
    corpus_texts = [
        "Hydraulic pressure must not exceed 0.75 MPa during continuous motor operation.",
        "Electrical wiring requires RS-485 serial communication with IP-67 enclosure.",
        "Routine maintenance schedule for pump lubrication and general inspection."
    ]

    bm25 = BM25()
    bm25.fit(corpus_ids, corpus_texts)

    # Query 1: Hydraulic pressure
    scores_1 = dict(bm25.score("0.75 MPa hydraulic pressure"))
    assert scores_1["doc_1"] > scores_1["doc_2"]
    assert scores_1["doc_1"] > scores_1["doc_3"]

    # Query 2: Serial communication
    scores_2 = dict(bm25.score("RS-485 communication"))
    assert scores_2["doc_2"] > scores_2["doc_1"]
    assert scores_2["doc_2"] > scores_2["doc_3"]

def test_db_retriever_hybrid_and_filtering(db_session: Session):
    """Verify DatabaseRetriever hybrid retrieval and document ID filtering."""
    # Seed test documents and chunks in DB
    doc1 = Document(
        id="test_retrieval_doc_1",
        title="Hydraulics Manual",
        filename="hydraulics.pdf",
        storage_path="mock/hydraulics.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        file_hash="hash_hydraulics_1",
        status=DocumentStatus.COMPLETED.value
    )
    doc2 = Document(
        id="test_retrieval_doc_2",
        title="Electronics Manual",
        filename="electronics.pdf",
        storage_path="mock/electronics.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        file_hash="hash_electronics_2",
        status=DocumentStatus.COMPLETED.value
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    # Synthetic 768-dim vectors
    vec_a = [0.05] * 768
    vec_b = [-0.05] * 768

    chunk1 = DocumentChunk(
        id="c1",
        document_id=doc1.id,
        chunk_index=0,
        page_number=1,
        text="Hydraulic pressure threshold is 0.75 MPa at 1200 RPM.",
        token_count=10
    )
    chunk1.set_embedding(vec_a, model_name=config.embedding_model, expected_dim=768)

    chunk2 = DocumentChunk(
        id="c2",
        document_id=doc2.id,
        chunk_index=0,
        page_number=1,
        text="The RS-485 transceiver operates up to 10 Mbps over twisted pair cable.",
        token_count=12
    )
    chunk2.set_embedding(vec_b, model_name=config.embedding_model, expected_dim=768)

    db_session.add_all([chunk1, chunk2])
    db_session.commit()

    retriever = DatabaseRetriever(db=db_session)

    # 1. Lexical Mode
    lex_results = retriever.retrieve("RS-485 transceiver", top_k=2, mode="lexical")
    assert len(lex_results) > 0
    assert lex_results[0].chunk_id == "c2"
    assert lex_results[0].lexical_score > 0

    # 2. Document Filtering Mode
    filtered_results = retriever.retrieve(
        "RS-485 transceiver",
        top_k=2,
        mode="lexical",
        document_ids=[doc1.id]  # Only search doc1
    )
    # Since c2 belongs to doc2, it should be excluded
    assert len(filtered_results) == 0

    # 3. Hybrid Mode
    hybrid_results = retriever.retrieve(
        "0.75 MPa hydraulic pressure",
        top_k=2,
        mode="hybrid"
    )
    assert len(hybrid_results) > 0
    assert hybrid_results[0].chunk_id == "c1"
    assert hybrid_results[0].fused_score > 0
    assert hybrid_results[0].page_number == 1
