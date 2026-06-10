from __future__ import annotations

import re
from dataclasses import dataclass

from app.ingestion.normalizer import IngestionValidationError, normalize_whitespace


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    bm25_text: str
    metadata: dict[str, int]


def build_bm25_text(text: str) -> str:
    lowered = text.lower()
    without_punctuation = re.sub(r"[^\w\s]", " ", lowered)
    return normalize_whitespace(without_punctuation)


def trailing_overlap_words(text: str, chunk_overlap: int) -> list[str]:
    if chunk_overlap <= 0:
        return []
    words = text.split()
    selected: list[str] = []
    current_length = 0
    for word in reversed(words):
        next_length = current_length + len(word) + (1 if selected else 0)
        if selected and next_length > chunk_overlap:
            break
        selected.append(word)
        current_length = next_length
    return list(reversed(selected))


def chunk_text(raw_text: str, chunk_size: int = 900, chunk_overlap: int = 150) -> list[TextChunk]:
    text = normalize_whitespace(raw_text)
    if not text:
        raise IngestionValidationError("raw_text must not be empty")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must not be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    words = text.split()
    chunks: list[str] = []
    current_words: list[str] = []

    for word in words:
        candidate = " ".join([*current_words, word]) if current_words else word
        if current_words and len(candidate) > chunk_size:
            chunk = " ".join(current_words)
            chunks.append(chunk)
            current_words = [*trailing_overlap_words(chunk, chunk_overlap), word]
        else:
            current_words.append(word)

    if current_words:
        chunks.append(" ".join(current_words))

    return [
        TextChunk(
            chunk_index=index,
            text=chunk,
            bm25_text=build_bm25_text(chunk),
            metadata={
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            },
        )
        for index, chunk in enumerate(chunks)
    ]
