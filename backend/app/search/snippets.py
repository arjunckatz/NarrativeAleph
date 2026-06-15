from __future__ import annotations

import re

from app.ingestion.chunking import build_bm25_text
from app.ingestion.normalizer import normalize_whitespace

DEFAULT_SNIPPET_LENGTH = 280


def generate_snippet(query: str, text: str, max_length: int = DEFAULT_SNIPPET_LENGTH) -> str:
    normalized_text = normalize_whitespace(text)
    if len(normalized_text) <= max_length:
        return normalized_text

    match_start = first_query_match_start(query, normalized_text)
    if match_start is None:
        return trim_to_word_boundary(normalized_text, 0, max_length)

    start = max(match_start - max_length // 2, 0)
    end = start + max_length
    if end > len(normalized_text):
        end = len(normalized_text)
        start = max(end - max_length, 0)

    return trim_to_word_boundary(normalized_text, start, end)


def first_query_match_start(query: str, text: str) -> int | None:
    query_terms = build_bm25_text(query).split()
    matches: list[int] = []
    for term in query_terms:
        match = re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE)
        if match:
            matches.append(match.start())
    return min(matches) if matches else None


def trim_to_word_boundary(text: str, start: int, end: int) -> str:
    if start > 0:
        next_space = text.find(" ", start)
        if next_space != -1 and next_space < end:
            start = next_space + 1

    if end < len(text):
        previous_space = text.rfind(" ", start, end)
        if previous_space > start:
            end = previous_space

    return text[start:end].strip()
