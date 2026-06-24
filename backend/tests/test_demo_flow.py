from pathlib import Path

from app.db.base import Base
from app.events.service import EventExtractionService
from app.ingestion.loader import ingest_document_file
from app.models import Event
from app.narratives.service import NarrativeAggregationService
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


def test_sample_documents_produce_persisted_events_and_narratives() -> None:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sample_path = Path(__file__).resolve().parents[2] / "data" / "sample_documents.json"

    with Session(engine) as session:
        ingestion = ingest_document_file(session, sample_path)
        extraction = EventExtractionService(session).extract_events()
        narratives = NarrativeAggregationService(session).aggregate(ticker="NVDA")

        assert ingestion.documents_inserted >= 20
        assert extraction.events_inserted > 0
        assert session.scalars(select(Event)).first() is not None
        assert any(
            candidate.narrative_name == "Export Restrictions"
            and candidate.supporting_event_ids
            for candidate in narratives
        )
