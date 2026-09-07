# ResearchMind AI

ResearchMind is an evidence-grounded research assistant designed to help researchers
search literature, examine methodologies, identify gaps, and prepare traceable academic
reports. This branch contains the rebuilt, testable foundation.

## Stage 1 status

- Safe environment-based configuration
- Deterministic multi-agent routing
- Typed research and evidence records
- Resumable checkpoint storage
- CLI installation diagnostics
- Automated foundation tests
- GitHub Actions checks on Python 3.10 and 3.12

Live paper retrieval, citation verification, and the Streamlit workspace are intentionally
scheduled for later stages so each layer can be verified independently.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Add the OpenRouter key to `.env`, then run:

```bash
researchmind --diagnose
researchmind "Review recent work on biometric privacy"
pytest
```

The diagnostic command does not call an external model and does not require an API key.
It reports `setup_required` until a key is configured, rather than claiming live research
is ready prematurely.

## Research-integrity design

ResearchMind follows a protocol-first workflow inspired by systematic-review practice:

1. Frame the question before searching.
2. Record databases, search strings, dates, and eligibility criteria.
3. Preserve provenance and extraction fields for every study.
4. Appraise observable quality indicators without pretending software replaces peer review.
5. Generate a gap only when a measurable corpus property supports it.
6. Attach a proposed experiment to every reported gap.
7. Reject unresolved citation markers and unsupported high-confidence findings.

The software does not treat an LLM suggestion as evidence. Human expert review remains
required for eligibility decisions, risk-of-bias assessment, and final scientific claims.

## Scholarly metadata retrieval

The retrieval layer currently supports Crossref and arXiv descriptive metadata. It:

- records provider, query, parameters, retrieval time, and result count;
- normalizes DOI and arXiv identifiers;
- deduplicates DOI matches, arXiv versions, and exact normalized title/year matches;
- strips markup from abstracts;
- labels arXiv records as preprints;
- never assumes a Crossref journal record has passed peer review;
- caches identical searches within a running session; and
- enforces arXiv's minimum three-second interval between uncached requests.

ResearchMind acknowledges arXiv metadata use and does not redistribute paper content.

## Document intelligence

User-authorized PDFs are validated by content signature, size, and SHA-256 hash before
extraction. The document layer preserves page numbers, flags pages that may require OCR,
rejects encrypted files, and builds section-aware evidence chunks with stable identifiers.

The local evidence index implements BM25 keyword retrieval and accepts a pluggable semantic
scorer for hybrid ranking. Every ranked passage retains its source identifier, document hash,
page range, section, and content hash. PDF extraction can still be imperfect for scanned or
complex layouts, so flagged pages require human review before publication.

## Security

Never commit `.env`, API keys, downloaded papers, generated reports containing sensitive
material, or local vector databases. ResearchMind diagnostics report only whether a key is
configured; they never print any part of it.

## Roadmap

1. Foundation and recovery
2. Evidence ingestion and hybrid retrieval
3. Citation-grounded research agents
4. Streamlit interface and report export
5. Evaluation, CI, and release packaging
