from datetime import date
from decimal import Decimal

import pytest
from app.db.base import Base
from app.models import Event, Narrative, NarrativeEvidence, NarrativeScore
from app.narratives.service import NarrativeAggregationService
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def add_event(
    session: Session,
    *,
    ticker: str = "NVDA",
    event_type: str = "export_restriction",
    event_date: date = date(2026, 6, 1),
    confidence: Decimal = Decimal("0.80"),
    metadata: dict | None = None,
) -> Event:
    event_row = Event(
        ticker=ticker,
        event_type=event_type,
        event_date=event_date,
        extracted_text=f"{ticker} {event_type} event",
        sentiment="negative",
        confidence=confidence,
        metadata_=metadata if metadata is not None else {"test": True},
    )
    session.add(event_row)
    session.commit()
    return event_row


def test_service_reads_event_rows_and_returns_narrative_candidates(db_session: Session) -> None:
    event_row = add_event(db_session)

    candidates = NarrativeAggregationService(db_session).aggregate()

    assert len(candidates) == 1
    assert candidates[0].narrative_name == "Export Restrictions"
    assert candidates[0].ticker == "NVDA"
    assert candidates[0].event_count == 1
    assert candidates[0].average_confidence == 0.8
    assert candidates[0].max_confidence == 0.8
    assert candidates[0].first_seen == date(2026, 6, 1)
    assert candidates[0].last_seen == date(2026, 6, 1)
    assert candidates[0].event_types == ("export_restriction",)
    assert candidates[0].supporting_event_ids == (event_row.id,)
    assert candidates[0].score == 58.0
    assert candidates[0].score_components == {
        "event_count_score": 6.0,
        "confidence_score": 32.0,
        "recency_score": 20.0,
        "event_type_diversity_score": 0.0,
    }
    assert candidates[0].supporting_evidence[0].event_id == event_row.id
    assert candidates[0].supporting_evidence[0].event_type == "export_restriction"


def test_ticker_filter_works(db_session: Session) -> None:
    add_event(db_session, ticker="NVDA", event_type="margin_pressure")
    add_event(db_session, ticker="AAPL", event_type="margin_pressure")

    candidates = NarrativeAggregationService(db_session).aggregate(ticker="nvda")

    assert len(candidates) == 1
    assert candidates[0].ticker == "NVDA"


def test_date_filters_work(db_session: Session) -> None:
    add_event(db_session, event_type="guidance_cut", event_date=date(2026, 5, 31))
    add_event(db_session, event_type="guidance_cut", event_date=date(2026, 6, 2))
    add_event(db_session, event_type="guidance_cut", event_date=date(2026, 6, 7))

    candidates = NarrativeAggregationService(db_session).aggregate(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
    )

    assert len(candidates) == 1
    assert candidates[0].event_count == 1
    assert candidates[0].first_seen == date(2026, 6, 2)
    assert candidates[0].last_seen == date(2026, 6, 2)


def test_supporting_evidence_includes_metadata_fields(db_session: Session) -> None:
    event_row = add_event(
        db_session,
        metadata={
            "document_id": 101,
            "chunk_id": 202,
            "chunk_index": 3,
            "document_title": "NVDA export controls update",
            "source_type": "news",
        },
    )

    candidates = NarrativeAggregationService(db_session).aggregate()

    evidence = candidates[0].supporting_evidence[0]
    assert evidence.event_id == event_row.id
    assert evidence.event_type == "export_restriction"
    assert evidence.confidence == 0.8
    assert evidence.extracted_text == "NVDA export_restriction event"
    assert evidence.document_id == 101
    assert evidence.chunk_id == 202
    assert evidence.document_title == "NVDA export controls update"
    assert evidence.source_type == "news"


def test_supporting_evidence_ordering_is_deterministic(db_session: Session) -> None:
    first_event = add_event(db_session, event_date=date(2026, 6, 1))
    second_event = add_event(db_session, event_date=date(2026, 6, 2))

    first = NarrativeAggregationService(db_session).aggregate()
    second = NarrativeAggregationService(db_session).aggregate()

    assert [item.event_id for item in first[0].supporting_evidence] == [
        first_event.id,
        second_event.id,
    ]
    assert first == second


def test_events_without_metadata_return_safe_evidence(db_session: Session) -> None:
    event_row = add_event(db_session, metadata={})

    candidates = NarrativeAggregationService(db_session).aggregate()

    evidence = candidates[0].supporting_evidence[0]
    assert evidence.event_id == event_row.id
    assert evidence.document_id is None
    assert evidence.chunk_id is None
    assert evidence.document_title is None
    assert evidence.source_type is None


def test_multiple_event_types_aggregate_correctly(db_session: Session) -> None:
    add_event(db_session, event_type="earnings_beat", confidence=Decimal("0.90"))
    add_event(db_session, event_type="earnings_miss", confidence=Decimal("0.70"))
    add_event(db_session, event_type="earnings_beat", confidence=Decimal("0.80"))

    candidates = NarrativeAggregationService(db_session).aggregate()

    assert [candidate.narrative_name for candidate in candidates] == [
        "Earnings Strength",
        "Earnings Weakness",
    ]
    assert [candidate.event_count for candidate in candidates] == [2, 1]
    assert candidates[0].average_confidence == 0.85
    assert candidates[0].max_confidence == 0.9


def test_unknown_event_types_are_ignored(db_session: Session) -> None:
    add_event(db_session, event_type="product_launch")
    add_event(db_session, event_type="demand_slowdown")

    candidates = NarrativeAggregationService(db_session).aggregate()

    assert len(candidates) == 1
    assert candidates[0].narrative_name == "Demand Slowdown"


def test_empty_event_table_returns_empty_list(db_session: Session) -> None:
    assert NarrativeAggregationService(db_session).aggregate() == []


def test_output_ordering_is_deterministic(db_session: Session) -> None:
    add_event(
        db_session,
        ticker="TSLA",
        event_type="guidance_cut",
        confidence=Decimal("0.95"),
    )
    add_event(
        db_session,
        ticker="AAPL",
        event_type="earnings_miss",
        confidence=Decimal("0.60"),
    )
    add_event(
        db_session,
        ticker="NVDA",
        event_type="export_restriction",
        confidence=Decimal("0.80"),
    )

    first = NarrativeAggregationService(db_session).aggregate()
    second = NarrativeAggregationService(db_session).aggregate()

    assert first == second
    assert [(candidate.ticker, candidate.narrative_name) for candidate in first] == [
        ("TSLA", "Guidance Concerns"),
        ("NVDA", "Export Restrictions"),
        ("AAPL", "Earnings Weakness"),
    ]
    assert [candidate.score for candidate in first] == sorted(
        (candidate.score for candidate in first),
        reverse=True,
    )


def test_service_is_read_only(db_session: Session) -> None:
    add_event(db_session)

    NarrativeAggregationService(db_session).aggregate()

    assert db_session.scalars(select(Narrative)).all() == []
    assert db_session.scalars(select(NarrativeScore)).all() == []
    assert db_session.scalars(select(NarrativeEvidence)).all() == []
