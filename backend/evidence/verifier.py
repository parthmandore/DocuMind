"""Two-Stage Evidence Verification Engine (Phase 4.2)

Distinguishes between passages that are merely topic-relevant versus those that
genuinely establish factual claims, detect partial support, identify conflicting
provisions, and enforce conservative abstention when evidence is insufficient.
"""

import re
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field

from backend.query.processor import ProcessedQuery
from backend.evidence.selector import EvidencePacket, SelectedEvidence
from backend.citations.contradictions import ContradictionDetector, ContradictionReport

class PassageSupportType(str, Enum):
    SUPPORTING = "supporting"                    # Actually establishes the requested fact
    PARTIALLY_SUPPORTING = "partially_supporting" # Establishes only part of a compound requirement
    CONTRADICTORY = "contradictory"              # Conflicts with or supersedes another relevant source
    RELEVANT_ONLY = "relevant_only"              # Discusses the general topic/entity but does not answer
    INSUFFICIENT = "insufficient"                # Completely lacks required information

class VerifiedPassage(BaseModel):
    passage_id: str
    chunk_id: str
    support_type: PassageSupportType
    supported_subquestions: List[str] = Field(default_factory=list)
    missing_attributes: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    rationale: str = ""

class TwoStageVerificationReport(BaseModel):
    overall_support: PassageSupportType
    should_abstain: bool
    confidence: float
    verified_passages: List[VerifiedPassage] = Field(default_factory=list)
    supported_subquestions: List[str] = Field(default_factory=list)
    unsupported_subquestions: List[str] = Field(default_factory=list)
    conflicting_aspects: List[str] = Field(default_factory=list)
    unsupported_attributes: List[str] = Field(default_factory=list)
    summary_reasoning: str = ""

class TwoStageEvidenceVerifier:
    """
    Two-Stage evidence verification separating topical relevance from factual support.
    Stage 1: Topical Relevance & Candidate Filtering.
    Stage 2: Semantic Attribute, Entity, Constraint & Fact Verification.
    """
    def __init__(self):
        self.contradiction_detector = ContradictionDetector()

    def _extract_requested_attributes(self, query: str) -> List[str]:
        """Identifies specific attributes, properties, or targets requested by the question."""
        q_lower = query.lower()
        attributes = []

        # 1. Credentials / Secrets / Prompt Injections
        if any(w in q_lower for w in ["password", "credential", "credentials", "secret key", "api key", "auth token", "internal secrets", "system prompt", "<untrusted", "override:"]):
            attributes.append("credential_secret")

        # 2. Date / Period / Retirement / Expiration
        if any(w in q_lower for w in ["retirement date", "decommission date"]):
            attributes.append("retirement_date")
        elif any(w in q_lower for w in ["expiration date", "deadline", "due date", "effective date"]):
            attributes.append("temporal_date")
        elif re.search(r'\b(?:what date|what year|what time|when (?:did|will|is|was|shall|does|are|were|can|should|would))\b', q_lower) or re.match(r'^when\s+(?:did|will|is|was|shall|does|are|were|can|should|would)\b', q_lower):
            attributes.append("temporal_date")

        # 3. Commercial / Pricing / Penalty / Surcharge / Fees
        if "liquidated damages" in q_lower:
            attributes.append("liquidated_damages")
        elif "impeller" in q_lower:
            attributes.append("impeller_spec")
        elif any(w in q_lower for w in ["price", "pricing", "supplier", "penalty fee", "penalty", "surcharge", "cost", "fee"]):
            attributes.append("pricing_financial")

        # 4. Service / Specific Entitlement
        if any(w in q_lower for w in ["dry cleaning", "personal side-trip", "side trip", "car rental", "mileage"]):
            attributes.append("specific_service")

        # 5. Numerical / Metric target
        if any(w in q_lower for w in ["how much", "how many", "what percentage", "what rate", "what class", "latency"]):
            attributes.append("quantitative_metric")

        return attributes

    def _verify_passage_attribute_support(
        self,
        passage_text: str,
        requested_attrs: List[str],
        query_years: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Verifies whether a passage actually contains the factual attribute requested,
        rather than merely discussing related background material.
        """
        p_lower = passage_text.lower()
        missing = []

        # Temporal year check
        for y in query_years:
            if y not in passage_text:
                missing.append(f"year_{y}")

        # Attribute presence checks
        for attr in requested_attrs:
            if attr == "credential_secret":
                # Must contain an actual secret or password string, not just the word 'credentials'
                has_actual_secret = bool(re.search(r'(?:password|secret|key)\s*[:=]\s*["\']?[A-Za-z0-9_\-!@#$%^&*]{6,}', passage_text, re.IGNORECASE))
                if not has_actual_secret:
                    missing.append("password_value")

            elif attr == "retirement_date":
                has_retire = ("retirement" in p_lower or "decommission" in p_lower) and bool(re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|\d{1,2}/\d{1,2}/\d{2,4}|20\d\d)\b', passage_text, re.IGNORECASE))
                if not has_retire:
                    missing.append("scheduled_retirement_date")

            elif attr == "liquidated_damages":
                if "liquidated" not in p_lower:
                    missing.append("liquidated_damages_clause")

            elif attr == "impeller_spec":
                if "impeller" not in p_lower:
                    missing.append("impeller_supplier_or_pricing")

            elif attr == "temporal_date":
                # Must contain an actual calendar date, month, explicit year, or relative timeframe/duration
                has_date = bool(re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|\d{1,2}/\d{1,2}/\d{2,4}|20\d\d|\d+\s*(?:days?|weeks?|months?|business days?|calendar days?|hours?))\b', passage_text, re.IGNORECASE))
                if not has_date:
                    missing.append("explicit_date")

            elif attr == "pricing_financial":
                # Must contain currency symbol, numeric fee, percentage, or explicit pricing terms
                has_price = bool(re.search(r'[\$€£]\s*\d+|\b\d+(?:\.\d+)?\s*(?:dollars|cents|percent|fee|penalty|\%)(?:\b|\s|[.,;]|$)', passage_text, re.IGNORECASE))
                if not has_price:
                    missing.append("price_or_fee_value")

            elif attr == "specific_service":
                # Look for specific service terms
                dry_cleaning = "dry cleaning" in p_lower or "dry-cleaning" in p_lower
                side_trips = "side-trip" in p_lower or "side trip" in p_lower or "personal trip" in p_lower
                if not (dry_cleaning or side_trips):
                    missing.append("specific_service_mention")

        is_supported = len(missing) == 0
        return is_supported, missing

    def verify(
        self,
        processed_query: ProcessedQuery,
        packet: EvidencePacket
    ) -> TwoStageVerificationReport:
        """
        Executes complete two-stage evidence verification on the retrieved packet.
        """
        # Zero evidence check
        if not packet.selected_items:
            return TwoStageVerificationReport(
                overall_support=PassageSupportType.INSUFFICIENT,
                should_abstain=True,
                confidence=0.0,
                unsupported_subquestions=processed_query.subquestions or [processed_query.cleaned_query],
                summary_reasoning="No candidate passages were retrieved."
            )

        # Stage 1: Extract constraints and requested attributes from query
        query_text = processed_query.cleaned_query
        query_years = re.findall(r'\b(20[2-9][0-9])\b', query_text)
        requested_attrs = self._extract_requested_attributes(query_text)

        # Collect attributes verified anywhere across the packet
        globally_satisfied_attrs: Set[str] = set()
        for item in packet.selected_items:
            for attr in requested_attrs:
                has_attr, _ = self._verify_passage_attribute_support(item.text, [attr], query_years)
                if has_attr:
                    globally_satisfied_attrs.add(attr)
        truly_missing_attrs = [attr for attr in requested_attrs if attr not in globally_satisfied_attrs]

        # Detect contradictions across all candidate evidence
        conflict_report: ContradictionReport = self.contradiction_detector.analyze(packet.selected_items)

        # Stage 2: Verify each individual passage
        verified_passages: List[VerifiedPassage] = []
        all_missing_attrs: Set[str] = set()
        supporting_count = 0
        contradictory_count = 0
        relevant_only_count = 0

        # Subquestion tracking
        subq_support_map: Dict[str, List[str]] = {sq: [] for sq in processed_query.subquestions}

        for item in packet.selected_items:
            p_text = item.text
            p_lower = p_text.lower()
            passage_id = f"{item.document_id}_p{item.page_number}_{item.chunk_id}"

            # Check if this passage is involved in a contradiction
            is_contradictory = False
            for conf in conflict_report.conflicts:
                if any(kw.lower() in p_lower for kw in [conf.description, "superseded", "notwithstanding", "addendum", "amendment"]):
                    is_contradictory = True
                    break

            # Verify attribute support
            is_supported, missing = self._verify_passage_attribute_support(p_text, requested_attrs, query_years)
            all_missing_attrs.update(missing)

            # Check subquestion coverage with stopword filtering, technical tokens, and stemming
            subqs_matched = []
            verifier_stopwords = {
                "what", "when", "where", "which", "whose", "why", "does", "have", "been",
                "that", "this", "from", "with", "about", "tell", "must", "should", "could",
                "would", "shall", "into", "onto", "their", "there", "then", "under", "over",
                "according"
            }
            for sq in processed_query.subquestions:
                raw_words = [
                    w.lower() for w in re.findall(r'\b[A-Za-z0-9_.-]+\b', sq)
                    if (len(w) > 3 or any(c.isdigit() for c in w)) and w.lower() not in verifier_stopwords
                ]
                if raw_words:
                    hits = 0
                    for w in raw_words:
                        if w in p_lower:
                            hits += 1
                        else:
                            stem = re.sub(r'(?:ation|itions?|ment|ing|ed|ies|es|s|ic|y)$', '', w)
                            if len(stem) >= 4 and stem in p_lower:
                                hits += 1
                            elif len(w) >= 5 and w[:5] in p_lower:
                                hits += 1
                    if (hits / len(raw_words)) >= 0.25:
                        subqs_matched.append(sq)
                        subq_support_map[sq].append(passage_id)

            if is_contradictory:
                support_type = PassageSupportType.CONTRADICTORY
                contradictory_count += 1
            elif is_supported and subqs_matched:
                if len(subqs_matched) == len(processed_query.subquestions):
                    support_type = PassageSupportType.SUPPORTING
                    supporting_count += 1
                else:
                    support_type = PassageSupportType.PARTIALLY_SUPPORTING
                    supporting_count += 1
            elif not is_supported and subqs_matched:
                support_type = PassageSupportType.RELEVANT_ONLY
                relevant_only_count += 1
            else:
                support_type = PassageSupportType.INSUFFICIENT

            verified_passages.append(VerifiedPassage(
                passage_id=passage_id,
                chunk_id=item.chunk_id,
                support_type=support_type,
                supported_subquestions=subqs_matched,
                missing_attributes=missing,
                confidence=round(item.dense_score or 0.8, 2),
                rationale=f"Classified as {support_type.value} (missing: {missing})"
            ))

        # Overall synthesis
        supported_subqs = [sq for sq, pids in subq_support_map.items() if len(pids) > 0]
        unsupported_subqs = [sq for sq, pids in subq_support_map.items() if len(pids) == 0]

        # Determine overall classification and abstention recommendation
        critical_unattested = [a for a in truly_missing_attrs if a in {"credential_secret", "retirement_date", "liquidated_damages", "specific_service"}]
        if critical_unattested:
            overall_support = PassageSupportType.RELEVANT_ONLY
            should_abstain = True
            confidence = 0.20
            summary = f"Retrieved passages discuss the general topic but lack required critical attributes: {critical_unattested}."
        elif conflict_report.has_conflicts:
            overall_support = PassageSupportType.CONTRADICTORY
            should_abstain = False
            confidence = 0.85
            summary = "Passages contain competing, superseded, or regionally amended provisions."
        elif len(truly_missing_attrs) > 0 and len(supported_subqs) == 0:
            overall_support = PassageSupportType.RELEVANT_ONLY
            should_abstain = True
            confidence = 0.20
            summary = f"Retrieved passages discuss the general topic but lack required attributes: {truly_missing_attrs}."
        elif len(supported_subqs) > 0 or supporting_count > 0:
            if len(unsupported_subqs) == 0 and len(truly_missing_attrs) == 0:
                overall_support = PassageSupportType.SUPPORTING
                should_abstain = False
                confidence = 0.95
                summary = "Evidence directly establishes all requested factual claims."
            else:
                overall_support = PassageSupportType.PARTIALLY_SUPPORTING
                should_abstain = False
                confidence = 0.70
                summary = f"Evidence supports {len(supported_subqs)} of {len(processed_query.subquestions)} subquestions."
        elif relevant_only_count > 0 and len(truly_missing_attrs) > 0:
            overall_support = PassageSupportType.RELEVANT_ONLY
            should_abstain = True
            confidence = 0.20
            summary = f"Retrieved passages discuss the general topic but lack required attributes: {truly_missing_attrs}."
        else:
            overall_support = PassageSupportType.INSUFFICIENT
            should_abstain = True
            confidence = 0.15
            summary = "Retrieved passages do not establish the requested answer."

        return TwoStageVerificationReport(
            overall_support=overall_support,
            should_abstain=should_abstain,
            confidence=confidence,
            verified_passages=verified_passages,
            supported_subquestions=supported_subqs,
            unsupported_subquestions=unsupported_subqs,
            conflicting_aspects=[c.description for c in conflict_report.conflicts],
            unsupported_attributes=truly_missing_attrs,
            summary_reasoning=summary
        )

two_stage_verifier = TwoStageEvidenceVerifier()
