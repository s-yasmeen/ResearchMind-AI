from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AgentName = Literal["literature", "methodology", "writing"]


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    identifier: str | None = None


@dataclass(frozen=True)
class Evidence:
    text: str
    source: Source
    page: int | None = None


@dataclass
class ResearchResult:
    query: str
    agent: AgentName
    answer: str
    evidence: list[Evidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
