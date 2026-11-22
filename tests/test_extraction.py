"""Tests for Document Extraction Engine (PDF, DOCX, TXT, Markdown)"""

import os
from backend.extraction.router import extract_document
from backend.extraction.pdf_parser import PyMuPDFParser
from backend.extraction.docx_parser import DocxParser
from backend.extraction.text_parser import TextMarkdownParser

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
PDF_DIR = os.path.join(FIXTURES_DIR, "pdfs")

def test_extract_pdf_single_column():
    """Extract single-column PDF and verify page numbers and bounding boxes."""
    pdf_path = os.path.join(PDF_DIR, "single_column_report.pdf")
    assert os.path.exists(pdf_path), "PDF fixture missing"
    
    doc = extract_document(pdf_path)
    assert doc.total_pages >= 1
    assert len(doc.blocks) > 0
    assert "DocuMind" in doc.full_text or "Executive" in doc.full_text
    
    # Verify page numbers and bounding boxes
    for block in doc.blocks:
        assert block.page >= 1
        assert block.bbox is not None
        assert block.bbox.x1 > block.bbox.x0
        assert block.bbox.y1 > block.bbox.y0

def test_extract_pdf_tables():
    """Extract table-dense PDF and verify table structure preservation."""
    pdf_path = os.path.join(PDF_DIR, "table_dense_spec.pdf")
    doc = extract_document(pdf_path)
    
    assert len(doc.tables) >= 1
    table = doc.tables[0]
    assert len(table.headers) > 0
    assert len(table.rows) > 0
    assert table.page >= 1
    assert table.bbox is not None

def test_extract_docx():
    """Extract DOCX and verify headings, paragraphs, and tables."""
    docx_path = os.path.join(FIXTURES_DIR, "sample.docx")
    doc = extract_document(docx_path)
    
    assert doc.total_pages == 1
    assert len(doc.blocks) > 0
    assert "DocuMind System Guide" in doc.full_text
    assert "8.7 tokens per second" in doc.full_text
    
    # Headings verification
    heading_blocks = [b for b in doc.blocks if b.block_type == "heading"]
    assert len(heading_blocks) >= 2
    
    # Table verification
    assert len(doc.tables) >= 1
    table = doc.tables[0]
    assert "Parameter" in table.headers or "Parameter" in [cell for row in table.rows for cell in row]

def test_extract_txt():
    """Extract TXT document and verify paragraph separation."""
    txt_path = os.path.join(FIXTURES_DIR, "sample.txt")
    doc = extract_document(txt_path)
    
    assert doc.total_pages == 1
    assert len(doc.blocks) >= 2
    assert "Section 1: General Overview" in doc.full_text
    assert "PyMuPDF" in doc.full_text

def test_extract_markdown():
    """Extract Markdown document and verify heading levels and table."""
    md_path = os.path.join(FIXTURES_DIR, "sample.md")
    doc = extract_document(md_path)
    
    assert doc.total_pages == 1
    assert "enterprise document intelligence" in doc.full_text
    
    # Check sections
    sec_titles = [s.title for s in doc.sections]
    assert any("Security" in t for t in sec_titles)
    assert any("Storage" in t for t in sec_titles)

    # Check table
    assert len(doc.tables) >= 1
    tab = doc.tables[0]
    assert "Component" in tab.headers
