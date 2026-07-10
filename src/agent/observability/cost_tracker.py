from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CostTracker:
    llm_calls: int = 0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    est_cost_usd: float = 0.0

    def record_llm_call(self, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
        self.llm_calls += 1
        self.tokens_in += prompt_tokens
        self.tokens_out += completion_tokens
        self.est_cost_usd += cost_usd

    def record_tool_call(self) -> None:
        self.tool_calls += 1

    def exceeded_budget(self, max_usd: float) -> bool:
        return self.est_cost_usd > max_usd

    def summary(self) -> dict[str, object]:
        return {
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "est_cost_usd": self.est_cost_usd,
        }
