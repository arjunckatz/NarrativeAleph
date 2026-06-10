import pytest
from app.ingestion.chunking import build_bm25_text, chunk_text
from app.ingestion.normalizer import IngestionValidationError


def test_short_text_produces_one_chunk() -> None:
    chunks = chunk_text("AI demand remains strong.", chunk_size=100, chunk_overlap=20)

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "AI demand remains strong."


def test_long_text_produces_word_safe_overlapping_chunks() -> None:
    text = " ".join(f"word{i}" for i in range(40))

    chunks = chunk_text(text, chunk_size=70, chunk_overlap=20)

    assert len(chunks) > 1
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].text.split()[-1] in chunks[1].text.split()
    assert all(chunk.text == " ".join(chunk.text.split()) for chunk in chunks)


def test_bm25_text_is_deterministic_normalized_text() -> None:
    assert build_bm25_text("AI, Datacenter: Demand!") == "ai datacenter demand"


def test_empty_text_is_rejected() -> None:
    with pytest.raises(IngestionValidationError):
        chunk_text("   ")


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=10, chunk_overlap=10)
