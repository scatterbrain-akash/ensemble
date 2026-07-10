from __future__ import annotations

from typing import Any, Type

from src.agent.config import Settings
from src.agent.llm.aistudio_provider import AIStudioProvider
from src.agent.llm.base_provider import LLMProvider
from src.agent.llm.groq_provider import GroqProvider
from src.agent.llm.mock_provider import MockProvider


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.providers: dict[str, Type[LLMProvider]] = {
            "groq": GroqProvider,
            "aistudio": AIStudioProvider,
            "mock": MockProvider,
        }

    def get_provider(self, role: str) -> LLMProvider:
        role_config = self.settings.model_role_config(role)
        candidates = [role_config.get("primary", "mock:mock")]
        candidates.extend(role_config.get("fallbacks", []))

        for candidate in candidates:
            provider_name, model_name = self._parse_primary(candidate)
            provider_class = self.providers.get(provider_name, MockProvider)
            api_key = self._get_api_key(provider_name)

            if provider_name == "mock":
                return provider_class(model_name=model_name or "mock", api_key=api_key)

            if api_key:
                return provider_class(model_name=model_name, api_key=api_key)

        return MockProvider(model_name="mock", api_key=None)

    def _parse_primary(self, primary: str) -> tuple[str, str]:
        if ":" in primary:
            provider_name, model_name = primary.split(":", 1)
            return provider_name.strip(), model_name.strip()
        return primary.strip(), ""

    def _get_api_key(self, provider_name: str) -> str | None:
        return getattr(self.settings, f"{provider_name}_api_key", None)
