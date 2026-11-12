"""Document Text Cleaning and Normalization Service

Normalizes whitespace, unfolds common typographic ligatures, strips unprintable
control characters, collapses excessive leader dots, and preserves headings,
paragraph structure, and markdown. Content is never silently discarded.
"""

import re
import unicodedata

# Common typographic ligatures and punctuation map
LIGATURE_MAP = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "ft",
    "\ufb06": "st",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬀ": "ff",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "--",
    "\u00a0": " ",  # Non-breaking space
    "\u200b": "",   # Zero-width space
    "\u200e": "",   # Left-to-right mark
    "\u200f": "",   # Right-to-left mark
    "\ufeff": ""    # Byte order mark
}

_LIGATURE_TRANS = str.maketrans(LIGATURE_MAP)
_CONTROL_ASCII_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_MULTI_HSPACE_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")
_DOT_LEADER_RE = re.compile(r"\.{4,}")


def unfold_ligatures(text: str) -> str:
    """Replaces typographic ligatures and directional marks with standard characters."""
    if not text:
        return ""
    return text.translate(_LIGATURE_TRANS)


def clean_text(text: str) -> str:
    """
    Cleans raw extracted text rapidly without discarding semantic content:
    1. Unfolds ligatures and unicode quote marks via O(N) C-level str.translate.
    2. Strips unprintable control characters while preserving tabs and newlines.
    3. Collapses pathological TOC dot leaders (....+) to '...' to prevent token bloat.
    4. Normalizes repeated horizontal whitespace without collapsing paragraph linebreaks.
    5. Normalizes consecutive blank lines (max 2 consecutive newlines).
    """
    if not text:
        return ""

    # 1. Ligatures and directional marks
    text = text.translate(_LIGATURE_TRANS)

    # 2. Strip control characters rapidly (fast ASCII regex + non-ASCII guard if needed)
    text = _CONTROL_ASCII_RE.sub("", text)
    if not text.isascii():
        # Only scan rare non-ASCII Unicode categories if non-ASCII exists and contains category 'C'
        if any(ord(ch) > 127 and unicodedata.category(ch).startswith("C") for ch in text):
            text = "".join(
                ch for ch in text
                if ord(ch) <= 127 or not unicodedata.category(ch).startswith("C")
            )

    # 3. Standardize carriage returns and collapse TOC dot-leader floods (4+ dots -> '...')
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "...." in text:
        text = _DOT_LEADER_RE.sub("...", text)

    # 4. Normalize spaces/tabs across text, then trim line ends cleanly
    text = _MULTI_HSPACE_RE.sub(" ", text)
    rebuilt = "\n".join(line.strip() for line in text.split("\n"))

    # 5. Limit excessive blank lines (max 2 newlines = 1 blank line between paragraphs)
    rebuilt = _MULTI_NL_RE.sub("\n\n", rebuilt)

    return rebuilt.strip()
