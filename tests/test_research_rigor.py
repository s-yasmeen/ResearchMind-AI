from researchmind.appraisal import appraise_corpus, appraise_study
from researchmind.gaps import identify_gaps
from researchmind.integrity import validate_citation_markers, validate_finding
from researchmind.models import Evidence, Finding, Source, StudyRecord
from researchmind.protocol import create_protocol, frame_question


def strong_study(identifier: str = "10.1000/example", dataset: str = "Dataset-A"):
    return StudyRecord(
        source=Source(
            title="A reproducible evaluation",
            url=f"https://doi.org/{identifier}",
            authors=("A. Researcher", "B. Scientist"),
            year=2025,
            identifier=identifier,
        ),
        abstract="We evaluate the proposed method against established baselines.",
        study_type="controlled experiment",
        peer_reviewed=True,
        sample_size=1000,
        dataset=dataset,
        methods=("transformer",),
        metrics=("F1", "AUROC"),
        limitations=("Single region",),
        has_comparator=True,
        external_validation=True,
        reproducible_assets=True,
    )


def test_protocol_is_reproducible_and_multidatabase():
    protocol = create_protocol("How can AI protect patient biometric privacy in telemedicine?")
    assert protocol.question.framework == "PICO"
    assert "IEEE Xplore" in protocol.search_plan.databases
    assert "ACM Digital Library" in protocol.search_plan.databases
    assert protocol.search_plan.inclusion_criteria
    assert protocol.search_plan.exclusion_criteria


def test_short_question_is_rejected():
    try:
        frame_question("AI?")
    except ValueError:
        pass
    else:
        raise AssertionError("Under-specified question was accepted")


def test_strong_study_receives_high_transparent_score():
    result = appraise_study(strong_study())
    assert result.score == 100
    assert result.evidence_level == "high"
    assert not result.concerns


def test_missing_metadata_reduces_evidence_level():
    weak = StudyRecord(source=Source(title="Unknown", url="https://example.org"), abstract="")
    result = appraise_study(weak)
    assert result.evidence_level == "insufficient"
    assert "Methods not extracted" in result.concerns


def test_no_corpus_does_not_invent_a_substantive_gap():
    gaps = identify_gaps([], [])
    assert len(gaps) == 1
    assert gaps[0].confidence == "insufficient"
    assert "no substantive research gap can be claimed" in gaps[0].statement


def test_observable_corpus_weaknesses_generate_testable_gaps():
    studies = [
        StudyRecord(
            source=Source(title=f"Study {i}", url=f"https://example.org/{i}"),
            abstract="Abstract",
            dataset="Dataset-A",
        )
        for i in range(3)
    ]
    gaps = identify_gaps(studies, appraise_corpus(studies))
    types = {gap.gap_type for gap in gaps}
    assert {"methodological", "replication", "population", "evidence"} <= types
    assert all(gap.basis and gap.proposed_test for gap in gaps)


def test_citation_integrity_rejects_unknown_sources():
    source = Source("Paper", "https://doi.org/known", identifier="known")
    evidence = [Evidence("Supported passage", source, page=3)]
    finding = Finding("Claim", ("missing",), "moderate")
    assert validate_finding(finding, evidence) == ["Unknown supporting source: missing"]
    assert validate_citation_markers("Claim [missing]", evidence) == [
        "Citation marker does not resolve: missing"
    ]


def test_high_confidence_needs_independent_sources():
    source = Source("Paper", "https://doi.org/known", identifier="known")
    evidence = [Evidence("Supported passage", source)]
    finding = Finding("Claim", ("known",), "high")
    problems = validate_finding(finding, evidence)
    assert "High-confidence finding requires at least two independent sources." in problems
