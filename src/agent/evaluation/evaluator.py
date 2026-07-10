from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.agent.config import Settings
from src.agent.core.orchestrator import Orchestrator
from src.agent.evaluation.metrics import evaluate_scenario


class Evaluator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.orchestrator = Orchestrator(settings=settings)

    def run_scenario(self, input_text: str) -> dict[str, Any]:
        state = self.orchestrator.run(input_text)
        return {
            "input_length": len(input_text),
            "extracted_claim": state.extracted_claim.model_dump_json() if state.extracted_claim else None,
            "appeal_draft": state.appeal_draft.model_dump_json() if state.appeal_draft else None,
            "critique_result": state.critique_result.model_dump_json() if state.critique_result else None,
            "escalation_reason": state.escalation_reason,
        }

    def run_scenarios(self, scenario_path: Path) -> list[dict[str, Any]]:
        scenarios = json.loads(scenario_path.read_text(encoding="utf-8"))
        results: list[dict[str, Any]] = []
        for scenario in scenarios:
            input_path = Path(scenario["input_path"])
            input_text = input_path.read_text(encoding="utf-8")
            state = self.orchestrator.run(input_text)
            evaluation = evaluate_scenario(state, scenario)
            results.append({
                "name": scenario.get("name", "unnamed"),
                "input_path": str(input_path),
                "state": {
                    "extracted_claim": state.extracted_claim.model_dump() if state.extracted_claim else None,
                    "appeal_draft": state.appeal_draft.model_dump() if state.appeal_draft else None,
                    "critique_result": state.critique_result.model_dump() if state.critique_result else None,
                    "escalation_reason": state.escalation_reason,
                },
                "evaluation": evaluation,
            })
        return results
