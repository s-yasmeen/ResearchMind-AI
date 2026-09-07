from __future__ import annotations

from dataclasses import dataclass

from .models import ResearchGap


@dataclass(frozen=True)
class ExperimentPlan:
    hypothesis: str
    independent_variables: tuple[str, ...]
    dependent_variables: tuple[str, ...]
    baselines: tuple[str, ...]
    datasets_or_populations: tuple[str, ...]
    primary_metrics: tuple[str, ...]
    secondary_metrics: tuple[str, ...]
    ablations: tuple[str, ...]
    uncertainty_analysis: tuple[str, ...]
    robustness_checks: tuple[str, ...]
    failure_criteria: tuple[str, ...]


@dataclass(frozen=True)
class ContributionPlan:
    gap: ResearchGap
    contribution_statement: str
    novelty_boundary: str
    experiment: ExperimentPlan
    human_approvals_required: tuple[str, ...]


def map_gap_to_contribution(
    gap: ResearchGap,
    proposed_method: str,
    datasets_or_populations: tuple[str, ...],
    baselines: tuple[str, ...],
    primary_metrics: tuple[str, ...],
) -> ContributionPlan:
    if gap.confidence == "insufficient":
        raise ValueError("An insufficiently supported gap cannot justify a research contribution.")
    if not gap.basis:
        raise ValueError("Gap must have an auditable evidence basis.")
    if not all((proposed_method.strip(), datasets_or_populations, baselines, primary_metrics)):
        raise ValueError("Method, evaluation scope, baselines, and primary metrics are required.")
    experiment = ExperimentPlan(
        hypothesis=f"{proposed_method} addresses the measured {gap.gap_type} gap without degrading the primary outcomes.",
        independent_variables=("proposed method", "baseline method", "evaluation condition"),
        dependent_variables=primary_metrics,
        baselines=baselines,
        datasets_or_populations=datasets_or_populations,
        primary_metrics=primary_metrics,
        secondary_metrics=("runtime", "memory", "calibration", "subgroup performance"),
        ablations=("remove each proposed component", "replace learned components with simple alternatives", "vary objective weights"),
        uncertainty_analysis=("confidence intervals", "effect sizes", "seed-to-seed variance", "multiple-comparison control when applicable"),
        robustness_checks=("external dataset or site", "distribution shift", "missing/noisy input", "sensitivity analysis"),
        failure_criteria=("no meaningful improvement over a strong baseline", "benefit disappears under external validation", "unacceptable subgroup harm", "results depend on one split or seed"),
    )
    return ContributionPlan(
        gap=gap,
        contribution_statement=f"Develop and evaluate {proposed_method} to address: {gap.statement}",
        novelty_boundary="Novelty remains a hypothesis until verified against prior art, ablations, and independent baselines.",
        experiment=experiment,
        human_approvals_required=("final novelty claim", "ethical and data-governance review", "domain validity of metrics", "interpretation of practical significance"),
    )
