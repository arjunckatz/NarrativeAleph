from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.schemas.narratives import SupportingEvidenceResponse


class ExplainNarrativeResponse(BaseModel):
    narrative_name: str
    score: float | None = None
    score_components: dict[str, float] | None = None
    event_count: int
    average_confidence: float
    max_confidence: float
    first_seen: date
    last_seen: date
    supporting_evidence: tuple[SupportingEvidenceResponse, ...] = ()


class ExplainResponse(BaseModel):
    ticker: str
    start_date: date | None = None
    end_date: date | None = None
    top_narratives: tuple[ExplainNarrativeResponse, ...]
    explanation_summary: str
