from __future__ import annotations

import re

from .models import AgentName

_METHODOLOGY_TERMS = {
    "dataset", "method", "methodology", "architecture", "baseline",
    "experiment", "metric", "preprocessing", "evaluation",
}
_WRITING_TERMS = {
    "abstract", "rewrite", "edit", "introduction", "conclusion",
    "proofread", "title", "paragraph",
}


def route_query(query: str) -> AgentName:
    """Route predictably; an LLM is not needed for this safety-critical step."""
    tokens = set(re.findall(r"[a-z]+", query.lower()))
    methodology_score = len(tokens & _METHODOLOGY_TERMS)
    writing_score = len(tokens & _WRITING_TERMS)
    if methodology_score > writing_score and methodology_score:
        return "methodology"
    if writing_score:
        return "writing"
    return "literature"
