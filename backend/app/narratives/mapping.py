from __future__ import annotations

from app.events.types import EventType

EVENT_TYPE_TO_NARRATIVE: dict[str, str] = {
    EventType.EXPORT_RESTRICTION.value: "Export Restrictions",
    EventType.DEMAND_SLOWDOWN.value: "Demand Slowdown",
    EventType.MARGIN_PRESSURE.value: "Margin Pressure",
    EventType.EARNINGS_BEAT.value: "Earnings Strength",
    EventType.EARNINGS_MISS.value: "Earnings Weakness",
    EventType.GUIDANCE_CUT.value: "Guidance Concerns",
}


def narrative_name_for_event_type(event_type: str | EventType) -> str | None:
    return EVENT_TYPE_TO_NARRATIVE.get(str(event_type))
