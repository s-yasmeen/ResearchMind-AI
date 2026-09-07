from __future__ import annotations

import math
from dataclasses import dataclass

from .manuscript import AlgorithmSpecification, MathematicalModel


@dataclass(frozen=True)
class Objective:
    symbol: str
    name: str
    definition: str
    direction: str  # maximize or minimize
    weight: float
    normalized: bool


@dataclass(frozen=True)
class Constraint:
    expression: str
    meaning: str
    verification_test: str


@dataclass(frozen=True)
class ModelDesign:
    model: MathematicalModel
    objectives: tuple[Objective, ...]
    constraints: tuple[Constraint, ...]
    algorithm: AlgorithmSpecification
    evaluation_requirements: tuple[str, ...]
    audit_warnings: tuple[str, ...]


def audit_objectives(objectives: tuple[Objective, ...]) -> list[str]:
    warnings: list[str] = []
    if len(objectives) < 2:
        warnings.append("A multi-objective design requires at least two objectives.")
    symbols = [objective.symbol for objective in objectives]
    if len(symbols) != len(set(symbols)):
        warnings.append("Objective symbols must be unique.")
    if any(objective.direction not in {"maximize", "minimize"} for objective in objectives):
        warnings.append("Every objective direction must be maximize or minimize.")
    if any(not math.isfinite(objective.weight) or objective.weight < 0 for objective in objectives):
        warnings.append("Objective weights must be finite and non-negative.")
    if not math.isclose(sum(o.weight for o in objectives), 1.0, abs_tol=1e-9):
        warnings.append("Objective weights must sum to 1.")
    if any(not objective.normalized for objective in objectives):
        warnings.append("Weighted objectives must be normalized or made dimensionally compatible.")
    return warnings


def design_multiobjective_model(
    name: str,
    purpose: str,
    objectives: tuple[Objective, ...],
    constraints: tuple[Constraint, ...],
    assumptions: tuple[str, ...],
    algorithm_steps: tuple[str, ...],
    time_complexity: str,
    space_complexity: str,
) -> ModelDesign:
    warnings = audit_objectives(objectives)
    if not assumptions:
        warnings.append("Model assumptions must be stated explicitly.")
    if not constraints:
        warnings.append("At least one operational, ethical, or validity constraint is required.")
    signed_terms = [
        f"{objective.weight:g}*{objective.symbol}" if objective.direction == "maximize"
        else f"-{objective.weight:g}*{objective.symbol}"
        for objective in objectives
    ]
    equation = "J(theta) = " + " + ".join(signed_terms).replace("+ -", "- ")
    symbols = tuple((o.symbol, f"{o.name}: {o.definition}", "normalized [0,1]") for o in objectives) + (("theta", "trainable/model parameters", "parameter space"),)
    model = MathematicalModel(
        name=name,
        purpose=purpose,
        assumptions=assumptions,
        symbols=symbols,
        equations=(equation, *(constraint.expression for constraint in constraints)),
        derivation_steps=("Define measurable objectives independently", "Normalize objectives on predeclared reference ranges", "Assign weights before final evaluation", "Optimize the scalar objective and report the Pareto frontier", "Test sensitivity to weights and constraints"),
        identifiability_conditions=("Each objective has an observable estimator", "Parameters are distinguishable under the evaluation design", "Weights and thresholds are fixed without using the final test set"),
        validation_tests=("objective-wise ablation", "weight sensitivity", "constraint violation rate", "external validation", "calibration and subgroup analysis"),
        limitations=("A weighted sum may miss non-convex Pareto solutions", "Results depend on objective validity and normalization", "The equation is a proposed model until empirically validated"),
    )
    algorithm = AlgorithmSpecification(
        name=f"Optimization procedure for {name}",
        inputs=("training data", "predeclared objectives", "constraints", "fixed hyperparameter search space"),
        outputs=("fitted parameters", "objective scores", "constraint report", "Pareto analysis"),
        pseudocode_steps=algorithm_steps,
        time_complexity=time_complexity,
        space_complexity=space_complexity,
        invariants=("test set is never used for optimization", "all constraints are checked each evaluation", "all objective components are reported separately"),
        failure_modes=("objective collapse", "constraint violation", "data leakage", "unstable convergence", "subgroup performance degradation"),
    )
    return ModelDesign(
        model=model,
        objectives=objectives,
        constraints=constraints,
        algorithm=algorithm,
        evaluation_requirements=("strong and simple baselines", "ablation study", "confidence intervals and effect sizes", "external or temporal validation", "computational cost", "fairness and privacy where relevant", "complete seed and configuration disclosure"),
        audit_warnings=tuple(warnings),
    )
