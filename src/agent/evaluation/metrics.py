from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScenarioEvaluation:
    passed: bool
    failures: list[str]


def evaluate_scenario(state: Any, expected: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    should_escalate = bool(expected.get("should_escalate", False))
    found_escalation = state.escalation_reason is not None

    if should_escalate and not found_escalation:
        failures.append("Expected escalation but run completed successfully.")
    if not should_escalate and found_escalation:
        failures.append(f"Unexpected escalation: {state.escalation_reason}")

    expected_claim_id = expected.get("expected_claim_id")
    if expected_claim_id and state.extracted_claim:
        if state.extracted_claim.claim_id != expected_claim_id:
            failures.append(
                f"Expected claim_id {expected_claim_id}, got {state.extracted_claim.claim_id}"
            )

    expected_procedure_codes = expected.get("expected_procedure_codes") or []
    if expected_procedure_codes and state.extracted_claim:
        missing_codes = [code for code in expected_procedure_codes if code not in state.extracted_claim.procedure_codes]
        if missing_codes:
            failures.append(f"Missing expected procedure codes: {missing_codes}")

    expected_source_ids = expected.get("expected_policy_source_ids") or []
    if expected_source_ids:
        evidence_ids = [item.source_id for item in state.policy_evidence]
        missing_sources = [source for source in expected_source_ids if source not in evidence_ids]
        if missing_sources:
            failures.append(f"Missing expected policy evidence source IDs: {missing_sources}")

    if not expected.get("should_escalate", False) and state.appeal_draft:
        if not state.appeal_draft.evidence_references:
            failures.append("Appeal draft has no evidence references.")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "summary": {
            "expected_claim_id": expected_claim_id,
            "found_claim_id": state.extracted_claim.claim_id if state.extracted_claim else None,
            "evidence_count": len(state.policy_evidence),
            "evidence_references": state.appeal_draft.evidence_references if state.appeal_draft else [],
        },
    }
