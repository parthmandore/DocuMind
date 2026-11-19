"""Unified Document Extraction Router

Routes incoming files to the appropriate format parser (PDF, DOCX, TXT, MD),
runs quality checks, and returns a verified ExtractedDocument.
"""

import os
from typing import Optional
from backend.extraction.base import ExtractedDocument
from backend.extraction.pdf_parser import PyMuPDFParser
from backend.extraction.docx_parser import DocxParser
from backend.extraction.text_parser import TextMarkdownParser
from backend.extraction.quality import assess_extraction_quality

def extract_document(file_path: str) -> ExtractedDocument:
    """
    Extracts structured content from a document file based on extension.
    Runs extraction quality assessment and attaches quality warnings.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        parser = PyMuPDFParser(sort_blocks=True)
    elif ext == ".docx":
        parser = DocxParser()
    elif ext in (".txt", ".md", ".markdown"):
        parser = TextMarkdownParser()
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    doc = parser.parse(file_path)
    
    # Assess extraction quality
    warnings = assess_extraction_quality(doc)
    doc.quality_warnings.extend(warnings)

    return doc
