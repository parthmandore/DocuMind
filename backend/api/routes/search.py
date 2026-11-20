"""Search API Routes

Endpoints for semantic, lexical, and hybrid document search over persisted
chunks with Reciprocal Rank Fusion (RRF).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.retrieval.db_retriever import DatabaseRetriever
from backend.ollama_runtime.arbiter import OllamaBusyError, MemoryThresholdError
from backend.api.schemas import SearchResponse, SearchHitSchema

router = APIRouter(prefix="/search", tags=["search"])

@router.get("", response_model=SearchResponse)
def search_documents(
    q: str = Query(..., min_length=1, description="Query string for semantic or lexical search"),
    mode: str = Query("hybrid", pattern="^(hybrid|dense|lexical)$", description="Retrieval mode"),
    top_k: int = Query(5, ge=1, le=50, description="Maximum number of chunks to return"),
    document_ids: Optional[List[str]] = Query(None, description="Optional list of document IDs to scope search"),
    db: Session = Depends(get_db)
):
    """
    Search indexed document chunks across the local knowledge base.
    Modes:
    - 'hybrid': Combines BM25 and vector embeddings via Reciprocal Rank Fusion (RRF).
    - 'dense': Pure cosine similarity on local 768-dim embeddings.
    - 'lexical': Pure Okapi BM25 keyword matching preserving technical terms.
    """
    retriever = DatabaseRetriever(db=db)

    try:
        results = retriever.retrieve(
            query=q,
            top_k=top_k,
            mode=mode,
            document_ids=document_ids
        )
    except OllamaBusyError as busy_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Inference engine is currently busy with another task: {busy_err}"
        )
    except MemoryThresholdError as mem_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Inference temporarily suspended due to high system RAM pressure: {mem_err}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval execution failed: {e}"
        )

    # Sanitize hits (ensure no raw filesystem paths are exposed)
    hits: List[SearchHitSchema] = []
    for r in results:
        sanitized_meta = dict(r.metadata or {})
        sanitized_meta.pop("storage_path", None)
        sanitized_meta.pop("absolute_path", None)

        hits.append(SearchHitSchema(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            section_id=r.section_id,
            page_number=r.page_number,
            text=r.text,
            bboxes=r.bboxes or [],
            dense_score=r.dense_score,
            lexical_score=r.lexical_score,
            fused_score=r.fused_score,
            rank=r.rank,
            metadata=sanitized_meta
        ))

    return SearchResponse(
        query=q,
        mode=mode,
        effective_mode=retriever.effective_mode,
        total_results=len(hits),
        results=hits
    )
