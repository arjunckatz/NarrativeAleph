from datetime import UTC, datetime
from hashlib import sha256

import pytest
from app.db.base import Base
from app.models import Document, DocumentChunk
from app.search.query import SearchParams
from app.search.service import SearchService
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


def add_document(
    session: Session,
    *,
    ticker: str,
    source_type: str,
    published_at: datetime,
    title: str,
    bm25_text: str,
    chunk_index: int = 0,
) -> Document:
    document = Document(
        source_type=source_type,
        ticker=ticker,
        title=title,
        published_at=published_at,
        source_name="Synthetic Test Source",
        url=None,
        content_hash=sha256(
            f"{ticker}|{source_type}|{published_at.isoformat()}|{title}|{chunk_index}".encode()
        ).hexdigest(),
        raw_text=bm25_text,
        metadata_={"test": True},
    )
    session.add(document)
    session.flush()
    session.add(
        DocumentChunk(
            document_id=document.id,
            chunk_index=chunk_index,
            text=bm25_text,
            bm25_text=bm25_text,
            metadata_={"chunk": chunk_index},
        )
    )
    session.commit()
    return document


def test_search_filters_by_ticker(db_session: Session) -> None:
    add_document(
        db_session,
        ticker="NVDA",
        source_type="synthetic",
        published_at=datetime(2026, 6, 1, tzinfo=UTC),
        title="NVDA export restrictions",
        bm25_text="export restrictions affect accelerator sales",
    )
    add_document(
        db_session,
        ticker="AAPL",
        source_type="synthetic",
        published_at=datetime(2026, 6, 2, tzinfo=UTC),
        title="AAPL export restrictions",
        bm25_text="export restrictions mentioned in market note",
    )

    response = SearchService(db_session).search(
        SearchParams(q="export restrictions", ticker="nvda")
    )

    assert [result.document.ticker for result in response.results] == ["NVDA"]


def test_search_filters_by_source_type(db_session: Session) -> None:
    add_document(
        db_session,
        ticker="NVDA",
        source_type="synthetic",
        published_at=datetime(2026, 6, 1, tzinfo=UTC),
        title="Synthetic capex note",
        bm25_text="cloud capex demand",
    )
    add_document(
        db_session,
        ticker="NVDA",
        source_type="news",
        published_at=datetime(2026, 6, 2, tzinfo=UTC),
        title="News capex note",
        bm25_text="cloud capex demand",
    )

    response = SearchService(db_session).search(
        SearchParams(q="cloud capex", source_type="synthetic")
    )

    assert [result.document.source_type for result in response.results] == ["synthetic"]


def test_search_filters_by_date_range(db_session: Session) -> None:
    add_document(
        db_session,
        ticker="TSLA",
        source_type="synthetic",
        published_at=datetime(2026, 5, 1, tzinfo=UTC),
        title="Old delivery miss",
        bm25_text="delivery miss pressure",
    )
    add_document(
        db_session,
        ticker="TSLA",
        source_type="synthetic",
        published_at=datetime(2026, 6, 10, tzinfo=UTC),
        title="Current delivery miss",
        bm25_text="delivery miss pressure",
    )

    response = SearchService(db_session).search(
        SearchParams(q="delivery miss", start_date="2026-06-01", end_date="2026-06-30")
    )

    assert [result.document.title for result in response.results] == ["Current delivery miss"]


def test_search_limit_caps_candidates(db_session: Session) -> None:
    for index in range(3):
        add_document(
            db_session,
            ticker="NVDA",
            source_type="synthetic",
            published_at=datetime(2026, 6, index + 1, tzinfo=UTC),
            title=f"AI demand {index}",
            bm25_text="ai demand datacenter",
            chunk_index=index,
        )

    response = SearchService(db_session).search(SearchParams(q="ai demand", limit=2))

    assert len(response.results) == 2
    assert [result.document.title for result in response.results] == ["AI demand 2", "AI demand 1"]


def test_search_returns_empty_results(db_session: Session) -> None:
    add_document(
        db_session,
        ticker="AAPL",
        source_type="synthetic",
        published_at=datetime(2026, 6, 1, tzinfo=UTC),
        title="China demand",
        bm25_text="china demand concerns",
    )

    response = SearchService(db_session).search(SearchParams(q="export restrictions"))

    assert response.results == []


def test_search_results_include_score_and_snippet(db_session: Session) -> None:
    add_document(
        db_session,
        ticker="NVDA",
        source_type="synthetic",
        published_at=datetime(2026, 6, 1, tzinfo=UTC),
        title="Export restrictions",
        bm25_text="export restrictions",
    )

    result = SearchService(db_session).search(SearchParams(q="export restrictions")).results[0]

    assert result.score is not None
    assert result.score > 0
    assert result.snippet == "export restrictions"
