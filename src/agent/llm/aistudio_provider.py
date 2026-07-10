from __future__ import annotations

import httpx
from src.agent.llm.base_provider import LLMProvider


class AIStudioProvider(LLMProvider):
    name = "aistudio"

    def __init__(self, model_name: str, api_key: str | None = None) -> None:
        super().__init__(model_name, api_key)
        self.base_url = "https://api.ai-studio.com/openai/v1"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> Any:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs,
        }
        response = httpx.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage") or {}
        return {"content": content, "usage": usage}

    def healthcheck(self) -> bool:
        return self.api_key is not None
