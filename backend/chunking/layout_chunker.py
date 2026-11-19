"""Layout-Aware and Structure-Aware Chunking Implementation

Preserves:
- Explicit parent section relationships (propagated from blocks, never substring guessed).
- Spatial bounding boxes for UI highlights.
- Original page numbers and element ordering.
- Table identity and table header context across large table splits.
- Heading and paragraph boundaries.
"""

from typing import List, Optional, Set, Dict, Any
from backend.extraction.base import ExtractedDocument, ExtractedBlock, BoundingBox
from backend.chunking.base import Chunker, DocumentChunk

class LayoutAwareChunker(Chunker):
    def __init__(self, target_words_per_chunk: int = 250, overlap_words: int = 30):
        self.target_words = target_words_per_chunk
        self.overlap_words = overlap_words

    def _split_large_table(
        self,
        block: ExtractedBlock,
        doc_id: str,
        start_chunk_idx: int,
        config_meta: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Splits a large table block while preserving table headers across every chunk fragment.
        """
        lines = block.text.strip().split("\n")
        if len(lines) <= 2:
            # Single row or small table
            return [
                DocumentChunk(
                    chunk_id=f"{doc_id}_chk_{start_chunk_idx:04d}",
                    doc_id=doc_id,
                    section_id=block.section_id,
                    table_id=block.table_id,
                    page_numbers=[block.page],
                    text=block.text,
                    bboxes=[block.bbox] if block.bbox else [],
                    token_count=len(block.text.split()),
                    metadata={
                        **config_meta,
                        "is_table": True,
                        "table_id": block.table_id or ""
                    }
                )
            ]

        header_line = lines[0]
        # Check if line 1 is a markdown separator (e.g. |---|---|)
        data_start_idx = 1
        if len(lines) > 1 and ("---" in lines[1] or ":---" in lines[1]):
            header_line = lines[0] + "\n" + lines[1]
            data_start_idx = 2

        data_rows = lines[data_start_idx:]
        chunks: List[DocumentChunk] = []
        current_rows: List[str] = []
        current_words = len(header_line.split())
        c_idx = start_chunk_idx

        for row in data_rows:
            row_words = len(row.split())
            if current_words + row_words > self.target_words and current_rows:
                chunk_text = header_line + "\n" + "\n".join(current_rows)
                chunks.append(DocumentChunk(
                    chunk_id=f"{doc_id}_chk_{c_idx:04d}",
                    doc_id=doc_id,
                    section_id=block.section_id,
                    table_id=block.table_id,
                    page_numbers=[block.page],
                    text=chunk_text,
                    bboxes=[block.bbox] if block.bbox else [],
                    token_count=len(chunk_text.split()),
                    metadata={
                        **config_meta,
                        "is_table": True,
                        "table_id": block.table_id or "",
                        "table_fragment": True
                    }
                ))
                c_idx += 1
                current_rows = []
                current_words = len(header_line.split())

            current_rows.append(row)
            current_words += row_words

        if current_rows:
            chunk_text = header_line + "\n" + "\n".join(current_rows)
            chunks.append(DocumentChunk(
                chunk_id=f"{doc_id}_chk_{c_idx:04d}",
                doc_id=doc_id,
                section_id=block.section_id,
                table_id=block.table_id,
                page_numbers=[block.page],
                text=chunk_text,
                bboxes=[block.bbox] if block.bbox else [],
                token_count=len(chunk_text.split()),
                metadata={
                    **config_meta,
                    "is_table": True,
                    "table_id": block.table_id or "",
                    "table_fragment": len(chunks) > 0
                }
            ))

        return chunks

    def chunk(self, doc: ExtractedDocument) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        if not doc.blocks:
            return chunks

        config_meta = {
            "chunk_size_words": self.target_words,
            "chunk_overlap_words": self.overlap_words,
            "doc_title": doc.metadata.get("title", "")
        }

        current_words = 0
        current_text_parts: List[str] = []
        current_bboxes: List[BoundingBox] = []
        current_pages: Set[int] = set()
        current_section_id: Optional[str] = None
        chunk_idx = 0

        def flush_current():
            nonlocal chunk_idx, current_text_parts, current_bboxes, current_pages, current_words, current_section_id
            if not current_text_parts:
                return
            
            chunk_id = f"{doc.doc_id}_chk_{chunk_idx:04d}"
            full_text = "\n\n".join(current_text_parts)
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc.doc_id,
                section_id=current_section_id,
                page_numbers=sorted(list(current_pages)),
                text=full_text,
                bboxes=list(current_bboxes),
                token_count=len(full_text.split()),
                metadata=dict(config_meta)
            ))
            chunk_idx += 1

            # Conservative overlap: retain last element if overlap requested and within bounds
            if self.overlap_words > 0 and len(current_text_parts) > 1:
                last_part = current_text_parts[-1]
                last_words = len(last_part.split())
                if last_words <= self.overlap_words:
                    current_text_parts = [last_part]
                    current_bboxes = [current_bboxes[-1]] if current_bboxes else []
                    current_pages = {sorted(list(current_pages))[-1]} if current_pages else set()
                    current_words = last_words
                    return

            current_text_parts = []
            current_bboxes = []
            current_pages = set()
            current_words = 0

        for block in doc.blocks:
            block_words = len(block.text.split())

            # Structure rule 1: If block is a large table, flush previous text and handle table preservation
            if block.block_type == "table":
                flush_current()
                table_chunks = self._split_large_table(block, doc.doc_id, chunk_idx, config_meta)
                chunks.extend(table_chunks)
                chunk_idx += len(table_chunks)
                current_section_id = block.section_id
                continue

            # Structure rule 2: Heading boundary or Section transition
            # If the block begins a new section or is a heading, flush previous section content to keep sections clean
            if block.block_type == "heading" or (block.section_id and block.section_id != current_section_id and current_text_parts):
                flush_current()
                current_section_id = block.section_id

            # Size limit rule: If adding this block exceeds target size, flush
            if current_words + block_words > self.target_words and current_text_parts:
                flush_current()
                current_section_id = block.section_id

            if not current_section_id:
                current_section_id = block.section_id

            current_text_parts.append(block.text)
            if block.bbox:
                current_bboxes.append(block.bbox)
            current_pages.add(block.page)
            current_words += block_words

        flush_current()
        return chunks
