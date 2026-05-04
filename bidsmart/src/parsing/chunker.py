"""Document chunker for large parsed documents.

Splits ParsedDocument into chunks of ~2000 tokens (~8000 chars),
respecting section boundaries with overlap between consecutive chunks.
Handles documents up to 100MB+ via efficient section-by-section processing.

Pure Python — no additional dependencies required.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.parsing.models import ParsedDocument, Section

# ── tuning constants ──────────────────────────────────────────────
# 1 token ≈ 4 chars for mixed English/Chinese/CJK text
CHARS_PER_TOKEN = 4

TARGET_TOKENS = 2000
TARGET_CHARS = TARGET_TOKENS * CHARS_PER_TOKEN   # 8000

OVERLAP_TOKENS = 50
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN  # 200

# Sections within 10 % of the target are kept as single chunks
# rather than being sub-split into a large chunk + tiny remainder.
FUZZ_FACTOR = 0.10
# ───────────────────────────────────────────────────────────────────


def _render_section(section: Section) -> str:
    """Render a section to its full plain-text representation."""
    parts: list[str] = []
    if section.heading:
        parts.append(section.heading)
    if section.content:
        parts.append(section.content)
    for item in section.items:
        parts.append(f"\u2022 {item}")
    return "\n".join(parts)


def _sub_split_section(
    text: str,
    heading: str,
    section_id: str,
    page_number: int,
) -> list[dict[str, Any]]:
    """Split a single oversized section into multiple chunks with overlap.

    Used when a section's rendered text exceeds *TARGET_CHARS* and
    cannot be placed in a single chunk.
    """
    chunks: list[dict[str, Any]] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + TARGET_CHARS, text_len)
        chunk_text = text[start:end]
        chunks.append({
            "text": chunk_text,
            "heading": heading,
            "section_id": section_id,
            "page_number": page_number,
        })
        if end >= text_len:
            break
        # Slide window back by OVERLAP_CHARS so consecutive sub-chunks
        # share context.
        start = end - OVERLAP_CHARS

    return chunks


def _add_overlap(raw_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepend overlap text from the previous chunk to each subsequent chunk.

    Returns the final list of chunk dicts with {content, heading,
    section_id, page_number, chunk_index, char_count}.
    """
    if not raw_chunks:
        return []

    result: list[dict[str, Any]] = []
    prev_tail = ""

    for i, rc in enumerate(raw_chunks):
        content = rc["text"]
        if i > 0 and prev_tail:
            # Prepend overlap from the previous chunk.
            content = prev_tail + "\n\n" + content

        result.append({
            "content": content,
            "heading": rc["heading"],
            "section_id": rc["section_id"],
            "page_number": rc["page_number"],
            "chunk_index": i,
            "char_count": len(content),
        })

        # Capture tail of the *original* text (without the inbound overlap)
        # so the *next* chunk gets the right context window.
        orig = rc["text"]
        prev_tail = orig[-OVERLAP_CHARS:] if len(orig) > OVERLAP_CHARS else orig

    return result


def _chunk_raw_text(doc: ParsedDocument) -> list[dict[str, Any]]:
    """Fallback: character-window chunking when the document has no sections."""
    text = doc.text
    if not text.strip():
        return []

    chunks: list[dict[str, Any]] = []
    text_len = len(text)
    start = 0
    idx = 0

    while start < text_len:
        end = min(start + TARGET_CHARS, text_len)
        chunk_text = text[start:end]
        chunks.append({
            "content": chunk_text,
            "heading": doc.title or "",
            "section_id": "",
            "page_number": 0,
            "chunk_index": idx,
            "char_count": len(chunk_text),
        })
        if end >= text_len:
            break
        start = end - OVERLAP_CHARS
        idx += 1

    return chunks


# ── public API ─────────────────────────────────────────────────────

def chunk_document(doc: ParsedDocument) -> list[dict[str, Any]]:
    """Split a parsed document into overlapping, section-boundary-aware chunks.

    Each returned dict contains::

        {
            "content":      str,   # chunk text (may include overlap from prev)
            "heading":      str,   # primary section heading
            "section_id":   str,   # section_id of the primary section
            "page_number":  int,   # starting page of the primary section
            "chunk_index":  int,   # 0-based position in the document
            "char_count":   int,   # total characters in this chunk
        }

    Rules
    -----
    * Sections shorter than ~8000 chars are **never** broken — they
      are packed into chunks until the next section would overflow.
    * Sections longer than ~8000 chars are sub-split with ~200-char
      overlap between sub-chunks.
    * Consecutive chunks overlap by ~200 chars for context continuity.
    * Documents without sections fall back to a simple sliding window.
    * Memory usage is proportional to the number of sections, not the
      raw byte size — 100 MB+ documents are handled comfortably.
    """
    if not doc.sections:
        return _chunk_raw_text(doc)

    # ── 1. Render every section to its plain-text form ─────────────
    rendered: list[dict[str, Any]] = []
    for sec in doc.sections:
        text = _render_section(sec)
        if not text.strip():
            continue
        rendered.append({
            "section": sec,
            "text": text,
            "char_count": len(text),
        })

    if not rendered:
        return []

    # ── 2. Pack sections into target-sized chunks ──────────────────
    raw_chunks: list[dict[str, Any]] = []
    current_parts: list[str] = []
    current_len = 0
    current_primary: tuple[str, str, int] | None = None  # (heading, section_id, page)

    # Allow a section to go slightly over the target to avoid tiny
    # trailing chunks.
    soft_max = int(TARGET_CHARS * (1 + FUZZ_FACTOR))  # 8800

    def _flush() -> None:
        nonlocal current_parts, current_len, current_primary
        if current_parts:
            text = "\n\n".join(current_parts)
            raw_chunks.append({
                "text": text,
                "heading": current_primary[0] if current_primary else "",
                "section_id": current_primary[1] if current_primary else "",
                "page_number": current_primary[2] if current_primary else 0,
            })
            current_parts = []
            current_len = 0
            current_primary = None

    for entry in rendered:
        sec: Section = entry["section"]
        text: str = entry["text"]
        text_len: int = entry["char_count"]

        # Single gigantic section — sub-split it.
        if text_len > soft_max:
            _flush()
            raw_chunks.extend(
                _sub_split_section(text, sec.heading, sec.section_id, sec.page_number)
            )
            continue

        # Try to fit into the current chunk.
        sep = 2 if current_parts else 0  # "\n\n" between sections
        if current_len + sep + text_len <= soft_max:
            current_parts.append(text)
            current_len += sep + text_len
            if current_primary is None:
                current_primary = (sec.heading, sec.section_id, sec.page_number)
        else:
            _flush()
            current_parts.append(text)
            current_len = text_len
            current_primary = (sec.heading, sec.section_id, sec.page_number)

    _flush()

    # ── 3. Inject inter-chunk overlap ──────────────────────────────
    return _add_overlap(raw_chunks)


# ── convenience ────────────────────────────────────────────────────

def estimate_tokens(text: str) -> float:
    """Rough token-count estimate (chars / 4 for mixed CJK + English)."""
    return len(text) / CHARS_PER_TOKEN


def chunk_stats(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Return aggregate statistics about a list of chunks."""
    if not chunks:
        return {"count": 0, "total_chars": 0, "avg_chars": 0.0,
                "min_chars": 0, "max_chars": 0}

    counts = [c["char_count"] for c in chunks]
    return {
        "count": len(chunks),
        "total_chars": sum(counts),
        "avg_chars": sum(counts) / len(counts),
        "min_chars": min(counts),
        "max_chars": max(counts),
        "avg_tokens": (sum(counts) / len(counts)) / CHARS_PER_TOKEN,
    }
