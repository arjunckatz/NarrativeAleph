from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.narratives.mapping import narrative_name_for_event_type


@dataclass(frozen=True)
class NarrativeCandidate:
    narrative_name: str
    ticker: str
    event_count: int
    average_confidence: float
    max_confidence: float
    first_seen: date
    last_seen: date
    event_types: tuple[str, ...]
    supporting_event_ids: tuple[int, ...]


@dataclass
class _NarrativeBucket:
    confidences: list[float]
    dates: list[date]
    event_types: set[str]
    supporting_event_ids: list[int]


class NarrativeAggregator:
    def aggregate(
        self,
        events: list[Any],
        *,
        ticker: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[NarrativeCandidate]:
        ticker_filter = ticker.upper() if ticker else None
        buckets: dict[tuple[str, str], _NarrativeBucket] = defaultdict(
            lambda: _NarrativeBucket([], [], set(), [])
        )

        for event in events:
            if not self._passes_filters(
                event,
                ticker=ticker_filter,
                start_date=start_date,
                end_date=end_date,
            ):
                continue

            event_type = str(event.event_type)
            narrative_name = narrative_name_for_event_type(event_type)
            if narrative_name is None:
                continue

            key = (event.ticker, narrative_name)
            bucket = buckets[key]
            bucket.confidences.append(float(event.confidence))
            bucket.dates.append(event.event_date)
            bucket.event_types.add(event_type)

            event_id = getattr(event, "id", None)
            if event_id is not None:
                bucket.supporting_event_ids.append(event_id)

        return [
            self._candidate_from_bucket(
                ticker=key[0],
                narrative_name=key[1],
                bucket=bucket,
            )
            for key, bucket in sorted(buckets.items())
        ]

    def _passes_filters(
        self,
        event: Any,
        *,
        ticker: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> bool:
        if ticker and event.ticker.upper() != ticker:
            return False
        if start_date and event.event_date < start_date:
            return False
        return not (end_date and event.event_date > end_date)

    def _candidate_from_bucket(
        self,
        *,
        ticker: str,
        narrative_name: str,
        bucket: _NarrativeBucket,
    ) -> NarrativeCandidate:
        event_count = len(bucket.confidences)
        average_confidence = sum(bucket.confidences) / event_count
        return NarrativeCandidate(
            narrative_name=narrative_name,
            ticker=ticker,
            event_count=event_count,
            average_confidence=round(average_confidence, 4),
            max_confidence=round(max(bucket.confidences), 4),
            first_seen=min(bucket.dates),
            last_seen=max(bucket.dates),
            event_types=tuple(sorted(bucket.event_types)),
            supporting_event_ids=tuple(bucket.supporting_event_ids),
        )
