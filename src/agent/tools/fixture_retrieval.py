from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.agent.tools.base import BaseTool


class FixtureRetrievalTool(BaseTool):
    name = "fixture_retrieval"
    description = "Retrieve fallback policy evidence from local fixtures."

    def __init__(self) -> None:
        self.fixture_path = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "policies" / "policy_fixtures.json"
        self._fixtures: dict[str, Any] | None = None

    def run(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        if self._fixtures is None:
            self._load_fixtures()
        code = query.get("code")
        if code is None:
            return []
        return self._fixtures.get(str(code), [])

    def _load_fixtures(self) -> None:
        if not self.fixture_path.exists():
            self._fixtures = {}
            return
        with self.fixture_path.open("r", encoding="utf-8") as handle:
            self._fixtures = json.load(handle)
