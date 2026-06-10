from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.chunking import chunk_text
from app.ingestion.hashing import compute_content_hash
from app.ingestion.normalizer import NormalizedDocument, load_and_normalize_documents
from app.models import Document, DocumentChunk


@dataclass(frozen=True)
class IngestionSummary:
    documents_read: int
    documents_inserted: int
    documents_skipped: int
    chunks_inserted: int


def find_existing_document(
    session: Session,
    document: NormalizedDocument,
    content_hash: str,
) -> Document | None:
    return (
        session.query(Document)
        .filter(
            Document.source_type == document.source_type,
            Document.ticker == document.ticker,
            Document.source_name == document.source_name,
            Document.content_hash == content_hash,
        )
        .one_or_none()
    )


def ingest_documents(
    session: Session,
    documents: list[NormalizedDocument],
    *,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
    dry_run: bool = False,
) -> IngestionSummary:
    prepared = [
        (
            document,
            compute_content_hash(document),
            chunk_text(document.raw_text, chunk_size, chunk_overlap),
        )
        for document in documents
    ]

    if dry_run:
        return IngestionSummary(
            documents_read=len(prepared),
            documents_inserted=0,
            documents_skipped=0,
            chunks_inserted=sum(len(chunks) for _, _, chunks in prepared),
        )

    inserted = 0
    skipped = 0
    chunks_inserted = 0

    for document, content_hash, chunks in prepared:
        if find_existing_document(session, document, content_hash) is not None:
            skipped += 1
            continue

        db_document = Document(
            source_type=document.source_type,
            ticker=document.ticker,
            title=document.title,
            published_at=document.published_at,
            source_name=document.source_name,
            url=document.url,
            content_hash=content_hash,
            raw_text=document.raw_text,
            metadata_=document.metadata,
        )
        session.add(db_document)

        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            skipped += 1
            continue

        for chunk in chunks:
            session.add(
                DocumentChunk(
                    document_id=db_document.id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    bm25_text=chunk.bm25_text,
                    embedding=None,
                    metadata_=chunk.metadata,
                )
            )
        inserted += 1
        chunks_inserted += len(chunks)

    session.commit()
    return IngestionSummary(
        documents_read=len(prepared),
        documents_inserted=inserted,
        documents_skipped=skipped,
        chunks_inserted=chunks_inserted,
    )


def ingest_document_file(
    session: Session,
    path: Path,
    *,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
    dry_run: bool = False,
) -> IngestionSummary:
    documents = load_and_normalize_documents(path)
    return ingest_documents(
        session,
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        dry_run=dry_run,
    )
