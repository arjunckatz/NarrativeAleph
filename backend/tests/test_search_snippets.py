from app.search.snippets import generate_snippet


def test_snippet_max_length() -> None:
    text = " ".join(["setup"] * 80 + ["export"] + ["tail"] * 80)

    snippet = generate_snippet("export", text, max_length=80)

    assert len(snippet) <= 80


def test_snippet_centers_around_matched_term() -> None:
    text = " ".join(
        [f"before{i}" for i in range(30)]
        + ["export"]
        + [f"after{i}" for i in range(30)]
    )

    snippet = generate_snippet("export", text, max_length=90)

    assert "export" in snippet
    assert "before29" in snippet
    assert "after0" in snippet


def test_no_match_fallback_uses_start_of_chunk() -> None:
    text = " ".join(["alpha"] * 50)

    snippet = generate_snippet("export", text, max_length=40)

    assert snippet.startswith("alpha")
    assert len(snippet) <= 40


def test_short_chunk_returns_cleanly() -> None:
    assert generate_snippet("export", "Short export note.") == "Short export note."


def test_punctuation_and_casing_query_still_matches() -> None:
    text = " ".join(["setup"] * 40 + ["Export restrictions"] + ["tail"] * 40)

    snippet = generate_snippet("EXPORT, restrictions!", text, max_length=100)

    assert "Export restrictions" in snippet
