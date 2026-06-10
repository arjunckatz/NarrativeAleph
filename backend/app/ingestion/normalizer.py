from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_SOURCE_TYPES = {"news", "filing", "transcript", "analyst_note", "synthetic"}
REQUIRED_FIELDS = {
    "source_type",
    "ticker",
    "title",
    "published_at",
    "source_name",
    "raw_text",
}


class IngestionValidationError(ValueError):
    """Raised when an ingestion file is malformed."""


@dataclass(frozen=True)
class NormalizedDocument:
    source_type: str
    ticker: str
    title: str
    published_at: datetime
    source_name: str
    url: str | None
    raw_text: str
    metadata: dict[str, Any]


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_published_at(value: Any, record_index: int) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise IngestionValidationError(f"record {record_index}: published_at must be a string")

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise IngestionValidationError(
            f"record {record_index}: published_at must be ISO-8601"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def require_string(record: dict[str, Any], field: str, record_index: int) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not normalize_whitespace(value):
        raise IngestionValidationError(f"record {record_index}: {field} is required")
    return normalize_whitespace(value)


def normalize_record(record: Any, record_index: int) -> NormalizedDocument:
    if not isinstance(record, dict):
        raise IngestionValidationError(f"record {record_index}: record must be an object")

    missing = sorted(field for field in REQUIRED_FIELDS if field not in record)
    if missing:
        raise IngestionValidationError(
            f"record {record_index}: missing required field(s): {', '.join(missing)}"
        )

    source_type = require_string(record, "source_type", record_index)
    if source_type not in ALLOWED_SOURCE_TYPES:
        raise IngestionValidationError(
            f"record {record_index}: invalid source_type '{source_type}'"
        )

    raw_text = require_string(record, "raw_text", record_index)
    metadata = record.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise IngestionValidationError(f"record {record_index}: metadata must be an object")

    url = record.get("url")
    if url is not None:
        if not isinstance(url, str):
            raise IngestionValidationError(f"record {record_index}: url must be null or string")
        url = normalize_whitespace(url) or None

    return NormalizedDocument(
        source_type=source_type,
        ticker=require_string(record, "ticker", record_index).upper(),
        title=require_string(record, "title", record_index),
        published_at=parse_published_at(record["published_at"], record_index),
        source_name=require_string(record, "source_name", record_index),
        url=url,
        raw_text=raw_text,
        metadata=metadata,
    )


def load_and_normalize_documents(path: Path) -> list[NormalizedDocument]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise IngestionValidationError(f"could not read {path}") from exc
    except json.JSONDecodeError as exc:
        raise IngestionValidationError(f"{path} is not valid JSON") from exc

    if not isinstance(payload, list):
        raise IngestionValidationError("sample document file must contain a JSON array")

    return [normalize_record(record, index) for index, record in enumerate(payload)]
