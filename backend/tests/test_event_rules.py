from app.events.rules import DEFAULT_EVENT_RULES
from app.events.types import EventType


def _rule_for(event_type: EventType):
    return next(rule for rule in DEFAULT_EVENT_RULES if rule.event_type == event_type)


def test_rule_matches_clear_positive_signal() -> None:
    rule = _rule_for(EventType.EXPORT_RESTRICTION)

    match = rule.match(
        text="New export restrictions could delay China accelerator shipments.",
        title="NVDA export update",
    )

    assert match is not None
    assert match.event_type == EventType.EXPORT_RESTRICTION
    assert "export restrictions" in match.matched_required
    assert match.confidence > 0


def test_negative_phrases_reduce_confidence() -> None:
    rule = _rule_for(EventType.GUIDANCE_CUT)

    base_match = rule.match(text="The company lowered guidance for the full year.")
    negative_match = rule.match(
        text="The company lowered guidance for the full year but also reaffirmed guidance."
    )

    assert base_match is not None
    assert negative_match is not None
    assert negative_match.confidence < base_match.confidence
    assert "reaffirmed guidance" in negative_match.matched_negative


def test_optional_phrases_boost_confidence() -> None:
    rule = _rule_for(EventType.MARGIN_PRESSURE)

    base_match = rule.match(text="Analysts flagged margin pressure.")
    optional_match = rule.match(
        text="Analysts flagged margin pressure from discounting, incentives, and capex."
    )

    assert base_match is not None
    assert optional_match is not None
    assert optional_match.confidence > base_match.confidence


def test_title_match_boosts_confidence() -> None:
    rule = _rule_for(EventType.EARNINGS_BEAT)

    no_title_match = rule.match(text="The company posted an earnings beat.")
    title_match = rule.match(
        text="The company posted an earnings beat.",
        title="Earnings beat lifts shares",
    )

    assert no_title_match is not None
    assert title_match is not None
    assert title_match.confidence > no_title_match.confidence
