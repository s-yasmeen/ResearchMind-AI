from researchmind.manuscript import (
    AlgorithmSpecification,
    Manuscript,
    ManuscriptClaim,
    MathematicalModel,
    VisualSpecification,
    manuscript_quality_gate,
    suspicious_source_overlap,
)


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
            ManuscriptClaim("C1", "A supported finding", "evidence", ("doi:1",)),
            ManuscriptClaim("C2", "Our proposed contribution", "author_contribution"),
            ManuscriptClaim("C3", "A cautious interpretation", "interpretation", uncertainty="Requires external validation"),
        ],
        models=[MathematicalModel(
            name="Utility-privacy objective",
            purpose="Optimize two measurable objectives",
            assumptions=("Metrics are normalized",),
            symbols=(("U", "utility", "[0,1]"), ("P", "privacy", "[0,1]")),
            equations=("J = alpha U + (1-alpha) P",),
            derivation_steps=("Normalize both objectives", "Apply a convex weighting"),
            identifiability_conditions=("alpha is selected before final evaluation",),
            validation_tests=("Sensitivity analysis over alpha",),
            limitations=("A scalar objective may hide Pareto trade-offs",),
        )],
        algorithms=[AlgorithmSpecification(
            name="Evidence screening",
            inputs=("candidate records",), outputs=("eligible records",),
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


def test_complete_manuscript_passes_gate():
    assert manuscript_quality_gate(complete_manuscript(), {"doi:1"}) == []


def test_gate_blocks_hallucinated_reference_and_missing_section():
    manuscript = complete_manuscript()
    manuscript.sections["results"] = ""
    manuscript.claims.append(ManuscriptClaim("C4", "Unsupported", "evidence", ("fake",)))
    problems = manuscript_quality_gate(manuscript, {"doi:1"})
    assert "Missing required section: results" in problems
    assert "Claim C4 cites unknown source: fake" in problems


def test_overlap_check_flags_verbatim_reuse():
    source = "This exact eight word phrase was copied from the original source text."
    assert suspicious_source_overlap(source, [source]) == 1.0
    assert suspicious_source_overlap("A wholly different short explanation", [source]) == 0.0
