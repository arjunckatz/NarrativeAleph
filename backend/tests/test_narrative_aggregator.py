from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.narratives.aggregator import NarrativeAggregator


@dataclass(frozen=True)
class EventLike:
    ticker: str
    event_type: str
    event_date: date
    confidence: Decimal
    id: int | None = None


def test_multiple_events_aggregate_into_one_narrative() -> None:
    events = [
        EventLike("NVDA", "export_restriction", date(2026, 6, 1), Decimal("0.70"), 10),
        EventLike("NVDA", "export_restriction", date(2026, 6, 3), Decimal("0.90"), 11),
    ]

    candidates = NarrativeAggregator().aggregate(events)

    assert len(candidates) == 1
    assert candidates[0].narrative_name == "Export Restrictions"
    assert candidates[0].ticker == "NVDA"
    assert candidates[0].event_count == 2
    assert candidates[0].supporting_event_ids == (10, 11)


def test_different_event_types_map_to_different_narratives() -> None:
    events = [
        EventLike("NVDA", "earnings_beat", date(2026, 6, 1), Decimal("0.80")),
        EventLike("NVDA", "earnings_miss", date(2026, 6, 2), Decimal("0.75")),
    ]

    candidates = NarrativeAggregator().aggregate(events)

    assert [candidate.narrative_name for candidate in candidates] == [
        "Earnings Strength",
        "Earnings Weakness",
    ]


def test_confidence_rollups_are_correct() -> None:
    events = [
        EventLike("TSLA", "demand_slowdown", date(2026, 5, 1), Decimal("0.60")),
        EventLike("TSLA", "demand_slowdown", date(2026, 5, 2), Decimal("0.90")),
    ]

    candidate = NarrativeAggregator().aggregate(events)[0]

    assert candidate.average_confidence == 0.75
    assert candidate.max_confidence == 0.9


def test_first_seen_and_last_seen_are_correct() -> None:
    events = [
        EventLike("AAPL", "guidance_cut", date(2026, 7, 5), Decimal("0.80")),
        EventLike("AAPL", "guidance_cut", date(2026, 7, 1), Decimal("0.70")),
    ]

    candidate = NarrativeAggregator().aggregate(events)[0]

    assert candidate.first_seen == date(2026, 7, 1)
    assert candidate.last_seen == date(2026, 7, 5)


def test_ticker_filter_works() -> None:
    events = [
        EventLike("NVDA", "margin_pressure", date(2026, 6, 1), Decimal("0.80")),
        EventLike("AAPL", "margin_pressure", date(2026, 6, 1), Decimal("0.80")),
    ]

    candidates = NarrativeAggregator().aggregate(events, ticker="nvda")

    assert len(candidates) == 1
    assert candidates[0].ticker == "NVDA"


def test_date_filter_works() -> None:
    events = [
        EventLike("NVDA", "guidance_cut", date(2026, 5, 31), Decimal("0.80")),
        EventLike("NVDA", "guidance_cut", date(2026, 6, 2), Decimal("0.70")),
        EventLike("NVDA", "guidance_cut", date(2026, 6, 7), Decimal("0.90")),
    ]

    candidates = NarrativeAggregator().aggregate(
        events,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
    )

    assert len(candidates) == 1
    assert candidates[0].event_count == 1
    assert candidates[0].first_seen == date(2026, 6, 2)


def test_unknown_event_types_are_ignored_cleanly() -> None:
    events = [
        EventLike("NVDA", "product_launch", date(2026, 6, 1), Decimal("0.80"), 20),
        EventLike("NVDA", "earnings_beat", date(2026, 6, 2), Decimal("0.85"), 21),
    ]

    candidates = NarrativeAggregator().aggregate(events)

    assert len(candidates) == 1
    assert candidates[0].narrative_name == "Earnings Strength"
    assert candidates[0].supporting_event_ids == (21,)
