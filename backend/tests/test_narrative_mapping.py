from app.events.types import EventType
from app.narratives.mapping import EVENT_TYPE_TO_NARRATIVE, narrative_name_for_event_type


def test_event_types_map_to_expected_narratives() -> None:
    assert EVENT_TYPE_TO_NARRATIVE == {
        "export_restriction": "Export Restrictions",
        "demand_slowdown": "Demand Slowdown",
        "margin_pressure": "Margin Pressure",
        "earnings_beat": "Earnings Strength",
        "earnings_miss": "Earnings Weakness",
        "guidance_cut": "Guidance Concerns",
    }


def test_mapping_accepts_event_type_enum() -> None:
    assert narrative_name_for_event_type(EventType.EARNINGS_BEAT) == "Earnings Strength"


def test_unknown_event_type_returns_none() -> None:
    assert narrative_name_for_event_type("product_launch") is None
