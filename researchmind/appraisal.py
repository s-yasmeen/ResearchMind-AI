from __future__ import annotations

from .models import Appraisal, EvidenceLevel, StudyRecord


def _level(score: int) -> EvidenceLevel:
    if score >= 80:
        return "high"
    if score >= 60:
        return "moderate"
    if score >= 35:
        return "low"
    return "insufficient"


def appraise_study(study: StudyRecord) -> Appraisal:
    """Apply a transparent metadata screen; this is not a substitute for expert review."""
    score = 0
    strengths: list[str] = []
    concerns: list[str] = []
    checks = (
        (bool(study.source.identifier), 10, "Persistent identifier present", "No persistent identifier"),
        (bool(study.source.authors), 5, "Authorship recorded", "Authorship missing"),
        (study.source.year is not None, 5, "Publication year recorded", "Publication year missing"),
        (study.peer_reviewed is True, 15, "Peer-reviewed source", "Peer-review status absent or negative"),
        (bool(study.abstract.strip()), 10, "Abstract available", "Abstract missing"),
        (bool(study.methods), 15, "Methods extracted", "Methods not extracted"),
        (bool(study.metrics), 10, "Evaluation metrics reported", "Metrics missing"),
        (study.has_comparator is True, 10, "Comparator or baseline reported", "Comparator not confirmed"),
        (study.external_validation is True, 10, "External validation reported", "External validation absent"),
        (study.reproducible_assets is True, 5, "Reproducible assets reported", "Reproducible assets absent"),
        (bool(study.limitations), 5, "Limitations explicitly recorded", "Limitations not recorded"),
    )
    for passed, weight, strength, concern in checks:
        if passed:
            score += weight
            strengths.append(strength)
        else:
            concerns.append(concern)
    return Appraisal(
        source_identifier=study.source.identifier or study.source.url,
        score=score,
        evidence_level=_level(score),
        strengths=tuple(strengths),
        concerns=tuple(concerns),
    )


def appraise_corpus(studies: list[StudyRecord]) -> list[Appraisal]:
    return [appraise_study(study) for study in studies]
