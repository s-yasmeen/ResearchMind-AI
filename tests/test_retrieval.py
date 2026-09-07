from researchmind.retrieval import (
    ArxivClient,
    CrossrefClient,
    deduplicate,
    normalize_doi,
    parse_arxiv,
    parse_crossref,
    search_all,
)


CROSSREF_FIXTURE = {
    "message": {
        "items": [
            {
                "DOI": "10.1000/ABC",
                "title": ["A Rigorous Study"],
                "author": [{"given": "Ada", "family": "Researcher"}],
                "published-online": {"date-parts": [[2025, 1, 2]]},
                "container-title": ["Journal of Tests"],
                "type": "journal-article",
                "URL": "https://doi.org/10.1000/ABC",
                "abstract": "<jats:p>Evidence-based abstract.</jats:p>",
            }
        ]
    }
}

ARXIV_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>https://arxiv.org/abs/2501.12345v2</id>
    <title> A Rigorous Preprint </title>
    <summary> Preprint evidence. </summary>
    <published>2025-01-10T00:00:00Z</published>
    <author><name>Ada Researcher</name></author>
  </entry>
</feed>"""


def test_doi_normalization():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_doi("doi: 10.1000/ABC") == "10.1000/abc"


def test_crossref_parser_preserves_provenance_without_assuming_peer_review():
    record = parse_crossref(CROSSREF_FIXTURE, "2026-01-01T00:00:00+00:00")[0]
    assert record.source.identifier == "10.1000/abc"
    assert record.source.venue == "Journal of Tests"
    assert record.source.retrieved_from == "Crossref"
    assert record.peer_reviewed is None
    assert record.abstract == "Evidence-based abstract."


def test_arxiv_parser_marks_preprint_not_peer_reviewed():
    record = parse_arxiv(ARXIV_FIXTURE, "2026-01-01T00:00:00+00:00")[0]
    assert record.source.identifier == "arXiv:2501.12345v2"
    assert record.source.publication_type == "preprint"
    assert record.peer_reviewed is False


def test_arxiv_versions_deduplicate():
    records = parse_arxiv(ARXIV_FIXTURE)
    older = records[0]
    from dataclasses import replace
    older = replace(older, source=replace(older.source, identifier="arXiv:2501.12345v1"))
    assert len(deduplicate([older, records[0]])) == 1


def test_clients_validate_and_cache_without_repeat_requests():
    calls = {"crossref": 0, "arxiv": 0}

    def json_get(url, params, headers):
        calls["crossref"] += 1
        return CROSSREF_FIXTURE

    def text_get(url, params, headers):
        calls["arxiv"] += 1
        return ARXIV_FIXTURE

    crossref = CrossrefClient("researcher@example.org", getter=json_get)
    arxiv = ArxivClient(getter=text_get, minimum_interval=3)
    first, audits = search_all("biometric privacy", [crossref, arxiv], 5)
    second, _ = search_all("biometric privacy", [crossref, arxiv], 5)
    assert len(first) == len(second) == 2
    assert [audit.provider for audit in audits] == ["Crossref", "arXiv"]
    assert calls == {"crossref": 1, "arxiv": 1}
