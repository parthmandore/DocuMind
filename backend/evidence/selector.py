"""Evidence Selection and Context Budgeting Module

Selects, filters, deduplicates, and budgets retrieved candidate chunks from the
DatabaseRetriever to form the precise evidence packet for grounded generation.
"""

from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.models import DocumentChunk, DocumentSection, Document
from backend.retrieval.db_retriever import DatabaseRetriever, SearchResult
from backend.query.processor import ProcessedQuery

class SelectedEvidence(BaseModel):
    chunk_id: str
    document_id: str
    document_filename: str = ""
    section_id: Optional[str] = None
    section_title: str = "General Section"
    page_number: int = 1
    text: str
    token_count: int = 0
    bboxes: List[Dict[str, Any]] = Field(default_factory=list)
    dense_score: Optional[float] = None
    lexical_score: Optional[float] = None
    fused_score: float = 0.0
    rank: int = 1
    is_table: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvidencePacket(BaseModel):
    query: str
    selected_items: List[SelectedEvidence] = Field(default_factory=list)
    total_tokens: int = 0
    candidate_count: int = 0
    has_contradictory_candidates: bool = False
    has_table_context: bool = False
    retrieval_trace: Dict[str, Any] = Field(default_factory=dict)
    completeness: Optional[Dict[str, Any]] = None

class EvidenceSelector:
    """
    Selects, budgets, and enriches retrieved evidence candidates.
    """
    def __init__(
        self,
        db: Session,
        max_evidence_tokens: int = 2200,
        max_chunks: int = 8
    ):
        self.db = db
        self.max_evidence_tokens = max_evidence_tokens
        self.max_chunks = max_chunks
        self.retriever = DatabaseRetriever(db=db)

    def select(
        self,
        processed_query: ProcessedQuery,
        top_k: int = 8,
        expand_neighbors: bool = False
    ) -> EvidencePacket:
        """
        Retrieves, deduplicates, and budgets candidate evidence for generation.
        """
        trace: Dict[str, Any] = {
            "query": processed_query.cleaned_query,
            "acronyms": getattr(processed_query, "acronyms", []),
            "expansions_used": [],
            "adaptive_depth_triggered": False,
            "sibling_expansions": []
        }

        # 1. Retrieve candidates for the main query
        raw_candidates = self.retriever.retrieve(
            query=processed_query.cleaned_query,
            top_k=top_k,
            mode="hybrid",
            document_ids=processed_query.document_ids
        )

        # 2. Acronym-aware expansion retrieval
        if getattr(processed_query, "query_expansions", None):
            for exp in processed_query.query_expansions[:3]:
                trace["expansions_used"].append(exp)
                exp_candidates = self.retriever.retrieve(
                    query=exp,
                    top_k=3,
                    mode="hybrid",
                    document_ids=processed_query.document_ids
                )
                for ec in exp_candidates:
                    raw_candidates.append(ec)

        # 3. If compound, retrieve for subquestions and guarantee coverage
        subq_guaranteed_cands: List[SearchResult] = []
        if processed_query.is_compound and len(processed_query.subquestions) > 1:
            for subq in processed_query.subquestions[:3]:
                sub_candidates = self.retriever.retrieve(
                    query=subq,
                    top_k=3,
                    mode="hybrid",
                    document_ids=processed_query.document_ids
                )
                if sub_candidates:
                    subq_guaranteed_cands.append(sub_candidates[0])
                    for sc in sub_candidates:
                        raw_candidates.append(sc)

        # 3B. If comparison query, retrieve for each entity and guarantee balanced coverage
        entity_guaranteed_cands: List[SearchResult] = []
        comp_entities = getattr(processed_query, "comparison_entities", None) or []
        if comp_entities and len(comp_entities) >= 2:
            trace["comparison_entities"] = comp_entities
            for ent in comp_entities[:4]:
                ent_candidates = self.retriever.retrieve(
                    query=ent,
                    top_k=2,
                    mode="hybrid",
                    document_ids=processed_query.document_ids
                )
                if ent_candidates:
                    entity_guaranteed_cands.append(ent_candidates[0])
                    for ec in ent_candidates:
                        raw_candidates.append(ec)

        # 4. Adaptive Retrieval Depth (Stage B2)
        q_lower = processed_query.cleaned_query.lower()
        is_broad_or_multi = any(k in q_lower for k in [
            "types", "kinds", "categories", "methods", "stages", "steps",
            "compare", "differentiate", "framework", "lifecycle", "process"
        ])
        if is_broad_or_multi and len(raw_candidates) < 8:
            trace["adaptive_depth_triggered"] = True
            adaptive_candidates = self.retriever.retrieve(
                query=processed_query.cleaned_query,
                top_k=min(top_k + 4, 12),
                mode="hybrid",
                document_ids=processed_query.document_ids
            )
            for ac in adaptive_candidates:
                raw_candidates.append(ac)

        if not raw_candidates:
            return EvidencePacket(query=processed_query.cleaned_query, retrieval_trace=trace)

        # 3. Deduplicate exact text content and rank
        unique_candidates: List[SearchResult] = []
        seen_texts: Set[str] = set()
        seen_chunk_ids: Set[str] = set()

        # Prioritize subquestion and comparison entity guaranteed candidates first
        for c in subq_guaranteed_cands + entity_guaranteed_cands:
            norm_text = " ".join(c.text.strip().split()).lower()
            if c.chunk_id not in seen_chunk_ids and norm_text not in seen_texts:
                seen_chunk_ids.add(c.chunk_id)
                seen_texts.add(norm_text)
                unique_candidates.append(c)

        # Then append remaining candidates sorted by fused_score
        remaining = [c for c in raw_candidates if c.chunk_id not in seen_chunk_ids]
        remaining.sort(key=lambda x: x.fused_score, reverse=True)
        for c in remaining:
            norm_text = " ".join(c.text.strip().split()).lower()
            if c.chunk_id in seen_chunk_ids or norm_text in seen_texts:
                continue
            seen_chunk_ids.add(c.chunk_id)
            seen_texts.add(norm_text)
            unique_candidates.append(c)

        # 4. Enrich with document and section titles from database
        doc_ids = list({c.document_id for c in unique_candidates})
        docs = self.db.query(Document).filter(Document.id.in_(doc_ids)).all()
        doc_map = {d.id: d.filename for d in docs}

        sec_ids = [c.section_id for c in unique_candidates if c.section_id]
        sec_map = {}
        if sec_ids:
            sections = self.db.query(DocumentSection).filter(DocumentSection.id.in_(sec_ids)).all()
            sec_map = {s.id: s.title for s in sections}

        # 5. Apply Token Budget & Sibling Expansion
        selected_items: List[SelectedEvidence] = []
        accumulated_tokens = 0
        has_table = False
        should_expand_siblings = expand_neighbors or is_broad_or_multi

        # Step 5A: Select initial top primary candidates
        # Guarantee at least 6 distinct primary candidates (or all candidates) before any sibling expansion
        guaranteed_count = len(subq_guaranteed_cands) + len(entity_guaranteed_cands)
        primary_quota = max(guaranteed_count + 3, min(6, self.max_chunks)) if should_expand_siblings else self.max_chunks
        primary_quota = min(primary_quota, self.max_chunks)

        for rank, c in enumerate(unique_candidates, start=1):
            if len(selected_items) >= primary_quota:
                break

            approx_tokens = len(c.text.split())
            if accumulated_tokens + approx_tokens > self.max_evidence_tokens and selected_items:
                break

            is_table_chunk = "|" in c.text and "\n|-" in c.text or "\n| -" in c.text
            if is_table_chunk:
                has_table = True

            item = SelectedEvidence(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_filename=doc_map.get(c.document_id, f"{c.document_id}.pdf"),
                section_id=c.section_id,
                section_title=sec_map.get(c.section_id, "Document Passage"),
                page_number=c.page_number,
                text=c.text,
                token_count=approx_tokens,
                bboxes=c.bboxes or [],
                dense_score=c.dense_score,
                lexical_score=c.lexical_score,
                fused_score=c.fused_score,
                rank=rank,
                is_table=is_table_chunk,
                metadata=c.metadata or {}
            )
            selected_items.append(item)
            accumulated_tokens += approx_tokens

        # Step 5B: Multi-Section & Sibling Chunk Expansion for primary candidates (max 1 sibling per candidate)
        if should_expand_siblings and len(selected_items) < self.max_chunks:
            for p_item in list(selected_items[:2]):
                chunk_obj = self.db.query(DocumentChunk).filter(DocumentChunk.id == p_item.chunk_id).first()
                if not chunk_obj:
                    continue

                # Fetch 1 consecutive following chunk (bounded to prevent candidate starvation)
                for step in range(1, 2):
                    if len(selected_items) >= self.max_chunks:
                        break
                    next_chunk = (
                        self.db.query(DocumentChunk)
                        .filter(
                            DocumentChunk.document_id == chunk_obj.document_id,
                            DocumentChunk.chunk_index == chunk_obj.chunk_index + step
                        )
                        .first()
                    )
                    if next_chunk and next_chunk.id not in seen_chunk_ids:
                        n_tokens = next_chunk.token_count or len(next_chunk.text.split())
                        if accumulated_tokens + n_tokens <= self.max_evidence_tokens:
                            seen_chunk_ids.add(next_chunk.id)
                            item_sib = SelectedEvidence(
                                chunk_id=next_chunk.id,
                                document_id=next_chunk.document_id,
                                document_filename=doc_map.get(next_chunk.document_id, ""),
                                section_id=next_chunk.section_id,
                                section_title=sec_map.get(next_chunk.section_id, "Document Passage"),
                                page_number=next_chunk.page_number,
                                text=next_chunk.text,
                                token_count=n_tokens,
                                bboxes=next_chunk.bboxes or [],
                                fused_score=p_item.fused_score * (0.95 ** step),
                                rank=len(selected_items) + 1,
                                metadata=next_chunk.chunk_metadata or {}
                            )
                            selected_items.append(item_sib)
                            accumulated_tokens += n_tokens
                            trace["sibling_expansions"].append(next_chunk.id)

        # Step 5C: Backfill any remaining capacity up to max_chunks from remaining unique candidates
        if len(selected_items) < self.max_chunks:
            for rank, c in enumerate(unique_candidates, start=len(selected_items) + 1):
                if len(selected_items) >= self.max_chunks:
                    break
                if c.chunk_id in seen_chunk_ids:
                    continue

                approx_tokens = len(c.text.split())
                if accumulated_tokens + approx_tokens > self.max_evidence_tokens:
                    break

                is_table_chunk = "|" in c.text and "\n|-" in c.text or "\n| -" in c.text
                if is_table_chunk:
                    has_table = True

                seen_chunk_ids.add(c.chunk_id)
                item = SelectedEvidence(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    document_filename=doc_map.get(c.document_id, f"{c.document_id}.pdf"),
                    section_id=c.section_id,
                    section_title=sec_map.get(c.section_id, "Document Passage"),
                    page_number=c.page_number,
                    text=c.text,
                    token_count=approx_tokens,
                    bboxes=c.bboxes or [],
                    dense_score=c.dense_score,
                    lexical_score=c.lexical_score,
                    fused_score=c.fused_score,
                    rank=len(selected_items) + 1,
                    is_table=is_table_chunk,
                    metadata=c.metadata or {}
                )
                selected_items.append(item)
                accumulated_tokens += approx_tokens

        # Stage C: Evidence Completeness Validation
        from backend.evidence.completeness import EvidenceCompletenessValidator
        completeness_eval = EvidenceCompletenessValidator().analyze(
            query=processed_query.cleaned_query,
            evidence_items=selected_items
        )

        return EvidencePacket(
            query=processed_query.cleaned_query,
            selected_items=selected_items,
            total_tokens=accumulated_tokens,
            candidate_count=len(unique_candidates),
            has_contradictory_candidates=False,
            has_table_context=has_table,
            retrieval_trace=trace,
            completeness=completeness_eval.model_dump()
        )
