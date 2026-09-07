from researchmind.models import Appraisal, Finding
from researchmind.synthesis import conservative_confidence, contradiction_map


def appraisal(identifier, level):
    return Appraisal(identifier, 80, level, (), ())


def test_single_source_high_evidence_is_downgraded():
    assert conservative_confidence(("A",), [appraisal("A", "high")]) == "moderate"


def test_two_independent_high_sources_support_high_confidence():
    items = [appraisal("A", "high"), appraisal("B", "high")]
    assert conservative_confidence(("A", "B"), items) == "high"


def test_contradictions_require_explicit_opposing_stances():
    findings = [
        Finding("Method improves utility", ("A",), "moderate", "supports"),
        Finding("Method improves utility", ("B",), "moderate", "contradicts"),
    ]
    assert contradiction_map(findings) == {"method improves utility": ("A", "B")}
