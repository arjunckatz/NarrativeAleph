from app.search.scoring import LexicalEvidenceScorer


def test_exact_phrase_match_boosts_score() -> None:
    scorer = LexicalEvidenceScorer()

    phrase_score = scorer.score(
        query="export restrictions",
        document_title="Nvidia update",
        chunk_bm25_text="new export restrictions affect accelerator sales",
    )
    term_score = scorer.score(
        query="export restrictions",
        document_title="Nvidia update",
        chunk_bm25_text="export controls and shipment restrictions affect sales",
    )

    assert phrase_score > term_score


def test_title_match_boosts_score() -> None:
    scorer = LexicalEvidenceScorer()

    title_score = scorer.score(
        query="cloud capex",
        document_title="Cloud capex outlook",
        chunk_bm25_text="cloud spending plans",
    )
    no_title_score = scorer.score(
        query="cloud capex",
        document_title="Hyperscaler update",
        chunk_bm25_text="cloud spending plans",
    )

    assert title_score > no_title_score


def test_higher_term_frequency_scores_higher() -> None:
    scorer = LexicalEvidenceScorer()

    high_frequency = scorer.score(
        query="margin pressure",
        document_title="Margin note",
        chunk_bm25_text="margin pressure margin pressure margin",
    )
    low_frequency = scorer.score(
        query="margin pressure",
        document_title="Margin note",
        chunk_bm25_text="margin pressure",
    )

    assert high_frequency > low_frequency


def test_identical_inputs_produce_identical_scores() -> None:
    scorer = LexicalEvidenceScorer()
    kwargs = {
        "query": "china demand",
        "document_title": "Apple China demand",
        "chunk_bm25_text": "china demand concerns",
    }

    assert scorer.score(**kwargs) == scorer.score(**kwargs)
