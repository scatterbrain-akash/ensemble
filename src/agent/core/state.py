from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agent.schemas.io_models import (
    AppealDraft,
    CritiqueResult,
    ExtractedClaim,
    PolicyEvidence,
    RetrievalPlan,
)


@dataclass
class AgentState:
    input_text: str
    extracted_claim: ExtractedClaim | None = None
    retrieval_plan: RetrievalPlan | None = None
    policy_evidence: list[PolicyEvidence] = field(default_factory=list)
    appeal_draft: AppealDraft | None = None
    critique_result: CritiqueResult | None = None
    escalation_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> dict[str, Any]:
        return {
            "input_text": self.input_text,
            "extracted_claim": self.extracted_claim.model_dump() if self.extracted_claim else None,
            "retrieval_plan": self.retrieval_plan.model_dump() if self.retrieval_plan else None,
            "policy_evidence": [item.model_dump() for item in self.policy_evidence],
            "appeal_draft": self.appeal_draft.model_dump() if self.appeal_draft else None,
            "critique_result": self.critique_result.model_dump() if self.critique_result else None,
            "escalation_reason": self.escalation_reason,
            "metadata": self.metadata,
        }

    def model_dump_json(self, **kwargs: str) -> str:
        import json

        return json.dumps(self.model_dump(), **kwargs)
