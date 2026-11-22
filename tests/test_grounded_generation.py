"""Tests for Evidence Sufficiency, Numerical Verification, Contradictions, and Citations (Phase 4)"""

import pytest
from sqlalchemy.orm import Session
from backend.evidence.sufficiency import EvidenceSufficiencyEngine, SufficiencyStatus
from backend.evidence.selector import EvidencePacket, SelectedEvidence
from backend.query.processor import QueryProcessor
from backend.citations.numerical import extract_numerical_facts, verify_numerical_facts
from backend.citations.contradictions import ContradictionDetector, ContradictionType
from backend.citations.verifier import ComprehensiveCitationVerifier
from backend.generation.schemas import CitationItem, SupportingClaim
from backend.db.models import Document, DocumentChunk, DocumentStatus

def test_evidence_sufficiency_abstention():
    """Verify that absent facts trigger explicit abstention."""
    engine = EvidenceSufficiencyEngine()
    qp = QueryProcessor()

    # Query asks for year 2028, but evidence only covers 2025/2026
    proc_q = qp.process("What is the forecasted parcel delivery volume for the full year 2028?")
    item = SelectedEvidence(
        chunk_id="c_guidance",
        document_id="doc_fin",
        page_number=39,
        text="Forward-looking guidance is provided exclusively through fiscal year 2026 with 8% to 11% growth.",
        token_count=15,
        dense_score=0.82
    )
    packet = EvidencePacket(query=proc_q.cleaned_query, selected_items=[item])

    assessment = engine.assess(proc_q, packet)
    assert assessment.should_abstain is True
    assert assessment.status == SufficiencyStatus.INSUFFICIENT_EVIDENCE
    assert "2028" in assessment.reasoning

def test_evidence_sufficiency_credential_refusal():
    """Verify that queries requesting internal credentials or passwords trigger abstention."""
    engine = EvidenceSufficiencyEngine()
    qp = QueryProcessor()

    proc_q = qp.process("What is the internal administrative password for Redis cache?")
    item = SelectedEvidence(
        chunk_id="c_redis",
        document_id="doc_tech",
        page_number=7,
        text="Session persistence uses Redis. Credentials must be retrieved dynamically via AWS Secrets Manager.",
        token_count=16,
        dense_score=0.79
    )
    packet = EvidencePacket(query=proc_q.cleaned_query, selected_items=[item])

    assessment = engine.assess(proc_q, packet)
    assert assessment.should_abstain is True
    assert "Credentials or secrets are explicitly not disclosed" in assessment.reasoning

def test_numerical_fact_verification():
    """Verify detection of true vs fabricated/altered numerical entities."""
    source_texts = [
        "Maximum operating hydraulic pressure: 0.75 MPa at 1200 RPM with total expenditure of $32.4 million."
    ]

    # Valid answer
    valid_answer = "The maximum operating pressure is 0.75 MPa at 1200 RPM and capital expenditure is $32.4 million."
    ok, facts = verify_numerical_facts(valid_answer, source_texts)
    assert ok is True
    assert all(f.is_verified for f in facts)

    # Hallucinated / altered values (0.57 MPa instead of 0.75 MPa)
    altered_answer = "The maximum operating pressure is 0.57 MPa at 1500 RPM."
    ok_alt, facts_alt = verify_numerical_facts(altered_answer, source_texts)
    assert ok_alt is False
    assert any(not f.is_verified for f in facts_alt)

def test_contradiction_detection():
    """Verify identification of explicit superseding clauses across evidence."""
    detector = ContradictionDetector()
    items = [
        SelectedEvidence(
            chunk_id="c1",
            document_id="doc_a",
            document_filename="legacy_spec.pdf",
            page_number=3,
            text="Communication protocol version 1.2 is approved for industrial fieldbus transceivers.",
            token_count=12
        ),
        SelectedEvidence(
            chunk_id="c2",
            document_id="doc_b",
            document_filename="modern_spec.pdf",
            page_number=1,
            text="Notice: Protocol version 1.2 was deprecated in favor of version 1.4 for all new deployments.",
            token_count=15
        )
    ]

    report = detector.analyze(items)
    assert report.has_conflicts is True
    assert len(report.conflicts) >= 1
    assert "deprecated" in report.conflicts[0].description.lower()
    assert "EVIDENCE CONTRADICTION NOTICE" in report.guidance_for_prompt

def test_comprehensive_citation_verifier(db_session: Session):
    """Verify 6-point verification of citations against database records."""
    doc = Document(
        id="doc_verif_test",
        title="Test Grounding Document",
        filename="grounding.pdf",
        storage_path="mock/path.pdf",
        mime_type="application/pdf",
        file_size_bytes=500,
        file_hash="hash_verif_1",
        status=DocumentStatus.COMPLETED.value
    )
    db_session.add(doc)
    db_session.commit()

    chunk = DocumentChunk(
        id="chk_verif_1",
        document_id=doc.id,
        chunk_index=0,
        page_number=4,
        text="The flagship European automated sorting hub is situated in Rotterdam, Netherlands.",
        token_count=12,
        bboxes=[{"page": 4, "x0": 10, "y0": 20, "x1": 300, "y1": 50}]
    )
    db_session.add(chunk)
    db_session.commit()

    verifier = ComprehensiveCitationVerifier(db=db_session)

    # 1. Perfectly verified citation
    good_cit = CitationItem(
        citation_id="cit_good",
        document_id=doc.id,
        document_filename=doc.filename,
        chunk_id=chunk.id,
        page_number=4,
        exact_quote="flagship European automated sorting hub is situated in Rotterdam",
        bounding_boxes=[]
    )
    claim = SupportingClaim(
        claim_id="clm_1",
        claim_text="The automated sorting hub is in Rotterdam, Netherlands.",
        supporting_chunk_ids=[chunk.id],
        citation_ids=[good_cit.citation_id]
    )

    report = verifier.verify_all([good_cit], [claim])
    assert report.verified_citations == 1
    assert report.unverified_citations == 0
    assert report.quote_match_rate == 1.0
    assert report.page_match_rate == 1.0
    assert report.claim_support_rate == 1.0
    assert report.overall_grounding_score == 1.0
    assert good_cit.verification_status == "verified"

    # 2. Page mismatch citation
    bad_page_cit = CitationItem(
        citation_id="cit_bad_page",
        document_id=doc.id,
        document_filename=doc.filename,
        chunk_id=chunk.id,
        page_number=99,  # Wrong page
        exact_quote="flagship European automated sorting hub is situated in Rotterdam"
    )
    res_page = verifier.verify_citation(bad_page_cit)
    assert res_page["status"] == "page_mismatch"
    assert res_page["page_matched"] is False

    # 3. Non-existent source document
    missing_doc_cit = CitationItem(
        citation_id="cit_missing_doc",
        document_id="non_existent_doc_id",
        document_filename="ghost.pdf",
        chunk_id=chunk.id,
        page_number=4,
        exact_quote="sample quote"
    )
    res_missing = verifier.verify_citation(missing_doc_cit)
    assert res_missing["status"] == "source_missing"
    assert res_missing["document_exists"] is False
