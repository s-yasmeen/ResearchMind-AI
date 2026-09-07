"""ResearchMind public package."""

from .engine import ResearchEngine
from .protocol import create_protocol
from .literature import LiteratureReviewAgent
from .model_design import design_multiobjective_model

__all__ = ["ResearchEngine", "create_protocol", "LiteratureReviewAgent", "design_multiobjective_model"]
__version__ = "0.6.0"
