"""Contradiction and Supersession Detection Module

Identifies conflicting factual claims, superseded technical standards,
and cross-document discrepancies across retrieved evidence.
"""

import re
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.evidence.selector import SelectedEvidence

class ContradictionType(str, Enum):
    EXPLICIT_SUPERSEDING = "explicit_superseding"
    DOCUMENT_AMENDMENT = "document_amendment"
    HISTORICAL_VS_CURRENT = "historical_vs_current"
    REGIONAL_STATUTORY_EXCEPTION = "regional_statutory_exception"
    DIFFERENT_SCOPES = "different_scopes"
    GENUINE_CONTRADICTION = "genuine_contradiction"

class ConflictSource(BaseModel):
    document_id: str
    document_title: str = ""
    section: str = ""
    page: int = 1
    source_date: Optional[str] = None
    version_info: Optional[str] = None
    exact_passage: str = ""
    is_superseding: bool = False
    supersession_indicator: Optional[str] = None

class ConflictItem(BaseModel):
    conflict_type: ContradictionType
    description: str
    source_chunks: List[str] = Field(default_factory=list)
    source_documents: List[str] = Field(default_factory=list)
    competing_statements: List[str] = Field(default_factory=list)
    baseline_source: Optional[ConflictSource] = None
    conflicting_source: Optional[ConflictSource] = None
    resolution_hint: Optional[str] = None

class ContradictionReport(BaseModel):
    has_conflicts: bool = False
    conflicts: List[ConflictItem] = Field(default_factory=list)
    guidance_for_prompt: str = ""

class ContradictionDetector:
    """
    Detects contradictory evidence, amendments, and version deprecations across chunks.
    """
    def __init__(self):
        self.supersession_patterns = [
            (re.compile(r'\b(?:supersedes?|superseded(?:\s+by)?|is\s+superseded)\b', re.IGNORECASE), "Superseded specification"),
            (re.compile(r'\b(?:replaced(?:\s+by)?|replaces|is\s+replaced)\b', re.IGNORECASE), "Replaced standard"),
            (re.compile(r'\b(?:deprecated(?:\s+in\s+favor\s+of)?|is\s+deprecated)\b', re.IGNORECASE), "Deprecated component"),
            (re.compile(r'\b(?:amends?|amended(?:\s+by)?|is\s+amended)\b', re.IGNORECASE), "Amended policy"),
            (re.compile(r'\b(?:effective\s+[A-Za-z]+\s+\d{4},\s*(?:replacing|overriding))\b', re.IGNORECASE), "Effective date override"),
            (re.compile(r'\b(?:notwithstanding\s+(?:section\s+)?([A-Za-z0-9_.-]+)?)\b', re.IGNORECASE), "Statutory override / Notwithstanding clause"),
            (re.compile(r'\b(?:except\s+as\s+(?:otherwise\s+)?provided\s*(?:in\s+([A-Za-z0-9_.-]+))?)\b', re.IGNORECASE), "Carve-out / Exception clause"),
            (re.compile(r'\b(?:addendum|exhibit\s+[A-Z])\b', re.IGNORECASE), "Specialized Addendum / Exhibit exception")
        ]

    def analyze(self, evidence_items: List[SelectedEvidence]) -> ContradictionReport:
        if len(evidence_items) < 2:
            return ContradictionReport()

        conflicts: List[ConflictItem] = []

        # 1. Check for explicit supersession keywords
        for idx, item in enumerate(evidence_items):
            for pattern, desc in self.supersession_patterns:
                match = pattern.search(item.text)
                if match:
                    other_chunks = [other.chunk_id for other in evidence_items if other.chunk_id != item.chunk_id]
                    other_docs = list({other.document_filename for other in evidence_items})
                    
                    target = match.group(0)
                    other_item = next((it for it in evidence_items if it.chunk_id != item.chunk_id), None)
                    
                    c_type = ContradictionType.EXPLICIT_SUPERSEDING
                    res_hint = "The superseding provision takes precedence. State both the baseline rule and the superseding requirement."
                    if "notwithstanding" in target.lower() or "california" in item.text.lower() or "european union" in item.text.lower():
                        c_type = ContradictionType.REGIONAL_STATUTORY_EXCEPTION
                        res_hint = "State the baseline rule as well as the regional or statutory exception (e.g. California or EU)."
                    elif "addendum" in target.lower() or "amend" in target.lower():
                        c_type = ContradictionType.DOCUMENT_AMENDMENT
                        res_hint = "State the original agreement provision and the modifying addendum or exhibit."
                    elif "except" in target.lower() or "carve-out" in target.lower():
                        c_type = ContradictionType.DIFFERENT_SCOPES
                        res_hint = "These clauses apply to different scopes (e.g. general liability vs indemnification). Cite both."

                    conf_source = ConflictSource(
                        document_id=item.document_id,
                        document_title=item.document_filename,
                        section=item.section_title,
                        page=item.page_number,
                        exact_passage=item.text[:250],
                        is_superseding=True,
                        supersession_indicator=target
                    )
                    base_source = ConflictSource(
                        document_id=other_item.document_id,
                        document_title=other_item.document_filename,
                        section=other_item.section_title,
                        page=other_item.page_number,
                        exact_passage=other_item.text[:250],
                        is_superseding=False
                    ) if other_item else None

                    conflicts.append(ConflictItem(
                        conflict_type=c_type,
                        description=f"{desc}: '{target}' detected in {item.document_filename} (p. {item.page_number}).",
                        source_chunks=[item.chunk_id] + ([other_item.chunk_id] if other_item else []),
                        source_documents=other_docs,
                        competing_statements=[item.text[:200]] + ([other_item.text[:200]] if other_item else []),
                        baseline_source=base_source,
                        conflicting_source=conf_source,
                        resolution_hint=res_hint
                    ))

        # 2. Check for conflicting version numbers across different documents
        version_pattern = re.compile(r'\b(?:v|version|ver\.?)\s*(\d+(?:\.\d+)+)\b', re.IGNORECASE)
        doc_versions: Dict[str, List[str]] = {}
        for item in evidence_items:
            v_matches = version_pattern.findall(item.text)
            if v_matches:
                doc_versions.setdefault(item.document_id, []).extend(v_matches)

        if len(doc_versions) > 1:
            all_versions = set()
            for v_list in doc_versions.values():
                all_versions.update(v_list)
            if len(all_versions) > 1:
                conflicts.append(ConflictItem(
                    conflict_type=ContradictionType.GENUINE_CONTRADICTION,
                    description=f"Multiple competing versions {list(all_versions)} referenced across documents.",
                    source_chunks=[it.chunk_id for it in evidence_items],
                    source_documents=list(doc_versions.keys()),
                    resolution_hint="State the conflicting versions explicitly; do not guess which one is authoritative."
                ))

        if not conflicts:
            return ContradictionReport(has_conflicts=False)

        # Build prompt guidance for the LLM
        guidance_lines = ["\nEVIDENCE CONTRADICTION NOTICE:"]
        for c in conflicts:
            guidance_lines.append(f"- {c.description}")
            if c.resolution_hint:
                guidance_lines.append(f"  Note: {c.resolution_hint}")
        guidance_lines.append("Instructions: State any conflicting provisions explicitly. Do not invent a resolution.\n")

        return ContradictionReport(
            has_conflicts=True,
            conflicts=conflicts,
            guidance_for_prompt="\n".join(guidance_lines)
        )
