from dataclasses import replace
from datetime import datetime, timedelta, timezone

from researchmind.manuscript import ManuscriptClaim
from researchmind.publication import (
    AuditEvent, ClaimEvidenceLink, EvidenceRecord, ExpertApproval, ReproducibilityPackage,
    SemanticAssessment, SourceVerification, StatisticalValidation, append_audit_event,
    create_expert_approval,
    manuscript_fingerprint, publication_readiness_gate,
)

NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)


def semantic_support(_claim: str, _passage: str):
    return SemanticAssessment("supports", "The passage entails the bounded claim.", "test-verifier-v1")


def valid_inputs(manuscript):
    fingerprint = manuscript_fingerprint(manuscript)
    source = SourceVerification(
        "doi:1", "Primary trial", True, True, "primary", "trial-registration-1",
        ("A. Researcher",), "none", NOW,
    )
    record = EvidenceRecord.create(
        "E1", "doi:1", "p. 4, Results", "Treatment improved the measured outcome."
    )
    link = ClaimEvidenceLink(
        "C1", "doi:1", record.locator, record.text, "supports", record.evidence_id, record.content_hash
    )
    approvals = [
        create_expert_approval(
            scope, "Independent reviewer", "Relevant specialist", "approved", NOW, fingerprint
        )
        for scope in ("novelty", "mathematics", "interpretation", "publication")
    ]
    statistics = StatisticalValidation(
        ("normality examined", "variance examined"), "A-priori power analysis",
        ("identity-disjoint split", "pipeline fitted on training data only"),
        ("Cohen's d",), ("95% CI for primary outcome",), "Holm correction", True,
    )
    reproducibility = ReproducibilityPackage(
        "config-sha256", (7, 19, 41), "environment-sha256", "Dataset A", "2.1",
        "dataset-accession-or-hash", ("run-log-1",), "git-commit-sha",
    )
    trail = []
    append_audit_event(trail, "system", "lock manuscript", fingerprint, NOW)
    return [source], [record], [link], approvals, statistics, reproducibility, trail


def run_gate(manuscript, **overrides):
    sources, records, links, approvals, statistics, reproducibility, trail = valid_inputs(manuscript)
    inputs = dict(
        sources=sources, evidence_records=records, evidence_links=links, approvals=approvals,
        semantic_verifier=semantic_support, statistics=statistics, reproducibility=reproducibility,
        audit_trail=trail, now=NOW,
    )
    inputs.update(overrides)
    return publication_readiness_gate(manuscript, **inputs)


def test_fully_verified_manuscript_passes(complete_manuscript):
    result = run_gate(complete_manuscript)
    assert result.ready
    assert result.claim_audits[0].status == "verified"


def test_fabricated_excerpt_is_blocked(complete_manuscript):
    sources, records, links, approvals, stats, repro, trail = valid_inputs(complete_manuscript)
    forged = [replace(links[0], supporting_excerpt="Fabricated result")]
    result = run_gate(complete_manuscript, sources=sources, evidence_records=records,
                      evidence_links=forged, approvals=approvals, statistics=stats,
                      reproducibility=repro, audit_trail=trail)
    assert "Fabricated or altered evidence binding: C1" in result.blockers


def test_forged_and_stale_approvals_are_blocked(complete_manuscript):
    _, _, _, approvals, _, _, _ = valid_inputs(complete_manuscript)
    forged = [replace(item, manuscript_hash="forged") for item in approvals]
    assert "Current manuscript lacks valid publication approval." in run_gate(
        complete_manuscript, approvals=forged
    ).blockers
    stale = [replace(item, reviewed_at=NOW - timedelta(days=181)) for item in approvals]
    assert "Current manuscript lacks valid publication approval." in run_gate(
        complete_manuscript, approvals=stale
    ).blockers
    altered_reviewer = [replace(item, reviewer="Impostor") for item in approvals]
    assert "Current manuscript lacks valid publication approval." in run_gate(
        complete_manuscript, approvals=altered_reviewer
    ).blockers


def test_manuscript_change_invalidates_approval_and_lock(complete_manuscript):
    sources, records, links, approvals, stats, repro, trail = valid_inputs(complete_manuscript)
    complete_manuscript.title = "Changed after approval"
    result = publication_readiness_gate(
        complete_manuscript, sources, links, approvals, evidence_records=records,
        semantic_verifier=semantic_support, statistics=stats, reproducibility=repro,
        audit_trail=trail, now=NOW,
    )
    assert "Current manuscript lacks valid publication approval." in result.blockers
    assert "Audit trail is not locked to the current manuscript version." in result.blockers


def test_duplicate_sources_and_citation_mismatch_are_blocked(complete_manuscript):
    sources, _, _, _, _, _, _ = valid_inputs(complete_manuscript)
    result = run_gate(complete_manuscript, sources=sources + sources, evidence_links=[])
    assert "Duplicate source identifiers prevent unambiguous traceability." in result.blockers
    assert "Claim-to-citation mismatch: C1" in result.blockers
    doi_variant = replace(sources[0], identifier="https://doi.org/DOI:1")
    assert "Duplicate source identifiers prevent unambiguous traceability." in run_gate(
        complete_manuscript, sources=sources + [doi_variant]
    ).blockers


def test_review_source_cannot_launder_primary_result(complete_manuscript):
    sources, *_ = valid_inputs(complete_manuscript)
    review = replace(sources[0], source_type="systematic_review")
    result = run_gate(complete_manuscript, sources=[review])
    assert "Possible citation laundering; direct claim must cite primary evidence: C1" in result.blockers


def test_high_confidence_requires_independent_primary_studies(complete_manuscript):
    complete_manuscript.claims[0] = replace(complete_manuscript.claims[0], confidence="high")
    result = run_gate(complete_manuscript)
    assert "High-confidence claim lacks two independent primary studies: C1" in result.blockers


def test_publication_notices_are_blocking(complete_manuscript):
    sources, *_ = valid_inputs(complete_manuscript)
    concerned = replace(sources[0], correction_status="expression_of_concern")
    assert "Source has an unresolved publication notice: doi:1" in run_gate(
        complete_manuscript, sources=[concerned]
    ).blockers
    uncorrected = replace(sources[0], correction_status="corrected", corrected_version_used=False)
    assert "Corrected source version was not used: doi:1" in run_gate(
        complete_manuscript, sources=[uncorrected]
    ).blockers


def test_partial_semantic_support_blocks_release(complete_manuscript):
    def partial(_claim, _passage):
        return SemanticAssessment("partially_supports", "Only a subgroup was studied.", "verifier")

    _, _, links, _, _, _, _ = valid_inputs(complete_manuscript)
    links = [replace(links[0], support_assessment="partially_supports")]
    result = run_gate(complete_manuscript, evidence_links=links, semantic_verifier=partial)
    assert "Partially supported claim must be narrowed and re-audited: C1" in result.blockers


def test_tampered_audit_statistics_and_reproducibility_are_blocked(complete_manuscript):
    _, _, _, _, _, _, trail = valid_inputs(complete_manuscript)
    event = trail[0]
    tampered = [AuditEvent(event.sequence, event.timestamp, event.actor, "changed",
                           event.manuscript_hash, event.previous_hash, event.event_hash)]
    result = run_gate(complete_manuscript, audit_trail=tampered, statistics=None, reproducibility=None)
    assert "Audit trail integrity failure at sequence 1." in result.blockers
    assert "Statistical validation record is missing." in result.blockers
    assert "Reproducibility package is missing." in result.blockers
