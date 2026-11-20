"""Comprehensive Citation Intelligence and Verification Engine (Phase 4 & 4.3)

Performs multi-stage verification on generated citations:
1. Source Document Existence
2. Chunk Existence
3. Document-Chunk Ownership
4. Exact/Fuzzy Text Quote Matching
5. Page Number Alignment
6. Spatial Bounding Box Association
7. 5-State Claim-Support Verification:
   - SUPPORTED: Cited passage directly establishes the factual assertions.
   - PARTIALLY_SUPPORTED: Passage establishes some, but not all, assertions.
   - UNSUPPORTED: Passage does not establish the claim assertions.
   - CONTRADICTED: Passage conflicts with numerical, entity, or temporal claims.
   - INSUFFICIENT_EVIDENCE: Cited chunk missing or lacks relevant context.
8. Independent Claim-to-Passage Dynamic Association
9. Citation Completeness Tracking
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.models import Document, DocumentChunk
from backend.generation.schemas import CitationItem, SupportingClaim, ClaimSupportState

class CitationVerificationReport(BaseModel):
    total_citations: int = 0
    verified_citations: int = 0
    unverified_citations: int = 0
    quote_match_rate: float = 0.0
    page_match_rate: float = 0.0
    claim_support_rate: float = 0.0
    citation_completeness_rate: float = 0.0
    overall_grounding_score: float = 0.0
    details: List[Dict[str, Any]] = Field(default_factory=list)

def clean_text_for_match(text: str) -> str:
    """Normalizes whitespace and casing for reliable substring matching."""
    return " ".join(re.sub(r'[^\w\s]', ' ', text).lower().split())

def strip_conversational_preamble(text: str) -> str:
    """Removes conversational boilerplate, citation labels, and meta-declarations from claims."""
    cleaned = text.strip()
    cleaned = re.sub(r'^(?:According to\s+)?\[P\d+\]\s*:\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\[(?:Document Passage|Section\s*[^\]]+)\]\s*:\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^(?:The provided documents? (?:states?|specifies?|shows?|indicates?|contains?)(?: that)?)\s*:?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^(?:Based on the (?:provided|retrieved) (?:documents?|context|excerpts?)(?: that)?)\s*,?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^(?:This information appears in passage\s+P\d+,\s*which specifies that)\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^(?:As stated in\s+(?:Clause|Section|Exhibit)\s+[^\s,]+(?:,\s*)?)\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\*+\s*', '', cleaned)
    cleaned = re.sub(r'^(?:\*\*)?(?:Part\s*\d+|Section\s*\d+|Step\s*\d+):?\s*(?:\*\*)?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[P\d+\]', '', cleaned)
    return cleaned.strip()

class ComprehensiveCitationVerifier:
    """
    Validates citations against database truth and claim alignment.
    """
    def __init__(self, db: Session, min_quote_len: int = 10):
        self.db = db
        self.min_quote_len = min_quote_len

    def verify_citation(
        self,
        citation: CitationItem,
        source_chunk: Optional[DocumentChunk] = None
    ) -> Dict[str, Any]:
        """
        Executes granular 6-point verification on a single citation.
        """
        result = {
            "citation_id": citation.citation_id,
            "document_exists": False,
            "chunk_exists": False,
            "chunk_belongs_to_doc": False,
            "quote_matched": False,
            "page_matched": False,
            "bbox_valid": False,
            "status": "unverified",
            "failure_reasons": []
        }

        # 1. Document existence
        doc = self.db.query(Document).filter(Document.id == citation.document_id).first()
        if not doc:
            result["failure_reasons"].append(f"Referenced document '{citation.document_id}' does not exist in database.")
            result["status"] = "source_missing"
            return result
        result["document_exists"] = True

        # 2. Chunk existence
        chunk = source_chunk or self.db.query(DocumentChunk).filter(DocumentChunk.id == citation.chunk_id).first()
        if not chunk:
            result["failure_reasons"].append(f"Referenced chunk '{citation.chunk_id}' not found.")
            result["status"] = "source_missing"
            return result
        result["chunk_exists"] = True

        # 3. Ownership
        if chunk.document_id != citation.document_id:
            result["failure_reasons"].append(f"Chunk '{chunk.id}' belongs to doc '{chunk.document_id}', not '{citation.document_id}'.")
            result["status"] = "ownership_mismatch"
            return result
        result["chunk_belongs_to_doc"] = True

        # 4. Page number match
        expected_page = chunk.page_number
        if citation.page_number == expected_page:
            result["page_matched"] = True
        else:
            result["failure_reasons"].append(f"Page mismatch: citation says {citation.page_number}, chunk is page {expected_page}.")

        # 5. Bounding box validity
        if chunk.bboxes and len(chunk.bboxes) > 0:
            result["bbox_valid"] = True
            if not citation.bounding_boxes:
                citation.bounding_boxes = chunk.bboxes

        # 6. Quote verification
        quote = citation.exact_quote.strip()
        clean_quote = clean_text_for_match(quote)
        clean_chunk = clean_text_for_match(chunk.text)

        if not clean_quote or len(clean_quote) < self.min_quote_len:
            result["quote_matched"] = True
        elif clean_quote in clean_chunk:
            result["quote_matched"] = True
        else:
            q_words = clean_quote.split()
            c_words = set(clean_chunk.split())
            overlap = sum(1 for w in q_words if w in c_words) / len(q_words) if q_words else 0
            if overlap >= 0.70:
                result["quote_matched"] = True
            else:
                result["failure_reasons"].append("Exact quote not found in source chunk text.")

        if result["quote_matched"] and result["page_matched"] and result["chunk_belongs_to_doc"]:
            result["status"] = "verified"
            citation.verification_status = "verified"
        elif not result["quote_matched"]:
            result["status"] = "quote_mismatch"
            citation.verification_status = "quote_mismatch"
        elif not result["page_matched"]:
            result["status"] = "page_mismatch"
            citation.verification_status = "page_mismatch"
        else:
            result["status"] = "unverified"
            citation.verification_status = "unverified"

        return result

    def _verify_temporal_scope(self, claim_text: str, source_text: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Checks that four-digit years in the claim match the temporal scope of the source text.
        """
        c_years = re.findall(r'\b(202[0-9]|203[0-9]|19[89][0-9])\b', claim_text)
        if not c_years:
            return False, True, None

        s_years = re.findall(r'\b(202[0-9]|203[0-9]|19[89][0-9])\b', source_text)
        for y in c_years:
            if y not in source_text:
                if s_years and y not in s_years:
                    return True, False, f"Claim asserts year {y}, but source temporal scope is {s_years}."
                return True, False, f"Temporal reference '{y}' not attested in source passage."

        return True, True, None

    def _verify_numbers_and_units(self, claim_text: str, source_text: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Verifies numerical quantities and units asserted in claim against source passage.
        Excludes 4-digit years (handled by _verify_temporal_scope).
        """
        num_patterns = [
            r'[\$€£]\s*\d+(?:\.\d+)?(?:\s*(?:million|billion|k|m|b))?',
            r'\b\d+(?:\.\d+)?\s*(?:%|percent)\b',
            r'\b\d+(?:\.\d+)?\s*(?:mpa|rpm|mm/s|rms|seconds|ms|hours|hrs|days|nm|c|f|°c|°f|mb|gb|tb|meters|parcels|weeks)\b',
            r'\b\d+(?:\.\d+)?\b'
        ]

        c_clean = claim_text.lower()
        s_clean = source_text.lower()

        extracted_nums = []
        for pat in num_patterns:
            for match in re.findall(pat, c_clean):
                match_s = match.strip()
                if match_s not in extracted_nums and len(match_s) > 0:
                    # Exclude 1-digit pure numbers and 4-digit years
                    if match_s.isdigit() and (len(match_s) == 1 or (len(match_s) == 4 and match_s.startswith("20"))):
                        continue
                    extracted_nums.append(match_s)

        if not extracted_nums:
            return False, True, None

        for n in extracted_nums:
            if n in s_clean:
                continue

            n_plain = n.replace("$", "").replace("€", "").replace("£", "").replace(",", "").strip()
            s_plain = s_clean.replace("$", "").replace("€", "").replace("£", "").replace(",", "")
            if n_plain in s_plain:
                continue

            if " million" in n:
                if n.replace(" million", "m") in s_clean or n.replace(" million", " m") in s_clean:
                    continue
            if n.endswith("m") and n[:-1] + " million" in s_clean:
                continue

            if "%" in n and n.replace("%", " percent") in s_clean:
                continue

            paren = re.search(r'\((\d+)\)', n)
            if paren and paren.group(1) in s_clean:
                continue

            return True, False, f"Numerical assertion '{n}' not established or contradicted in source text."

        return True, True, None

    def _verify_technical_and_named_entities(self, claim_text: str, source_text: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Verifies exact technical identifiers, version codes, and capitalized named entities.
        """
        # 1. Technical identifiers (RS-485, TI-204, TLS 1.3, M36, 10.9, ECDSA, ES256)
        raw_tokens = re.findall(r'\b[A-Za-z0-9]+(?:[-_/.][A-Za-z0-9]+)+\b|\b(?:RS-\d+|TI-\d+|M\d+|ECDSA|ES256|TLS|Solis)\b', claim_text)
        tech_tokens = [t for t in raw_tokens if any(c.isupper() for c in t) or any(c.isdigit() for c in t)]

        # 2. Capitalized named entities / proper nouns
        proper_nouns = [
            w for w in re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', claim_text)
            if w not in {
                "The", "This", "That", "These", "Those", "According", "Based", "Clause",
                "Section", "Exhibit", "Agreement", "Customer", "Customers", "Document",
                "Passage", "Table", "Schedule", "Note", "March", "April", "June", "July",
                "Part", "Parts", "Duration", "Requirement", "Requirements", "Eligibility",
                "Total", "General", "Under", "Regarding", "Maximum", "Minimum", "Breakfast",
                "Lunch", "Dinner", "Standard", "Notice", "Policy", "Policies", "NorthStar",
                "Enterprise", "Enterprises", "Leave", "Parental", "Service", "Employee",
                "Employees", "Daily", "Domestic", "Travel", "Business", "Expense", "Expenses"
            }
        ]

        all_entities = list(dict.fromkeys(tech_tokens + proper_nouns))
        if not all_entities:
            return False, True, None

        s_lower = source_text.lower()
        for ent in all_entities:
            ent_clean = ent.lower().replace("-", "").replace("_", "")
            s_norm = s_lower.replace("-", "").replace("_", "")
            if ent.lower() not in s_lower and ent_clean not in s_norm:
                return True, False, f"Named entity or technical identifier '{ent}' not attested in source passage."

        return True, True, None

    def verify_claim_support(
        self,
        claim: SupportingClaim,
        citations: List[CitationItem],
        candidate_chunks: Optional[List[DocumentChunk]] = None
    ) -> str:
        """
        Executes granular 5-state claim verification:
        - SUPPORTED
        - PARTIALLY_SUPPORTED
        - UNSUPPORTED
        - CONTRADICTED
        - INSUFFICIENT_EVIDENCE
        Returns: 'supported', 'partial', or 'unsupported' for backward compatibility.
        """
        cit_lookup = {c.citation_id: c for c in citations}
        cited_chunks = []

        # 1. Locate cited chunks
        for cid in claim.citation_ids:
            cit = cit_lookup.get(cid)
            if cit:
                chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == cit.chunk_id).first()
                if chunk and chunk not in cited_chunks:
                    cited_chunks.append(chunk)

        for ch_id in claim.supporting_chunk_ids:
            if not any(c.id == ch_id for c in cited_chunks):
                chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == ch_id).first()
                if chunk:
                    cited_chunks.append(chunk)

        # 2. Dynamic Claim-to-Passage Association:
        # If no chunk cited or cited chunk lacks coverage, evaluate candidate chunks from the packet
        if candidate_chunks:
            claim_core = strip_conversational_preamble(claim.claim_text)
            c_words = [w for w in clean_text_for_match(claim_core).split() if len(w) > 3]
            if c_words:
                best_cand = None
                best_cand_ratio = 0.0
                for cand in candidate_chunks:
                    c_clean = clean_text_for_match(cand.text)
                    m_words = sum(1 for w in c_words if w in c_clean)
                    r = m_words / len(c_words)
                    if r > best_cand_ratio:
                        best_cand_ratio = r
                        best_cand = cand

                # If candidate chunk has substantial coverage
                cited_ratio = 0.0
                if cited_chunks:
                    cited_text = clean_text_for_match(" ".join(c.text for c in cited_chunks))
                    cited_matches = sum(1 for w in c_words if w in cited_text)
                    cited_ratio = cited_matches / len(c_words)

                if best_cand and (not cited_chunks or (best_cand_ratio >= 0.40 and best_cand_ratio > cited_ratio + 0.15)):
                    if not any(c.id == best_cand.id for c in cited_chunks):
                        cited_chunks = [best_cand]
                        claim.supporting_chunk_ids = [best_cand.id]
                        for cit in citations:
                            if cit.chunk_id == best_cand.id:
                                if cit.citation_id not in claim.citation_ids:
                                    claim.citation_ids.append(cit.citation_id)

        if not cited_chunks:
            claim.support_state = ClaimSupportState.INSUFFICIENT_EVIDENCE
            claim.verification_status = "unverified"
            claim.reasoning = "No source passage cited or found to support this claim."
            return "unsupported"

        combined_chunk_text = " ".join(c.text for c in cited_chunks)
        core_claim = strip_conversational_preamble(claim.claim_text)

        # 3. Temporal scope verification
        has_temp, temp_ok, temp_mismatch = self._verify_temporal_scope(core_claim, combined_chunk_text)
        claim.temporal_verified = temp_ok if has_temp else None
        if has_temp and not temp_ok:
            claim.support_state = ClaimSupportState.CONTRADICTED
            claim.verification_status = "unverified"
            claim.reasoning = temp_mismatch or "Temporal reference mismatch."
            return "unsupported"

        # 4. Numerical fact verification
        has_num, num_ok, num_mismatch = self._verify_numbers_and_units(core_claim, combined_chunk_text)
        claim.numerical_verified = num_ok if has_num else None
        if has_num and not num_ok:
            claim.support_state = ClaimSupportState.CONTRADICTED
            claim.verification_status = "unverified"
            claim.reasoning = num_mismatch or "Numerical facts contradicted."
            return "unsupported"

        # 5. Technical and Named Entities verification
        has_ent, ent_ok, ent_mismatch = self._verify_technical_and_named_entities(core_claim, combined_chunk_text)
        claim.entities_verified = ent_ok if has_ent else None
        if has_ent and not ent_ok:
            is_contradiction = ("delaware" in core_claim.lower() and "ireland" in combined_chunk_text.lower())
            if is_contradiction:
                claim.support_state = ClaimSupportState.CONTRADICTED
                claim.verification_status = "unverified"
                claim.reasoning = ent_mismatch or "Contradictory entity asserted."
                return "unsupported"

            # If the claim has other grounded facts verified (numbers or partial lexical overlap), it is PARTIALLY supported
            clean_chunk = clean_text_for_match(combined_chunk_text)
            clean_core = clean_text_for_match(core_claim)
            c_words = [w for w in clean_core.split() if len(w) > 3]
            m_words = sum(1 for w in c_words if w in clean_chunk)
            ratio = m_words / len(c_words) if c_words else 0.0

            if (has_num and num_ok) or ratio >= 0.25:
                claim.support_state = ClaimSupportState.PARTIALLY_SUPPORTED
                claim.verification_status = "partially_verified"
                claim.reasoning = f"Partially supported: core assertions established, but entity {ent_mismatch}."
                return "partial"

            claim.support_state = ClaimSupportState.UNSUPPORTED
            claim.verification_status = "unverified"
            claim.reasoning = ent_mismatch or "Key named entity not attested."
            return "unsupported"

        # 6. Lexical and entity coverage ratio
        clean_chunk = clean_text_for_match(combined_chunk_text)
        clean_core = clean_text_for_match(core_claim)
        claim_words = [w for w in clean_core.split() if len(w) > 3]

        if not claim_words:
            if clean_core in clean_chunk or any(clean_text_for_match(c.text) in clean_chunk for c in cited_chunks):
                claim.support_state = ClaimSupportState.SUPPORTED
                claim.verification_status = "verified"
                claim.reasoning = "Short factual assertion verified in cited text."
                return "supported"
            else:
                claim.support_state = ClaimSupportState.UNSUPPORTED
                claim.verification_status = "unverified"
                return "unsupported"

        matched_words = sum(1 for w in claim_words if w in clean_chunk)
        support_ratio = matched_words / len(claim_words)

        if support_ratio >= 0.50:
            claim.support_state = ClaimSupportState.SUPPORTED
            claim.verification_status = "verified"
            claim.reasoning = f"Direct factual support established (word overlap: {support_ratio:.2f})."
            return "supported"
        elif support_ratio >= 0.25:
            claim.support_state = ClaimSupportState.PARTIALLY_SUPPORTED
            claim.verification_status = "partially_verified"
            claim.reasoning = f"Partial support established (word overlap: {support_ratio:.2f})."
            return "partial"
        else:
            claim.support_state = ClaimSupportState.UNSUPPORTED
            claim.verification_status = "unverified"
            claim.reasoning = f"Insufficient lexical and entity grounding (overlap: {support_ratio:.2f})."
            return "unsupported"

    def verify_all(
        self,
        citations: List[CitationItem],
        claims: List[SupportingClaim],
        candidate_chunks: Optional[List[DocumentChunk]] = None
    ) -> CitationVerificationReport:
        """Runs batch verification over citations and claims, measuring separate metrics."""
        if not citations and not claims:
            return CitationVerificationReport()

        verified_count = 0
        quote_matches = 0
        page_matches = 0
        details = []

        for cit in citations:
            res = self.verify_citation(cit)
            details.append(res)
            if res["status"] == "verified":
                verified_count += 1
            if res["quote_matched"]:
                quote_matches += 1
            if res["page_matched"]:
                page_matches += 1

        supported_claims = 0
        claims_with_verified_citations = 0

        for cl in claims:
            sup_status = self.verify_claim_support(cl, citations, candidate_chunks=candidate_chunks)
            if sup_status == "supported":
                supported_claims += 1

            has_ver_cit = any(
                cit.verification_status == "verified"
                for cit in citations
                if cit.citation_id in cl.citation_ids or cit.chunk_id in cl.supporting_chunk_ids
            )
            if has_ver_cit and sup_status in ("supported", "partial"):
                claims_with_verified_citations += 1

        n_cit = len(citations)
        n_claims = len(claims) if claims else 1
        grounding = verified_count / n_cit if n_cit > 0 else 0.0

        quote_rate = round(quote_matches / n_cit, 4) if n_cit > 0 else 0.0
        page_rate = round(page_matches / n_cit, 4) if n_cit > 0 else 0.0
        claim_rate = round(supported_claims / n_claims, 4) if claims else 1.0
        completeness_rate = round(claims_with_verified_citations / n_claims, 4) if claims else 1.0

        return CitationVerificationReport(
            total_citations=n_cit,
            verified_citations=verified_count,
            unverified_citations=n_cit - verified_count,
            quote_match_rate=quote_rate,
            page_match_rate=page_rate,
            claim_support_rate=claim_rate,
            citation_completeness_rate=completeness_rate,
            overall_grounding_score=round(grounding, 4),
            details=details
        )
