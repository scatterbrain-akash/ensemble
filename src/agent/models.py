from __future__ import annotations

"""Legacy module kept for compatibility.

Use :class:`src.agent.core.router.ModelRouter` for active model routing logic.
"""

from typing import Any

from src.agent.config import Settings


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def route(self, role: str) -> dict[str, Any]:
        return self.settings.model_role_config(role)
