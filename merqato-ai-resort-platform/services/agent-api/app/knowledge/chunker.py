from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.knowledge.formatter import format_knowledge
from app.knowledge.models import KnowledgeChunk


@dataclass
class ChunkConfig:
    max_chars: int = 1200
    overlap_chars: int = 0


def chunk_document(
    category: str,
    content: dict[str, Any],
    *,
    source_filename: str | None = None,
    config: ChunkConfig | None = None,
) -> list[KnowledgeChunk]:
    """Create bounded chunks from formatted factual text.

    - short factual records are kept whole (no unnecessary splitting)
    - category + field context is preserved in every chunk
    - chunk ordering is deterministic (single pass, index order)
    - chunk size is configurable
    - a document/tenant is never mixed with another in the same chunk
    """
    cfg = config or ChunkConfig()
    text = format_knowledge(category, content)
    if not text.strip():
        return []

    # Keep short records as a single chunk.
    if len(text) <= cfg.max_chars:
        return [
            KnowledgeChunk(
                chunk_index=0,
                text=text,
                category=category,
                source_filename=source_filename,
                metadata={"category": category, "source_filename": source_filename},
            )
        ]

    pieces = _split_text(text, cfg.max_chars, cfg.overlap_chars)
    chunks: list[KnowledgeChunk] = []
    for i, piece in enumerate(pieces):
        chunks.append(
            KnowledgeChunk(
                chunk_index=i,
                text=piece,
                category=category,
                source_filename=source_filename,
                metadata={"category": category, "source_filename": source_filename},
            )
        )
    return chunks


def _split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Deterministic greedy splitter on paragraph/line boundaries."""
    pieces: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        segment = text[start:end]
        # Prefer breaking at the last newline within the segment.
        if end < n and "\n" in segment:
            last_nl = segment.rfind("\n")
            if last_nl > 0:
                end = start + last_nl + 1
                segment = text[start:end]
        pieces.append(segment.strip())
        if end >= n:
            break
        start = end - overlap if overlap else end
    return [p for p in pieces if p]
