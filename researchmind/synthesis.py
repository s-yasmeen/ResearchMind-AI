from __future__ import annotations

from collections import defaultdict

from .models import Appraisal, EvidenceLevel, Finding


_RANK = {"insufficient": 0, "low": 1, "moderate": 2, "high": 3}


def conservative_confidence(source_ids: tuple[str, ...], appraisals: list[Appraisal]) -> EvidenceLevel:
    levels = {
        item.source_identifier: item.evidence_level
        for item in appraisals
    }
    available = [levels[item] for item in set(source_ids) if item in levels]
    if not available:
        return "insufficient"
    best = max(available, key=_RANK.get)
    if len(set(source_ids)) < 2 and best == "high":
        return "moderate"
    return best


def contradiction_map(findings: list[Finding]) -> dict[str, tuple[str, ...]]:
    """Group explicitly coded opposing findings; never infer opposition from prose alone."""
    grouped: dict[str, list[str]] = defaultdict(list)
    normalized: dict[str, set[str]] = defaultdict(set)
    for finding in findings:
        topic = " ".join(finding.claim.lower().split())
        grouped[topic].extend(finding.source_identifiers)
        normalized[topic].add(finding.stance)
    return {
        topic: tuple(dict.fromkeys(grouped[topic]))
        for topic, stances in normalized.items()
        if "supports" in stances and "contradicts" in stances
    }
