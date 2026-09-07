from __future__ import annotations

from collections import Counter

from .models import Appraisal, ResearchGap, StudyRecord


def identify_gaps(studies: list[StudyRecord], appraisals: list[Appraisal]) -> list[ResearchGap]:
    """Infer only gaps supported by observable corpus properties."""
    if len(studies) != len(appraisals):
        raise ValueError("Every study must have exactly one appraisal.")
    if not studies:
        return [ResearchGap(
            gap_type="evidence",
            statement="No eligible studies were supplied; no substantive research gap can be claimed.",
            basis=("eligible_study_count=0",),
            confidence="insufficient",
            proposed_test="Execute and document the search and screening protocol first.",
        )]

    gaps: list[ResearchGap] = []
    total = len(studies)
    externally_validated = sum(s.external_validation is True for s in studies)
    reproducible = sum(s.reproducible_assets is True for s in studies)
    comparators = sum(s.has_comparator is True for s in studies)
    datasets = Counter(s.dataset for s in studies if s.dataset)
    low_quality = sum(a.evidence_level in {"low", "insufficient"} for a in appraisals)

    if externally_validated / total < 0.4:
        gaps.append(ResearchGap("methodological", "External validation is uncommon in the screened corpus.", (f"external_validation={externally_validated}/{total}",), "moderate", "Evaluate leading methods on an independent dataset, site, or population."))
    if reproducible / total < 0.4:
        gaps.append(ResearchGap("replication", "Publicly reproducible assets are uncommon in the screened corpus.", (f"reproducible_assets={reproducible}/{total}",), "moderate", "Release code, fixed splits, configuration, seeds, and an executable evaluation protocol."))
    if comparators / total < 0.5:
        gaps.append(ResearchGap("methodological", "Fewer than half of the studies confirm a comparator or baseline.", (f"confirmed_comparators={comparators}/{total}",), "moderate", "Run controlled comparisons against current and simple baselines with uncertainty estimates."))
    if datasets and datasets.most_common(1)[0][1] / total >= 0.6:
        dataset, count = datasets.most_common(1)[0]
        gaps.append(ResearchGap("population", f"Evidence is concentrated on the dataset '{dataset}'.", (f"dataset_concentration={count}/{total}",), "moderate", "Test generalization across demographically, geographically, or operationally distinct datasets."))
    if low_quality / total >= 0.5:
        gaps.append(ResearchGap("evidence", "At least half of the corpus has low or insufficient appraisal scores.", (f"low_or_insufficient={low_quality}/{total}",), "moderate", "Strengthen the evidence base before drawing firm conclusions."))
    return gaps
