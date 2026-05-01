"""Text chunker and embedding engine for knowledge base.

Chunking: 500 chars per chunk, 50 char overlap, preserves section headings.
Embedding: BAAI/bge-small-zh-v1.5 via sentence-transformers (lazy-loaded singleton).
"""

import json
import re
from typing import List, Tuple

import numpy as np


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Tuple[str, str]]:
    """Split text into chunks, returning (heading, chunk_text) pairs.

    Detects section headings (lines ending with '：' or matching patterns like '第X条')
    and carries the most recent heading forward into subsequent chunks.
    """
    lines = text.split("\n")
    chunks = []
    current_heading = ""
    buffer = ""

    heading_pattern = re.compile(
        r"^(第[一二三四五六七八九十\d]+[章节条]|[\d]+[\.\、]|［[^］]+］|[一二三四五六七八九十]+[\.\、])"
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                buffer += "\n"
            continue

        # Detect heading
        if heading_pattern.match(stripped) or (
            len(stripped) < 50
            and (stripped.endswith("：") or stripped.endswith(":"))
        ):
            # Flush current buffer
            if len(buffer) >= 100:
                chunks.append((current_heading, buffer.strip()))
            current_heading = stripped.rstrip("：:")
            buffer = ""
            continue

        buffer += stripped + "\n"

    # Flush final buffer
    if buffer.strip():
        chunks.append((current_heading, buffer.strip()))

    # Sub-split large chunks
    final_chunks = []
    for heading, text_block in chunks:
        if len(text_block) <= chunk_size:
            final_chunks.append((heading, text_block))
        else:
            start = 0
            while start < len(text_block):
                end = start + chunk_size
                chunk = text_block[start:end]
                final_chunks.append((heading, chunk))
                start = end - overlap

    # Fallback: if no chunks created, use simple character-based chunking
    if not final_chunks and text.strip():
        text = text.strip()
        start = 0
        while start < len(text):
            end = start + chunk_size
            final_chunks.append(('' , text[start:end]))
            start = end - overlap

    return final_chunks


class Embedder:
    """Singleton embedding engine using BAAI/bge-small-zh-v1.5."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
        return cls._instance

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.model.encode([text], normalize_embeddings=True, show_progress_bar=False)[0]

    def search(self, query: str, chunk_embeddings: List[np.ndarray], top_k: int = 5) -> List[Tuple[int, float]]:
        """Search query against stored embeddings, returns (index, score) pairs."""
        query_vec = self.embed_single(query)
        scores = np.dot(chunk_embeddings, query_vec)  # cosine similarity (already normalized)
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [(int(i), float(scores[i])) for i in top_indices if scores[i] > 0.3]


embedder = Embedder()
