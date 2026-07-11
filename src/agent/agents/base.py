from __future__ import annotations

import ast
import json
from abc import ABC, abstractmethod
from typing import Any

from src.agent.config import Settings
from src.agent.core.state import AgentState
from src.agent.core.router import ModelRouter
from src.agent.prompts import load_system_prompt
from src.agent.cache.cache_service import CacheService
from src.agent.observability.cost_tracker import CostTracker
import hashlib
import json


class BaseAgent(ABC):
    role: str = ""

    def __init__(
        self,
        settings: Settings,
        model_router: ModelRouter,
        cache_service: CacheService | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.settings = settings
        self.model_router = model_router
        self.cache_service = cache_service
        self.cost_tracker = cost_tracker

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        raise NotImplementedError

    def call_llm(self, user_prompt: Any, **kwargs: Any) -> str:
        provider = self.model_router.get_provider(self.role)
        system_prompt = load_system_prompt(self.role)
        if isinstance(user_prompt, (dict, list)):
            user_prompt = json.dumps(user_prompt)

        # Exact-match prompt cache
        cache_key = None
        if self.cache_service is not None:
            key_obj = {
                "provider": getattr(provider, "name", ""),
                "model": getattr(provider, "model_name", ""),
                "system": system_prompt,
                "user": user_prompt,
                "kwargs": kwargs,
            }
            key_raw = json.dumps(key_obj, sort_keys=True, ensure_ascii=False)
            cache_key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()
            cached = self.cache_service.get(f"llm:{cache_key}")
            if cached is not None:
                if self.cost_tracker:
                    self.cost_tracker.record_cache_hit()
                return cached

        # Call provider — try primary, then fallbacks on HTTP errors
        provider_result = None
        last_exc: Exception | None = None
        providers_to_try = [provider] + self.model_router.get_fallback_providers(self.role)
        for attempt_provider in providers_to_try:
            try:
                provider_result = attempt_provider.generate(system_prompt=system_prompt, user_prompt=user_prompt, **kwargs)
                provider = attempt_provider  # keep reference for cost calculation
                break
            except Exception as exc:
                last_exc = exc
                continue
        if provider_result is None:
            raise RuntimeError(f"All providers failed for role '{self.role}'") from last_exc

        # provider_result may be either a string or a dict {content, usage}
        response_text = None
        prompt_tokens = None
        completion_tokens = None
        if isinstance(provider_result, dict):
            response_text = provider_result.get("content", "")
            usage = provider_result.get("usage", {}) or {}
            # usage may follow OpenAI style: prompt_tokens, completion_tokens
            prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
            completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
        else:
            response_text = str(provider_result)

        # Fallback heuristic if provider didn't return usage
        if prompt_tokens is None or completion_tokens is None:
            try:
                prompt_tokens = max(1, (len(system_prompt) + len(user_prompt)) // 4)
                completion_tokens = max(1, len(response_text) // 4)
            except Exception:
                prompt_tokens = 1
                completion_tokens = 1

        # Record cost via cost_tracker
        try:
            provider_rate_key = f"{getattr(provider, 'name', '')}_per_token_usd"
            per_token = float(self.settings.cost.get(provider_rate_key, self.settings.cost.get("per_token_usd", 0.0)))
            est_cost = (int(prompt_tokens) + int(completion_tokens)) * per_token
            if self.cost_tracker:
                self.cost_tracker.record_llm_call(int(prompt_tokens), int(completion_tokens), est_cost)
        except Exception:
            pass

        # Store in cache if available
        if self.cache_service is not None and cache_key is not None:
            ttl = int(self.settings.cache.get("llm_ttl_seconds", 600))
            try:
                self.cache_service.set(f"llm:{cache_key}", response_text, ttl)
            except Exception:
                pass

        return response_text

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
