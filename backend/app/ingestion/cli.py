from __future__ import annotations

import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.ingestion.loader import ingest_document_file
from app.ingestion.normalizer import IngestionValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest local Narrative Alpha documents.")
    parser.add_argument("path", type=Path, help="Path to a local JSON document file.")
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        with SessionLocal() as session:
            summary = ingest_document_file(
                session,
                args.path,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                dry_run=args.dry_run,
            )
    except (IngestionValidationError, ValueError) as exc:
        parser.exit(status=1, message=f"ingestion failed: {exc}\n")

    print(
        f"documents_read={summary.documents_read} "
        f"documents_inserted={summary.documents_inserted} "
        f"documents_skipped={summary.documents_skipped} "
        f"chunks_inserted={summary.chunks_inserted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
