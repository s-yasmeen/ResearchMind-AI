from pathlib import Path

import pytest

from researchmind.checkpoints import CheckpointStore
from researchmind.config import ConfigurationError, Settings
from researchmind.engine import ResearchEngine
from researchmind.router import route_query


def test_router_is_deterministic():
    assert route_query("Recommend a dataset and evaluation metrics") == "methodology"
    assert route_query("Rewrite my abstract") == "writing"
    assert route_query("What work exists on biometric privacy?") == "literature"


def test_settings_reject_missing_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        Settings.from_env()


def test_safe_summary_never_contains_key(tmp_path):
    settings = Settings(api_key="secret-value", data_dir=tmp_path)
    assert "secret-value" not in str(settings.safe_summary())


def test_checkpoint_round_trip(tmp_path: Path):
    store = CheckpointStore(tmp_path)
    payload = {"query": "test topic", "status": "complete"}
    store.save("test topic", payload)
    assert store.load("test topic") == payload


def test_engine_rejects_blank_query(tmp_path):
    engine = ResearchEngine(Settings(api_key="test", data_dir=tmp_path))
    with pytest.raises(ValueError):
        engine.run("   ")


def test_engine_creates_resumable_record(tmp_path):
    engine = ResearchEngine(Settings(api_key="test", data_dir=tmp_path))
    result = engine.run("Review biometric privacy literature")
    assert result.agent == "literature"
    assert engine.checkpoints.load(result.query) is not None
