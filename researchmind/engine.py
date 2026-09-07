from __future__ import annotations

from collections.abc import Callable

from .checkpoints import CheckpointStore
from .config import Settings
from .models import ResearchResult
from .router import route_query

AgentHandler = Callable[[str], ResearchResult]


class ResearchEngine:
    """Small orchestration core; retrieval and live LLM handlers plug in later."""

    def __init__(self, settings: Settings, handlers: dict[str, AgentHandler] | None = None):
        self.settings = settings
        self.handlers = handlers or {}
        self.checkpoints = CheckpointStore(settings.data_dir / "checkpoints")

    def run(self, query: str) -> ResearchResult:
        query = query.strip()
        if not query:
            raise ValueError("Research query cannot be empty.")

        agent = route_query(query)
        handler = self.handlers.get(agent)
        if handler is None:
            result = ResearchResult(
                query=query,
                agent=agent,
                answer="",
                warnings=[
                    f"The {agent} agent is configured but its live evidence pipeline "
                    "will be connected in Stage 2."
                ],
            )
        else:
            result = handler(query)

        self.checkpoints.save(query, {"query": query, "result": result.to_dict()})
        return result

    def health(self) -> dict[str, object]:
        return {
            "status": "ready",
            "configuration": self.settings.safe_summary(),
            "agents": ["literature", "methodology", "writing"],
        }
