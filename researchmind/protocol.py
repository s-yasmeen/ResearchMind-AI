from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import ResearchProtocol, ResearchQuestion, SearchPlan

_STOPWORDS = {"a", "an", "and", "are", "for", "from", "how", "in", "is", "of", "on", "or", "the", "to", "using", "what", "with"}


def _concepts(query: str) -> tuple[str, ...]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9-]+", query.lower())
    unique: list[str] = []
    for token in tokens:
        if token not in _STOPWORDS and token not in unique:
            unique.append(token)
    return tuple(unique[:12])


def frame_question(query: str) -> ResearchQuestion:
    query = " ".join(query.split())
    if len(query) < 10:
        raise ValueError("A research question must contain enough detail to frame a protocol.")
    concepts = _concepts(query)
    if len(concepts) < 2:
        raise ValueError("A research question needs at least two meaningful concepts.")
    lowered = query.lower()
    framework = "PICO" if any(word in lowered for word in ("effect", "versus", "patient", "clinical")) else "SPIDER"
    return ResearchQuestion(
        original=query,
        objective=f"Systematically examine the evidence concerning: {query}",
        framework=framework,
        concepts=concepts,
    )


def build_search_plan(question: ResearchQuestion) -> SearchPlan:
    quoted = [f'"{term}"' if "-" in term else term for term in question.concepts]
    broad = " AND ".join(quoted[:5])
    alternatives = " OR ".join(quoted[:8])
    current_year = datetime.now(timezone.utc).year
    return SearchPlan(
        databases=("IEEE Xplore", "ACM Digital Library", "Scopus/Web of Science", "Crossref", "Semantic Scholar", "arXiv"),
        query_strings=(broad, f"({alternatives}) AND (evaluation OR experiment OR benchmark)"),
        inclusion_criteria=(
            "Directly addresses at least two framed concepts",
            "Reports a method, dataset, evaluation, or substantiated synthesis",
            "Provides sufficient metadata to verify provenance",
            "Falls within the protocol date and language scope",
        ),
        exclusion_criteria=(
            "Duplicate or superseded record without unique evidence",
            "Opinion-only material without a transparent evidence base",
            "Unavailable abstract/full text when claims cannot be verified",
            "Retracted or materially corrected work unless studied as such",
        ),
        date_from=max(2000, current_year - 10),
        date_to=current_year,
    )


def create_protocol(query: str) -> ResearchProtocol:
    question = frame_question(query)
    return ResearchProtocol(
        question=question,
        search_plan=build_search_plan(question),
        screening_fields=("source_id", "title", "authors", "year", "venue", "doi_or_url", "duplicate_status", "eligibility_decision", "exclusion_reason"),
        extraction_fields=("research_question", "study_design", "sample_or_dataset", "method", "baseline", "outcomes", "metrics", "main_results", "limitations", "external_validation", "reproducible_assets"),
        appraisal_dimensions=("provenance", "study_design", "sample_adequacy", "comparison_quality", "evaluation_validity", "external_validation", "reproducibility", "limitation_transparency"),
    )
