from datetime import date
from decimal import Decimal

import pytest
from app.db.base import Base
from app.explain.service import ExplainService
from app.models import Event
from sqlalchemy import create_engine, event
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
        extracted_text=f"{ticker} {event_type}",
        sentiment="negative",
        confidence=confidence,
        metadata_=metadata if metadata is not None else {"test": True},
    )
    session.add(event_row)
    session.commit()
    return event_row


def test_explain_returns_top_narratives_for_ticker(db_session: Session) -> None:
    add_event(db_session, ticker="NVDA", event_type="export_restriction")
    add_event(db_session, ticker="AAPL", event_type="export_restriction")

    result = ExplainService(db_session).explain(ticker="nvda")

    assert result.ticker == "NVDA"
    assert len(result.top_narratives) == 1
    assert result.top_narratives[0].narrative_name == "Export Restrictions"


def test_limit_works(db_session: Session) -> None:
    add_event(db_session, event_type="export_restriction", confidence=Decimal("0.90"))
    add_event(db_session, event_type="margin_pressure", confidence=Decimal("0.80"))

    result = ExplainService(db_session).explain(ticker="NVDA", limit=1)

    assert len(result.top_narratives) == 1


def test_empty_narratives_return_safe_summary(db_session: Session) -> None:
    result = ExplainService(db_session).explain(ticker="nvda")

    assert result.ticker == "NVDA"
    assert result.top_narratives == ()
    assert result.explanation_summary == "For NVDA, no active narratives were detected."


def test_explanation_summary_is_deterministic(db_session: Session) -> None:
    add_event(db_session, event_type="export_restriction", confidence=Decimal("0.80"))
    add_event(db_session, event_type="export_restriction", confidence=Decimal("0.84"))
    add_event(db_session, event_type="margin_pressure", confidence=Decimal("0.70"))

    service = ExplainService(db_session)
    first = service.explain(ticker="NVDA")
    second = service.explain(ticker="NVDA")

    assert first.explanation_summary == second.explanation_summary
    assert first.explanation_summary == (
        "For NVDA, the strongest detected narrative is Export Restrictions, "
        "supported by 2 extracted events with average confidence 0.82. "
        "Other active narratives include Margin Pressure."
    )


def test_response_includes_supporting_evidence(db_session: Session) -> None:
    event_row = add_event(
        db_session,
        metadata={
            "document_id": 10,
            "chunk_id": 20,
            "document_title": "NVDA export controls",
            "source_type": "synthetic",
        },
    )

    result = ExplainService(db_session).explain(ticker="NVDA")

    evidence = result.top_narratives[0].supporting_evidence[0]
    assert evidence.event_id == event_row.id
    assert evidence.event_type == "export_restriction"
    assert evidence.document_id == 10
    assert evidence.chunk_id == 20


def test_date_filters_are_passed_through(db_session: Session) -> None:
    add_event(db_session, event_date=date(2026, 5, 31))
    add_event(db_session, event_date=date(2026, 6, 2))

    result = ExplainService(db_session).explain(
        ticker="NVDA",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
    )

    assert result.start_date == date(2026, 6, 1)
    assert result.end_date == date(2026, 6, 5)
    assert result.top_narratives[0].event_count == 1
    assert result.top_narratives[0].first_seen == date(2026, 6, 2)
