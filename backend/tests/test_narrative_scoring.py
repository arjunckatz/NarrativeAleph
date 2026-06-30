from datetime import date

from app.narratives.aggregator import NarrativeCandidate
from app.narratives.scoring import NarrativeScorer


def make_candidate(**overrides) -> NarrativeCandidate:
    values = {
        "narrative_name": "Export Restrictions",
        "ticker": "NVDA",
        "event_count": 2,
        "average_confidence": 0.75,
        "max_confidence": 0.85,
        "first_seen": date(2026, 6, 1),
        "last_seen": date(2026, 6, 5),
        "event_types": ("export_restriction",),
        "supporting_event_ids": (1, 2),
    }
    values.update(overrides)
    return NarrativeCandidate(**values)


def score(candidate: NarrativeCandidate):
    return NarrativeScorer().score(
        candidate,
        range_start=date(2026, 6, 1),
        range_end=date(2026, 6, 10),
    )


def test_score_is_deterministic() -> None:
    candidate = make_candidate()

    assert score(candidate) == score(candidate)


def test_score_components_are_demo_readable() -> None:
    result = NarrativeScorer().score(
        make_candidate(
            event_count=3,
            average_confidence=0.8333,
            max_confidence=0.95,
            first_seen=date(2026, 5, 1),
            last_seen=date(2026, 5, 6),
        ),
        range_start=date(2026, 5, 1),
        range_end=date(2026, 5, 6),
    )

    assert result.score == 73.67
    assert result.components["confidence_score"] == 35.67


def test_higher_confidence_increases_score() -> None:
    lower = score(make_candidate(average_confidence=0.6, max_confidence=0.7))
    higher = score(make_candidate(average_confidence=0.8, max_confidence=0.9))

    assert higher.score > lower.score
    assert higher.components["confidence_score"] > lower.components["confidence_score"]


def test_more_events_increases_score_until_cap() -> None:
    fewer = score(make_candidate(event_count=1))
    more = score(make_candidate(event_count=4))

    assert more.score > fewer.score
    assert more.components["event_count_score"] > fewer.components["event_count_score"]


def test_recent_narrative_scores_higher_within_date_range() -> None:
    older = score(make_candidate(last_seen=date(2026, 6, 2)))
    newer = score(make_candidate(last_seen=date(2026, 6, 9)))

    assert newer.score > older.score
    assert newer.components["recency_score"] > older.components["recency_score"]


def test_event_type_diversity_adds_small_boost() -> None:
    single_type = score(make_candidate(event_types=("export_restriction",)))
    diverse = score(
        make_candidate(
            event_types=("export_restriction", "regulatory_risk"),
        )
    )

    assert diverse.score > single_type.score
    assert 0 < diverse.components["event_type_diversity_score"] <= 10
