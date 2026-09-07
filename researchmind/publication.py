from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from .manuscript import Manuscript, manuscript_quality_gate

ApprovalScope = Literal["novelty", "mathematics", "interpretation", "publication"]
ApprovalDecision = Literal["approved", "rejected", "changes_required"]


@dataclass(frozen=True)
class SourceVerification:
    identifier: str
    title: str
    retrievable: bool
    metadata_verified: bool
    retracted: bool = False


@dataclass(frozen=True)
class ClaimEvidenceLink:
    claim_id: str
    source_identifier: str
    locator: str
    supporting_excerpt: str
    support_assessment: Literal["supports", "partially_supports", "contradicts", "unclear"]


@dataclass(frozen=True)
class ExpertApproval:
    scope: ApprovalScope
    reviewer: str
    expertise: str
    decision: ApprovalDecision
    reviewed_at: datetime
    target_id: str = "manuscript"
    notes: str = ""
    conflict_of_interest_declared: bool = False


@dataclass(frozen=True)
class ClaimAudit:
    claim_id: str
    status: Literal["verified", "partial", "contradicted", "unverified"]
    sources: tuple[str, ...]
    explanation: str


@dataclass
class PublicationGateResult:
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    claim_audits: list[ClaimAudit] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.blockers


_NOVELTY_LANGUAGE = re.compile(
    r"\b(first|novel|unprecedented|state[- ]of[- ]the[- ]art|outperform(?:s|ed)? all)\b",
    re.IGNORECASE,
)


def _valid_approval(approvals: list[ExpertApproval], scope: ApprovalScope) -> bool:
    candidates = [item for item in approvals if item.scope == scope and item.target_id == "manuscript"]
    if not candidates:
        return False
    latest = max(candidates, key=lambda item: item.reviewed_at)
    if latest.reviewed_at.tzinfo is None:
        return False
    return (
        latest.decision == "approved"
        and bool(latest.reviewer.strip())
        and bool(latest.expertise.strip())
        and latest.conflict_of_interest_declared
        and latest.reviewed_at <= datetime.now(timezone.utc)
    )


def publication_readiness_gate(
    manuscript: Manuscript,
    sources: list[SourceVerification],
    evidence_links: list[ClaimEvidenceLink],
    approvals: list[ExpertApproval],
) -> PublicationGateResult:
    """Audit traceability and governance without pretending to replace peer review."""
    result = PublicationGateResult()
    source_map = {source.identifier: source for source in sources}
    result.blockers.extend(manuscript_quality_gate(manuscript, set(source_map)))
    if len(source_map) != len(sources):
        result.blockers.append("Duplicate source identifiers prevent unambiguous traceability.")
    for source in sources:
        if not source.identifier.strip() or not source.title.strip():
            result.blockers.append("Every source requires a non-empty identifier and title.")

    links_by_claim: dict[str, list[ClaimEvidenceLink]] = {}
    for link in evidence_links:
        links_by_claim.setdefault(link.claim_id, []).append(link)
        if link.source_identifier not in source_map:
            result.blockers.append(f"Evidence link for {link.claim_id} cites unknown source: {link.source_identifier}")
        if not link.locator.strip():
            result.blockers.append(f"Evidence link lacks a page, section, or record locator: {link.claim_id}")
        if not link.supporting_excerpt.strip():
            result.blockers.append(f"Evidence link lacks auditable supporting text: {link.claim_id}")

    claim_ids = {claim.claim_id for claim in manuscript.claims}
    for orphan in sorted(set(links_by_claim) - claim_ids):
        result.blockers.append(f"Evidence link refers to unknown claim: {orphan}")

    novelty_present = False
    interpretation_present = False
    for claim in manuscript.claims:
        links = links_by_claim.get(claim.claim_id, [])
        linked_sources = tuple(sorted({link.source_identifier for link in links}))
        novelty_claim = bool(_NOVELTY_LANGUAGE.search(claim.text))
        novelty_present = novelty_present or novelty_claim
        interpretation_present = interpretation_present or claim.kind == "interpretation"

        if (claim.kind == "evidence" or novelty_claim) and not links:
            result.blockers.append(f"Claim lacks pinpoint evidence links: {claim.claim_id}")
        if set(claim.source_identifiers) != set(linked_sources):
            result.blockers.append(
                f"Claim-to-citation mismatch for {claim.claim_id}: declared and audited sources differ."
            )

        unusable = [
            source_map[item] for item in linked_sources
            if item in source_map and (
                not source_map[item].retrievable
                or not source_map[item].metadata_verified
                or source_map[item].retracted
            )
        ]
        if unusable:
            result.blockers.append(
                f"Claim {claim.claim_id} relies on unavailable, unverified, or retracted evidence."
            )

        assessments = {link.support_assessment for link in links}
        if "contradicts" in assessments:
            status = "contradicted"
            result.blockers.append(f"Cited evidence contradicts claim: {claim.claim_id}")
        elif not links or "unclear" in assessments:
            status = "unverified"
            if links:
                result.blockers.append(f"Evidence support is unclear for claim: {claim.claim_id}")
        elif "partially_supports" in assessments:
            status = "partial"
            result.warnings.append(f"Claim requires narrower wording: {claim.claim_id}")
        else:
            status = "verified"
        result.claim_audits.append(ClaimAudit(
            claim.claim_id, status, linked_sources,
            "Traceability assessment only; scientific interpretation still requires expert review.",
        ))

    if novelty_present and not _valid_approval(approvals, "novelty"):
        result.blockers.append("Novelty claims require current expert approval and a conflict declaration.")
    if manuscript.models and not _valid_approval(approvals, "mathematics"):
        result.blockers.append("Mathematical validity requires current expert approval and a conflict declaration.")
    if interpretation_present and not _valid_approval(approvals, "interpretation"):
        result.blockers.append("Interpretive claims require current domain-expert approval.")
    if not _valid_approval(approvals, "publication"):
        result.blockers.append("Final publication approval is missing or not approved.")
    return result
