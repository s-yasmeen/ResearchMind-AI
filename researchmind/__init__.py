"""ResearchMind public package."""

from .engine import ResearchEngine
from .protocol import create_protocol
from .literature import LiteratureReviewAgent
from .model_design import design_multiobjective_model
from .publication import publication_readiness_gate

__all__ = [
    "ResearchEngine", "create_protocol", "LiteratureReviewAgent",
    "design_multiobjective_model", "publication_readiness_gate",
]
__version__ = "0.8.0"
