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
def narratives_client() -> Generator[tuple[TestClient, Session], None, None]:
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


def test_narratives_route_is_registered(narratives_client: tuple[TestClient, Session]) -> None:
    client, _session = narratives_client

    response = client.get("/api/narratives")

    assert response.status_code == 200


def test_narratives_empty_event_table_returns_empty_list(
    narratives_client: tuple[TestClient, Session],
) -> None:
    client, _session = narratives_client

    response = client.get("/api/narratives")

    assert response.status_code == 200
    assert response.json() == []


def test_narratives_successful_response_shape(
    narratives_client: tuple[TestClient, Session],
) -> None:
    client, session = narratives_client
    event_row = add_event(
        session,
        metadata={
            "document_id": 11,
            "chunk_id": 22,
            "document_title": "NVDA export restriction report",
            "source_type": "news",
        },
    )

    response = client.get("/api/narratives")

    assert response.status_code == 200
    payload = response.json()
    assert payload == [
        {
            "narrative_name": "Export Restrictions",
            "ticker": "NVDA",
            "event_count": 1,
            "average_confidence": 0.8,
            "max_confidence": 0.8,
            "first_seen": "2026-06-01",
            "last_seen": "2026-06-01",
            "event_types": ["export_restriction"],
            "supporting_event_ids": [event_row.id],
            "score": 58.0,
            "score_components": {
                "event_count_score": 6.0,
                "confidence_score": 32.0,
                "recency_score": 20.0,
                "event_type_diversity_score": 0.0,
            },
            "supporting_evidence": [
                {
                    "event_id": event_row.id,
                    "event_type": "export_restriction",
                    "confidence": 0.8,
                    "extracted_text": "NVDA export_restriction",
                    "document_id": 11,
                    "chunk_id": 22,
                    "document_title": "NVDA export restriction report",
                    "source_type": "news",
                }
            ],
        }
    ]


def test_narratives_ticker_filter(narratives_client: tuple[TestClient, Session]) -> None:
    client, session = narratives_client
    add_event(session, ticker="NVDA", event_type="margin_pressure")
    add_event(session, ticker="AAPL", event_type="margin_pressure")

    response = client.get("/api/narratives", params={"ticker": "nvda"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["ticker"] == "NVDA"
    assert payload[0]["supporting_evidence"][0]["event_type"] == "margin_pressure"


def test_narratives_start_date_filter(narratives_client: tuple[TestClient, Session]) -> None:
    client, session = narratives_client
    add_event(session, event_type="guidance_cut", event_date=date(2026, 5, 31))
    add_event(session, event_type="guidance_cut", event_date=date(2026, 6, 2))

    response = client.get("/api/narratives", params={"start_date": "2026-06-01"})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["event_count"] == 1
    assert payload[0]["first_seen"] == "2026-06-02"


def test_narratives_end_date_filter(narratives_client: tuple[TestClient, Session]) -> None:
    client, session = narratives_client
    add_event(session, event_type="demand_slowdown", event_date=date(2026, 6, 2))
    add_event(session, event_type="demand_slowdown", event_date=date(2026, 6, 7))

    response = client.get("/api/narratives", params={"end_date": "2026-06-05"})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["event_count"] == 1
    assert payload[0]["last_seen"] == "2026-06-02"
    assert payload[0]["supporting_evidence"][0]["extracted_text"] == (
        "NVDA demand_slowdown"
    )


def test_narratives_supporting_evidence_ordering_is_deterministic(
    narratives_client: tuple[TestClient, Session],
) -> None:
    client, session = narratives_client
    first_event = add_event(session, event_date=date(2026, 6, 1))
    second_event = add_event(session, event_date=date(2026, 6, 2))

    response = client.get("/api/narratives")

    assert response.status_code == 200
    evidence = response.json()[0]["supporting_evidence"]
    assert [item["event_id"] for item in evidence] == [first_event.id, second_event.id]


def test_narratives_events_without_metadata_return_safe_evidence(
    narratives_client: tuple[TestClient, Session],
) -> None:
    client, session = narratives_client
    event_row = add_event(session, metadata={})

    response = client.get("/api/narratives")

    assert response.status_code == 200
    evidence = response.json()[0]["supporting_evidence"][0]
    assert evidence["event_id"] == event_row.id
    assert evidence["document_id"] is None
    assert evidence["chunk_id"] is None
    assert evidence["document_title"] is None
    assert evidence["source_type"] is None


def test_narratives_invalid_date_range_returns_validation_error(
    narratives_client: tuple[TestClient, Session],
) -> None:
    client, _session = narratives_client

    response = client.get(
        "/api/narratives",
        params={"start_date": "2026-06-30", "end_date": "2026-06-01"},
    )

    assert response.status_code == 422


def test_narratives_response_includes_confidence_rollups(
    narratives_client: tuple[TestClient, Session],
) -> None:
    client, session = narratives_client
    add_event(session, event_type="earnings_beat", confidence=Decimal("0.70"))
    add_event(session, event_type="earnings_beat", confidence=Decimal("0.90"))

    response = client.get("/api/narratives")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["average_confidence"] == 0.8
    assert payload[0]["max_confidence"] == 0.9
    assert payload[0]["event_count"] == 2


def test_narratives_multiple_results_have_deterministic_order(
    narratives_client: tuple[TestClient, Session],
) -> None:
    client, session = narratives_client
    add_event(
        session,
        ticker="TSLA",
        event_type="guidance_cut",
        confidence=Decimal("0.95"),
    )
    add_event(
        session,
        ticker="AAPL",
        event_type="earnings_miss",
        confidence=Decimal("0.60"),
    )
    add_event(
        session,
        ticker="NVDA",
        event_type="export_restriction",
        confidence=Decimal("0.80"),
    )

    response = client.get("/api/narratives")

    assert response.status_code == 200
    payload = response.json()
    assert [(item["ticker"], item["narrative_name"]) for item in payload] == [
        ("TSLA", "Guidance Concerns"),
        ("NVDA", "Export Restrictions"),
        ("AAPL", "Earnings Weakness"),
    ]
    assert [item["score"] for item in payload] == sorted(
        (item["score"] for item in payload),
        reverse=True,
    )
