from app.events.extractor import EventExtractor
from app.events.types import EventType


def _event_types_for(text: str, title: str = "") -> set[EventType]:
    return {event.event_type for event in EventExtractor().extract(text=text, title=title)}


def test_extracts_export_restriction_event() -> None:
    event_types = _event_types_for(
        "New export controls may limit NVDA accelerator shipments to China.",
        "Export controls hit AI chips",
    )

    assert EventType.EXPORT_RESTRICTION in event_types


def test_extracts_demand_slowdown_event() -> None:
    event_types = _event_types_for(
        "Channel checks point to weaker demand as inventory builds across resellers."
    )

    assert EventType.DEMAND_SLOWDOWN in event_types


def test_extracts_margin_pressure_event() -> None:
    event_types = _event_types_for(
        "Management said gross margin pressure reflected discounting and higher costs."
    )

    assert EventType.MARGIN_PRESSURE in event_types


def test_extracts_earnings_beat_event() -> None:
    event_types = _event_types_for(
        "The company delivered an earnings beat with revenue beat and EPS beat signals."
    )

    assert EventType.EARNINGS_BEAT in event_types


def test_extracts_earnings_miss_event() -> None:
    event_types = _event_types_for(
        "The company reported an earnings miss after revenue miss and weak quarter commentary."
    )

    assert EventType.EARNINGS_MISS in event_types


def test_extracts_guidance_cut_event() -> None:
    event_types = _event_types_for(
        "Executives cut guidance for the full year and lowered the revenue outlook."
    )

    assert EventType.GUIDANCE_CUT in event_types


def test_confidence_is_deterministic() -> None:
    extractor = EventExtractor()
    text = "New export restrictions could delay China accelerator shipments."

    first = extractor.extract(text=text)
    second = extractor.extract(text=text)

    assert first == second


def test_unrelated_text_produces_no_events() -> None:
    events = EventExtractor().extract(
        text="The company opened a new office and discussed long-term hiring plans."
    )

    assert events == []


def test_extracted_text_is_non_empty_and_bounded() -> None:
    text = (
        "This opening sentence is background context. "
        "Analysts flagged margin pressure from discounting and incentives in the quarter. "
        "Additional commentary described operations, hiring, and regional expansion plans. "
        * 5
    )

    events = EventExtractor().extract(text=text)

    assert events
    assert all(event.extracted_text for event in events)
    assert all(len(event.extracted_text) <= 280 for event in events)
