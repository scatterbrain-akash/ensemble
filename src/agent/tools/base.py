from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError
