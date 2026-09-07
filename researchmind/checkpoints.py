from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class CheckpointStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, query: str) -> Path:
        digest = hashlib.sha256(query.strip().encode("utf-8")).hexdigest()[:16]
        return self.root / f"{digest}.json"

    def save(self, query: str, payload: dict[str, Any]) -> Path:
        path = self._path(query)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)
        return path

    def load(self, query: str) -> dict[str, Any] | None:
        path = self._path(query)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if data.get("query") == query else None
