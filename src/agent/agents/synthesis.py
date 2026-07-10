from __future__ import annotations

from src.agent.agents.base import BaseAgent
from src.agent.core.state import AgentState
from src.agent.schemas.io_models import AppealDraft


class SynthesisAgent(BaseAgent):
    role = "synthesis"

    def run(self, state: AgentState) -> AgentState:
        if state.extracted_claim is None:
            return state
        payload = {
            "claim": state.extracted_claim.model_dump(),
            "evidence": [item.model_dump() for item in state.policy_evidence],
        }
        response_text = self.call_llm(payload)
        parsed = self.parse_json(response_text)
        if not parsed:
            parsed = {
                "summary": "Unable to create appeal draft.",
                "appeal_arguments": [],
                "evidence_references": [],
                "limitations": ["Synthesis failed to generate valid JSON."],
            }
        appeal_draft = AppealDraft(
            summary=parsed.get("summary", ""),
            appeal_arguments=parsed.get("appeal_arguments", []),
            evidence_references=parsed.get("evidence_references", []),
            limitations=parsed.get("limitations", []),
        )
        state.appeal_draft = appeal_draft
        return state
