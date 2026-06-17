from __future__ import annotations

import re

from app.events.rules import DEFAULT_EVENT_RULES, EventRule, normalize_for_matching
from app.events.types import ExtractedEvent

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_RE = re.compile(r"\s+")


class EventExtractor:
    def __init__(
        self,
        *,
        rules: tuple[EventRule, ...] = DEFAULT_EVENT_RULES,
        min_confidence: float = 0.55,
        max_text_length: int = 280,
    ) -> None:
        self.rules = rules
        self.min_confidence = min_confidence
        self.max_text_length = max_text_length

    def extract(self, *, text: str, title: str = "") -> list[ExtractedEvent]:
        matches = []
        for rule in self.rules:
            match = rule.match(text=text, title=title)
            if match is None or match.confidence < self.min_confidence:
                continue

            matches.append(
                ExtractedEvent(
                    event_type=match.event_type,
                    sentiment=match.sentiment,
                    confidence=match.confidence,
                    extracted_text=extract_text_window(
                        text=text,
                        anchor_phrase=match.anchor_phrase,
                        max_length=self.max_text_length,
                    ),
                    matched_required=match.matched_required,
                    matched_optional=match.matched_optional,
                    matched_negative=match.matched_negative,
                )
            )

        return matches


def extract_text_window(*, text: str, anchor_phrase: str, max_length: int = 280) -> str:
    compact_text = _WHITESPACE_RE.sub(" ", text).strip()
    if not compact_text:
        return ""
    if len(compact_text) <= max_length:
        return compact_text

    sentence = _first_matching_sentence(compact_text, anchor_phrase)
    if sentence:
        return _trim_to_word_boundary(sentence, max_length=max_length)

    return _centered_window(compact_text, anchor_phrase=anchor_phrase, max_length=max_length)


def _first_matching_sentence(text: str, anchor_phrase: str) -> str | None:
    normalized_anchor = normalize_for_matching(anchor_phrase)
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        if normalized_anchor and normalized_anchor in normalize_for_matching(sentence):
            return sentence.strip()
    return None


def _centered_window(text: str, *, anchor_phrase: str, max_length: int) -> str:
    normalized_text = normalize_for_matching(text)
    normalized_anchor = normalize_for_matching(anchor_phrase)
    anchor_position = normalized_text.find(normalized_anchor)

    if anchor_position < 0:
        return _trim_to_word_boundary(text, max_length=max_length)

    start = max(0, anchor_position - max_length // 2)
    end = min(len(text), start + max_length)
    return _trim_edges_to_word_boundary(text[start:end], max_length=max_length)


def _trim_to_word_boundary(text: str, *, max_length: int) -> str:
    if len(text) <= max_length:
        return text.strip()
    return _trim_edges_to_word_boundary(text[:max_length], max_length=max_length)


def _trim_edges_to_word_boundary(text: str, *, max_length: int) -> str:
    clipped = text[:max_length].strip()
    if len(clipped) == max_length and " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    if clipped and not clipped[0].isalnum() and " " in clipped:
        clipped = clipped.split(" ", 1)[1]
    return clipped.strip()
