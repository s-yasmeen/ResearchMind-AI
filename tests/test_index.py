from researchmind.index import EvidenceIndex
from researchmind.models import EvidenceChunk


def chunk(identifier: str, text: str):
    return EvidenceChunk(identifier, "doc", "doi:1", 1, 1, "Results", text, identifier)


def test_keyword_retrieval_ranks_relevant_evidence_first():
    index = EvidenceIndex([
        chunk("privacy", "biometric privacy masking protects patient identity"),
        chunk("weather", "rainfall forecasting with satellite observations"),
    ])
    results = index.search("patient biometric privacy", limit=2)
    assert results[0].chunk.chunk_id == "privacy"
    assert results[0].keyword_score > results[1].keyword_score


def test_hybrid_retrieval_combines_keyword_and_semantic_scores():
    index = EvidenceIndex([
        chunk("keyword", "patient biometric privacy"),
        chunk("semantic", "identity protection in remote health consultations"),
    ])
    def scorer(query, texts):
        return [0.0, 1.0]
    results = index.search("patient biometric privacy", semantic_scorer=scorer, keyword_weight=0.4)
    assert results[0].chunk.chunk_id == "semantic"


def test_semantic_score_count_must_match_corpus():
    index = EvidenceIndex([chunk("one", "text")])
    try:
        index.search("query", semantic_scorer=lambda query, texts: [])
    except ValueError as exc:
        assert "wrong number" in str(exc)
    else:
        raise AssertionError("Invalid semantic result count was accepted")
