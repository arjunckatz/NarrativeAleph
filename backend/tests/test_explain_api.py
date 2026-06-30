from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Event
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def explain_client() -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, session

    session.close()
    app.dependency_overrides.clear()


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


def test_explain_endpoint_returns_top_narratives_for_ticker(
    explain_client: tuple[TestClient, Session],
) -> None:
    client, session = explain_client
    add_event(session, ticker="NVDA", event_type="export_restriction")
    add_event(session, ticker="AAPL", event_type="export_restriction")

    response = client.get("/api/explain", params={"ticker": "NVDA"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert len(payload["top_narratives"]) == 1
    assert payload["top_narratives"][0]["narrative_name"] == "Export Restrictions"


def test_explain_limit_works(explain_client: tuple[TestClient, Session]) -> None:
    client, session = explain_client
    add_event(session, event_type="export_restriction", confidence=Decimal("0.90"))
    add_event(session, event_type="margin_pressure", confidence=Decimal("0.80"))

    response = client.get("/api/explain", params={"ticker": "NVDA", "limit": 1})

    assert response.status_code == 200
    assert len(response.json()["top_narratives"]) == 1


def test_explain_requires_ticker(explain_client: tuple[TestClient, Session]) -> None:
    client, _session = explain_client

    response = client.get("/api/explain")

    assert response.status_code == 422


def test_explain_normalizes_ticker(explain_client: tuple[TestClient, Session]) -> None:
    client, session = explain_client
    add_event(session, ticker="NVDA")

    response = client.get("/api/explain", params={"ticker": "nvda"})

    assert response.status_code == 200
    assert response.json()["ticker"] == "NVDA"


def test_explain_empty_narratives_returns_safe_response(
    explain_client: tuple[TestClient, Session],
) -> None:
    client, _session = explain_client

    response = client.get("/api/explain", params={"ticker": "NVDA"})

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "NVDA",
        "start_date": None,
        "end_date": None,
        "top_narratives": [],
        "explanation_summary": "For NVDA, no active narratives were detected.",
    }


def test_explain_summary_is_deterministic(
    explain_client: tuple[TestClient, Session],
) -> None:
    client, session = explain_client
    add_event(session, event_type="export_restriction", confidence=Decimal("0.80"))
    add_event(session, event_type="export_restriction", confidence=Decimal("0.84"))
    add_event(session, event_type="margin_pressure", confidence=Decimal("0.70"))

    first = client.get("/api/explain", params={"ticker": "NVDA"})
    second = client.get("/api/explain", params={"ticker": "NVDA"})

    assert first.status_code == 200
    assert first.json()["explanation_summary"] == second.json()["explanation_summary"]
    assert first.json()["explanation_summary"] == (
        "For NVDA, the strongest detected narrative is Export Restrictions, "
        "supported by 2 extracted events with average confidence 0.82. "
        "Other active narratives include Margin Pressure."
    )


def test_explain_response_includes_supporting_evidence(
    explain_client: tuple[TestClient, Session],
) -> None:
    client, session = explain_client
    event_row = add_event(
        session,
        metadata={
            "document_id": 11,
            "chunk_id": 22,
            "document_title": "NVDA export restriction report",
            "source_type": "synthetic",
        },
    )

    response = client.get("/api/explain", params={"ticker": "NVDA"})

    assert response.status_code == 200
    evidence = response.json()["top_narratives"][0]["supporting_evidence"][0]
    assert evidence["event_id"] == event_row.id
    assert evidence["event_type"] == "export_restriction"
    assert evidence["document_id"] == 11
    assert evidence["chunk_id"] == 22


def test_explain_date_filters_are_passed_through(
    explain_client: tuple[TestClient, Session],
) -> None:
    client, session = explain_client
    add_event(session, event_date=date(2026, 5, 31))
    add_event(session, event_date=date(2026, 6, 2))

    response = client.get(
        "/api/explain",
        params={
            "ticker": "NVDA",
            "start_date": "2026-06-01",
            "end_date": "2026-06-05",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["start_date"] == "2026-06-01"
    assert payload["end_date"] == "2026-06-05"
    assert payload["top_narratives"][0]["event_count"] == 1
    assert payload["top_narratives"][0]["first_seen"] == "2026-06-02"


def test_explain_invalid_date_range_returns_validation_error(
    explain_client: tuple[TestClient, Session],
) -> None:
    client, _session = explain_client

    response = client.get(
        "/api/explain",
        params={
            "ticker": "NVDA",
            "start_date": "2026-06-30",
            "end_date": "2026-06-01",
        },
    )

    assert response.status_code == 422


def test_explain_limit_is_bounded(explain_client: tuple[TestClient, Session]) -> None:
    client, _session = explain_client

    response = client.get("/api/explain", params={"ticker": "NVDA", "limit": 11})

    assert response.status_code == 422
