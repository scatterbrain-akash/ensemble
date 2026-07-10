from __future__ import annotations

import ast
import json
import re
from typing import Any

from src.agent.llm.base_provider import LLMProvider


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, model_name: str = "mock", api_key: str | None = None) -> None:
        super().__init__(model_name=model_name, api_key=api_key)

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        lower_prompt = system_prompt.lower()
        if "extraction agent" in lower_prompt:
            return self._mock_extraction(user_prompt)
        if "planning agent" in lower_prompt:
            return self._mock_planner(user_prompt)
        if "synthesis agent" in lower_prompt:
            return self._mock_synthesis(user_prompt)
        if "critique agent" in lower_prompt:
            return self._mock_critique(user_prompt)
        return json.dumps({"message": "mock response"})

    def healthcheck(self) -> bool:
        return True

    def _load_json_or_python(self, prompt: str) -> Any:
        if prompt is None:
            return None
        try:
            return json.loads(prompt)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(prompt)
            except (ValueError, SyntaxError):
                return None

    def _mock_extraction(self, prompt: str) -> str:
        claim_id = self._find_field(prompt, r"claim\s*id[:\s]+([A-Za-z0-9-]+)")
        payer = self._find_field(prompt, r"payer[:\s]+([A-Za-z0-9 \-&]+)")
        procedure_codes = self._find_procedure_codes(prompt)
        if claim_id and claim_id in procedure_codes:
            procedure_codes = [code for code in procedure_codes if code != claim_id]
        diagnosis_codes = self._find_all_codes(prompt, r"\b[A-Z]\d{2}(?:\.\d+)?\b")
        denial_reason = self._find_field(prompt, r"denial reason[:\s]+([^\n]+)")
        service_dates = self._find_all_dates(prompt)
        response = {
            "claim_id": claim_id,
            "payer": payer,
            "procedure_codes": procedure_codes,
            "diagnosis_codes": diagnosis_codes,
            "denial_reason": denial_reason,
            "service_dates": service_dates,
            "missing_fields": [
                name for name, value in [
                    ("claim_id", claim_id),
                    ("payer", payer),
                    ("procedure_codes", procedure_codes),
                ]
                if not value
            ],
            "confidence": 0.95 if claim_id and payer and procedure_codes else 0.5,
        }
        return json.dumps(response)

    def _find_procedure_codes(self, text: str) -> list[str]:
        explicit_field = self._find_field(text, r"procedure[:\s]+(.+)") or ""
        explicit = self._find_all_codes(explicit_field, r"\b\d{5}\b")
        if explicit:
            return explicit
        return self._find_all_codes(text, r"\b\d{5}\b")

    def _mock_planner(self, prompt: str) -> str:
        claim_data = self._load_json_or_python(prompt)
        if not isinstance(claim_data, dict):
            return json.dumps({"queries": [], "escalate_before_draft": True})

        queries = []
        procedure_codes = claim_data.get("procedure_codes", []) or []
        diagnosis_codes = claim_data.get("diagnosis_codes", []) or []
        for code in procedure_codes:
            queries.append(
                {
                    "code": code,
                    "code_type": "procedure",
                    "policy_type": "ncd",
                    "rationale": "Use the procedure code to find a relevant CMS coverage policy.",
                }
            )
        for code in diagnosis_codes:
            queries.append(
                {
                    "code": code,
                    "code_type": "diagnosis",
                    "policy_type": "lcd",
                    "rationale": "Use the diagnosis code to check for a local coverage determination.",
                }
            )
        escalate = not bool(queries)
        return json.dumps({"queries": queries, "escalate_before_draft": escalate})

    def _mock_synthesis(self, prompt: str) -> str:
        try:
            request = json.loads(prompt)
        except json.JSONDecodeError:
            request = {}
        claim = request.get("claim", {})
        evidence = request.get("evidence", [])
        if not evidence:
            summary = "Unable to create an evidence-backed appeal package because no policy evidence was available."
            return json.dumps(
                {
                    "summary": summary,
                    "appeal_arguments": [],
                    "evidence_references": [],
                    "limitations": ["No evidence was retrieved from CMS or fallback fixtures."],
                }
            )
        arguments = [
            f"The procedure code {item.get('retrieval_query', {}).get('code')} is supported by policy {item.get('source_id')}"
            for item in evidence
        ]
        summary = f"The denial appears related to {claim.get('denial_reason', 'missing medical necessity reason')}. Evidence-backed arguments are provided."
        references = [item.get("source_id", "") for item in evidence if item.get("source_id")]
        return json.dumps(
            {
                "summary": summary,
                "appeal_arguments": arguments,
                "evidence_references": references,
                "limitations": ["This draft is based on extracted claim data and retrieved policy evidence only."],
            }
        )

    def _mock_critique(self, prompt: str) -> str:
        try:
            request = json.loads(prompt)
        except json.JSONDecodeError:
            request = {}
        draft = request.get("draft", {})
        evidence = request.get("evidence", [])
        passed = bool(draft.get("appeal_arguments") and evidence)
        response = {
            "passed": passed,
            "unsupported_claims": [] if passed else ["Appeal draft does not include sufficient arguments."],
            "missing_evidence": [] if passed else ["No evidence references were found."],
            "revision_instructions": [] if passed else ["Add explicit citations and evidence-backed reasoning."],
            "escalation_required": not passed,
        }
        return json.dumps(response)

    def _find_field(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip()

    def _find_all_codes(self, text: str, pattern: str) -> list[str]:
        codes = re.findall(pattern, text)
        return list(dict.fromkeys(code.strip() for code in codes if code.strip()))

    def _find_all_dates(self, text: str) -> list[str]:
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
        return list(dict.fromkeys(dates))
