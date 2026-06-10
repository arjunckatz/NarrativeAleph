from datetime import UTC, datetime

from app.ingestion.hashing import compute_content_hash
from app.ingestion.normalizer import NormalizedDocument


def make_normalized_document(
    *,
    ticker: str = "NVDA",
    raw_text: str = "Nvidia demand remains strong.",
) -> NormalizedDocument:
    return NormalizedDocument(
        source_type="synthetic",
        ticker=ticker,
        title="AI demand note",
        published_at=datetime(2026, 6, 10, 13, 30, tzinfo=UTC),
        source_name="Synthetic Markets Daily",
        url=None,
        raw_text=raw_text,
        metadata={"synthetic": True},
    )


def test_hash_is_stable_for_logical_whitespace_changes() -> None:
    first = make_normalized_document(raw_text="Nvidia demand remains strong.")
    second = make_normalized_document(raw_text="  Nvidia   demand\nremains strong.  ")

    assert compute_content_hash(first) == compute_content_hash(second)


def test_hash_is_stable_for_ticker_case() -> None:
    upper = make_normalized_document(ticker="NVDA")
    lower = make_normalized_document(ticker="nvda")

    assert compute_content_hash(upper) == compute_content_hash(lower)


def test_hash_changes_when_raw_text_changes() -> None:
    first = make_normalized_document(raw_text="Nvidia demand remains strong.")
    second = make_normalized_document(raw_text="Nvidia demand weakened.")

    assert compute_content_hash(first) != compute_content_hash(second)
