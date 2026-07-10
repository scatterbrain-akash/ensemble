from __future__ import annotations

from src.agent.agents.base import BaseAgent
from src.agent.core.state import AgentState
from src.agent.schemas.io_models import CritiqueResult


class CritiqueAgent(BaseAgent):
    role = "critique"

    def run(self, state: AgentState) -> AgentState:
        if state.appeal_draft is None:
            return state
        payload = {
            "draft": state.appeal_draft.model_dump(),
            "claim": state.extracted_claim.model_dump() if state.extracted_claim else {},
            "evidence": [item.model_dump() for item in state.policy_evidence],
        }
        response_text = self.call_llm(payload)
        parsed = self.parse_json(response_text)
        if not parsed:
            parsed = {
                "passed": False,
                "unsupported_claims": ["Unable to parse critique response."],
                "missing_evidence": ["No critique output."],
                "revision_instructions": ["Generate a valid critique response."],
                "escalation_required": True,
            }
        critique_result = CritiqueResult(
            passed=parsed.get("passed", False),
            unsupported_claims=parsed.get("unsupported_claims", []),
            missing_evidence=parsed.get("missing_evidence", []),
            revision_instructions=parsed.get("revision_instructions", []),
            escalation_required=parsed.get("escalation_required", True),
        )
        state.critique_result = critique_result
        return state
