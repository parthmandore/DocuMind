"""Numerical and Technical Fact Verification Module

Extracts, validates, and cross-references exact numerical entities, measurements,
units, and technical qualifiers between generated answers and source documents.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel

class NumericalFact(BaseModel):
    raw_text: str
    value: float
    unit: Optional[str] = None
    qualifier: Optional[str] = None
    is_verified: bool = False
    evidence_source: Optional[str] = None

# Comprehensive pattern capturing numbers, decimals, scale words, and units
FACT_REGEX = re.compile(
    r'(?:[\$€£]\s*)?\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:million|billion|trillion|[MKG]B|megabytes|gigabytes|kilobytes|[MK]b|M\b|%|MPa|RPM|Nm|mm/s|RMS|kW|V|A|Hz|kHz|MHz|GHz|ohms?|kbps|Mbps|Gbps|kg|mg|g|cm|mm|ms|seconds?|mins?|minutes?|hours?|calendar\s+days|days?|weeks?|months?|years?|degrees?\s+Celsius|°C|°F|\bs\b)?\b',
    re.IGNORECASE
)

def are_units_compatible(u1: Optional[str], u2: Optional[str]) -> bool:
    """Checks whether two unit representations are equivalent (e.g. million vs M, s vs seconds)."""
    if not u1 or not u2:
        return True
    u1_low = u1.lower().strip()
    u2_low = u2.lower().strip()
    if u1_low == u2_low:
        return True
    compatible_sets = [
        {"m", "million"},
        {"b", "billion"},
        {"k", "thousand"},
        {"s", "seconds"},
        {"s", "second"},
        {"sec", "second"},
        {"sec", "seconds"},
        {"min", "minute"},
        {"min", "minutes"},
        {"hr", "hour"},
        {"hr", "hours"},
        {"hrs", "hours"},
        {"day", "days"},
        {"calendar days", "days"}
    ]
    return {u1_low, u2_low} in compatible_sets

def extract_numerical_facts(text: str) -> List[NumericalFact]:
    """Extracts all numeric measurements, percentages, currencies, and technical values."""
    facts: List[NumericalFact] = []
    if not text:
        return facts

    # Qualifiers that might precede a number
    qualifiers = ["maximum", "minimum", "operating", "nominal", "total", "average", "exceeding", "up to", "at least", "approximately"]
    text_lower = text.lower()

    for match in FACT_REGEX.finditer(text):
        raw = match.group(0).strip()
        # Extract numeric core
        num_str = re.sub(r'[^\d.]', '', raw.replace(',', ''))
        if not num_str:
            continue
        try:
            val = float(num_str)
        except ValueError:
            continue

        unit = None
        # Extract scale / unit
        unit_match = re.search(r'(million|billion|trillion|[MKG]B|megabytes|gigabytes|kilobytes|[MK]b|M\b|%|MPa|RPM|Nm|mm/s|RMS|kW|V|A|Hz|kHz|MHz|GHz|ohms?|kbps|Mbps|Gbps|kg|mg|g|cm|mm|ms|seconds?|\bs\b|mins?|minutes?|hours?|calendar\s+days|days?|weeks?|months?|years?|degrees?\s+Celsius|°C|°F)', raw, re.IGNORECASE)
        if unit_match:
            unit = unit_match.group(0).strip()
        elif raw.startswith(("$", "€", "£")):
            unit = raw[0]

        # Check for scale multiplier
        if "million" in raw.lower() and val < 1000:
            # Keep value as float but note unit
            pass

        # Look for qualifier in 25-character window preceding match
        start_idx = max(0, match.start() - 25)
        window = text_lower[start_idx:match.start()]
        qual = next((q for q in qualifiers if q in window), None)

        facts.append(NumericalFact(
            raw_text=raw,
            value=val,
            unit=unit,
            qualifier=qual
        ))

    return facts

def verify_numerical_facts(
    answer: str,
    evidence_texts: List[str]
) -> Tuple[bool, List[NumericalFact]]:
    """
    Cross-checks every numerical entity in the answer against source passages.
    Returns (all_verified: bool, facts: List[NumericalFact]).
    """
    answer_facts = extract_numerical_facts(answer)
    if not answer_facts:
        return True, []

    combined_evidence = " ".join(evidence_texts)
    evidence_facts = extract_numerical_facts(combined_evidence)
    evidence_values = [f.value for f in evidence_facts]
    evidence_text_lower = combined_evidence.lower()

    all_verified = True
    verified_facts: List[NumericalFact] = []

    for af in answer_facts:
        # Check 1: Exact raw text match in evidence (e.g. "$84.6 million" or "0.75 MPa")
        raw_clean = af.raw_text.lower()
        if raw_clean in evidence_text_lower:
            af.is_verified = True
            af.evidence_source = "exact_text_match"
            verified_facts.append(af)
            continue

        # Check 2: Numeric value match with compatible unit
        matched = False
        for ef in evidence_facts:
            # Check numeric equivalence within floating point tolerance
            if abs(af.value - ef.value) < 1e-4:
                # Check unit consistency
                if are_units_compatible(af.unit, ef.unit):
                    af.is_verified = True
                    af.evidence_source = f"value_match_{ef.raw_text}"
                    matched = True
                    break
        
        if not matched:
            af.is_verified = False
            all_verified = False

        verified_facts.append(af)

    return all_verified, verified_facts
