from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is unavailable or invalid."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str = "openai/gpt-4.1-mini"
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: float = 60.0
    data_dir: Path = Path(".researchmind")

    @classmethod
    def from_env(cls, *, require_api_key: bool = True) -> "Settings":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip().strip("\"'")
        if require_api_key and not api_key:
            raise ConfigurationError(
                "OPENROUTER_API_KEY is missing. Copy .env.example to .env and add your key."
            )

        try:
            timeout = float(os.getenv("RESEARCHMIND_TIMEOUT_SECONDS", "60"))
        except ValueError as exc:
            raise ConfigurationError("RESEARCHMIND_TIMEOUT_SECONDS must be numeric.") from exc
        if timeout <= 0:
            raise ConfigurationError("RESEARCHMIND_TIMEOUT_SECONDS must be greater than zero.")

        return cls(
            api_key=api_key,
            model=os.getenv("RESEARCHMIND_MODEL", "openai/gpt-4.1-mini").strip(),
            base_url=os.getenv(
                "RESEARCHMIND_BASE_URL", "https://openrouter.ai/api/v1"
            ).rstrip("/"),
            timeout_seconds=timeout,
            data_dir=Path(os.getenv("RESEARCHMIND_DATA_DIR", ".researchmind")),
        )

    def safe_summary(self) -> dict[str, object]:
        """Return diagnostics without revealing any part of the API key."""
        return {
            "provider": "OpenRouter",
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "api_key_configured": bool(self.api_key),
            "data_dir": str(self.data_dir),
        }
