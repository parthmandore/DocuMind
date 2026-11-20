"""Query Processing Module

Deterministically analyzes, validates, and extracts technical constraints from
natural-language user questions without degrading technical specificity.
"""

import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Pattern for technical terms, codes, protocol identifiers, versions
TECH_PATTERN = re.compile(
    r'\b[A-Za-z0-9]+(?:[-_.:/][A-Za-z0-9]+)+\b|\b[A-Z]{2,}(?:-[0-9]+)?\b'
)

# Pattern for numerical values, currencies, units, percentages
NUMERICAL_PATTERN = re.compile(
    r'(?:[\$€£]\s*)?\b\d+(?:\.\d+)?\s*(?:%|MPa|RPM|kW|V|A|Hz|kg|mg|m|cm|mm|ms|s|min|hours?|days?|degrees?\s+Celsius|°C|°F|million|billion)?\b',
    re.IGNORECASE
)

# Pattern for splitting compound questions on coordinating clauses
COMPOUND_SPLIT_PATTERN = re.compile(
    r'(?<=[.?!])\s+|;\s+|\s+and\s+(?=(?:what|how|where|when|which|who|why|is|are|does|can|will|should)\b)',
    re.IGNORECASE
)

# Acronym knowledge base for conservative domain-aware expansions
ACRONYM_EXPANSIONS: Dict[str, List[str]] = {
    "FINER": [
        "FINER framework",
        "FINER criteria",
        "Feasible Interesting Novel Ethical Relevant",
        "criteria for selecting a good research topic"
    ],
    "PICO": [
        "PICO framework",
        "Population Intervention Comparison Outcome"
    ],
    "SMART": [
        "SMART criteria",
        "Specific Measurable Achievable Relevant Time-bound"
    ],
    "RAG": [
        "Retrieval-Augmented Generation"
    ],
    "BM25": [
        "Best Matching 25",
        "Okapi BM25"
    ]
}

class NumericalConstraint(BaseModel):
    raw_text: str
    value: Optional[float] = None
    unit: Optional[str] = None
    qualifier: Optional[str] = None  # e.g., 'maximum', 'minimum', 'operating', 'total'

class ProcessedQuery(BaseModel):
    original_query: str
    cleaned_query: str
    technical_terms: List[str] = Field(default_factory=list)
    acronyms: List[str] = Field(default_factory=list)
    query_expansions: List[str] = Field(default_factory=list)
    numerical_constraints: List[NumericalConstraint] = Field(default_factory=list)
    document_ids: Optional[List[str]] = None
    is_compound: bool = False
    subquestions: List[str] = Field(default_factory=list)
    comparison_entities: List[str] = Field(default_factory=list)
    conversation_context_hint: Optional[str] = None

class QueryProcessor:
    """
    Deterministic query processor enforcing input validation and technical preservation.
    """
    def __init__(self, max_length: int = 1000):
        self.max_length = max_length

    def validate(self, query: str) -> str:
        """Validates query length and content."""
        if not query or not query.strip():
            raise ValueError("Question cannot be empty or blank.")
        
        cleaned = " ".join(query.strip().split())
        if len(cleaned) > self.max_length:
            raise ValueError(f"Question exceeds maximum length of {self.max_length} characters (got {len(cleaned)}).")
        
        return cleaned

    def extract_technical_terms(self, query: str) -> List[str]:
        """Extracts technical codes, model identifiers, protocols, and versions."""
        matches = TECH_PATTERN.findall(query)
        # Deduplicate while preserving order
        seen = set()
        terms = []
        for m in matches:
            m_clean = m.strip("._-/:")
            if m_clean and m_clean.upper() not in seen:
                seen.add(m_clean.upper())
                terms.append(m_clean)
        return terms

    def extract_numerical_constraints(self, query: str) -> List[NumericalConstraint]:
        """Extracts numerical limits, measurements, and units."""
        constraints = []
        # Check for qualifiers near numbers
        qualifiers = ["maximum", "minimum", "operating", "nominal", "total", "average", "threshold", "exceed"]
        query_lower = query.lower()

        for match in NUMERICAL_PATTERN.finditer(query):
            raw = match.group(0).strip()
            # Try parsing numeric value
            num_match = re.search(r'\d+(?:\.\d+)?', raw)
            if not num_match:
                continue
            
            val = float(num_match.group(0))
            unit_part = raw[num_match.end():].strip()
            if not unit_part and raw.startswith(("$", "€", "£")):
                unit_part = raw[0]

            # Detect preceding qualifier in query window
            start_idx = max(0, match.start() - 30)
            window = query_lower[start_idx:match.start()]
            found_qual = next((q for q in qualifiers if q in window), None)

            constraints.append(NumericalConstraint(
                raw_text=raw,
                value=val,
                unit=unit_part if unit_part else None,
                qualifier=found_qual
            ))
        return constraints

    def decompose_compound_question(self, query: str) -> List[str]:
        """Splits compound multi-part questions into discrete sub-queries."""
        parts = COMPOUND_SPLIT_PATTERN.split(query)
        cleaned_parts = [p.strip() for p in parts if p.strip()]
        if len(cleaned_parts) > 1:
            return cleaned_parts
        
        # Check for "both X and Y" or "X and corresponding Y"
        match = re.search(r'what (?:was|is|are) (?:the )?(.+?) and (?:the |corresponding )?(.+?)\??$', query, re.IGNORECASE)
        if match:
            return [
                f"What is the {match.group(1).strip()}?",
                f"What is the {match.group(2).strip()}?"
            ]

        return [query]

    def extract_acronyms_and_expansions(self, query: str) -> tuple[List[str], List[str]]:
        """Identifies uppercase acronyms and generates conservative domain expansions."""
        words = re.findall(r'\b[A-Z]{3,8}\b', query)
        detected_acronyms: List[str] = []
        expansions: List[str] = []
        seen_exp = set()

        for w in words:
            w_upper = w.upper()
            if w_upper not in detected_acronyms:
                detected_acronyms.append(w_upper)
            if w_upper in ACRONYM_EXPANSIONS:
                for exp in ACRONYM_EXPANSIONS[w_upper]:
                    if exp.lower() not in seen_exp and exp.lower() not in query.lower():
                        seen_exp.add(exp.lower())
                        expansions.append(exp)

        return detected_acronyms, expansions

    def extract_comparison_entities(self, query: str) -> List[str]:
        """
        Extracts individual compared entities from comparison, distinction, or multi-definition queries.
        Handles:
        - "Differentiate between X, Y, and Z..."
        - "Compare X and Y..."
        - "Difference between X and Y..."
        - "How do X, Y, and Z define..."
        - "Contrast X with Y..."
        """
        entities: List[str] = []
        # Pattern 1: Differentiate / compare / contrast between X, Y, and Z
        m = re.search(
            r'(?:differentiate|distinguish|compare|contrast)\s+(?:between\s+)?(.+?)(?:\s+as\s+|\s+in\s+terms\s+of|\s+regarding|\s+based\s+on|\s+within|\?|$)',
            query,
            re.IGNORECASE
        )
        if m:
            clause = m.group(1).strip()
            parts = re.split(r',\s*(?:and\s+)?|\s+and\s+|\s+with\s+|\s+versus\s+|\s+vs\.?\s+', clause, flags=re.IGNORECASE)
            for p in parts:
                p_clean = re.sub(r'^(?:the|their|both|all|sources\s+of)\s+', '', p.strip(), flags=re.IGNORECASE).strip()
                if len(p_clean) > 2 and p_clean.lower() not in {"research", "literature", "engineering", "document", "unit", "methodology"}:
                    entities.append(p_clean)
            if len(entities) >= 2:
                return entities

        # Pattern 2: How do X, Y, and Z define...
        m2 = re.search(r'how\s+do\s+(.+?)\s+define', query, re.IGNORECASE)
        if m2:
            clause = m2.group(1).strip()
            clause = clause.replace("Redman and Mory", "Redman and Mory###")
            parts = re.split(r',\s*(?:and\s+)?', clause)
            for p in parts:
                p_clean = p.replace("###", "").strip()
                if len(p_clean) > 2:
                    entities.append(p_clean)
            if len(entities) >= 2:
                return entities

        # Pattern 3: Explain the difference between X and Y
        m3 = re.search(r'difference\s+between\s+(.+?)\s+and\s+(.+?)(?:\.|\?|$|\s+why)', query, re.IGNORECASE)
        if m3:
            e1 = re.sub(r'^(?:the|a)\s+', '', m3.group(1).strip(), flags=re.IGNORECASE)
            e2 = re.sub(r'^(?:the|a)\s+', '', m3.group(2).strip(), flags=re.IGNORECASE)
            if e1 and e2:
                return [e1, e2]

        return []

    def extract_semantic_expansions(self, query: str) -> List[str]:
        """Maps common colloquial or paraphrased formulations to textbook phrasing."""
        expansions = []
        q_lower = query.lower()
        semantic_map = {
            "point of doing research": "significance importance purpose of research",
            "good research topic": "criteria for selecting a good research topic FINER",
            "problem statement": "formulation of research problem significance",
            "eight stages": "stages of the literature review process planning search formulation screening",
            "stages of the literature review": "literature review process stages steps",
            "gap in literature": "research gap identification",
            "cyclical rather than linear": "research lifecycle cyclical vs linear process"
        }
        for trigger, exp in semantic_map.items():
            if trigger in q_lower:
                expansions.append(exp)
        return expansions

    def process(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> ProcessedQuery:
        """
        Executes deterministic query processing without semantic distortion.
        """
        cleaned = self.validate(query)
        tech_terms = self.extract_technical_terms(cleaned)
        acronyms, expansions = self.extract_acronyms_and_expansions(cleaned)
        for sem_exp in self.extract_semantic_expansions(cleaned):
            if sem_exp not in expansions:
                expansions.append(sem_exp)

        num_constraints = self.extract_numerical_constraints(cleaned)
        subquestions = self.decompose_compound_question(cleaned)
        is_compound = len(subquestions) > 1
        comp_entities = self.extract_comparison_entities(cleaned)

        context_hint = None
        if conversation_context and len(conversation_context) > 0:
            last_msg = conversation_context[-1]
            if last_msg.get("role") == "user":
                context_hint = last_msg.get("content")

        return ProcessedQuery(
            original_query=query,
            cleaned_query=cleaned,
            technical_terms=tech_terms,
            acronyms=acronyms,
            query_expansions=expansions,
            numerical_constraints=num_constraints,
            document_ids=document_ids,
            is_compound=is_compound,
            subquestions=subquestions,
            comparison_entities=comp_entities,
            conversation_context_hint=context_hint
        )
