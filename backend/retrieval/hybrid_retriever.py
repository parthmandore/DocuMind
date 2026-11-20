"""Local Hybrid Retriever Implementation

Combines vector dense similarity with exact lexical keyword matching
for high-precision retrieval on technical documentation.
"""

import math
import numpy as np
from typing import List, Dict
from backend.chunking.base import DocumentChunk
from backend.retrieval.base import Retriever, ScoredChunk
from backend.embeddings.base import EmbeddingService

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

class LocalHybridRetriever(Retriever):
    def __init__(self, embedding_service: EmbeddingService = None, alpha: float = 0.6):
        """
        alpha: Weight for dense vector search (0.0 = pure lexical, 1.0 = pure dense).
        """
        self.embedding_service = embedding_service
        self.alpha = alpha
        self.chunks: List[DocumentChunk] = []
        self.vectors: List[List[float]] = []

    def index(self, chunks: List[DocumentChunk]) -> None:
        self.chunks = chunks
        self.vectors = []
        if self.embedding_service and chunks:
            texts = [c.text for c in chunks]
            self.vectors = self.embedding_service.embed_batch(texts)

    def _lexical_score(self, query_tokens: List[str], chunk_text: str) -> float:
        if not query_tokens:
            return 0.0
        text_lower = chunk_text.lower()
        matches = sum(1 for tok in query_tokens if tok in text_lower)
        return matches / len(query_tokens)

    def retrieve(self, query: str, top_k: int = 5) -> List[ScoredChunk]:
        if not self.chunks:
            return []

        query_tokens = [tok.lower() for tok in query.split() if len(tok) > 2]
        query_vector = None
        if self.embedding_service and self.vectors:
            try:
                query_vector = self.embedding_service.embed_text(query)
            except Exception:
                query_vector = None

        scored: List[ScoredChunk] = []
        for idx, chunk in enumerate(self.chunks):
            lex_score = self._lexical_score(query_tokens, chunk.text)
            
            dense_score = 0.0
            if query_vector and idx < len(self.vectors) and self.vectors[idx]:
                dense_score = cosine_similarity(query_vector, self.vectors[idx])
                dense_score = max(0.0, (dense_score + 1.0) / 2.0)  # Normalize to [0, 1]

            if query_vector:
                combined_score = (self.alpha * dense_score) + ((1.0 - self.alpha) * lex_score)
            else:
                combined_score = lex_score

            scored.append(ScoredChunk(
                chunk=chunk,
                score=round(combined_score, 4),
                score_type="hybrid" if query_vector else "sparse",
                explanation={
                    "dense_score": round(dense_score, 4),
                    "lexical_score": round(lex_score, 4)
                }
            ))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]
