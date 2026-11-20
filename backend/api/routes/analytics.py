"""Citation Analytics & Quality Insights Routes (Phase 5.9)

Calculates corpus grounding metrics, claim verification distributions,
document citation densities, and contradiction monitoring from persisted SQLite records.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from backend.db.base import get_db
from backend.db.models import Document, DocumentChunk, Message, Citation, EvaluationRecord

router = APIRouter(prefix="/analytics", tags=["analytics"])

class CorpusOverview(BaseModel):
    total_documents: int
    total_chunks: int
    total_indexed_chunks: int
    total_queries: int
    total_answers: int
    total_citations: int
    verified_citations: int
    unverified_citations: int
    abstained_answers: int

class CitationQualityMetrics(BaseModel):
    citation_verification_rate: float = Field(..., description="verified_citations / total_citations")
    claim_support_rate: float = Field(..., description="supported_claims / evaluated_claims")
    supported_claims_count: int
    partially_supported_claims_count: int
    unsupported_claims_count: int
    contradicted_claims_count: int
    insufficient_evidence_count: int
    total_evaluated_claims: int
    total_contradictions_detected: int

class ClaimDistributionItem(BaseModel):
    status: str
    count: int
    percentage: float

class DocumentAnalyticsItem(BaseModel):
    document_id: str
    title: str
    filename: str
    total_chunks: int
    total_citations: int
    verified_citations: int
    verification_rate: float

class ContradictionLogItem(BaseModel):
    message_id: str
    created_at: datetime
    claim_text: str
    conflicting_passage: str
    source_document_title: Optional[str] = None
    page_number: Optional[int] = None

class DailyActivityItem(BaseModel):
    date: str
    queries: int
    citations: int
    verified_citations: int

class InsightsResponse(BaseModel):
    overview: CorpusOverview
    quality: CitationQualityMetrics
    claim_distribution: List[ClaimDistributionItem]
    top_cited_documents: List[DocumentAnalyticsItem]
    contradiction_logs: List[ContradictionLogItem]
    daily_activity: List[DailyActivityItem]

@router.get("/insights", response_model=InsightsResponse)
def get_insights(db: Session = Depends(get_db)):
    """
    Computes corpus-wide grounding verification statistics, claim verification
    distributions, and contradiction records strictly from real persisted SQLite data.
    """
    # 1. Corpus Overview
    total_documents = db.query(Document).count()
    total_chunks = db.query(DocumentChunk).count()
    total_indexed_chunks = db.query(DocumentChunk).filter(DocumentChunk.embedding.isnot(None)).count()
    total_queries = db.query(Message).filter(Message.role == "user").count()
    total_answers = db.query(Message).filter(Message.role == "assistant").count()
    total_citations = db.query(Citation).count()
    verified_citations = db.query(Citation).filter(Citation.is_verified == True).count()
    unverified_citations = total_citations - verified_citations

    # 2. Assistant messages claim & contradiction evaluation
    assistant_msgs = (
        db.query(Message)
        .filter(Message.role == "assistant")
        .order_by(Message.created_at.desc())
        .all()
    )

    abstained_count = 0
    supp_count = 0
    partial_count = 0
    unsupp_count = 0
    contra_count = 0
    insuff_count = 0
    contradiction_items: List[ContradictionLogItem] = []

    for msg in assistant_msgs:
        meta = msg.message_metadata or {}
        if meta.get("abstained") is True or meta.get("status") == "abstained":
            abstained_count += 1

        claims = meta.get("supporting_claims", [])
        for c in claims:
            state = (c.get("support_state") or c.get("verification_status") or "").lower()
            if "partially" in state:
                partial_count += 1
            elif "unsupported" in state:
                unsupp_count += 1
            elif "contradict" in state:
                contra_count += 1
            elif "insuffic" in state:
                insuff_count += 1
            elif "supported" in state or "verified" in state:
                supp_count += 1

        # Extract contradictions logged
        msg_contradictions = meta.get("contradictions", [])
        for contra in msg_contradictions:
            if isinstance(contra, dict):
                claim_t = contra.get("claim_text") or contra.get("claim", "Contradictory claim")
                passage_t = contra.get("conflicting_passage") or contra.get("passage", "")
                doc_t = contra.get("document_title")
                pg_n = contra.get("page_number")
            else:
                claim_t = str(contra)
                passage_t = "Conflicting evidence identified across corpus."
                doc_t = None
                pg_n = None

            contradiction_items.append(
                ContradictionLogItem(
                    message_id=msg.id,
                    created_at=msg.created_at,
                    claim_text=claim_t,
                    conflicting_passage=passage_t,
                    source_document_title=doc_t,
                    page_number=pg_n
                )
            )

    total_evaluated_claims = supp_count + partial_count + unsupp_count + contra_count + insuff_count
    claim_support_rate = round(supp_count / total_evaluated_claims, 4) if total_evaluated_claims > 0 else 0.0
    citation_verif_rate = round(verified_citations / total_citations, 4) if total_citations > 0 else 0.0

    overview = CorpusOverview(
        total_documents=total_documents,
        total_chunks=total_chunks,
        total_indexed_chunks=total_indexed_chunks,
        total_queries=total_queries,
        total_answers=total_answers,
        total_citations=total_citations,
        verified_citations=verified_citations,
        unverified_citations=unverified_citations,
        abstained_answers=abstained_count
    )

    quality = CitationQualityMetrics(
        citation_verification_rate=citation_verif_rate,
        claim_support_rate=claim_support_rate,
        supported_claims_count=supp_count,
        partially_supported_claims_count=partial_count,
        unsupported_claims_count=unsupp_count,
        contradicted_claims_count=contra_count,
        insufficient_evidence_count=insuff_count,
        total_evaluated_claims=total_evaluated_claims,
        total_contradictions_detected=len(contradiction_items)
    )

    # 3. Distribution percentages
    def safe_pct(val: int) -> float:
        return round((val / total_evaluated_claims) * 100, 1) if total_evaluated_claims > 0 else 0.0

    claim_distribution = [
        ClaimDistributionItem(status="SUPPORTED", count=supp_count, percentage=safe_pct(supp_count)),
        ClaimDistributionItem(status="PARTIALLY_SUPPORTED", count=partial_count, percentage=safe_pct(partial_count)),
        ClaimDistributionItem(status="UNSUPPORTED", count=unsupp_count, percentage=safe_pct(unsupp_count)),
        ClaimDistributionItem(status="CONTRADICTED", count=contra_count, percentage=safe_pct(contra_count)),
        ClaimDistributionItem(status="INSUFFICIENT_EVIDENCE", count=insuff_count, percentage=safe_pct(insuff_count)),
    ]

    # 4. Top cited documents
    # Query citations grouped by chunk -> document
    docs = db.query(Document).all()
    doc_analytics: List[DocumentAnalyticsItem] = []

    for d in docs:
        d_chunks = db.query(DocumentChunk.id).filter(DocumentChunk.document_id == d.id).all()
        chunk_ids = [c[0] for c in d_chunks]

        if chunk_ids:
            d_cits = db.query(Citation).filter(Citation.chunk_id.in_(chunk_ids)).all()
            d_total_cits = len(d_cits)
            d_verif_cits = sum(1 for c in d_cits if c.is_verified)
            d_rate = round(d_verif_cits / d_total_cits, 4) if d_total_cits > 0 else 0.0
        else:
            d_total_cits = 0
            d_verif_cits = 0
            d_rate = 0.0

        doc_analytics.append(
            DocumentAnalyticsItem(
                document_id=d.id,
                title=d.title,
                filename=d.filename,
                total_chunks=len(chunk_ids),
                total_citations=d_total_cits,
                verified_citations=d_verif_cits,
                verification_rate=d_rate
            )
        )

    # Sort documents by total citations descending
    doc_analytics.sort(key=lambda x: (x.total_citations, x.total_chunks), reverse=True)

    # 5. Daily activity trends (last 14 days)
    today = datetime.now(timezone.utc).date()
    daily_map: Dict[str, Dict[str, int]] = {}
    for i in range(13, -1, -1):
        d_str = (today - timedelta(days=i)).isoformat()
        daily_map[d_str] = {"queries": 0, "citations": 0, "verified_citations": 0}

    # Aggregate queries by day
    for m in db.query(Message).filter(Message.role == "user").all():
        d_str = m.created_at.date().isoformat()
        if d_str in daily_map:
            daily_map[d_str]["queries"] += 1

    # Aggregate citations by day
    for cit in db.query(Citation).all():
        d_str = cit.created_at.date().isoformat()
        if d_str in daily_map:
            daily_map[d_str]["citations"] += 1
            if cit.is_verified:
                daily_map[d_str]["verified_citations"] += 1

    daily_activity = [
        DailyActivityItem(
            date=d_str,
            queries=data["queries"],
            citations=data["citations"],
            verified_citations=data["verified_citations"]
        )
        for d_str, data in daily_map.items()
    ]

    return InsightsResponse(
        overview=overview,
        quality=quality,
        claim_distribution=claim_distribution,
        top_cited_documents=doc_analytics[:15],
        contradiction_logs=contradiction_items[:50],
        daily_activity=daily_activity
    )
