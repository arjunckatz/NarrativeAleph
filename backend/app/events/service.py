from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.extractor import EventExtractor
from app.events.types import ExtractedEvent
from app.models import Document, DocumentChunk, Event


@dataclass(frozen=True)
class EventExtractionSummary:
    chunks_scanned: int
    events_extracted: int
    events_inserted: int
    events_skipped_existing: int
    dry_run: bool


class EventExtractionService:
    def __init__(self, session: Session, extractor: EventExtractor | None = None) -> None:
        self.session = session
        self.extractor = extractor or EventExtractor()

    def extract_events(
        self,
        *,
        ticker: str | None = None,
        min_confidence: float | None = None,
        dry_run: bool = False,
    ) -> EventExtractionSummary:
        chunks = self._load_chunks(ticker=ticker)
        events_extracted = 0
        events_inserted = 0
        events_skipped_existing = 0

        for chunk, document in chunks:
            accepted_events = self._extract_accepted_events(
                chunk=chunk,
                document=document,
                min_confidence=min_confidence,
            )
            events_extracted += len(accepted_events)

            for extracted_event in accepted_events:
                if self._existing_event(
                    extracted_event=extracted_event,
                    document=document,
                    chunk=chunk,
                ):
                    events_skipped_existing += 1
                    continue

                if dry_run:
                    continue

                self.session.add(
                    self._build_event(
                        extracted_event=extracted_event,
                        document=document,
                        chunk=chunk,
                    )
                )
                events_inserted += 1

        if not dry_run and events_inserted:
            self.session.commit()

        return EventExtractionSummary(
            chunks_scanned=len(chunks),
            events_extracted=events_extracted,
            events_inserted=events_inserted,
            events_skipped_existing=events_skipped_existing,
            dry_run=dry_run,
        )

    def _extract_accepted_events(
        self,
        *,
        chunk: DocumentChunk,
        document: Document,
        min_confidence: float | None,
    ) -> list[ExtractedEvent]:
        extracted_events = self.extractor.extract(text=chunk.text, title=document.title)
        if min_confidence is None:
            return extracted_events
        return [event for event in extracted_events if event.confidence >= min_confidence]

    def _load_chunks(self, *, ticker: str | None) -> list[tuple[DocumentChunk, Document]]:
        statement = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .order_by(Document.id.asc(), DocumentChunk.chunk_index.asc(), DocumentChunk.id.asc())
        )
        if ticker:
            statement = statement.where(Document.ticker == ticker.upper())
        return list(self.session.execute(statement).all())

    def _existing_event(
        self,
        *,
        extracted_event: ExtractedEvent,
        document: Document,
        chunk: DocumentChunk,
    ) -> bool:
        statement = select(Event).where(
            Event.ticker == document.ticker,
            Event.event_type == extracted_event.event_type.value,
            Event.event_date == document.published_at.date(),
            Event.extracted_text == extracted_event.extracted_text,
        )
        candidates = self.session.scalars(statement).all()
        return any(
            event.metadata_.get("document_id") == document.id
            and event.metadata_.get("chunk_id") == chunk.id
            for event in candidates
        )

    def _build_event(
        self,
        *,
        extracted_event: ExtractedEvent,
        document: Document,
        chunk: DocumentChunk,
    ) -> Event:
        matched_terms = sorted(
            set(extracted_event.matched_required + extracted_event.matched_optional)
        )
        return Event(
            ticker=document.ticker,
            event_type=extracted_event.event_type.value,
            event_date=document.published_at.date(),
            extracted_text=extracted_event.extracted_text,
            sentiment=extracted_event.sentiment,
            confidence=Decimal(str(extracted_event.confidence)),
            metadata_={
                "document_id": document.id,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "rule_id": extracted_event.event_type.value,
                "rule_name": extracted_event.event_type.value,
                "matched_terms": matched_terms,
                "matched_negative_terms": list(extracted_event.matched_negative),
                "document_title": document.title,
                "source_type": document.source_type,
            },
        )
