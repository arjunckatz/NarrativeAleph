import json
from pathlib import Path

import pytest
from app.db.base import Base
from app.ingestion.loader import ingest_document_file
from app.ingestion.normalizer import IngestionValidationError
from app.models import Document, DocumentChunk
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


def write_documents(path: Path, records: list[dict]) -> Path:
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def make_record(**overrides) -> dict:
    record = {
        "source_type": "synthetic",
        "ticker": "nvda",
        "title": "Synthetic Nvidia demand note",
        "published_at": "2026-06-10T13:30:00Z",
        "source_name": "Synthetic Markets Daily",
        "url": None,
        "raw_text": (
            "Nvidia datacenter demand remained strong as cloud customers expanded AI "
            "capacity for training and inference workloads."
        ),
        "metadata": {"synthetic": True, "topic": "AI datacenter demand"},
    }
    record.update(overrides)
    return record


def test_ingest_document_file_creates_documents_and_chunks(
    tmp_path: Path,
    db_session: Session,
) -> None:
    path = write_documents(tmp_path / "documents.json", [make_record()])

    summary = ingest_document_file(db_session, path, chunk_size=70, chunk_overlap=15)

    documents = db_session.query(Document).all()
    chunks = db_session.query(DocumentChunk).all()
    assert summary.documents_read == 1
    assert summary.documents_inserted == 1
    assert summary.documents_skipped == 0
    assert len(documents) == 1
    assert documents[0].ticker == "NVDA"
    assert len(documents[0].content_hash) == 64
    assert documents[0].metadata_["topic"] == "AI datacenter demand"
    assert len(chunks) == summary.chunks_inserted
    assert len(chunks) > 1


def test_ingestion_is_idempotent(tmp_path: Path, db_session: Session) -> None:
    path = write_documents(tmp_path / "documents.json", [make_record()])

    first = ingest_document_file(db_session, path, chunk_size=70, chunk_overlap=15)
    second = ingest_document_file(db_session, path, chunk_size=70, chunk_overlap=15)

    assert first.documents_inserted == 1
    assert second.documents_inserted == 0
    assert second.documents_skipped == 1
    assert db_session.query(Document).count() == 1
    assert db_session.query(DocumentChunk).count() == first.chunks_inserted


@pytest.mark.parametrize(
    "bad_record, expected_message",
    [
        ({}, "missing required field"),
        (make_record(source_type="blog"), "invalid source_type"),
        (make_record(published_at="not-a-date"), "published_at must be ISO-8601"),
        (make_record(raw_text="   "), "raw_text is required"),
    ],
)
def test_invalid_inputs_fail_fast_without_partial_ingest(
    tmp_path: Path,
    db_session: Session,
    bad_record: dict,
    expected_message: str,
) -> None:
    valid_record = make_record(content_hash="ignored")
    path = write_documents(tmp_path / "documents.json", [valid_record, bad_record])

    with pytest.raises(IngestionValidationError, match=expected_message):
        ingest_document_file(db_session, path)

    assert db_session.query(Document).count() == 0
    assert db_session.query(DocumentChunk).count() == 0


def test_sample_documents_file_is_valid(db_session: Session) -> None:
    path = Path("data/sample_documents.json")

    summary = ingest_document_file(db_session, path)

    assert 20 <= summary.documents_read <= 30
    assert summary.documents_inserted == summary.documents_read
    assert summary.chunks_inserted >= summary.documents_inserted
