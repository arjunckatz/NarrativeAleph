from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.chunking import build_bm25_text


@dataclass(frozen=True)
class LexicalScoreFeatures:
    exact_phrase_match: int
    title_term_matches: int
    chunk_term_frequency: int
    unique_query_terms_matched: int


class LexicalEvidenceScorer:
    def score(self, *, query: str, document_title: str, chunk_bm25_text: str) -> float:
        features = self.features(
            query=query,
            document_title=document_title,
            chunk_bm25_text=chunk_bm25_text,
        )
        score = (
            3.0 * features.exact_phrase_match
            + 1.5 * features.title_term_matches
            + 1.0 * features.chunk_term_frequency
            + 0.5 * features.unique_query_terms_matched
        )
        return round(score, 4)

    def features(
        self,
        *,
        query: str,
        document_title: str,
        chunk_bm25_text: str,
    ) -> LexicalScoreFeatures:
        normalized_query = build_bm25_text(query)
        query_terms = normalized_query.split()
        unique_query_terms = set(query_terms)
        title_terms = set(build_bm25_text(document_title).split())
        chunk_terms = build_bm25_text(chunk_bm25_text).split()

        exact_phrase_match = int(
            bool(normalized_query and normalized_query in " ".join(chunk_terms))
        )
        title_term_matches = sum(1 for term in unique_query_terms if term in title_terms)
        chunk_term_frequency = sum(1 for term in chunk_terms if term in unique_query_terms)
        unique_query_terms_matched = sum(1 for term in unique_query_terms if term in chunk_terms)

        return LexicalScoreFeatures(
            exact_phrase_match=exact_phrase_match,
            title_term_matches=title_term_matches,
            chunk_term_frequency=chunk_term_frequency,
            unique_query_terms_matched=unique_query_terms_matched,
        )
