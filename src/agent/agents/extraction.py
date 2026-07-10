from __future__ import annotations

from src.agent.agents.base import BaseAgent
from src.agent.core.state import AgentState
from src.agent.schemas.io_models import ExtractedClaim


class ExtractionAgent(BaseAgent):
    role = "extraction"

    def run(self, state: AgentState) -> AgentState:
        response_text = self.call_llm(state.input_text)
        parsed = self.parse_json(response_text)
        if not parsed:
            parsed = {}
        extracted_claim = ExtractedClaim(
            claim_id=parsed.get("claim_id"),
            payer=parsed.get("payer"),
            procedure_codes=parsed.get("procedure_codes", []),
            diagnosis_codes=parsed.get("diagnosis_codes", []),
            denial_reason=parsed.get("denial_reason"),
            service_dates=parsed.get("service_dates", []),
            missing_fields=parsed.get("missing_fields", []),
            confidence=parsed.get("confidence", 0.0),
        )
        state.extracted_claim = extracted_claim
        return state
