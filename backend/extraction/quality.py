"""Extraction Quality Assessment Service

Detects:
- Empty documents
- Corrupted files
- Unusually sparse extraction (e.g. scanned image PDFs missing OCR)
- Missing or blank pages
- Potentially incorrect reading order

Produces structured warnings recorded in the database and surfaced via API.
"""

from typing import List, Dict, Any
from backend.extraction.base import ExtractedDocument
from backend.config import config

def assess_extraction_quality(doc: ExtractedDocument) -> List[str]:
    warnings: List[str] = []

    # 1. Detect completely empty documents
    total_chars = len(doc.full_text.strip())
    if len(doc.blocks) == 0 or total_chars == 0:
        warnings.append("EMPTY_DOCUMENT: No readable text was extracted from this file.")
        return warnings

    # 2. Detect unusually sparse extraction
    if total_chars < config.min_doc_char_count:
        warnings.append(
            f"SPARSE_EXTRACTION: Document contains only {total_chars} character(s). Possible scanned image without OCR or placeholder content."
        )

    # Multi-page sparsity and blank page detection
    if doc.total_pages > 1:
        chars_per_page: Dict[int, int] = {p: 0 for p in range(1, doc.total_pages + 1)}
        for b in doc.blocks:
            chars_per_page[b.page] = chars_per_page.get(b.page, 0) + len(b.text.strip())

        blank_pages = [p for p, c in chars_per_page.items() if c == 0]
        if blank_pages:
            warnings.append(
                f"BLANK_PAGES: Missing or empty content on page(s): {', '.join(str(p) for p in blank_pages)}."
            )

        avg_chars = total_chars / doc.total_pages
        if avg_chars < config.sparse_page_char_threshold:
            warnings.append(
                f"SPARSE_PAGES: Average characters per page is only {avg_chars:.1f} (threshold: {config.sparse_page_char_threshold}). Verify if PDF is scanned."
            )

    # 3. Detect potentially incorrect reading order (PDFs with bounding boxes)
    pages_with_order_issues = set()
    blocks_by_page: Dict[int, list] = {}
    for b in doc.blocks:
        blocks_by_page.setdefault(b.page, []).append(b)

    for page_num, page_blocks in blocks_by_page.items():
        if len(page_blocks) < 3:
            continue
        
        # Check consecutive blocks with bounding boxes
        for i in range(len(page_blocks) - 1):
            curr_b = page_blocks[i]
            next_b = page_blocks[i + 1]
            if curr_b.bbox and next_b.bbox:
                # If next block is significantly above current block (by more than 150 points)
                # and both blocks span similar horizontal coordinates (not clean separate columns)
                if next_b.bbox.y0 < (curr_b.bbox.y0 - 150):
                    # Check if horizontal spans overlap substantially
                    x_overlap = max(0.0, min(curr_b.bbox.x1, next_b.bbox.x1) - max(curr_b.bbox.x0, next_b.bbox.x0))
                    if x_overlap > 50:
                        pages_with_order_issues.add(page_num)
                        break

    if pages_with_order_issues:
        sorted_pages = sorted(list(pages_with_order_issues))
        warnings.append(
            f"POTENTIAL_READING_ORDER_ANOMALY: Non-sequential block coordinate jumps detected on page(s): {', '.join(str(p) for p in sorted_pages)}."
        )

    return warnings
