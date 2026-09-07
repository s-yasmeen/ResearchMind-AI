from researchmind.manuscript import ManuscriptClaim, manuscript_quality_gate, suspicious_source_overlap


def test_complete_manuscript_passes_gate(complete_manuscript):
    assert manuscript_quality_gate(complete_manuscript, {"doi:1"}) == []


def test_gate_blocks_hallucinated_reference_and_missing_section(complete_manuscript):
    manuscript = complete_manuscript
    manuscript.sections["results"] = ""
    manuscript.claims.append(ManuscriptClaim("C4", "Unsupported", "evidence", ("fake",)))
    problems = manuscript_quality_gate(manuscript, {"doi:1"})
    assert "Missing required section: results" in problems
    assert "Claim C4 cites unknown source: fake" in problems


def test_overlap_check_flags_verbatim_reuse():
    source = "This exact eight word phrase was copied from the original source text."
    assert suspicious_source_overlap(source, [source]) == 1.0
    assert suspicious_source_overlap("A wholly different short explanation", [source]) == 0.0
