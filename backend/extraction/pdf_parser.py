"""PyMuPDF Document Parser Implementation

Extracts structured blocks, line-level bounding boxes, page metadata,
headings, sections, and tabular structures using PyMuPDF (fitz).
Preserves original page numbers, coordinates, reading order, rotation,
and explicit section identity while avoiding redundant page parses and
false-positive neural/layout table scans.
"""

import os
import re
import pymupdf
from typing import List, Dict, Any, Optional, Tuple
from backend.extraction.base import (
    DocumentParser,
    ExtractedDocument,
    ExtractedBlock,
    ExtractedSection,
    ExtractedTable,
    BoundingBox
)
from backend.cleaning.cleaner import clean_text

_TOC_LINE_RE = re.compile(r"\.{3,}\s*\d*\s*$")
_NUM_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?(?=[ \t]+[A-Za-z]|[A-Z])")
_ALNUM_CODE_RE = re.compile(r"^[A-Z0-9_-]+$")
_BORDERLESS_CAPTION_RE = re.compile(
    r"(?im)^(?:table|tab\.|schedule)\s+[a-z0-9]+|^(?:balance\s+sheet|income\s+statement|summary\s+of\s+costs)\b"
)
_NUM_TOKEN_RE = re.compile(r"([$€£¥]?\d+[\.,]?\d*%?)")
_MULTI_SPACE_SPLIT_RE = re.compile(r"\S\s{2,}\S")


def _analyze_page_drawings(
    page_rect: pymupdf.Rect,
    drawings: List[Dict[str, Any]]
) -> Tuple[int, int, Optional[pymupdf.Rect]]:
    """
    Analyzes vector paths on a PDF page to count table grid lines ('l') and
    cell-sized rectangles ('re'), excluding full-page backdrops and slide canvases.
    Returns (line_count, rect_count, union_clip_rect).
    """
    line_count = 0
    rect_count = 0
    table_rects: List[pymupdf.Rect] = []
    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")

    pw = page_rect.width
    ph = page_rect.height

    for d in drawings:
        r = d.get("rect")
        if not r:
            continue
        # Exclude full-page backdrop rectangles and canvas borders
        if r.width >= 0.90 * pw and r.height >= 0.90 * ph:
            continue

        is_candidate = False
        for item in d.get("items", []):
            kind = item[0]
            if kind == "l":
                line_count += 1
                is_candidate = True
            elif kind == "re":
                if r.height < 0.40 * ph:
                    rect_count += 1
                    is_candidate = True

        if is_candidate:
            table_rects.append(r)
            if r.x0 < min_x:
                min_x = r.x0
            if r.y0 < min_y:
                min_y = r.y0
            if r.x1 > max_x:
                max_x = r.x1
            if r.y1 > max_y:
                max_y = r.y1

    if not table_rects:
        return line_count, rect_count, None

    clip = pymupdf.Rect(
        max(0.0, min_x - 3.0),
        max(0.0, min_y - 3.0),
        min(pw, max_x + 3.0),
        min(ph, max_y + 3.0),
    )
    return line_count, rect_count, clip


def _has_borderless_table_signal(
    text: str,
    raw_blocks: Optional[List[Any]] = None
) -> bool:
    """
    Detects genuine borderless tabular columns while ignoring Table of Contents
    dot-leader lines and ordinary numbered bullet prose.
    """
    if not text:
        return False

    non_toc_lines = []
    for raw_line in text.split("\n"):
        s = raw_line.strip()
        if not s:
            continue
        # Skip TOC dot-leader entries (never borderless data tables)
        if "...." in s or _TOC_LINE_RE.search(s):
            continue
        non_toc_lines.append(s)

    if not non_toc_lines:
        return False

    non_toc_text = "\n".join(non_toc_lines)
    has_caption = bool(_BORDERLESS_CAPTION_RE.search(non_toc_text))

    # Count lines with multi-space-separated numeric columns (3+ numbers with wide whitespace)
    tabular_lines = 0
    for line in non_toc_lines:
        if _MULTI_SPACE_SPLIT_RE.search(line) and len(_NUM_TOKEN_RE.findall(line)) >= 3:
            tabular_lines += 1
            if tabular_lines >= 2:
                return True

    # Also check spatial block alignment on the same horizontal row when raw_blocks available
    if raw_blocks and len(raw_blocks) >= 6:
        y_bands: Dict[int, List[Tuple[float, str]]] = {}
        for b in raw_blocks:
            if len(b) >= 5:
                b_txt = b[4].strip()
                if not b_txt or "...." in b_txt or _TOC_LINE_RE.search(b_txt):
                    continue
                y_bucket = int(round(b[1] / 6.0))
                y_bands.setdefault(y_bucket, []).append((b[0], b_txt))

        aligned_multi_col_rows = 0
        for cols in y_bands.values():
            if len(cols) >= 3:
                # Must contain numeric/tabular values on that aligned row
                row_str = " ".join(c[1] for c in cols)
                if len(_NUM_TOKEN_RE.findall(row_str)) >= 2:
                    aligned_multi_col_rows += 1
                    if aligned_multi_col_rows >= 2:
                        return True

    if has_caption and tabular_lines >= 1:
        return True

    return False


def page_has_table_indicator(
    page,
    raw_blocks: Optional[List[Any]] = None,
    drawings: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """
    Fast heuristic to detect whether a PDF page contains tabular structures
    (bordered or borderless), without triggering slow table heuristics on plain text,
    slide decks, or Table of Contents pages.
    """
    page_rect = page.rect
    page_drawings = drawings if drawings is not None else page.get_drawings()
    line_count, rect_count, _ = _analyze_page_drawings(page_rect, page_drawings)

    if line_count >= 2 or rect_count >= 4:
        return True

    if raw_blocks is not None:
        text = "\n".join(b[4] for b in raw_blocks if len(b) >= 5 and b[4])
    else:
        text = page.get_text()

    return _has_borderless_table_signal(text, raw_blocks=raw_blocks)


class PyMuPDFParser(DocumentParser):
    def __init__(self, sort_blocks: bool = True):
        self.sort_blocks = sort_blocks

    def _classify_heading(self, cleaned_str: str) -> Tuple[bool, int]:
        """
        Determines whether a cleaned text block is a genuine section heading and
        returns (is_heading, level). Avoids splitting Table-of-Contents lines,
        multi-line prose, bullet sentences, and Level 3 sub-bullets into separate sections.
        """
        if not cleaned_str or len(cleaned_str) >= 100 or len(cleaned_str.split("\n")) > 2:
            return False, 1

        # Ignore TOC dot-leader entries (e.g. "1.2 Scope... 5") and URLs
        if _TOC_LINE_RE.search(cleaned_str) or "..." in cleaned_str:
            return False, 1
        lower_str = cleaned_str.lower()
        if "http://" in lower_str or "https://" in lower_str or "www." in lower_str:
            return False, 1

        # Explicit section/chapter keywords
        if cleaned_str.startswith(("Section ", "Chapter ", "Article ", "PART ")):
            if cleaned_str.count(".") >= 2:
                return True, 3
            if cleaned_str.count(".") == 1:
                return True, 2
            return True, 1

        # Exclude compact alphanumeric course/serial codes (e.g. "23UCOPEL4703X", "CS101")
        if " " not in cleaned_str and any(c.isdigit() for c in cleaned_str) and _ALNUM_CODE_RE.match(cleaned_str):
            return False, 1

        # All-uppercase concise headings (excluding course codes / alphanumeric IDs)
        if cleaned_str.isupper() and len(cleaned_str) >= 6 and any(ch.isalpha() for ch in cleaned_str):
            if " " in cleaned_str or cleaned_str.isalpha():
                return True, 1

        # Numbered heading pattern (e.g. "1. Meaning...", "1.1 Introduction", "2.3.1 Objectivity")
        m = _NUM_PREFIX_RE.match(cleaned_str)
        if m and len(cleaned_str) > 3:
            prefix = m.group(1)
            depth = prefix.count(".") + 1
            try:
                lead_num = int(prefix.split(".")[0])
            except ValueError:
                lead_num = 999
            if lead_num > 50:
                return False, 1

            # Ignore multi-line items or numbered list sentences ending in terminal punctuation
            if depth == 1:
                if "\n" in cleaned_str:
                    return False, 1
                if cleaned_str.endswith((".", "?", "!")) and len(cleaned_str.split()) >= 4:
                    return False, 1
                if "edition" in lower_str or "press" in lower_str or "publisher" in lower_str:
                    return False, 1
                return True, 1
            elif depth == 2:
                if cleaned_str.endswith((".", "?", "!")) and len(cleaned_str.split()) >= 8:
                    return False, 2
                return True, 2
            else:
                # Level 3+ sub-headings (e.g. "2.3.1 Objectivity") belong inside their Level 2 parent
                return False, 3

        return False, 1

    def parse(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF document not found: {file_path}")

        try:
            doc = pymupdf.open(file_path)
        except Exception as e:
            raise ValueError(f"Corrupted or invalid PDF file: {e}")

        doc_id = os.path.splitext(os.path.basename(file_path))[0]
        extracted_blocks: List[ExtractedBlock] = []
        extracted_sections: List[ExtractedSection] = []
        extracted_tables: List[ExtractedTable] = []

        current_section_title = "Document Start"
        current_section_level = 1
        current_section_content: List[str] = []
        current_section_page = 1
        section_idx = 0
        current_section_id = f"sec_{section_idx}"

        for page_idx, page in enumerate(doc):
            page_num = page_idx + 1
            page_rect = page.rect

            # Parse layout blocks and drawings ONCE per page and reuse across table & text pipelines
            raw_blocks = page.get_text("blocks", sort=self.sort_blocks)
            drawings = page.get_drawings()

            # 1. Extract tables only when indicators confirm bordered or genuine borderless tables
            try:
                line_count, rect_count, table_clip = _analyze_page_drawings(page_rect, drawings)
                has_vector_grid = (line_count >= 2 or rect_count >= 4)
                tabs = None

                if has_vector_grid and table_clip is not None:
                    # Fast path: clipped pure vector table finder without ONNX layout network
                    tabs = page.find_tables(use_layout=False, paths=drawings, clip=table_clip)
                    # Fallback for row-banded tables without vertical grid lines (e.g. shaded strips)
                    if (not tabs or not tabs.tables) and rect_count >= 4:
                        tabs = page.find_tables(use_layout=True, paths=drawings, clip=table_clip)
                else:
                    block_text = "\n".join(b[4] for b in raw_blocks if len(b) >= 5 and b[4])
                    if _has_borderless_table_signal(block_text, raw_blocks=raw_blocks):
                        tabs = page.find_tables(use_layout=True, paths=drawings)

                if tabs and tabs.tables:
                    for t_idx, tab in enumerate(tabs.tables):
                        df_rows = tab.extract()
                        if df_rows and len(df_rows) > 0:
                            headers = [clean_text(str(c or "")) for c in df_rows[0]]
                            rows = [[clean_text(str(c or "")) for c in r] for r in df_rows[1:]]
                            tb_bbox = BoundingBox(
                                x0=float(tab.bbox[0]),
                                y0=float(tab.bbox[1]),
                                x1=float(tab.bbox[2]),
                                y1=float(tab.bbox[3]),
                                page=page_num
                            )
                            extracted_tables.append(ExtractedTable(
                                table_id=f"tab_p{page_num}_{t_idx}",
                                page=page_num,
                                headers=headers,
                                rows=rows,
                                bbox=tb_bbox
                            ))
            except Exception:
                pass

            # 2. Process already-extracted layout blocks
            for b_idx, b in enumerate(raw_blocks):
                # b tuple format: (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5:
                    x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
                    cleaned_str = clean_text(text)
                    if not cleaned_str:
                        continue

                    is_heading, heading_level = self._classify_heading(cleaned_str)

                    if is_heading:
                        if current_section_content:
                            extracted_sections.append(ExtractedSection(
                                section_id=current_section_id,
                                title=current_section_title,
                                section_level=current_section_level,
                                page_number=current_section_page,
                                order_index=section_idx,
                                content="\n\n".join(current_section_content)
                            ))
                            section_idx += 1
                            current_section_content = []

                        current_section_id = f"sec_{section_idx}"
                        current_section_title = cleaned_str
                        current_section_level = heading_level
                        current_section_page = page_num
                    else:
                        current_section_content.append(cleaned_str)

                    bbox = BoundingBox(
                        x0=float(x0),
                        y0=float(y0),
                        x1=float(x1),
                        y1=float(y1),
                        page=page_num
                    )
                    extracted_blocks.append(ExtractedBlock(
                        block_id=f"blk_p{page_num}_{b_idx}",
                        page=page_num,
                        text=cleaned_str,
                        bbox=bbox,
                        block_type="heading" if is_heading else "text",
                        section_id=current_section_id
                    ))

        # Flush final section
        if current_section_content:
            extracted_sections.append(ExtractedSection(
                section_id=current_section_id,
                title=current_section_title,
                section_level=current_section_level,
                page_number=current_section_page,
                order_index=section_idx,
                content="\n\n".join(current_section_content)
            ))

        metadata: Dict[str, Any] = {
            "title": doc.metadata.get("title", "") if doc.metadata else "",
            "author": doc.metadata.get("author", "") if doc.metadata else "",
            "format": doc.metadata.get("format", "PDF") if doc.metadata else "PDF",
            "total_pages": len(doc)
        }

        total_p = len(doc)
        doc.close()

        return ExtractedDocument(
            doc_id=doc_id,
            source_path=file_path,
            total_pages=total_p,
            blocks=extracted_blocks,
            sections=extracted_sections,
            tables=extracted_tables,
            metadata=metadata
        )
