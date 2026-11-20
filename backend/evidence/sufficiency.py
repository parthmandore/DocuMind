"""Evidence Sufficiency and Abstention Assessment Module

Evaluates whether retrieved evidence provides genuine, sufficient grounding to
answer the user's question, distinguishing between direct support, partial support,
insufficient context, conflicts, and total absence.
"""

import re
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.query.processor import ProcessedQuery
from backend.evidence.selector import EvidencePacket, SelectedEvidence

class SufficiencyStatus(str, Enum):
    DIRECTLY_SUPPORTED = "directly_supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    NO_RELEVANT_EVIDENCE = "no_relevant_evidence"

class SufficiencyAssessment(BaseModel):
    status: SufficiencyStatus
    should_abstain: bool
    confidence_score: float = 0.0  # 0.0 to 1.0
    supported_subquestions: List[str] = Field(default_factory=list)
    unsupported_subquestions: List[str] = Field(default_factory=list)
    detected_conflicts: List[str] = Field(default_factory=list)
    reasoning: str = ""

class EvidenceSufficiencyEngine:
    """
    Evaluates grounding sufficiency before dispatching to generation.
    """
    def __init__(
        self,
        min_dense_threshold: float = 0.50,
        min_term_coverage: float = 0.25
    ):
        self.min_dense_threshold = min_dense_threshold
        self.min_term_coverage = min_term_coverage

    def _assess_subquestion_coverage(self, subq: str, evidence_texts: List[str]) -> bool:
        """Determines if the critical content terms of a subquestion appear in evidence."""
        combined_text = " ".join(evidence_texts).lower()
        # Extract meaningful words (length > 3, excluding question and auxiliary words)
        stopwords = {
            "what", "when", "where", "which", "whose", "why", "does", "have", "been",
            "that", "this", "from", "with", "about", "tell", "must", "should", "could",
            "would", "shall", "into", "onto", "their", "there", "then", "under", "over"
        }
        words = [w.lower() for w in re.findall(r'\b[A-Za-z0-9_.-]+\b', subq) if len(w) > 3 and w.lower() not in stopwords]
        if not words:
            return True

        matches = 0
        for w in words:
            if w in combined_text:
                matches += 1
            else:
                # Root / stem matching (e.g. notification -> notif, specific -> specif)
                stem = re.sub(r'(?:ation|itions?|ment|ing|ed|ies|es|s|ic|y)$', '', w)
                if len(stem) >= 4 and stem in combined_text:
                    matches += 1
                elif len(w) >= 5 and w[:5] in combined_text:
                    matches += 1

        return (matches / len(words)) >= self.min_term_coverage

    def _detect_contradictions_in_evidence(self, items: List[SelectedEvidence]) -> List[str]:
        """Detects explicit supersession, conflicting versions, or amendment clauses."""
        conflicts = []
        texts = [item.text for item in items]
        combined = " ".join(texts)

        supersession_keywords = [
            r'supersedes\b',
            r'replaced by\b',
            r'deprecated\b',
            r'amended by\b',
            r'overrides\b',
            r'prior version\b',
            r'conflicting provisions\b'
        ]
        for kw in supersession_keywords:
            if re.search(kw, combined, re.IGNORECASE):
                conflicts.append(f"Detected explicit supersession or revision indicator matching '{kw}'.")

        return conflicts

    def assess(
        self,
        processed_query: ProcessedQuery,
        packet: EvidencePacket
    ) -> SufficiencyAssessment:
        """
        Assesses sufficiency of evidence packet against the processed query.
        """
        # 1. Zero evidence case
        if not packet.selected_items:
            return SufficiencyAssessment(
                status=SufficiencyStatus.NO_RELEVANT_EVIDENCE,
                should_abstain=True,
                confidence_score=0.0,
                unsupported_subquestions=processed_query.subquestions,
                reasoning="No relevant document passages were retrieved matching the query."
            )

        evidence_texts = [item.text for item in packet.selected_items]
        combined_evidence = " ".join(evidence_texts).lower()

        # 2. Check technical terms and numerical entities in query
        missing_technical_terms = []
        for term in processed_query.technical_terms:
            if term.lower() not in combined_evidence:
                missing_technical_terms.append(term)

        # 3. Check specific year or numerical query targets
        # e.g., if query asks for 2028 and only 2025/2026 are present
        years_in_query = re.findall(r'\b(20[2-9][0-9])\b', processed_query.cleaned_query)
        missing_years = [y for y in years_in_query if y not in combined_evidence]

        # 4. Security, Prompt Injection & Credential Defense Analysis
        from backend.evidence.security import security_analyzer
        sec_res = security_analyzer.analyze(processed_query.original_query)
        if sec_res.is_injection_or_secret_probe:
            return SufficiencyAssessment(
                status=SufficiencyStatus.INSUFFICIENT_EVIDENCE,
                should_abstain=True,
                confidence_score=0.1,
                unsupported_subquestions=[processed_query.cleaned_query],
                reasoning=f"Credentials or secrets are explicitly not disclosed in the documentation, or prompt injection was detected: {sec_res.reasoning}"
            )

        top_item = packet.selected_items[0]
        top_dense = top_item.dense_score if top_item.dense_score is not None else 0.8
        top_lex = top_item.lexical_score if top_item.lexical_score is not None else 0.0

        # Unanswerable triggers
        if missing_years:
            return SufficiencyAssessment(
                status=SufficiencyStatus.INSUFFICIENT_EVIDENCE,
                should_abstain=True,
                confidence_score=0.2,
                unsupported_subquestions=[processed_query.cleaned_query],
                reasoning=f"The query requests data for specific period(s) {missing_years} which are absent from retrieved context."
            )

        if top_dense < self.min_dense_threshold and top_lex == 0:
            return SufficiencyAssessment(
                status=SufficiencyStatus.INSUFFICIENT_EVIDENCE,
                should_abstain=True,
                confidence_score=0.3,
                unsupported_subquestions=[processed_query.cleaned_query],
                reasoning=f"Top candidate similarity ({top_dense:.3f}) falls below minimum relevance floor."
            )

        # 5. Check for conflicts
        conflicts = self._detect_contradictions_in_evidence(packet.selected_items)
        if conflicts:
            return SufficiencyAssessment(
                status=SufficiencyStatus.CONFLICTING_EVIDENCE,
                should_abstain=False,
                confidence_score=0.75,
                detected_conflicts=conflicts,
                supported_subquestions=processed_query.subquestions,
                reasoning="Evidence contains competing, superseded, or conflicting document statements."
            )

        # 6. Two-stage semantic and attribute verification
        from backend.evidence.verifier import two_stage_verifier, PassageSupportType
        v_report = two_stage_verifier.verify(processed_query, packet)
        if v_report.should_abstain:
            return SufficiencyAssessment(
                status=SufficiencyStatus.INSUFFICIENT_EVIDENCE,
                should_abstain=True,
                confidence_score=v_report.confidence,
                unsupported_subquestions=v_report.unsupported_subquestions or [processed_query.cleaned_query],
                reasoning=v_report.summary_reasoning
            )

        # 7. Compound subquestion coverage
        supported = []
        unsupported = []
        for subq in processed_query.subquestions:
            if self._assess_subquestion_coverage(subq, evidence_texts):
                supported.append(subq)
            else:
                unsupported.append(subq)

        if unsupported and supported:
            return SufficiencyAssessment(
                status=SufficiencyStatus.PARTIALLY_SUPPORTED,
                should_abstain=False,
                confidence_score=0.6,
                supported_subquestions=supported,
                unsupported_subquestions=unsupported,
                reasoning="Only part of the compound question is answerable from the retrieved evidence."
            )

        if unsupported and not supported:
            return SufficiencyAssessment(
                status=SufficiencyStatus.INSUFFICIENT_EVIDENCE,
                should_abstain=True,
                confidence_score=0.25,
                unsupported_subquestions=unsupported,
                reasoning="Retrieved passages do not contain sufficient facts to answer the question."
            )

        # Fully supported
        return SufficiencyAssessment(
            status=SufficiencyStatus.DIRECTLY_SUPPORTED,
            should_abstain=False,
            confidence_score=round(min(1.0, top_dense + (0.1 if top_lex > 0 else 0.0)), 2),
            supported_subquestions=supported,
            reasoning="Evidence contains direct factual grounding for all question components."
        )
