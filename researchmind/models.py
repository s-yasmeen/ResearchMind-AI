from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AgentName = Literal["literature", "methodology", "writing"]
EvidenceLevel = Literal["high", "moderate", "low", "insufficient"]
GapType = Literal["evidence", "methodological", "population", "measurement", "theoretical", "implementation", "contradiction", "replication"]


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    identifier: str | None = None
    venue: str | None = None
    publication_type: str | None = None
    retrieved_from: str | None = None
    retrieved_at: str | None = None


@dataclass(frozen=True)
class Evidence:
    text: str
    source: Source
    page: int | None = None


@dataclass(frozen=True)
class ResearchQuestion:
    original: str
    objective: str
    framework: str
    concepts: tuple[str, ...]
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcomes: tuple[str, ...] = ()
    context: str | None = None


@dataclass(frozen=True)
class SearchPlan:
    databases: tuple[str, ...]
    query_strings: tuple[str, ...]
    inclusion_criteria: tuple[str, ...]
    exclusion_criteria: tuple[str, ...]
    date_from: int | None = None
    date_to: int | None = None


@dataclass(frozen=True)
class StudyRecord:
    source: Source
    abstract: str
    study_type: str = "unspecified"
    peer_reviewed: bool | None = None
    sample_size: int | None = None
    dataset: str | None = None
    methods: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    has_comparator: bool | None = None
    external_validation: bool | None = None
    reproducible_assets: bool | None = None


@dataclass(frozen=True)
class Appraisal:
    source_identifier: str
    score: int
    evidence_level: EvidenceLevel
    strengths: tuple[str, ...]
    concerns: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    claim: str
    source_identifiers: tuple[str, ...]
    confidence: EvidenceLevel
    stance: Literal["supports", "contradicts", "mixed", "unclear"] = "unclear"


@dataclass(frozen=True)
class ResearchGap:
    gap_type: GapType
    statement: str
    basis: tuple[str, ...]
    confidence: EvidenceLevel
    proposed_test: str


@dataclass
class ResearchProtocol:
    question: ResearchQuestion
    search_plan: SearchPlan
    screening_fields: tuple[str, ...]
    extraction_fields: tuple[str, ...]
    appraisal_dimensions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentPage:
    document_id: str
    page_number: int
    text: str
    section: str | None = None
    extraction_warning: str | None = None


@dataclass(frozen=True)
class EvidenceChunk:
    chunk_id: str
    document_id: str
    source_identifier: str
    page_start: int
    page_end: int
    section: str | None
    text: str
    content_hash: str


@dataclass(frozen=True)
class RankedChunk:
    chunk: EvidenceChunk
    keyword_score: float
    semantic_score: float | None
    combined_score: float


@dataclass
class ResearchResult:
    query: str
    agent: AgentName
    answer: str
    evidence: list[Evidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
