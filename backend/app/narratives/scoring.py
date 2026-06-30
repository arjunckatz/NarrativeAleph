from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.narratives.aggregator import NarrativeCandidate


@dataclass(frozen=True)
class NarrativeScoreResult:
    score: float
    components: dict[str, float]


class NarrativeScorer:
    SCORE_DECIMAL_PLACES = 2
    EVENT_COUNT_WEIGHT = 30.0
    CONFIDENCE_WEIGHT = 40.0
    RECENCY_WEIGHT = 20.0
    DIVERSITY_WEIGHT = 10.0
    EVENT_COUNT_CAP = 5
    EVENT_TYPE_DIVERSITY_CAP = 4

    def score(
        self,
        candidate: NarrativeCandidate,
        *,
        range_start: date,
        range_end: date,
    ) -> NarrativeScoreResult:
        event_count_score = (
            min(candidate.event_count, self.EVENT_COUNT_CAP)
            / self.EVENT_COUNT_CAP
            * self.EVENT_COUNT_WEIGHT
        )
        confidence_score = (
            (candidate.average_confidence + candidate.max_confidence)
            / 2
            * self.CONFIDENCE_WEIGHT
        )
        recency_score = self._recency_ratio(
            last_seen=candidate.last_seen,
            range_start=range_start,
            range_end=range_end,
        ) * self.RECENCY_WEIGHT
        event_type_diversity_score = (
            min(
                max(len(candidate.event_types) - 1, 0),
                self.EVENT_TYPE_DIVERSITY_CAP - 1,
            )
            / (self.EVENT_TYPE_DIVERSITY_CAP - 1)
            * self.DIVERSITY_WEIGHT
        )

        components = {
            "event_count_score": self._round_score(event_count_score),
            "confidence_score": self._round_score(confidence_score),
            "recency_score": self._round_score(recency_score),
            "event_type_diversity_score": self._round_score(
                event_type_diversity_score
            ),
        }
        return NarrativeScoreResult(
            score=self._round_score(sum(components.values())),
            components=components,
        )

    def _round_score(self, value: float) -> float:
        return round(value, self.SCORE_DECIMAL_PLACES)

    @staticmethod
    def _recency_ratio(*, last_seen: date, range_start: date, range_end: date) -> float:
        span_days = (range_end - range_start).days
        if span_days <= 0:
            return 1.0

        elapsed_days = (last_seen - range_start).days
        return max(0.0, min(1.0, elapsed_days / span_days))
