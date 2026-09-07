from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable

from .models import EvidenceChunk, RankedChunk

SemanticScorer = Callable[[str, list[str]], list[float]]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class EvidenceIndex:
    def __init__(self, chunks: list[EvidenceChunk]):
        self.chunks = chunks
        self.documents = [_tokens(chunk.text) for chunk in chunks]
        self.doc_frequency = Counter(
            token for document in self.documents for token in set(document)
        )
        self.average_length = (
            sum(map(len, self.documents)) / len(self.documents) if self.documents else 0.0
        )

    def _bm25(self, query: str, document: list[str], k1: float = 1.5, b: float = 0.75) -> float:
        if not document or not self.documents:
            return 0.0
        frequencies = Counter(document)
        score = 0.0
        for term in set(_tokens(query)):
            df = self.doc_frequency.get(term, 0)
            idf = math.log(1 + (len(self.documents) - df + 0.5) / (df + 0.5))
            frequency = frequencies.get(term, 0)
            denominator = frequency + k1 * (1 - b + b * len(document) / self.average_length)
            score += idf * (frequency * (k1 + 1) / denominator if denominator else 0.0)
        return score

    def search(
        self,
        query: str,
        limit: int = 8,
        semantic_scorer: SemanticScorer | None = None,
        keyword_weight: float = 0.55,
    ) -> list[RankedChunk]:
        if not query.strip():
            raise ValueError("query cannot be empty.")
        if limit < 1:
            raise ValueError("limit must be positive.")
        keyword = [self._bm25(query, document) for document in self.documents]
        maximum = max(keyword, default=0.0)
        normalized = [score / maximum if maximum else 0.0 for score in keyword]
        semantic = semantic_scorer(query, [chunk.text for chunk in self.chunks]) if semantic_scorer else [None] * len(self.chunks)
        if len(semantic) != len(self.chunks):
            raise ValueError("semantic_scorer returned the wrong number of scores.")
        results: list[RankedChunk] = []
        for chunk, keyword_score, semantic_score in zip(self.chunks, normalized, semantic):
            combined = keyword_score if semantic_score is None else keyword_weight * keyword_score + (1 - keyword_weight) * float(semantic_score)
            results.append(RankedChunk(chunk, keyword_score, semantic_score, combined))
        results.sort(key=lambda item: (-item.combined_score, item.chunk.chunk_id))
        return results[:limit]
