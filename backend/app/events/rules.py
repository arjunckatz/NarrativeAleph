from __future__ import annotations

import re
from dataclasses import dataclass

from app.events.types import EventType, Sentiment

_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


def clamp_confidence(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def normalize_for_matching(text: str) -> str:
    lowered = text.lower()
    without_punctuation = _NON_WORD_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", without_punctuation).strip()


def phrase_matches(phrase: str, normalized_text: str) -> bool:
    normalized_phrase = normalize_for_matching(phrase)
    return bool(normalized_phrase and normalized_phrase in normalized_text)


@dataclass(frozen=True)
class RuleMatch:
    event_type: EventType
    sentiment: Sentiment
    confidence: float
    matched_required: tuple[str, ...]
    matched_optional: tuple[str, ...]
    matched_negative: tuple[str, ...]
    anchor_phrase: str


@dataclass(frozen=True)
class EventRule:
    event_type: EventType
    sentiment: Sentiment
    required_phrases: tuple[str, ...]
    optional_phrases: tuple[str, ...] = ()
    negative_phrases: tuple[str, ...] = ()

    def match(self, *, text: str, title: str = "") -> RuleMatch | None:
        normalized_text = normalize_for_matching(text)
        normalized_title = normalize_for_matching(title)

        matched_required = self._matched_phrases(self.required_phrases, normalized_text)
        if not matched_required:
            return None

        matched_optional = self._matched_phrases(self.optional_phrases, normalized_text)
        matched_negative = self._matched_phrases(self.negative_phrases, normalized_text)
        title_match = self._has_title_match(
            normalized_title=normalized_title,
            matched_phrases=matched_required + matched_optional,
        )

        confidence = self._score(
            required_count=len(matched_required),
            optional_count=len(matched_optional),
            negative_count=len(matched_negative),
            title_match=title_match,
        )

        return RuleMatch(
            event_type=self.event_type,
            sentiment=self.sentiment,
            confidence=confidence,
            matched_required=matched_required,
            matched_optional=matched_optional,
            matched_negative=matched_negative,
            anchor_phrase=matched_required[0],
        )

    def _score(
        self,
        *,
        required_count: int,
        optional_count: int,
        negative_count: int,
        title_match: bool,
    ) -> float:
        score = 0.6
        score += 0.1 * min(optional_count, 2)
        score += 0.1 if title_match else 0.0
        score += 0.05 * max(required_count - 1, 0)
        score -= 0.4 * negative_count
        return clamp_confidence(score)

    @staticmethod
    def _matched_phrases(phrases: tuple[str, ...], normalized_text: str) -> tuple[str, ...]:
        return tuple(phrase for phrase in phrases if phrase_matches(phrase, normalized_text))

    @staticmethod
    def _has_title_match(
        *,
        normalized_title: str,
        matched_phrases: tuple[str, ...],
    ) -> bool:
        return any(phrase_matches(phrase, normalized_title) for phrase in matched_phrases)


DEFAULT_EVENT_RULES: tuple[EventRule, ...] = (
    EventRule(
        event_type=EventType.EXPORT_RESTRICTION,
        sentiment="negative",
        required_phrases=(
            "export restriction",
            "export restrictions",
            "export control",
            "export controls",
            "export license",
            "license requirements",
            "restricted accelerator",
            "shipment restrictions",
        ),
        optional_phrases=("china", "shipment", "compliant chip", "accelerator"),
        negative_phrases=(
            "restriction eased",
            "restrictions eased",
            "no export restriction",
            "not subject to export restriction",
        ),
    ),
    EventRule(
        event_type=EventType.DEMAND_SLOWDOWN,
        sentiment="negative",
        required_phrases=(
            "demand slowdown",
            "soft demand",
            "weaker demand",
            "demand softened",
            "slowing demand",
            "slower demand",
            "order slowdown",
        ),
        optional_phrases=("channel checks", "replacement cycle", "inventory", "orders"),
        negative_phrases=(
            "demand remains strong",
            "demand accelerated",
            "robust demand",
            "no demand slowdown",
        ),
    ),
    EventRule(
        event_type=EventType.MARGIN_PRESSURE,
        sentiment="negative",
        required_phrases=(
            "margin pressure",
            "gross margin pressure",
            "pricing pressure",
            "depreciation pressure",
            "cost pressure",
            "gross margins compressed",
        ),
        optional_phrases=("discounting", "incentives", "capex", "operating leverage"),
        negative_phrases=(
            "margin expansion",
            "margins improved",
            "no margin pressure",
            "without margin pressure",
        ),
    ),
    EventRule(
        event_type=EventType.EARNINGS_BEAT,
        sentiment="positive",
        required_phrases=(
            "earnings beat",
            "beat estimates",
            "beat expectations",
            "above consensus",
            "better than expected earnings",
            "topped expectations",
        ),
        optional_phrases=("revenue beat", "eps beat", "strong quarter"),
        negative_phrases=("missed estimates", "below consensus", "not an earnings beat"),
    ),
    EventRule(
        event_type=EventType.EARNINGS_MISS,
        sentiment="negative",
        required_phrases=(
            "earnings miss",
            "missed estimates",
            "missed expectations",
            "below consensus",
            "weaker than expected earnings",
        ),
        optional_phrases=("revenue miss", "eps miss", "weak quarter"),
        negative_phrases=("beat estimates", "above consensus", "not an earnings miss"),
    ),
    EventRule(
        event_type=EventType.GUIDANCE_CUT,
        sentiment="negative",
        required_phrases=(
            "guidance cut",
            "cut guidance",
            "lowered guidance",
            "reduced outlook",
            "lowered forecast",
            "trimmed outlook",
        ),
        optional_phrases=("full year", "next quarter", "revenue outlook", "margin outlook"),
        negative_phrases=(
            "raised guidance",
            "guidance raise",
            "reaffirmed guidance",
            "guidance unchanged",
            "did not cut guidance",
        ),
    ),
)
