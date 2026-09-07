from __future__ import annotations

from collections.abc import Callable

from .checkpoints import CheckpointStore
from .config import Settings
from .models import ResearchResult
from .protocol import create_protocol
from .literature import LiteratureReviewAgent
from .screening import ScreeningCriteria
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
            protocol = create_protocol(query)
            result = ResearchResult(
                query=query,
                agent=agent,
                answer=(
                    "A reproducible research protocol has been prepared. "
                    f"Framework: {protocol.question.framework}. "
                    f"Databases: {', '.join(protocol.search_plan.databases)}."
                ),
                warnings=[
                    "No literature claims have been generated because eligible studies "
                    "have not yet been retrieved and appraised."
                ],
            )
            self.checkpoints.save(
                query,
                {"query": query, "protocol": protocol.to_dict(), "result": result.to_dict()},
            )
            return result
        else:
            result = handler(query)

        self.checkpoints.save(query, {"query": query, "result": result.to_dict()})
        return result

    def plan(self, query: str):
        """Create the auditable protocol before retrieval or generation."""
        return create_protocol(query)

    def review(self, studies, criteria: ScreeningCriteria, findings=None):
        """Run the structured review layer without generating unsupported prose."""
        return LiteratureReviewAgent().analyze(studies, criteria, findings)

    def health(self) -> dict[str, object]:
        configured = bool(self.settings.api_key)
        return {
            "status": "ready" if configured else "setup_required",
            "can_run_live_research": configured,
            "configuration": self.settings.safe_summary(),
            "agents": ["literature", "methodology", "writing"],
        }
