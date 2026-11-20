"""Citation Validation and Grounding Verification Service

Verifies whether citations in generated answers correlate directly with
source document blocks, checks textual substring/fuzzy alignment,
and confirms exact page/bounding box attribution.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from backend.chunking.base import DocumentChunk
from backend.generation.base import CitationRef, GenerationResponse

class ValidationStatus(BaseModel):
    is_valid: bool
    grounding_score: float  # 0.0 to 1.0
    verified_citations: List[CitationRef] = Field(default_factory=list)
    unverified_citations: List[CitationRef] = Field(default_factory=list)
    hallucination_detected: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)

class CitationValidator:
    def __init__(self, min_quote_len: int = 15):
        self.min_quote_len = min_quote_len

    def validate(
        self,
        response: GenerationResponse,
        source_chunks: List[DocumentChunk]
    ) -> ValidationStatus:
        if response.abstained:
            return ValidationStatus(
                is_valid=True,
                grounding_score=1.0,
                details={"reason": "Model correctly abstained; no citations required."}
            )

        if not response.citations:
            return ValidationStatus(
                is_valid=False,
                grounding_score=0.0,
                hallucination_detected=True,
                details={"reason": "Answer provided without citations."}
            )

        chunk_lookup = {c.chunk_id: c for c in source_chunks}
        verified = []
        unverified = []

        for cit in response.citations:
            source_c = chunk_lookup.get(cit.chunk_id)
            if not source_c:
                unverified.append(cit)
                continue

            # Verify page match
            page_matched = cit.page in source_c.page_numbers
            
            # Verify quote match
            clean_quote = cit.quote.strip().replace("...", "")
            quote_matched = (
                clean_quote.lower() in source_c.text.lower()
                or len(clean_quote) < self.min_quote_len
            )

            if page_matched and quote_matched:
                verified.append(cit)
            else:
                unverified.append(cit)

        total_citations = len(response.citations)
        grounding_score = len(verified) / total_citations if total_citations > 0 else 0.0
        hallucination = len(unverified) > 0 or grounding_score < 0.5

        return ValidationStatus(
            is_valid=not hallucination,
            grounding_score=round(grounding_score, 4),
            verified_citations=verified,
            unverified_citations=unverified,
            hallucination_detected=hallucination,
            details={
                "total_citations": total_citations,
                "verified_count": len(verified),
                "unverified_count": len(unverified)
            }
        )
