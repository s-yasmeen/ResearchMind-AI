from __future__ import annotations

import re

from .models import Evidence, Finding

_CITATION = re.compile(r"\[([A-Za-z0-9_.:/-]+)\]")


def validate_finding(finding: Finding, evidence: list[Evidence]) -> list[str]:
    known = {item.source.identifier or item.source.url for item in evidence}
    problems: list[str] = []
    if not finding.source_identifiers:
        problems.append("Finding has no supporting source identifier.")
    for identifier in finding.source_identifiers:
        if identifier not in known:
            problems.append(f"Unknown supporting source: {identifier}")
    if finding.confidence == "high" and len(set(finding.source_identifiers)) < 2:
        problems.append("High-confidence finding requires at least two independent sources.")
    return problems


def validate_citation_markers(text: str, evidence: list[Evidence]) -> list[str]:
    known = {item.source.identifier or item.source.url for item in evidence}
    cited = set(_CITATION.findall(text))
    return [f"Citation marker does not resolve: {item}" for item in sorted(cited - known)]
