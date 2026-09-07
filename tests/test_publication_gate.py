from datetime import datetime, timezone

from researchmind.manuscript import ManuscriptClaim
from researchmind.publication import (
    ClaimEvidenceLink, ExpertApproval, SourceVerification, publication_readiness_gate,
)
from test_manuscript_integrity import complete_manuscript


def approvals():
    now = datetime.now(timezone.utc)
    return [
        ExpertApproval(scope, "Independent reviewer", "Relevant specialist", "approved", now,
                       conflict_of_interest_declared=True)
        for scope in ("novelty", "mathematics", "interpretation", "publication")
    ]


def test_verified_manuscript_passes_publication_gate():
    result = publication_readiness_gate(
        complete_manuscript(),
        [SourceVerification("doi:1", "Verified study", True, True)],
        [ClaimEvidenceLink("C1", "doi:1", "p. 4, Results", "Reported result", "supports")],
        approvals(),
    )
    assert result.ready
    assert result.blockers == []
    assert result.claim_audits[0].status == "verified"


def test_gate_blocks_hallucinated_or_unsafe_evidence_and_missing_approvals():
    manuscript = complete_manuscript()
    manuscript.claims.append(
        ManuscriptClaim("C4", "This is the first method to solve the problem", "evidence", ("fake",))
    )
    result = publication_readiness_gate(
        manuscript,
        [
            SourceVerification("doi:1", "Retracted study", True, True, retracted=True),
            SourceVerification("fake", "Unverified record", False, False),
        ],
        [
            ClaimEvidenceLink("C1", "doi:1", "p. 4", "Reported result", "contradicts"),
            ClaimEvidenceLink("C4", "fake", "", "", "unclear"),
        ],
        [],
    )
    combined = "\n".join(result.blockers)
    assert not result.ready
    assert "contradicts claim: C1" in combined
    assert "unavailable, unverified, or retracted" in combined
    assert "Novelty claims require" in combined
    assert "Mathematical validity requires" in combined
    assert "Final publication approval" in combined


def test_partial_support_is_visible_and_requires_narrower_wording():
    result = publication_readiness_gate(
        complete_manuscript(),
        [SourceVerification("doi:1", "Verified study", True, True)],
        [ClaimEvidenceLink("C1", "doi:1", "Table 2", "Subset result", "partially_supports")],
        approvals(),
    )
    assert result.ready
    assert result.claim_audits[0].status == "partial"
    assert "Claim requires narrower wording: C1" in result.warnings
