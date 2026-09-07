from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal

from .manuscript import Manuscript, manuscript_quality_gate

ApprovalScope = Literal["novelty", "mathematics", "interpretation", "publication"]
ApprovalDecision = Literal["approved", "rejected", "changes_required"]
SemanticVerdict = Literal["supports", "partially_supports", "contradicts", "unclear"]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized_identifier(identifier: str) -> str:
    value = identifier.strip().lower()
    changed = True
    while changed:
        changed = False
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if value.startswith(prefix):
                value = value[len(prefix):]
                changed = True
                break
    return value


def manuscript_fingerprint(manuscript: Manuscript) -> str:
    payload = json.dumps(asdict(manuscript), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256(payload)


@dataclass(frozen=True)
class SourceVerification:
    identifier: str
    title: str
    retrievable: bool
    metadata_verified: bool
    source_type: Literal["primary", "review", "systematic_review", "meta_analysis", "other"] = "primary"
    independence_group: str = ""
    authors: tuple[str, ...] = ()
    correction_status: Literal["none", "corrected", "expression_of_concern", "retracted"] = "none"
    notice_checked_at: datetime | None = None
    corrected_version_used: bool = False


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source_identifier: str
    locator: str
    text: str
    content_hash: str

    @classmethod
    def create(cls, evidence_id: str, source_identifier: str, locator: str, text: str):
        return cls(evidence_id, source_identifier, locator, text, _sha256(text))


@dataclass(frozen=True)
class ClaimEvidenceLink:
    claim_id: str
    source_identifier: str
    locator: str
    supporting_excerpt: str
    support_assessment: SemanticVerdict
    evidence_id: str = ""
    evidence_hash: str = ""


@dataclass(frozen=True)
class SemanticAssessment:
    verdict: SemanticVerdict
    rationale: str
    verifier: str


SemanticVerifier = Callable[[str, str], SemanticAssessment]


@dataclass(frozen=True)
class ExpertApproval:
    scope: ApprovalScope
    reviewer: str
    expertise: str
    decision: ApprovalDecision
    reviewed_at: datetime
    manuscript_hash: str = ""
    target_id: str = "manuscript"
    notes: str = ""
    conflict_of_interest_declared: bool = False
    valid_days: int = 180
    reviewer_identity_verified: bool = False
    record_hash: str = ""


def create_expert_approval(
    scope: ApprovalScope, reviewer: str, expertise: str, decision: ApprovalDecision,
    reviewed_at: datetime, manuscript_hash: str, *, notes: str = "",
    conflict_of_interest_declared: bool = True, valid_days: int = 180,
) -> ExpertApproval:
    payload = "|".join((
        scope, reviewer, expertise, decision, reviewed_at.isoformat(), manuscript_hash,
        notes, str(conflict_of_interest_declared), str(valid_days),
    ))
    return ExpertApproval(
        scope, reviewer, expertise, decision, reviewed_at, manuscript_hash,
        notes=notes, conflict_of_interest_declared=conflict_of_interest_declared,
        valid_days=valid_days, reviewer_identity_verified=True, record_hash=_sha256(payload),
    )


@dataclass(frozen=True)
class StatisticalValidation:
    assumptions_checked: tuple[str, ...]
    sample_size_justification: str
    leakage_checks: tuple[str, ...]
    effect_sizes: tuple[str, ...]
    confidence_intervals: tuple[str, ...]
    multiple_testing_correction: str
    analysis_plan_locked_before_test: bool


@dataclass(frozen=True)
class ReproducibilityPackage:
    configuration_hash: str
    seeds: tuple[int, ...]
    environment_lock_hash: str
    dataset_name: str
    dataset_version: str
    dataset_hash_or_accession: str
    experiment_log_hashes: tuple[str, ...]
    code_commit: str


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    timestamp: datetime
    actor: str
    action: str
    manuscript_hash: str
    previous_hash: str
    event_hash: str


def append_audit_event(
    trail: list[AuditEvent], actor: str, action: str, manuscript_hash: str,
    timestamp: datetime | None = None,
) -> AuditEvent:
    moment = timestamp or datetime.now(timezone.utc)
    sequence = len(trail) + 1
    previous = trail[-1].event_hash if trail else "GENESIS"
    payload = f"{sequence}|{moment.isoformat()}|{actor}|{action}|{manuscript_hash}|{previous}"
    event = AuditEvent(sequence, moment, actor, action, manuscript_hash, previous, _sha256(payload))
    trail.append(event)
    return event


def verify_audit_trail(trail: list[AuditEvent]) -> list[str]:
    problems: list[str] = []
    previous = "GENESIS"
    for expected, event in enumerate(trail, 1):
        payload = (
            f"{event.sequence}|{event.timestamp.isoformat()}|{event.actor}|{event.action}|"
            f"{event.manuscript_hash}|{event.previous_hash}"
        )
        if event.sequence != expected or event.previous_hash != previous or event.event_hash != _sha256(payload):
            problems.append(f"Audit trail integrity failure at sequence {expected}.")
        previous = event.event_hash
    return problems


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


def _valid_approval(
    approvals: list[ExpertApproval], scope: ApprovalScope, current_hash: str, now: datetime,
) -> bool:
    candidates = [item for item in approvals if item.scope == scope and item.target_id == "manuscript"]
    aware = [item for item in candidates if item.reviewed_at.tzinfo is not None]
    if not aware:
        return False
    latest = max(aware, key=lambda item: item.reviewed_at)
    payload = "|".join((
        latest.scope, latest.reviewer, latest.expertise, latest.decision,
        latest.reviewed_at.isoformat(), latest.manuscript_hash, latest.notes,
        str(latest.conflict_of_interest_declared), str(latest.valid_days),
    ))
    return (
        latest.decision == "approved"
        and bool(latest.reviewer.strip())
        and bool(latest.expertise.strip())
        and latest.conflict_of_interest_declared
        and latest.reviewer_identity_verified
        and latest.record_hash == _sha256(payload)
        and latest.manuscript_hash == current_hash
        and latest.reviewed_at <= now <= latest.reviewed_at + timedelta(days=latest.valid_days)
    )


def _statistics_problems(record: StatisticalValidation | None) -> list[str]:
    if record is None:
        return ["Statistical validation record is missing."]
    checks = (
        (record.assumptions_checked, "Statistical assumptions were not checked."),
        (record.sample_size_justification.strip(), "Sample-size justification is missing."),
        (record.leakage_checks, "Data-leakage checks are missing."),
        (record.effect_sizes, "Effect sizes are missing."),
        (record.confidence_intervals, "Confidence intervals are missing."),
        (record.multiple_testing_correction.strip(), "Multiple-testing handling is missing."),
        (record.analysis_plan_locked_before_test, "Analysis plan was not locked before test evaluation."),
    )
    return [message for value, message in checks if not value]


def _reproducibility_problems(package: ReproducibilityPackage | None) -> list[str]:
    if package is None:
        return ["Reproducibility package is missing."]
    values = (
        package.configuration_hash, package.seeds, package.environment_lock_hash,
        package.dataset_name, package.dataset_version, package.dataset_hash_or_accession,
        package.experiment_log_hashes, package.code_commit,
    )
    return [] if all(values) else ["Reproducibility package is incomplete."]


def publication_readiness_gate(
    manuscript: Manuscript,
    sources: list[SourceVerification],
    evidence_links: list[ClaimEvidenceLink],
    approvals: list[ExpertApproval],
    *,
    evidence_records: list[EvidenceRecord] | None = None,
    semantic_verifier: SemanticVerifier | None = None,
    statistics: StatisticalValidation | None = None,
    reproducibility: ReproducibilityPackage | None = None,
    audit_trail: list[AuditEvent] | None = None,
    now: datetime | None = None,
) -> PublicationGateResult:
    """Fail-closed publication audit with evidence, statistical, and governance controls."""
    result = PublicationGateResult()
    moment = now or datetime.now(timezone.utc)
    current_hash = manuscript_fingerprint(manuscript)
    records = evidence_records or []
    trail = audit_trail or []
    source_map = {source.identifier: source for source in sources}
    normalized_source_ids = [_normalized_identifier(source.identifier) for source in sources]
    evidence_map = {record.evidence_id: record for record in records}
    result.blockers.extend(manuscript_quality_gate(manuscript, set(source_map)))
    if len(set(normalized_source_ids)) != len(sources):
        result.blockers.append("Duplicate source identifiers prevent unambiguous traceability.")
    if len(evidence_map) != len(records):
        result.blockers.append("Duplicate evidence identifiers prevent unambiguous traceability.")

    for source in sources:
        if not all((source.identifier.strip(), source.title.strip(), source.independence_group.strip())):
            result.blockers.append(f"Source identity or independence group is incomplete: {source.identifier!r}")
        if source.notice_checked_at is None or source.notice_checked_at.tzinfo is None:
            result.blockers.append(f"Publication-notice check is missing: {source.identifier}")
        elif source.notice_checked_at > moment:
            result.blockers.append(f"Publication-notice check has a future timestamp: {source.identifier}")
        elif moment - source.notice_checked_at > timedelta(days=30):
            result.blockers.append(f"Publication-notice check is stale: {source.identifier}")
        if source.correction_status in {"retracted", "expression_of_concern"}:
            result.blockers.append(f"Source has an unresolved publication notice: {source.identifier}")
        if source.correction_status == "corrected" and not source.corrected_version_used:
            result.blockers.append(f"Corrected source version was not used: {source.identifier}")

    links_by_claim: dict[str, list[ClaimEvidenceLink]] = {}
    for link in evidence_links:
        links_by_claim.setdefault(link.claim_id, []).append(link)
        record = evidence_map.get(link.evidence_id)
        if record is None:
            result.blockers.append(f"Evidence record is missing for claim: {link.claim_id}")
            continue
        if (
            record.source_identifier != link.source_identifier
            or record.locator != link.locator
            or record.text != link.supporting_excerpt
            or record.content_hash != link.evidence_hash
            or record.content_hash != _sha256(record.text)
        ):
            result.blockers.append(f"Fabricated or altered evidence binding: {link.claim_id}")

    claim_ids = {claim.claim_id for claim in manuscript.claims}
    for orphan in sorted(set(links_by_claim) - claim_ids):
        result.blockers.append(f"Evidence link refers to unknown claim: {orphan}")

    novelty_present = False
    interpretation_present = False
    for claim in manuscript.claims:
        links = links_by_claim.get(claim.claim_id, [])
        linked_sources = tuple(sorted({link.source_identifier for link in links}))
        direct = claim.kind in {"evidence", "direct_evidence"}
        inference = claim.kind in {"inference", "interpretation"}
        novelty_present |= claim.kind == "author_contribution"
        interpretation_present |= inference

        if direct and not links:
            result.blockers.append(f"Claim lacks pinpoint evidence links: {claim.claim_id}")
        if set(claim.source_identifiers) != set(linked_sources):
            result.blockers.append(f"Claim-to-citation mismatch: {claim.claim_id}")
        if inference and not claim.derived_from_claims:
            result.blockers.append(f"Inference lacks explicit derivation links: {claim.claim_id}")
        if any(parent not in claim_ids for parent in claim.derived_from_claims):
            result.blockers.append(f"Claim derives from an unknown claim: {claim.claim_id}")

        source_records = [source_map[item] for item in linked_sources if item in source_map]
        if any(not item.retrievable or not item.metadata_verified for item in source_records):
            result.blockers.append(f"Claim relies on unavailable or unverified evidence: {claim.claim_id}")
        if direct and any(item.source_type != "primary" for item in source_records):
            result.blockers.append(f"Possible citation laundering; direct claim must cite primary evidence: {claim.claim_id}")
        if claim.confidence == "high":
            primary = [item for item in source_records if item.source_type == "primary"]
            independent_pair = any(
                left.independence_group != right.independence_group
                and bool(left.authors) and bool(right.authors)
                and not ({a.casefold() for a in left.authors} & {a.casefold() for a in right.authors})
                for index, left in enumerate(primary) for right in primary[index + 1:]
            )
            if not independent_pair:
                result.blockers.append(f"High-confidence claim lacks two independent primary studies: {claim.claim_id}")

        verdicts: list[SemanticVerdict] = []
        rationales: list[str] = []
        for link in links:
            if semantic_verifier is None:
                result.blockers.append(f"Independent semantic verification is missing: {claim.claim_id}")
                verdicts.append("unclear")
                continue
            assessment = semantic_verifier(claim.text, link.supporting_excerpt)
            verdicts.append(assessment.verdict)
            rationales.append(f"{assessment.verifier}: {assessment.rationale}")
            if assessment.verdict != link.support_assessment:
                result.blockers.append(f"Declared and verified support assessments differ: {claim.claim_id}")

        if "contradicts" in verdicts:
            status = "contradicted"
            result.blockers.append(f"Cited passage contradicts claim: {claim.claim_id}")
        elif not verdicts or "unclear" in verdicts:
            status = "unverified"
            if links:
                result.blockers.append(f"Semantic support is unclear: {claim.claim_id}")
        elif "partially_supports" in verdicts:
            status = "partial"
            result.blockers.append(f"Partially supported claim must be narrowed and re-audited: {claim.claim_id}")
        else:
            status = "verified"
        result.claim_audits.append(ClaimAudit(
            claim.claim_id, status, linked_sources,
            "; ".join(rationales) or "No passage-level semantic assessment was available.",
        ))

    for scope, required in (
        ("novelty", novelty_present), ("mathematics", bool(manuscript.models)),
        ("interpretation", interpretation_present), ("publication", True),
    ):
        if required and not _valid_approval(approvals, scope, current_hash, moment):
            result.blockers.append(f"Current manuscript lacks valid {scope} approval.")

    result.blockers.extend(_statistics_problems(statistics))
    result.blockers.extend(_reproducibility_problems(reproducibility))
    result.blockers.extend(verify_audit_trail(trail))
    if not trail or trail[-1].manuscript_hash != current_hash:
        result.blockers.append("Audit trail is not locked to the current manuscript version.")
    return result
