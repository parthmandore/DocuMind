"""Evidence Completeness Validation Module

Analyzes user questions to determine required entities, list items, comparison dimensions,
and verifies whether retrieved evidence contains sufficient coverage for each component.
Enforces adaptive response directives without hallucinating missing items.
"""

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.evidence.selector import SelectedEvidence

class RequiredComponent(BaseModel):
    name: str
    status: str = "COVERED"  # COVERED, PARTIALLY_COVERED, NOT_FOUND, AMBIGUOUS
    matched_passage_ids: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class CompletenessAssessment(BaseModel):
    is_structured_request: bool = False
    request_type: str = "general"  # "list", "comparison", "framework", "general"
    requested_count: Optional[int] = None
    target_entities: List[str] = Field(default_factory=list)
    components: List[RequiredComponent] = Field(default_factory=list)
    all_covered: bool = True
    guidance_prompt: str = ""
    coverage_ratio: float = 1.0

# Canonical framework components
KNOWN_FRAMEWORKS: Dict[str, List[str]] = {
    "FINER": [
        "Feasible (adequate subjects, technical expertise, affordable, manageable in scope)",
        "Interesting (gets researcher curiosity and attention)",
        "Novel (confirms, refutes, or extends previous findings; provides new insights)",
        "Ethical (approved by review boards, minimizes harm, respects privacy)",
        "Relevant (advances scientific knowledge, guides future research or policy)"
    ],
    "PICO": [
        "Population / Patient / Problem",
        "Intervention",
        "Comparison / Control",
        "Outcome"
    ]
}

# Number words mapping
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

class EvidenceCompletenessValidator:
    """
    Validates completeness of retrieved evidence against explicit question requirements.
    """

    def analyze(
        self,
        query: str,
        evidence_items: List[SelectedEvidence]
    ) -> CompletenessAssessment:
        q_lower = query.lower()
        combined_evidence = " \n ".join([item.text for item in evidence_items]).lower()

        # 1. Framework check (e.g., FINER)
        for fw_key, fw_components in KNOWN_FRAMEWORKS.items():
            if re.search(r'\b' + re.escape(fw_key.lower()) + r'\b', q_lower):
                components: List[RequiredComponent] = []
                for comp in fw_components:
                    comp_key = comp.split()[0].lower()
                    found_passages = [
                        f"P{idx+1}" for idx, item in enumerate(evidence_items)
                        if comp_key in item.text.lower()
                    ]
                    status = "COVERED" if found_passages else "NOT_FOUND"
                    components.append(RequiredComponent(
                        name=comp,
                        status=status,
                        matched_passage_ids=found_passages
                    ))

                all_covered = all(c.status == "COVERED" for c in components)
                ratio = sum(1 for c in components if c.status == "COVERED") / max(1, len(components))
                guidance = (
                    f"COMPLETENESS DIRECTIVE (Framework: {fw_key}):\n"
                    f"Synthesize each of the {len(components)} criteria: {', '.join([c.name.split()[0] for c in components])}.\n"
                    f"Explain each criterion clearly and cite the relevant passages."
                )
                return CompletenessAssessment(
                    is_structured_request=True,
                    request_type="framework",
                    target_entities=[fw_key],
                    components=components,
                    all_covered=all_covered,
                    guidance_prompt=guidance,
                    coverage_ratio=round(ratio, 2)
                )

        # 2. Comparison check (e.g., "differentiate between patents, standards, and technical reports")
        comp_match = re.search(
            r'(?:compare|differentiate between|distinguish between|difference between)\s+([^?]+)',
            query,
            re.IGNORECASE
        )
        if comp_match:
            raw_entities = comp_match.group(1).strip()
            # Split by commas and "and" / "as well as"
            parts = re.split(r',|\band\b|\bas well as\b', raw_entities, flags=re.IGNORECASE)
            entities = [p.strip().rstrip(".:;?") for p in parts if len(p.strip()) > 2]
            # Filter noise words
            clean_entities = [e for e in entities if e.lower() not in {"sources", "literature", "engineering", "research", "sources of"}]

            if len(clean_entities) >= 2:
                components = []
                for ent in clean_entities:
                    ent_kw = ent.split()[-1].lower() if len(ent.split()) > 1 else ent.lower()
                    found_passages = [
                        f"P{idx+1}" for idx, item in enumerate(evidence_items)
                        if ent_kw in item.text.lower()
                    ]
                    status = "COVERED" if found_passages else "NOT_FOUND"
                    components.append(RequiredComponent(
                        name=ent,
                        status=status,
                        matched_passage_ids=found_passages
                    ))

                all_covered = all(c.status == "COVERED" for c in components)
                ratio = sum(1 for c in components if c.status == "COVERED") / max(1, len(components))
                guidance = (
                    f"COMPLETENESS DIRECTIVE (Comparison):\n"
                    f"Differentiate the following entities clearly: {', '.join(clean_entities)}.\n"
                    f"Address their primary nature/purpose, key characteristics, and research value based on the provided excerpts.\n"
                    f"If useful, organize the comparison using a clear Markdown table or structured sections with [P#] citations."
                )
                return CompletenessAssessment(
                    is_structured_request=True,
                    request_type="comparison",
                    target_entities=clean_entities,
                    components=components,
                    all_covered=all_covered,
                    guidance_prompt=guidance,
                    coverage_ratio=round(ratio, 2)
                )

        # 3. Explicit count check (e.g., "five major types of research", "four objectives", "eight stages")
        count_match = re.search(
            r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+([a-zA-Z\s_-]+?\b(?:types|kinds|categories|objectives|stages|phases|steps|methods|criteria|principles|dimensions))\b',
            q_lower
        )
        if count_match:
            raw_num = count_match.group(1)
            target_concept = count_match.group(2).strip()
            num_val = int(raw_num) if raw_num.isdigit() else NUMBER_WORDS.get(raw_num, 0)

            guidance = (
                f"COMPLETENESS DIRECTIVE (List: {num_val} {target_concept}):\n"
                f"Identify and enumerate all {num_val} {target_concept} discussed in the excerpts.\n"
                f"For each item, clearly state its definition/purpose and typical outputs or characteristics.\n"
                f"If the text only contains details for a subset, explicitly explain which are documented and which are missing."
            )
            return CompletenessAssessment(
                is_structured_request=True,
                request_type="list",
                requested_count=num_val,
                target_entities=[target_concept],
                components=[],
                all_covered=True,
                guidance_prompt=guidance,
                coverage_ratio=1.0
            )

        return CompletenessAssessment()
