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
