from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SearchDocument(BaseModel):
    id: int
    ticker: str
    source_type: str
    title: str
    published_at: datetime
    source_name: str
    url: str | None
    metadata: dict[str, Any]


class SearchChunk(BaseModel):
    id: int
    chunk_index: int
    metadata: dict[str, Any]


class SearchResult(BaseModel):
    score: float | None = None
    snippet: str | None = None
    document: SearchDocument
    chunk: SearchChunk


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
