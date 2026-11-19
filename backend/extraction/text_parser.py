"""Plain Text and Markdown Document Parser Implementation

Parses TXT and Markdown (.md, .markdown) documents.
Extracts headings, code fences, bullet lists, tables, and paragraphs.
Preserves explicit structural section identity.
"""

import os
import re
from typing import List, Dict, Any, Optional
from backend.extraction.base import (
    DocumentParser,
    ExtractedDocument,
    ExtractedBlock,
    ExtractedSection,
    ExtractedTable
)
from backend.cleaning.cleaner import clean_text

class TextMarkdownParser(DocumentParser):
    def parse(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                raw_content = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read text file: {e}")

        doc_id = os.path.splitext(os.path.basename(file_path))[0]
        ext = os.path.splitext(file_path)[1].lower()
        is_markdown = ext in (".md", ".markdown")

        extracted_blocks: List[ExtractedBlock] = []
        extracted_sections: List[ExtractedSection] = []
        extracted_tables: List[ExtractedTable] = []

        current_section_title = "Document Start"
        current_section_level = 1
        current_section_content: List[str] = []
        section_idx = 0
        block_idx = 0
        current_section_id = f"sec_{section_idx}"

        if is_markdown:
            lines = raw_content.splitlines()
            buffer: List[str] = []
            in_code_block = False
            in_table = False
            table_lines: List[str] = []

            def flush_buffer(b_type: str = "text"):
                nonlocal block_idx, buffer, current_section_content, current_section_id
                if not buffer:
                    return
                text = clean_text("\n".join(buffer))
                buffer = []
                if text:
                    extracted_blocks.append(ExtractedBlock(
                        block_id=f"blk_md_{block_idx}",
                        page=1,
                        text=text,
                        bbox=None,
                        block_type=b_type,
                        section_id=current_section_id
                    ))
                    block_idx += 1
                    current_section_content.append(text)

            def flush_table():
                nonlocal table_lines, extracted_tables, current_section_content, block_idx, current_section_id
                if not table_lines:
                    return
                rows = []
                for t_line in table_lines:
                    if re.match(r"^\|?\s*[-:]+[-| :]*\|?$", t_line.strip()):
                        continue
                    cells = [clean_text(c) for c in t_line.strip("|").split("|")]
                    if any(cells):
                        rows.append(cells)
                if rows:
                    t_id = f"tab_md_{len(extracted_tables)}"
                    extracted_tables.append(ExtractedTable(
                        table_id=t_id,
                        page=1,
                        headers=rows[0],
                        rows=rows[1:],
                        bbox=None
                    ))
                    table_str = "\n".join(table_lines)
                    extracted_blocks.append(ExtractedBlock(
                        block_id=f"blk_md_{block_idx}",
                        page=1,
                        text=table_str,
                        bbox=None,
                        block_type="table",
                        section_id=current_section_id,
                        table_id=t_id
                    ))
                    block_idx += 1
                    current_section_content.append(table_str)
                table_lines = []

            for line in lines:
                stripped = line.strip()

                if stripped.startswith(("```", "~~~")):
                    if in_code_block:
                        buffer.append(line)
                        flush_buffer("code")
                        in_code_block = False
                    else:
                        flush_buffer()
                        in_code_block = True
                        buffer.append(line)
                    continue

                if in_code_block:
                    buffer.append(line)
                    continue

                if "|" in stripped and not stripped.startswith("#"):
                    flush_buffer()
                    in_table = True
                    table_lines.append(stripped)
                    continue
                elif in_table:
                    flush_table()
                    in_table = False

                heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
                if heading_match:
                    flush_buffer()
                    h_level = len(heading_match.group(1))
                    h_text = clean_text(heading_match.group(2))

                    if current_section_content:
                        extracted_sections.append(ExtractedSection(
                            section_id=current_section_id,
                            title=current_section_title,
                            section_level=current_section_level,
                            page_number=1,
                            order_index=section_idx,
                            content="\n\n".join(current_section_content)
                        ))
                        section_idx += 1
                        current_section_content = []

                    current_section_id = f"sec_{section_idx}"
                    current_section_title = h_text
                    current_section_level = h_level

                    extracted_blocks.append(ExtractedBlock(
                        block_id=f"blk_md_{block_idx}",
                        page=1,
                        text=h_text,
                        bbox=None,
                        block_type="heading",
                        section_id=current_section_id
                    ))
                    block_idx += 1
                    continue

                if not stripped:
                    flush_buffer()
                else:
                    buffer.append(line)

            flush_buffer()
            if in_table:
                flush_table()

        else:
            paragraphs = re.split(r"\n\s*\n", raw_content)
            for p in paragraphs:
                cleaned = clean_text(p)
                if not cleaned:
                    continue
                extracted_blocks.append(ExtractedBlock(
                    block_id=f"blk_txt_{block_idx}",
                    page=1,
                    text=cleaned,
                    bbox=None,
                    block_type="text",
                    section_id=current_section_id
                ))
                block_idx += 1
                current_section_content.append(cleaned)

        if current_section_content:
            extracted_sections.append(ExtractedSection(
                section_id=current_section_id,
                title=current_section_title,
                section_level=current_section_level,
                page_number=1,
                order_index=section_idx,
                content="\n\n".join(current_section_content)
            ))

        metadata: Dict[str, Any] = {
            "format": "Markdown" if is_markdown else "TXT",
            "total_characters": len(raw_content),
            "total_blocks": len(extracted_blocks)
        }

        return ExtractedDocument(
            doc_id=doc_id,
            source_path=file_path,
            total_pages=1,
            blocks=extracted_blocks,
            sections=extracted_sections,
            tables=extracted_tables,
            metadata=metadata
        )
