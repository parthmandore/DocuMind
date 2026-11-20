"""Citations Package"""

from backend.citations.validator import CitationValidator, ValidationStatus
from backend.citations.numerical import (
    extract_numerical_facts,
    verify_numerical_facts,
    NumericalFact
)
from backend.citations.contradictions import (
    ContradictionDetector,
    ContradictionReport,
    ConflictItem,
    ContradictionType
)
from backend.citations.verifier import (
    ComprehensiveCitationVerifier,
    CitationVerificationReport
)

__all__ = [
    "CitationValidator",
    "ValidationStatus",
    "extract_numerical_facts",
    "verify_numerical_facts",
    "NumericalFact",
    "ContradictionDetector",
    "ContradictionReport",
    "ConflictItem",
    "ContradictionType",
    "ComprehensiveCitationVerifier",
    "CitationVerificationReport"
]
