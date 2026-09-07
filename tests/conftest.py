import pytest

from researchmind.manuscript import (
    AlgorithmSpecification, Manuscript, ManuscriptClaim, MathematicalModel, VisualSpecification,
)


@pytest.fixture
def complete_manuscript():
    sections = {
        key: "Substantive draft content"
        for key in (
            "abstract", "keywords", "introduction", "related_work", "research_gap",
            "methodology", "mathematical_model", "algorithm", "experimental_design",
            "results", "discussion", "threats_to_validity", "conclusion", "references",
        )
    }
    return Manuscript(
        title="Evidence-Grounded Research",
        sections=sections,
        claims=[
            ManuscriptClaim("C1", "Treatment improved the measured outcome.", "direct_evidence",
                            ("doi:1",), confidence="moderate"),
            ManuscriptClaim("C2", "Our proposed contribution", "author_contribution",
                            confidence="not_applicable"),
            ManuscriptClaim("C3", "The result may generalize cautiously.", "inference",
                            uncertainty="Requires external validation", confidence="low",
                            derived_from_claims=("C1",)),
        ],
        models=[MathematicalModel(
            name="Utility-privacy objective", purpose="Optimize two measurable objectives",
            assumptions=("Metrics are normalized",),
            symbols=(("U", "utility", "[0,1]"), ("P", "privacy", "[0,1]")),
            equations=("J = alpha U + (1-alpha) P",),
            derivation_steps=("Normalize both objectives", "Apply a convex weighting"),
            identifiability_conditions=("alpha is selected before final evaluation",),
            validation_tests=("Sensitivity analysis over alpha",),
            limitations=("A scalar objective may hide Pareto trade-offs",),
        )],
        algorithms=[AlgorithmSpecification(
            name="Evidence screening", inputs=("candidate records",), outputs=("eligible records",),
            pseudocode_steps=("Deduplicate", "Apply eligibility criteria", "Record decisions"),
            time_complexity="O(n log n)", space_complexity="O(n)",
            invariants=("Every exclusion has a reason",),
            failure_modes=("Incomplete metadata requires human adjudication",),
        )],
        visuals=[VisualSpecification(
            "T1", "table", "Study characteristics", "Compare eligible studies",
            "Structured extraction records", "Characteristics of eligible studies.",
            "The studies differ in validation scope.", "External validation is the main weakness.",
        )],
    )
