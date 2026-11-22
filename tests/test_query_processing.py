"""Tests for Query Processing, Technical Term Preservation, and Validation (Phase 4 Stage 2)"""

import pytest
from backend.query.processor import QueryProcessor

def test_query_validation():
    """Verify empty and excessively long questions are rejected."""
    qp = QueryProcessor(max_length=200)

    # Empty / whitespace rejection
    with pytest.raises(ValueError, match="Question cannot be empty"):
        qp.validate("")
    with pytest.raises(ValueError, match="Question cannot be empty"):
        qp.validate("    \n\t  ")

    # Max length rejection
    with pytest.raises(ValueError, match="Question exceeds maximum length"):
        qp.validate("a" * 250)

    # Valid query cleaning
    cleaned = qp.validate("  What is   the operating   pressure?  ")
    assert cleaned == "What is the operating pressure?"

def test_preserve_technical_terms():
    """Verify that technical terms, protocols, and versions are preserved accurately."""
    qp = QueryProcessor()
    q = "What is the status of RS-485 communication with IP-67 enclosure in API v2.1?"
    proc = qp.process(q)

    assert "RS-485" in proc.technical_terms
    assert "IP-67" in proc.technical_terms
    assert "API" in proc.technical_terms
    assert "v2.1" in proc.technical_terms

def test_numerical_and_unit_extraction():
    """Verify extraction of numerical values, units, and qualifiers."""
    qp = QueryProcessor()
    q = "What is the maximum operating pressure of 0.75 MPa at 1200 RPM?"
    proc = qp.process(q)

    assert len(proc.numerical_constraints) == 2
    c1 = proc.numerical_constraints[0]
    assert c1.value == 0.75
    assert c1.unit == "MPa"
    assert c1.qualifier in ("maximum", "operating")

    c2 = proc.numerical_constraints[1]
    assert c2.value == 1200.0
    assert c2.unit == "RPM"

def test_compound_question_decomposition():
    """Verify that multi-part compound questions are split into discrete subquestions."""
    qp = QueryProcessor()
    q = "What was the total operating income and corresponding operating margin percentage?"
    proc = qp.process(q)

    assert proc.is_compound is True
    assert len(proc.subquestions) == 2
    assert "operating income" in proc.subquestions[0].lower()
    assert "operating margin" in proc.subquestions[1].lower()
