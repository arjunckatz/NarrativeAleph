from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class SupportingEvidenceResponse(BaseModel):
    event_id: int
    event_type: str
    confidence: float
    extracted_text: str
    document_id: int | None = None
    chunk_id: int | None = None
    document_title: str | None = None
    source_type: str | None = None


class NarrativeCandidateResponse(BaseModel):
    narrative_name: str
    ticker: str
    event_count: int
    average_confidence: float
    max_confidence: float
    first_seen: date
    last_seen: date
    event_types: tuple[str, ...]
    supporting_event_ids: tuple[int, ...]
    score: float | None = None
    score_components: dict[str, float] | None = None
    supporting_evidence: tuple[SupportingEvidenceResponse, ...] = ()
