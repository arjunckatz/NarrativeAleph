from __future__ import annotations

from dataclasses import replace
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event
from app.narratives.aggregator import (
    NarrativeAggregator,
    NarrativeCandidate,
    SupportingEvidence,
)
from app.narratives.scoring import NarrativeScorer


class NarrativeAggregationService:
    def __init__(
        self,
        session: Session,
        aggregator: NarrativeAggregator | None = None,
        scorer: NarrativeScorer | None = None,
    ) -> None:
        self.session = session
        self.aggregator = aggregator or NarrativeAggregator()
        self.scorer = scorer or NarrativeScorer()

    def aggregate(
        self,
        *,
        ticker: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[NarrativeCandidate]:
        events = self._load_events(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )
        candidates = self.aggregator.aggregate(events)
        if not candidates:
            return []

        range_start = start_date or min(candidate.first_seen for candidate in candidates)
        range_end = end_date or max(candidate.last_seen for candidate in candidates)
        scored_candidates = []
        events_by_id = {event.id: event for event in events}
        for candidate in candidates:
            score_result = self.scorer.score(
                candidate,
                range_start=range_start,
                range_end=range_end,
            )
            scored_candidates.append(
                replace(
                    candidate,
                    score=score_result.score,
                    score_components=score_result.components,
                    supporting_evidence=self._supporting_evidence(
                        candidate,
                        events_by_id,
                    ),
                )
            )

        return sorted(
            scored_candidates,
            key=lambda candidate: (
                -(candidate.score or 0.0),
                -candidate.event_count,
                -candidate.max_confidence,
                candidate.narrative_name,
                candidate.ticker,
            ),
        )

    def _supporting_evidence(
        self,
        candidate: NarrativeCandidate,
        events_by_id: dict[int, Event],
    ) -> tuple[SupportingEvidence, ...]:
        evidence = []
        for event_id in candidate.supporting_event_ids:
            event = events_by_id.get(event_id)
            if event is None:
                continue

            metadata = event.metadata_ or {}
            evidence.append(
                SupportingEvidence(
                    event_id=event.id,
                    event_type=event.event_type,
                    confidence=round(float(event.confidence), 4),
                    extracted_text=event.extracted_text,
                    document_id=metadata.get("document_id"),
                    chunk_id=metadata.get("chunk_id"),
                    document_title=metadata.get("document_title"),
                    source_type=metadata.get("source_type"),
                )
            )
        return tuple(evidence)

    def _load_events(
        self,
        *,
        ticker: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[Event]:
        statement = select(Event).order_by(
            Event.ticker.asc(),
            Event.event_date.asc(),
            Event.id.asc(),
        )
        if ticker:
            statement = statement.where(Event.ticker == ticker.upper())
        if start_date:
            statement = statement.where(Event.event_date >= start_date)
        if end_date:
            statement = statement.where(Event.event_date <= end_date)
        return list(self.session.scalars(statement).all())
