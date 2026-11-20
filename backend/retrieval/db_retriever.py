"""Database-Backed Hybrid Retriever

Performs dense vector retrieval via local Ollama embeddings, lexical retrieval via BM25,
and rank-based Reciprocal Rank Fusion (RRF) on persisted database chunks.
"""

import logging
import time
from typing import List, Optional, Dict, Any
import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import config
from backend.db.models import DocumentChunk, Document, DocumentStatus
from backend.retrieval.bm25 import BM25
from backend.ollama_runtime.client import ollama_client
from backend.ollama_runtime.arbiter import OllamaBusyError, MemoryThresholdError

logger = logging.getLogger(__name__)

class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    section_id: Optional[str] = None
    page_number: int
    text: str
    bboxes: List[Dict[str, Any]] = Field(default_factory=list)
    dense_score: Optional[float] = None
    lexical_score: Optional[float] = None
    fused_score: float
    rank: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DatabaseRetriever:
    """
    Production-grade hybrid retriever operating directly against the SQLite/PostgreSQL
    database storage.
    """
    def __init__(
        self,
        db: Session,
        rrf_k: int = 60,
        dense_weight: float = 0.6,
        lexical_weight: float = 0.4
    ):
        self.db = db
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight
        self.lexical_weight = lexical_weight
        self.effective_mode: str = "hybrid"
        self.last_latency_profile: Dict[str, float] = {}
        self._query_embed_cache: Dict[str, List[float]] = {}

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",  # "hybrid", "dense", "lexical"
        document_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        self.effective_mode = mode
        """
        Executes retrieval according to mode:
        - 'dense': Vector cosine similarity only.
        - 'lexical': BM25 keyword matching only.
        - 'hybrid': Reciprocal Rank Fusion (RRF) of dense and lexical ranks.
        """
        t_total_start = time.perf_counter()
        if not query.strip():
            self.last_latency_profile = {
                "db_load_ms": 0.0,
                "query_embed_ms": 0.0,
                "similarity_ms": 0.0,
                "ranking_ms": 0.0,
                "total_ms": 0.0
            }
            return []

        # 1. Fetch eligible candidate chunks from DB
        t_db_start = time.perf_counter()
        query_stmt = self.db.query(DocumentChunk)
        if document_ids:
            query_stmt = query_stmt.filter(DocumentChunk.document_id.in_(document_ids))
        
        chunks = query_stmt.all()
        db_load_ms = (time.perf_counter() - t_db_start) * 1000.0

        if not chunks:
            self.last_latency_profile = {
                "db_load_ms": round(db_load_ms, 3),
                "query_embed_ms": 0.0,
                "similarity_ms": 0.0,
                "ranking_ms": 0.0,
                "total_ms": round((time.perf_counter() - t_total_start) * 1000.0, 3)
            }
            return []

        # 2. Dense Vector Retrieval
        dense_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}
        query_embed_ms = 0.0
        similarity_ms = 0.0

        if mode in ("dense", "hybrid"):
            try:
                # Generate or reuse query embedding sequentially under Ollama Hardware Arbiter
                t_embed_start = time.perf_counter()
                if query in self._query_embed_cache:
                    query_vec = self._query_embed_cache[query]
                else:
                    query_vec = ollama_client.embed_single(
                        query,
                        model=config.embedding_model,
                        timeout=config.llm_timeout_seconds
                    )
                    if query_vec:
                        self._query_embed_cache[query] = query_vec
                query_embed_ms = (time.perf_counter() - t_embed_start) * 1000.0

                # Filter chunks with matching embedding model and valid vectors
                t_sim_start = time.perf_counter()
                valid_chunks = [
                    c for c in chunks
                    if c.embedding and c.embedding_model == config.embedding_model
                ]

                if valid_chunks and query_vec:
                    matrix = np.array([c.embedding for c in valid_chunks], dtype=np.float32)
                    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                    norms[norms == 0] = 1e-10
                    norm_matrix = matrix / norms

                    q_arr = np.array(query_vec, dtype=np.float32)
                    q_norm = np.linalg.norm(q_arr)
                    if q_norm > 0:
                        q_arr = q_arr / q_norm
                        sims = np.dot(norm_matrix, q_arr)

                        for chunk, sim in zip(valid_chunks, sims):
                            # Cosine sim in [-1, 1], normalized to [0, 1] for display
                            norm_sim = float(max(0.0, (sim + 1.0) / 2.0))
                            dense_scores[chunk.id] = round(norm_sim, 4)

                        # Sort descending for dense ranking
                        sorted_dense = sorted(
                            dense_scores.items(),
                            key=lambda item: item[1],
                            reverse=True
                        )
                        for rank, (c_id, _) in enumerate(sorted_dense, start=1):
                            dense_ranks[c_id] = rank
                similarity_ms = (time.perf_counter() - t_sim_start) * 1000.0

            except (OllamaBusyError, MemoryThresholdError, Exception) as e:
                logger.warning("Dense embedding lookup failed or arbiter busy: %s", e)
                if mode == "dense":
                    raise e
                # In hybrid mode, fall back to purely lexical retrieval

        # 3. Lexical BM25 Retrieval
        lexical_ranks: Dict[str, int] = {}
        lexical_scores: Dict[str, float] = {}

        if mode in ("lexical", "hybrid") or (mode == "hybrid" and not dense_scores):
            bm25 = BM25()
            chunk_ids = [c.id for c in chunks]
            chunk_texts = [c.text for c in chunks]
            bm25.fit(chunk_ids, chunk_texts)
            scored_bm25 = bm25.score(query)

            # Filter non-zero or take top scoring
            for c_id, score in scored_bm25:
                if score > 0:
                    lexical_scores[c_id] = round(score, 4)

            sorted_lex = sorted(
                lexical_scores.items(),
                key=lambda item: item[1],
                reverse=True
            )
            for rank, (c_id, _) in enumerate(sorted_lex, start=1):
                lexical_ranks[c_id] = rank

        # 4. Fusion and Result Construction
        t_rank_start = time.perf_counter()
        if mode == "hybrid" and not dense_scores:
            self.effective_mode = "degraded_lexical"

        chunk_map = {c.id: c for c in chunks}
        all_candidate_ids = set(dense_ranks.keys()) | set(lexical_ranks.keys())
        if not all_candidate_ids:
            self.last_latency_profile = {
                "db_load_ms": round(db_load_ms, 3),
                "query_embed_ms": round(query_embed_ms, 3),
                "similarity_ms": round(similarity_ms, 3),
                "ranking_ms": round((time.perf_counter() - t_rank_start) * 1000.0, 3),
                "total_ms": round((time.perf_counter() - t_total_start) * 1000.0, 3)
            }
            return []

        fused_items: List[SearchResult] = []

        if mode == "dense":
            sorted_ids = sorted(
                dense_scores.keys(),
                key=lambda x: dense_scores[x],
                reverse=True
            )[:top_k]
            for rank, c_id in enumerate(sorted_ids, start=1):
                c = chunk_map[c_id]
                fused_items.append(SearchResult(
                    chunk_id=c.id,
                    document_id=c.document_id,
                    section_id=c.section_id,
                    page_number=c.page_number,
                    text=c.text,
                    bboxes=c.bboxes or [],
                    dense_score=dense_scores.get(c_id),
                    lexical_score=None,
                    fused_score=dense_scores.get(c_id, 0.0),
                    rank=rank,
                    metadata=c.chunk_metadata or {}
                ))

        elif mode == "lexical":
            sorted_ids = sorted(
                lexical_scores.keys(),
                key=lambda x: lexical_scores[x],
                reverse=True
            )[:top_k]
            for rank, c_id in enumerate(sorted_ids, start=1):
                c = chunk_map[c_id]
                fused_items.append(SearchResult(
                    chunk_id=c.id,
                    document_id=c.document_id,
                    section_id=c.section_id,
                    page_number=c.page_number,
                    text=c.text,
                    bboxes=c.bboxes or [],
                    dense_score=None,
                    lexical_score=lexical_scores.get(c_id),
                    fused_score=lexical_scores.get(c_id, 0.0),
                    rank=rank,
                    metadata=c.chunk_metadata or {}
                ))

        else:
            # Hybrid RRF: Reciprocal Rank Fusion
            # RRF score = w_dense / (k + rank_dense) + w_lex / (k + rank_lex)
            rrf_scores: Dict[str, float] = {}

            for c_id in all_candidate_ids:
                score = 0.0
                if c_id in dense_ranks:
                    score += self.dense_weight * (1.0 / (self.rrf_k + dense_ranks[c_id]))
                if c_id in lexical_ranks:
                    score += self.lexical_weight * (1.0 / (self.rrf_k + lexical_ranks[c_id]))
                rrf_scores[c_id] = score

            sorted_ids = sorted(
                rrf_scores.keys(),
                key=lambda x: rrf_scores[x],
                reverse=True
            )[:top_k]

            for rank, c_id in enumerate(sorted_ids, start=1):
                c = chunk_map[c_id]
                fused_items.append(SearchResult(
                    chunk_id=c.id,
                    document_id=c.document_id,
                    section_id=c.section_id,
                    page_number=c.page_number,
                    text=c.text,
                    bboxes=c.bboxes or [],
                    dense_score=dense_scores.get(c_id),
                    lexical_score=lexical_scores.get(c_id),
                    fused_score=round(rrf_scores[c_id], 6),
                    rank=rank,
                    metadata=c.chunk_metadata or {}
                ))

        ranking_ms = (time.perf_counter() - t_rank_start) * 1000.0
        total_ms = (time.perf_counter() - t_total_start) * 1000.0

        self.last_latency_profile = {
            "db_load_ms": round(db_load_ms, 3),
            "query_embed_ms": round(query_embed_ms, 3),
            "similarity_ms": round(similarity_ms, 3),
            "ranking_ms": round(ranking_ms, 3),
            "total_ms": round(total_ms, 3)
        }

        return fused_items
