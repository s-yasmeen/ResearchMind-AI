from dataclasses import replace

import pytest

from researchmind.contribution import map_gap_to_contribution
from researchmind.literature import LiteratureReviewAgent
from researchmind.model_design import Constraint, Objective, audit_objectives, design_multiobjective_model
from researchmind.models import Finding, ResearchGap, Source, StudyRecord
from researchmind.screening import ScreeningCriteria, screen_corpus


def study(identifier: str, year: int = 2025, dataset: str = "A") -> StudyRecord:
    return StudyRecord(
        source=Source(
            title=f"Biometric privacy study {identifier}",
            url=f"https://doi.org/{identifier}",
            authors=("A. Researcher",),
            year=year,
            identifier=identifier,
            venue="IEEE Test Venue",
            publication_type="journal-article",
        ),
        abstract="Biometric privacy masking is evaluated for telemedicine patients.",
        peer_reviewed=True,
        dataset=dataset,
        methods=("privacy mask",),
        metrics=("privacy risk", "diagnostic utility"),
        limitations=("single dataset",),
        has_comparator=True,
        external_validation=False,
        reproducible_assets=False,
    )


def test_screening_records_decisions_and_deduplicates():
    criteria = ScreeningCriteria(("biometric", "privacy"), 2020, 2026)
    included, decisions = screen_corpus([study("10.1/a"), study("10.1/a"), study("10.1/old", 2010)], criteria)
    assert len(included) == 1
    assert len(decisions) == 2
    assert {decision.decision for decision in decisions} == {"include", "exclude"}
    assert all(decision.reasons for decision in decisions)


def test_missing_metadata_requires_human_review():
    incomplete = replace(study("10.1/x"), source=replace(study("10.1/x").source, year=None), abstract="")
    included, decisions = screen_corpus([incomplete], ScreeningCriteria(("biometric", "privacy")))
    assert included == []
    assert decisions[0].decision == "human_review"


def test_literature_agent_builds_matrix_themes_gaps_and_contradictions():
    studies = [study("10.1/a"), study("10.1/b")]
    findings = [
        Finding("Mask improves utility", ("10.1/a",), "moderate", "supports"),
        Finding("Mask improves utility", ("10.1/b",), "moderate", "contradicts"),
    ]
    review = LiteratureReviewAgent().analyze(
        studies, ScreeningCriteria(("biometric", "privacy")), findings
    )
    assert review.included_count == 2
    assert len(review.matrix) == 2
    assert any(theme.category == "method" for theme in review.themes)
    assert review.gaps
    assert review.contradictions == {"mask improves utility": ("10.1/a", "10.1/b")}
    assert review.limitations


def test_insufficient_gap_cannot_become_contribution():
    gap = ResearchGap("evidence", "No evidence", ("count=0",), "insufficient", "Search first")
    with pytest.raises(ValueError):
        map_gap_to_contribution(gap, "method", ("dataset",), ("baseline",), ("F1",))


def test_supported_gap_maps_to_falsifiable_experiment():
    gap = ResearchGap("methodological", "No external validation", ("0/10",), "moderate", "External test")
    plan = map_gap_to_contribution(
        gap, "task-aware privacy model", ("internal", "external"),
        ("blur", "pixelation"), ("privacy risk", "diagnostic utility"),
    )
    assert "Novelty remains a hypothesis" in plan.novelty_boundary
    assert plan.experiment.ablations
    assert plan.experiment.failure_criteria
    assert "external dataset or site" in plan.experiment.robustness_checks


def test_explainable_model_has_equation_derivation_algorithm_and_audit():
    objectives = (
        Objective("U", "diagnostic utility", "task performance", "maximize", 0.6, True),
        Objective("R", "privacy risk", "identity leakage", "minimize", 0.4, True),
    )
    constraints = (Constraint("R(theta) <= tau", "Bound identity leakage", "Evaluate an unseen identity attacker"),)
    design = design_multiobjective_model(
        "Task-aware privacy objective", "Balance utility and privacy", objectives, constraints,
        ("Utility and risk estimators are valid", "Test identities are disjoint"),
        ("Split by identity", "Fit on training data", "Select on validation data", "Evaluate once on test data"),
        "O(E*N*C)", "O(N+D)",
    )
    assert design.audit_warnings == ()
    assert "0.6*U" in design.model.equations[0]
    assert design.model.derivation_steps and design.model.validation_tests and design.model.limitations
    assert design.algorithm.pseudocode_steps and design.algorithm.failure_modes
    assert "test set is never used for optimization" in design.algorithm.invariants


def test_model_auditor_rejects_unbalanced_or_dimensional_objectives():
    invalid = (
        Objective("X", "one", "raw score", "maximize", 0.8, False),
        Objective("X", "two", "raw score", "sideways", 0.8, False),
    )
    warnings = audit_objectives(invalid)
    assert "Objective symbols must be unique." in warnings
    assert "Every objective direction must be maximize or minimize." in warnings
    assert "Objective weights must sum to 1." in warnings
    assert "Weighted objectives must be normalized or made dimensionally compatible." in warnings
