from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import StudyRecord
from .retrieval import deduplicate

Decision = Literal["include", "exclude", "human_review"]


@dataclass(frozen=True)
class ScreeningCriteria:
    concepts: tuple[str, ...]
    year_from: int | None = None
    year_to: int | None = None
    allowed_types: tuple[str, ...] = ()
    require_abstract: bool = True


@dataclass(frozen=True)
class ScreeningDecision:
    source_identifier: str
    decision: Decision
    reasons: tuple[str, ...]


def screen_study(study: StudyRecord, criteria: ScreeningCriteria) -> ScreeningDecision:
    identifier = study.source.identifier or study.source.url
    reasons: list[str] = []
    if criteria.year_from and study.source.year and study.source.year < criteria.year_from:
        reasons.append(f"Published before {criteria.year_from}")
    if criteria.year_to and study.source.year and study.source.year > criteria.year_to:
        reasons.append(f"Published after {criteria.year_to}")
    if criteria.allowed_types and study.source.publication_type not in criteria.allowed_types:
        reasons.append("Publication type outside protocol")
    searchable = f"{study.source.title} {study.abstract}".lower()
    matched = sum(concept.lower() in searchable for concept in criteria.concepts)
    if criteria.concepts and matched < min(2, len(criteria.concepts)):
        reasons.append("Insufficient conceptual relevance")
    if reasons:
        return ScreeningDecision(identifier, "exclude", tuple(reasons))
    if study.source.year is None:
        reasons.append("Publication year requires verification")
    if criteria.require_abstract and not study.abstract.strip():
        reasons.append("Abstract/full text required for eligibility review")
    if reasons:
        return ScreeningDecision(identifier, "human_review", tuple(reasons))
    return ScreeningDecision(identifier, "include", ("Meets automated protocol checks",))


def screen_corpus(studies: list[StudyRecord], criteria: ScreeningCriteria) -> tuple[list[StudyRecord], list[ScreeningDecision]]:
    unique = deduplicate(studies)
    decisions = [screen_study(study, criteria) for study in unique]
    included_ids = {d.source_identifier for d in decisions if d.decision == "include"}
    included = [s for s in unique if (s.source.identifier or s.source.url) in included_ids]
    return included, decisions
