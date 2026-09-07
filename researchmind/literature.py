from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from .appraisal import appraise_corpus
from .gaps import identify_gaps
from .models import Appraisal, Finding, ResearchGap, StudyRecord
from .screening import ScreeningCriteria, ScreeningDecision, screen_corpus
from .retrieval import deduplicate
from .synthesis import contradiction_map


@dataclass(frozen=True)
class StudyMatrixRow:
    source_identifier: str
    title: str
    year: int | None
    venue: str | None
    publication_type: str | None
    dataset: str | None
    methods: tuple[str, ...]
    metrics: tuple[str, ...]
    limitations: tuple[str, ...]
    external_validation: bool | None
    reproducible_assets: bool | None
    evidence_level: str


@dataclass(frozen=True)
class CorpusTheme:
    category: str
    label: str
    study_count: int
    source_identifiers: tuple[str, ...]


@dataclass
class LiteratureReview:
    searched_count: int
    included_count: int
    screening: list[ScreeningDecision]
    matrix: list[StudyMatrixRow]
    themes: list[CorpusTheme]
    appraisals: list[Appraisal]
    gaps: list[ResearchGap]
    contradictions: dict[str, tuple[str, ...]]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _matrix(studies: list[StudyRecord], appraisals: list[Appraisal]) -> list[StudyMatrixRow]:
    quality = {a.source_identifier: a.evidence_level for a in appraisals}
    return [StudyMatrixRow(
        source_identifier=s.source.identifier or s.source.url,
        title=s.source.title,
        year=s.source.year,
        venue=s.source.venue,
        publication_type=s.source.publication_type,
        dataset=s.dataset,
        methods=s.methods,
        metrics=s.metrics,
        limitations=s.limitations,
        external_validation=s.external_validation,
        reproducible_assets=s.reproducible_assets,
        evidence_level=quality[s.source.identifier or s.source.url],
    ) for s in studies]


def _themes(studies: list[StudyRecord]) -> list[CorpusTheme]:
    values: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for study in studies:
        identifier = study.source.identifier or study.source.url
        for method in study.methods:
            values["method"][method].append(identifier)
        for metric in study.metrics:
            values["metric"][metric].append(identifier)
        if study.dataset:
            values["dataset"][study.dataset].append(identifier)
        for limitation in study.limitations:
            values["limitation"][limitation].append(identifier)
    themes = [CorpusTheme(category, label, len(set(ids)), tuple(dict.fromkeys(ids)))
              for category, labels in values.items() for label, ids in labels.items()]
    return sorted(themes, key=lambda item: (-item.study_count, item.category, item.label.lower()))


class LiteratureReviewAgent:
    """Produces an auditable evidence map; prose generation comes only after this passes."""

    def analyze(
        self,
        studies: list[StudyRecord],
        criteria: ScreeningCriteria,
        findings: list[Finding] | None = None,
    ) -> LiteratureReview:
        included, decisions = screen_corpus(studies, criteria)
        appraisals = appraise_corpus(included)
        limitations: list[str] = []
        if len(included) < 10:
            limitations.append("Small eligible corpus; gap and trend claims require cautious interpretation.")
        if any(s.peer_reviewed is None for s in included):
            limitations.append("Peer-review status is unresolved for one or more included records.")
        if not any(s.external_validation is True for s in included):
            limitations.append("No included study confirms external validation.")
        return LiteratureReview(
            searched_count=len(deduplicate(studies)),
            included_count=len(included),
            screening=decisions,
            matrix=_matrix(included, appraisals),
            themes=_themes(included),
            appraisals=appraisals,
            gaps=identify_gaps(included, appraisals),
            contradictions=contradiction_map(findings or []),
            limitations=limitations,
        )
