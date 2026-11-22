"""Tests for Contradiction Detection, Explicit Supersession, and Regional Carve-outs (Phase 4.1)"""

import pytest
from backend.citations.contradictions import ContradictionDetector, ContradictionType, ConflictSource
from backend.evidence.selector import SelectedEvidence

def test_explicit_supersession_detection():
    """Verify detection of explicit 'superseded' clauses with baseline and conflicting sources."""
    detector = ContradictionDetector()
    
    base_item = SelectedEvidence(
        chunk_id="c_edge_tls",
        document_id="doc_tech_v1",
        page_number=3,
        section_title="Network Edge",
        text="Inbound gateway edge connections accept TLS 1.2 and TLS 1.3 protocol handshakes."
    )
    superseding_item = SelectedEvidence(
        chunk_id="c_sec_addendum",
        document_id="doc_tech_v2",
        page_number=8,
        section_title="2026 Security Hardening Addendum",
        text="Effective January 1, 2026, Section 1.2 is superseded: TLS 1.2 ciphers are disabled on all external load balancers; only TLS 1.3 is permitted."
    )
    
    report = detector.analyze([base_item, superseding_item])
    assert report.has_conflicts is True
    assert len(report.conflicts) >= 1
    
    conflict = report.conflicts[0]
    assert conflict.conflict_type in (ContradictionType.EXPLICIT_SUPERSEDING, ContradictionType.REGIONAL_STATUTORY_EXCEPTION)
    assert conflict.conflicting_source is not None
    assert conflict.conflicting_source.is_superseding is True
    assert "superseded" in conflict.description.lower() or "addendum" in conflict.description.lower()

def test_regional_statutory_carveout_detection():
    """Verify detection of statutory/regional carve-outs using 'notwithstanding' or 'statutory addendum'."""
    detector = ContradictionDetector()
    
    general_policy = SelectedEvidence(
        chunk_id="c_vac_gen",
        document_id="doc_hr",
        page_number=4,
        section_title="Annual Leave",
        text="Employees may roll over a maximum of 5 unused PTO days into the following calendar year. Any excess days are forfeited on Dec 31."
    )
    regional_addendum = SelectedEvidence(
        chunk_id="c_vac_stat",
        document_id="doc_hr",
        page_number=10,
        section_title="Statutory Addendum",
        text="Notwithstanding Section 4.1, for employees residing in California and the European Union, accrued unused vacation does not expire and rolls over in full."
    )
    
    report = detector.analyze([general_policy, regional_addendum])
    assert report.has_conflicts is True
    assert report.guidance_for_prompt is not None
    assert "conflicting" in report.guidance_for_prompt.lower() or "superseding" in report.guidance_for_prompt.lower()

def test_multiple_competing_version_detection():
    """Verify detection of incompatible version identifiers across different documents."""
    detector = ContradictionDetector()
    
    item_v1 = SelectedEvidence(
        chunk_id="c_v1",
        document_id="doc_api_old",
        page_number=1,
        text="The platform implements core protocol version 2.1 across all microservices."
    )
    item_v2 = SelectedEvidence(
        chunk_id="c_v2",
        document_id="doc_api_new",
        page_number=1,
        text="The platform deprecates legacy protocols and enforces core protocol version 3.4."
    )
    
    report = detector.analyze([item_v1, item_v2])
    assert report.has_conflicts is True
    v_conflicts = [c for c in report.conflicts if c.conflict_type == ContradictionType.GENUINE_CONTRADICTION]
    assert len(v_conflicts) >= 1
    assert "2.1" in v_conflicts[0].description
    assert "3.4" in v_conflicts[0].description
