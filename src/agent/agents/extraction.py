from __future__ import annotations

from src.agent.agents.base import BaseAgent
from src.agent.core.state import AgentState
from src.agent.schemas.io_models import ExtractedClaim


class ExtractionAgent(BaseAgent):
    role = "extraction"

    def run(self, state: AgentState) -> AgentState:
        response_text = self.call_llm(state.input_text)
        parsed = self.parse_json(response_text)
        if parsed is None:
            parsed = self._parse_text_response(response_text)
        if not parsed:
            parsed = {}
        extracted_claim = ExtractedClaim(
            claim_id=str(parsed.get("claim_id")) if parsed.get("claim_id") is not None else None,
            payer=str(parsed.get("payer")) if parsed.get("payer") is not None else None,
            procedure_codes=[str(code) for code in parsed.get("procedure_codes", [])],
            diagnosis_codes=[str(code) for code in parsed.get("diagnosis_codes", [])],
            denial_reason=str(parsed.get("denial_reason")) if parsed.get("denial_reason") is not None else None,
            service_dates=[str(date) for date in parsed.get("service_dates", [])],
            missing_fields=[str(field) for field in parsed.get("missing_fields", [])],
            confidence=float(parsed.get("confidence") or 0.0),
        )
        state.extracted_claim = extracted_claim
        return state

    def _parse_text_response(self, text: str) -> dict[str, object]:
        import re

        def _find_field(pattern: str) -> str | None:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                return None
            return match.group(1).strip().strip("'\"")

        def _find_all(pattern: str) -> list[str]:
            matches = re.findall(pattern, text)
            return list(dict.fromkeys(match.strip().strip("'\"") for match in matches if match.strip()))

        claim_id = _find_field(r"claim\s*id[:\s]+([A-Za-z0-9-]+)")
        payer = _find_field(r"payer[:\s]+([A-Za-z0-9 \-&]+)")
        procedure_codes = _find_all(r"\b\d{5}\b")
        if claim_id and claim_id in procedure_codes:
            procedure_codes = [code for code in procedure_codes if code != claim_id]
        diagnosis_codes = _find_all(r"\b[A-Z]\d{2}(?:\.\d+)?\b")
        denial_reason = _find_field(r"denial reason[:\s]+([^\n]+)")
        service_dates = _find_all(r"\b\d{4}-\d{2}-\d{2}\b")
        missing_fields = [
            name
            for name, value in [
                ("claim_id", claim_id),
                ("payer", payer),
                ("procedure_codes", procedure_codes),
            ]
            if not value
        ]
        confidence = 0.95 if claim_id and payer and procedure_codes else 0.5
        return {
            "claim_id": claim_id,
            "payer": payer,
            "procedure_codes": procedure_codes,
            "diagnosis_codes": diagnosis_codes,
            "denial_reason": denial_reason,
            "service_dates": service_dates,
            "missing_fields": missing_fields,
            "confidence": confidence,
        }
