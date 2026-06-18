from __future__ import annotations

import argparse

from app.db.session import SessionLocal
from app.events.extractor import EventExtractor
from app.events.service import EventExtractionService, EventExtractionSummary


def confidence_threshold(value: str) -> float:
    threshold = float(value)
    if threshold < 0 or threshold > 1:
        raise argparse.ArgumentTypeError("--min-confidence must be between 0.0 and 1.0")
    return threshold


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract rule-based market events.")
    parser.add_argument("--ticker", help="Optional ticker filter, for example NVDA.")
    parser.add_argument("--min-confidence", type=confidence_threshold, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def format_summary(summary: EventExtractionSummary, *, threshold_used: float) -> str:
    return "\n".join(
        [
            f"chunks scanned: {summary.chunks_scanned}",
            f"events extracted: {summary.events_extracted}",
            f"events inserted: {summary.events_inserted}",
            f"events skipped: {summary.events_skipped_existing}",
            f"confidence threshold used: {threshold_used:g}",
            f"dry run: {'yes' if summary.dry_run else 'no'}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    threshold_used = args.min_confidence
    if threshold_used is None:
        threshold_used = EventExtractor().min_confidence

    with SessionLocal() as session:
        summary = EventExtractionService(session).extract_events(
            ticker=args.ticker,
            min_confidence=args.min_confidence,
            dry_run=args.dry_run,
        )

    print(format_summary(summary, threshold_used=threshold_used))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
