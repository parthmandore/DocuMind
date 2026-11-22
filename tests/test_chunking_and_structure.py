"""Tests for Structure-Aware Chunking, Section ID Inheritance, and Table Preservation"""

import pytest
from backend.extraction.base import ExtractedDocument, ExtractedBlock, BoundingBox
from backend.chunking.layout_chunker import LayoutAwareChunker

def test_section_id_inheritance_across_multiple_chunks():
    """Verify that multiple chunks belonging to the same section retain that section identity."""
    # Create blocks belonging to sec_0
    blocks = [
        ExtractedBlock(
            block_id="b1", page=1, text="Section 1: Enterprise Architecture",
            block_type="heading", section_id="sec_0"
        ),
        ExtractedBlock(
            block_id="b2", page=1,
            text="This is paragraph one of section one with substantial architectural explanation " * 8,
            block_type="text", section_id="sec_0"
        ),
        ExtractedBlock(
            block_id="b3", page=1,
            text="This is paragraph two of section one also containing important design constraints " * 8,
            block_type="text", section_id="sec_0"
        ),
        ExtractedBlock(
            block_id="b4", page=2, text="Section 2: Database Layer",
            block_type="heading", section_id="sec_1"
        ),
        ExtractedBlock(
            block_id="b5", page=2,
            text="Database layer utilizes SQLite and PostgreSQL with strict cascade constraints.",
            block_type="text", section_id="sec_1"
        )
    ]
    doc = ExtractedDocument(doc_id="test_doc", source_path="dummy.pdf", total_pages=2, blocks=blocks)

    chunker = LayoutAwareChunker(target_words_per_chunk=50, overlap_words=0)
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 3
    # Check that chunks derived from Section 1 have section_id == "sec_0"
    sec_0_chunks = [c for c in chunks if c.section_id == "sec_0"]
    assert len(sec_0_chunks) >= 2
    for c in sec_0_chunks:
        assert c.section_id == "sec_0"

    # Check that chunks derived from Section 2 have section_id == "sec_1"
    sec_1_chunks = [c for c in chunks if c.section_id == "sec_1"]
    assert len(sec_1_chunks) >= 1
    assert sec_1_chunks[0].section_id == "sec_1"

def test_chunk_without_section_has_none():
    """Blocks without an identifiable section must produce chunks with section_id = None."""
    blocks = [
        ExtractedBlock(
            block_id="b1", page=1, text="Unassociated text block without any section header.",
            block_type="text", section_id=None
        )
    ]
    doc = ExtractedDocument(doc_id="no_sec_doc", source_path="dummy.txt", total_pages=1, blocks=blocks)
    chunker = LayoutAwareChunker()
    chunks = chunker.chunk(doc)

    assert len(chunks) == 1
    assert chunks[0].section_id is None

def test_table_preservation_and_header_replication():
    """Verify that tables are kept intact or split with headers replicated."""
    header = "Parameter | Type | Specification | Tolerance"
    rows = [f"Item_{i} | Sensor | 1200 RPM | +-0.5%" for i in range(1, 30)]
    full_table_text = header + "\n" + "\n".join(rows)

    table_block = ExtractedBlock(
        block_id="tbl_1", page=1, text=full_table_text,
        block_type="table", section_id="sec_tables", table_id="tab_01"
    )
    doc = ExtractedDocument(doc_id="table_doc", source_path="dummy.pdf", total_pages=1, blocks=[table_block])

    chunker = LayoutAwareChunker(target_words_per_chunk=30, overlap_words=0)
    chunks = chunker.chunk(doc)

    assert len(chunks) > 1
    # Every fragment must preserve table_id and include the header
    for c in chunks:
        assert c.table_id == "tab_01"
        assert c.section_id == "sec_tables"
        assert "Parameter | Type | Specification | Tolerance" in c.text
        assert c.metadata.get("is_table") is True
