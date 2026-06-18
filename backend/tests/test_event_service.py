from datetime import UTC, datetime
from hashlib import sha256

import pytest
from app.db.base import Base
from app.events import cli as event_cli
from app.events.service import EventExtractionService
from app.models import Document, DocumentChunk, Event
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


def add_document_with_chunk(
    session: Session,
    *,
    ticker: str = "NVDA",
    title: str = "Synthetic market note",
    text: str,
    source_type: str = "synthetic",
    published_at: datetime = datetime(2026, 6, 1, tzinfo=UTC),
    chunk_index: int = 0,
) -> tuple[Document, DocumentChunk]:
    document = Document(
        source_type=source_type,
        ticker=ticker,
        title=title,
        published_at=published_at,
        source_name="Synthetic Test Source",
        url=None,
        content_hash=sha256(
            f"{ticker}|{title}|{published_at.isoformat()}|{chunk_index}|{text}".encode()
        ).hexdigest(),
        raw_text=text,
        metadata_={"test": True},
    )
    session.add(document)
    session.flush()
    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=chunk_index,
        text=text,
        bm25_text=text.lower(),
        metadata_={"chunk": chunk_index},
    )
    session.add(chunk)
    session.commit()
    return document, chunk


def test_service_reads_chunks_and_writes_event_rows(db_session: Session) -> None:
    add_document_with_chunk(
        db_session,
        title="NVDA export restrictions",
        text="New export restrictions could delay China accelerator shipments.",
    )

    summary = EventExtractionService(db_session).extract_events()
    events = db_session.scalars(select(Event)).all()

    assert summary.chunks_scanned == 1
    assert summary.events_extracted == 1
    assert summary.events_inserted == 1
    assert len(events) == 1
    assert events[0].ticker == "NVDA"
    assert events[0].event_type == "export_restriction"
    assert events[0].event_date.isoformat() == "2026-06-01"
    assert events[0].sentiment == "negative"


def test_repeated_run_does_not_duplicate_events(db_session: Session) -> None:
    add_document_with_chunk(
        db_session,
        text="Executives cut guidance for the full year and lowered the revenue outlook.",
    )
    service = EventExtractionService(db_session)

    first_summary = service.extract_events()
    second_summary = service.extract_events()
    events = db_session.scalars(select(Event)).all()

    assert first_summary.events_inserted == 1
    assert second_summary.events_inserted == 0
    assert second_summary.events_skipped_existing == 1
    assert len(events) == 1


def test_duplicate_suppression_preserves_existing_row(db_session: Session) -> None:
    document, chunk = add_document_with_chunk(
        db_session,
        text="New export restrictions could delay China accelerator shipments.",
    )
    existing = Event(
        ticker=document.ticker,
        event_type="export_restriction",
        event_date=document.published_at.date(),
        extracted_text="New export restrictions could delay China accelerator shipments.",
        sentiment="negative",
        confidence=0.8,
        metadata_={
            "document_id": document.id,
            "chunk_id": chunk.id,
        },
    )
    db_session.add(existing)
    db_session.commit()

    summary = EventExtractionService(db_session).extract_events()
    events = db_session.scalars(select(Event)).all()

    assert summary.events_inserted == 0
    assert summary.events_skipped_existing == 1
    assert len(events) == 1


def test_ticker_filter_limits_scanned_chunks(db_session: Session) -> None:
    add_document_with_chunk(
        db_session,
        ticker="NVDA",
        text="New export controls may limit accelerator shipments.",
    )
    add_document_with_chunk(
        db_session,
        ticker="AAPL",
        text="The company delivered an earnings beat with a strong quarter.",
        chunk_index=1,
    )

    summary = EventExtractionService(db_session).extract_events(ticker="nvda")
    events = db_session.scalars(select(Event)).all()

    assert summary.chunks_scanned == 1
    assert summary.events_inserted == 1
    assert [event.ticker for event in events] == ["NVDA"]


def test_min_confidence_filter_skips_lower_confidence_events(db_session: Session) -> None:
    add_document_with_chunk(
        db_session,
        text="Analysts flagged margin pressure.",
    )

    summary = EventExtractionService(db_session).extract_events(min_confidence=0.85)
    events = db_session.scalars(select(Event)).all()

    assert summary.events_extracted == 0
    assert summary.events_inserted == 0
    assert events == []


def test_multiple_event_matches_in_one_chunk(db_session: Session) -> None:
    add_document_with_chunk(
        db_session,
        text=(
            "New export controls may limit accelerator shipments. "
            "The company also delivered an earnings beat with a revenue beat."
        ),
    )

    summary = EventExtractionService(db_session).extract_events()
    event_types = {event.event_type for event in db_session.scalars(select(Event)).all()}

    assert summary.events_extracted == 2
    assert summary.events_inserted == 2
    assert event_types == {"export_restriction", "earnings_beat"}


def test_dry_run_writes_nothing(db_session: Session) -> None:
    add_document_with_chunk(
        db_session,
        text="The company reported an earnings miss after a revenue miss.",
    )

    summary = EventExtractionService(db_session).extract_events(dry_run=True)
    events = db_session.scalars(select(Event)).all()

    assert summary.dry_run is True
    assert summary.events_extracted == 1
    assert summary.events_inserted == 0
    assert events == []


def test_event_metadata_includes_document_and_chunk_ids(db_session: Session) -> None:
    document, chunk = add_document_with_chunk(
        db_session,
        title="Guidance cut",
        text="The company lowered guidance for the full year.",
    )

    EventExtractionService(db_session).extract_events()
    event_row = db_session.scalars(select(Event)).one()

    assert event_row.metadata_["document_id"] == document.id
    assert event_row.metadata_["chunk_id"] == chunk.id
    assert event_row.metadata_["chunk_index"] == chunk.chunk_index
    assert event_row.metadata_["rule_id"] == "guidance_cut"
    assert event_row.metadata_["rule_name"] == "guidance_cut"
    assert "lowered guidance" in event_row.metadata_["matched_terms"]
    assert "full year" in event_row.metadata_["matched_terms"]
    assert event_row.metadata_["matched_negative_terms"] == []
    assert event_row.metadata_["document_title"] == "Guidance cut"
    assert event_row.metadata_["source_type"] == "synthetic"


def test_unrelated_chunks_create_no_events(db_session: Session) -> None:
    add_document_with_chunk(
        db_session,
        text="The company opened a new office and discussed hiring plans.",
    )

    summary = EventExtractionService(db_session).extract_events()
    events = db_session.scalars(select(Event)).all()

    assert summary.chunks_scanned == 1
    assert summary.events_extracted == 0
    assert summary.events_inserted == 0
    assert events == []


def test_cli_dry_run_path(db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    add_document_with_chunk(
        db_session,
        text="Analysts flagged margin pressure from discounting and incentives.",
    )
    monkeypatch.setattr(event_cli, "SessionLocal", lambda: db_session)

    exit_code = event_cli.main(["--dry-run", "--min-confidence", "0.7"])
    output = capsys.readouterr().out
    events = db_session.scalars(select(Event)).all()

    assert exit_code == 0
    assert "chunks scanned: 1" in output
    assert "events extracted: 1" in output
    assert "events inserted: 0" in output
    assert "confidence threshold used: 0.7" in output
    assert "dry run: yes" in output
    assert events == []
