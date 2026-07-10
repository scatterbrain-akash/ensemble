from __future__ import annotations

from src.agent.agents.base import BaseAgent
from src.agent.core.state import AgentState
from src.agent.schemas.io_models import RetrievalPlan


class PlannerAgent(BaseAgent):
    role = "planner"

    def run(self, state: AgentState) -> AgentState:
        if state.extracted_claim is None:
            return state

        payload = state.extracted_claim.model_dump()
        response_text = self.call_llm(payload)
        parsed = self.parse_json(response_text)
        if not parsed:
            parsed = {"queries": [], "escalate_before_draft": True}
        retrieval_plan = RetrievalPlan(
            queries=parsed.get("queries", []),
            escalate_before_draft=parsed.get("escalate_before_draft", True),
        )
        state.retrieval_plan = retrieval_plan
        return state
