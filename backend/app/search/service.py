from __future__ import annotations

from datetime import UTC, datetime, time

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.ingestion.chunking import build_bm25_text
from app.models import Document, DocumentChunk
from app.schemas.search import SearchChunk, SearchDocument, SearchResponse, SearchResult
from app.search.query import SearchParams


class SearchService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, params: SearchParams) -> SearchResponse:
        query = self._build_query(params)
        rows = self.session.execute(query).all()

        return SearchResponse(
            query=params.q,
            results=[
                SearchResult(
                    document=SearchDocument(
                        id=document.id,
                        ticker=document.ticker,
                        source_type=document.source_type,
                        title=document.title,
                        published_at=document.published_at,
                        source_name=document.source_name,
                        url=document.url,
                        metadata=document.metadata_,
                    ),
                    chunk=SearchChunk(
                        id=chunk.id,
                        chunk_index=chunk.chunk_index,
                        metadata=chunk.metadata_,
                    ),
                )
                for document, chunk in rows
            ],
        )

    def _build_query(self, params: SearchParams) -> Select:
        query_terms = build_bm25_text(params.q).split()
        statement = select(Document, DocumentChunk).join(
            DocumentChunk,
            DocumentChunk.document_id == Document.id,
        )

        for term in query_terms:
            statement = statement.where(DocumentChunk.bm25_text.contains(term))

        if params.ticker:
            statement = statement.where(Document.ticker == params.ticker)
        if params.source_type:
            statement = statement.where(Document.source_type == params.source_type)
        if params.start_date:
            start_at = datetime.combine(params.start_date, time.min, tzinfo=UTC)
            statement = statement.where(Document.published_at >= start_at)
        if params.end_date:
            end_at = datetime.combine(params.end_date, time.max, tzinfo=UTC)
            statement = statement.where(Document.published_at <= end_at)

        return statement.order_by(
            Document.published_at.desc(),
            Document.id.asc(),
            DocumentChunk.chunk_index.asc(),
        ).limit(params.limit)
