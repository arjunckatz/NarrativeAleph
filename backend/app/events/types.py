from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class EventType(StrEnum):
    EXPORT_RESTRICTION = "export_restriction"
    DEMAND_SLOWDOWN = "demand_slowdown"
    MARGIN_PRESSURE = "margin_pressure"
    EARNINGS_BEAT = "earnings_beat"
    EARNINGS_MISS = "earnings_miss"
    GUIDANCE_CUT = "guidance_cut"


Sentiment = Literal["positive", "negative", "neutral"]


@dataclass(frozen=True)
class ExtractedEvent:
    event_type: EventType
    sentiment: Sentiment
    confidence: float
    extracted_text: str
    matched_required: tuple[str, ...]
    matched_optional: tuple[str, ...]
    matched_negative: tuple[str, ...]
