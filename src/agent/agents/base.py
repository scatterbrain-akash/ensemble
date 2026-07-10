from __future__ import annotations

import ast
import json
from abc import ABC, abstractmethod
from typing import Any

from src.agent.config import Settings
from src.agent.core.state import AgentState
from src.agent.core.router import ModelRouter
from src.agent.prompts import load_system_prompt


class BaseAgent(ABC):
    role: str = ""

    def __init__(self, settings: Settings, model_router: ModelRouter) -> None:
        self.settings = settings
        self.model_router = model_router

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        raise NotImplementedError

    def call_llm(self, user_prompt: Any, **kwargs: Any) -> str:
        provider = self.model_router.get_provider(self.role)
        system_prompt = load_system_prompt(self.role)
        if isinstance(user_prompt, (dict, list)):
            user_prompt = json.dumps(user_prompt)
        return provider.generate(system_prompt=system_prompt, user_prompt=user_prompt, **kwargs)

    def parse_json(self, text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(text)
            except (ValueError, SyntaxError):
                pass
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                snippet = text[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    try:
                        return ast.literal_eval(snippet)
                    except (ValueError, SyntaxError):
                        return None
            return None
