from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.narratives.aggregator import NarrativeCandidate
from app.narratives.service import NarrativeAggregationService


@dataclass(frozen=True)
class ExplainResult:
    ticker: str
    start_date: date | None
    end_date: date | None
    top_narratives: tuple[NarrativeCandidate, ...]
    explanation_summary: str


class ExplainService:
    def __init__(
        self,
        session: Session,
        narrative_service: NarrativeAggregationService | None = None,
    ) -> None:
        self.narrative_service = narrative_service or NarrativeAggregationService(session)

    def explain(
        self,
        *,
        ticker: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 3,
    ) -> ExplainResult:
        normalized_ticker = ticker.upper()
        narratives = self.narrative_service.aggregate(
            ticker=normalized_ticker,
            start_date=start_date,
            end_date=end_date,
        )
        top_narratives = tuple(narratives[:limit])
        return ExplainResult(
            ticker=normalized_ticker,
            start_date=start_date,
            end_date=end_date,
            top_narratives=top_narratives,
            explanation_summary=self._summary(normalized_ticker, top_narratives),
        )

    def _summary(
        self,
        ticker: str,
        narratives: tuple[NarrativeCandidate, ...],
    ) -> str:
        if not narratives:
            return f"For {ticker}, no active narratives were detected."

        strongest = narratives[0]
        summary = (
            f"For {ticker}, the strongest detected narrative is "
            f"{strongest.narrative_name}, supported by {strongest.event_count} "
            f"extracted events with average confidence "
            f"{strongest.average_confidence:.2f}."
        )
        other_narratives = [item.narrative_name for item in narratives[1:]]
        if other_narratives:
            summary += (
                " Other active narratives include "
                f"{self._join_names(other_narratives)}."
            )
        return summary

    @staticmethod
    def _join_names(names: list[str]) -> str:
        if len(names) == 1:
            return names[0]
        return f"{', '.join(names[:-1])} and {names[-1]}"
