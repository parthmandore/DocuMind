"""DOCX Document Parser Implementation

Extracts structured blocks, headings, sections, and tables from DOCX files
using python-docx. Preserves hierarchical heading levels, paragraph order,
and explicit section identity.
"""

import os
from typing import List, Dict, Any
import docx
from backend.extraction.base import (
    DocumentParser,
    ExtractedDocument,
    ExtractedBlock,
    ExtractedSection,
    ExtractedTable
)
from backend.cleaning.cleaner import clean_text

class DocxParser(DocumentParser):
    def parse(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DOCX file not found: {file_path}")

        try:
            doc = docx.Document(file_path)
        except Exception as e:
            raise ValueError(f"Corrupted or invalid DOCX file: {e}")

        doc_id = os.path.splitext(os.path.basename(file_path))[0]
        extracted_blocks: List[ExtractedBlock] = []
        extracted_sections: List[ExtractedSection] = []
        extracted_tables: List[ExtractedTable] = []

        current_section_title = "Document Start"
        current_section_level = 1
        current_section_content: List[str] = []
        section_idx = 0
        block_idx = 0
        current_section_id = f"sec_{section_idx}"

        # Process paragraphs
        for p in doc.paragraphs:
            cleaned = clean_text(p.text)
            if not cleaned:
                continue

            style_name = p.style.name if p.style else ""
            is_heading = style_name.startswith("Heading") or style_name.startswith("Title")
            
            heading_level = 1
            if style_name.startswith("Heading"):
                try:
                    heading_level = int(style_name.replace("Heading", "").strip())
                except ValueError:
                    heading_level = 1
            elif style_name == "Title":
                heading_level = 1

            if is_heading:
                # Flush previous section
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
                current_section_title = cleaned
                current_section_level = heading_level
            else:
                current_section_content.append(cleaned)

            block_type = "heading" if is_heading else "text"
            extracted_blocks.append(ExtractedBlock(
                block_id=f"blk_docx_{block_idx}",
                page=1,
                text=cleaned,
                bbox=None,
                block_type=block_type,
                section_id=current_section_id
            ))
            block_idx += 1

        # Process tables
        for t_idx, table in enumerate(doc.tables):
            table_rows: List[List[str]] = []
            for row in table.rows:
                row_cells = [clean_text(cell.text) for cell in row.cells]
                table_rows.append(row_cells)

            if table_rows:
                headers = table_rows[0]
                rows = table_rows[1:]
                t_id = f"tab_docx_{t_idx}"
                extracted_tables.append(ExtractedTable(
                    table_id=t_id,
                    page=1,
                    headers=headers,
                    rows=rows,
                    bbox=None
                ))

                table_str = " | ".join(headers) + "\n" + "\n".join(" | ".join(r) for r in rows)
                extracted_blocks.append(ExtractedBlock(
                    block_id=f"blk_docx_{block_idx}",
                    page=1,
                    text=table_str,
                    bbox=None,
                    block_type="table",
                    section_id=current_section_id,
                    table_id=t_id
                ))
                block_idx += 1
                current_section_content.append(table_str)

        # Flush final section
        if current_section_content:
            extracted_sections.append(ExtractedSection(
                section_id=current_section_id,
                title=current_section_title,
                section_level=current_section_level,
                page_number=1,
                order_index=section_idx,
                content="\n\n".join(current_section_content)
            ))

        props = doc.core_properties
        metadata: Dict[str, Any] = {
            "title": props.title or "",
            "author": props.author or "",
            "format": "DOCX",
            "total_paragraphs": len(doc.paragraphs),
            "total_tables": len(doc.tables)
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
