from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from app.ingestion.normalizer import NormalizedDocument, normalize_whitespace


def utc_isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def compute_content_hash(document: NormalizedDocument) -> str:
    parts = [
        document.source_type,
        document.ticker.upper(),
        normalize_whitespace(document.source_name),
        normalize_whitespace(document.title),
        utc_isoformat(document.published_at),
        normalize_whitespace(document.raw_text),
    ]
    canonical = "\n".join(parts)
    return sha256(canonical.encode("utf-8")).hexdigest()
