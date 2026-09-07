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
    contact_email: str | None = None

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

        model = os.getenv("RESEARCHMIND_MODEL", "openai/gpt-4.1-mini").strip()
        if not model:
            raise ConfigurationError("RESEARCHMIND_MODEL cannot be empty.")

        base_url = os.getenv(
            "RESEARCHMIND_BASE_URL", "https://openrouter.ai/api/v1"
        ).rstrip("/")
        if not base_url.startswith(("https://", "http://")):
            raise ConfigurationError("RESEARCHMIND_BASE_URL must be an HTTP(S) URL.")

        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout,
            data_dir=Path(os.getenv("RESEARCHMIND_DATA_DIR", ".researchmind")),
            contact_email=os.getenv("RESEARCHMIND_CONTACT_EMAIL", "").strip() or None,
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
            "contact_email_configured": bool(self.contact_email),
        }
