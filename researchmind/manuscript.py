from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


ClaimKind = Literal["evidence", "author_contribution", "interpretation", "limitation"]


@dataclass(frozen=True)
class ManuscriptClaim:
    claim_id: str
    text: str
    kind: ClaimKind
    source_identifiers: tuple[str, ...] = ()
    uncertainty: str | None = None


@dataclass(frozen=True)
class MathematicalModel:
    name: str
    purpose: str
    assumptions: tuple[str, ...]
    symbols: tuple[tuple[str, str, str], ...]  # symbol, meaning, unit/domain
    equations: tuple[str, ...]
    derivation_steps: tuple[str, ...]
    identifiability_conditions: tuple[str, ...]
    validation_tests: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class AlgorithmSpecification:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    pseudocode_steps: tuple[str, ...]
    time_complexity: str
    space_complexity: str
    invariants: tuple[str, ...]
    failure_modes: tuple[str, ...]


@dataclass(frozen=True)
class VisualSpecification:
    visual_id: str
    kind: Literal["table", "figure"]
    title: str
    purpose: str
    data_source: str
    caption: str
    interpretation: str
    takeaway: str


@dataclass
class Manuscript:
    title: str
    sections: dict[str, str]
    claims: list[ManuscriptClaim] = field(default_factory=list)
    models: list[MathematicalModel] = field(default_factory=list)
    algorithms: list[AlgorithmSpecification] = field(default_factory=list)
    visuals: list[VisualSpecification] = field(default_factory=list)


REQUIRED_SECTIONS = (
    "abstract", "keywords", "introduction", "related_work", "research_gap",
    "methodology", "mathematical_model", "algorithm", "experimental_design",
    "results", "discussion", "threats_to_validity", "conclusion", "references",
)


def manuscript_quality_gate(manuscript: Manuscript, known_sources: set[str]) -> list[str]:
    """Return blocking integrity problems; an empty list means structurally admissible."""
    problems: list[str] = []
    for section in REQUIRED_SECTIONS:
        if not manuscript.sections.get(section, "").strip():
            problems.append(f"Missing required section: {section}")

    ids: set[str] = set()
    for claim in manuscript.claims:
        if claim.claim_id in ids:
            problems.append(f"Duplicate claim identifier: {claim.claim_id}")
        ids.add(claim.claim_id)
        if claim.kind == "evidence" and not claim.source_identifiers:
            problems.append(f"Evidence claim has no citation: {claim.claim_id}")
        for source in claim.source_identifiers:
            if source not in known_sources:
                problems.append(f"Claim {claim.claim_id} cites unknown source: {source}")
        if claim.kind == "interpretation" and not claim.uncertainty:
            problems.append(f"Interpretive claim lacks uncertainty statement: {claim.claim_id}")

    for model in manuscript.models:
        if not model.assumptions:
            problems.append(f"Mathematical model lacks assumptions: {model.name}")
        if not model.symbols or not model.equations or not model.derivation_steps:
            problems.append(f"Mathematical model is not fully specified: {model.name}")
        if not model.validation_tests or not model.limitations:
            problems.append(f"Mathematical model lacks validation or limitations: {model.name}")

    for algorithm in manuscript.algorithms:
        if not algorithm.pseudocode_steps:
            problems.append(f"Algorithm lacks pseudocode: {algorithm.name}")
        if not algorithm.time_complexity or not algorithm.space_complexity:
            problems.append(f"Algorithm lacks complexity analysis: {algorithm.name}")
        if not algorithm.failure_modes:
            problems.append(f"Algorithm lacks failure-mode analysis: {algorithm.name}")

    for visual in manuscript.visuals:
        if not all((visual.title, visual.purpose, visual.data_source, visual.caption, visual.interpretation, visual.takeaway)):
            problems.append(f"Visual is not fully explained: {visual.visual_id}")
    return problems


def suspicious_source_overlap(text: str, source_texts: list[str], ngram_size: int = 8) -> float:
    """Estimate verbatim phrase overlap for editorial review; not a plagiarism verdict."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) < ngram_size:
        return 0.0
    manuscript_ngrams = {
        tuple(words[i : i + ngram_size]) for i in range(len(words) - ngram_size + 1)
    }
    source_ngrams: set[tuple[str, ...]] = set()
    for source in source_texts:
        source_words = re.findall(r"[a-z0-9]+", source.lower())
        source_ngrams.update(
            tuple(source_words[i : i + ngram_size])
            for i in range(len(source_words) - ngram_size + 1)
        )
    if not manuscript_ngrams:
        return 0.0
    return len(manuscript_ngrams & source_ngrams) / len(manuscript_ngrams)
