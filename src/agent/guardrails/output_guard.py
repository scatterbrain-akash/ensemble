from __future__ import annotations

from src.agent.schemas.io_models import AppealDraft


def validate_appeal_draft(draft: AppealDraft, evidence_ids: list[str] | None = None) -> None:
    if not draft.summary:
        raise ValueError("Appeal draft summary is required.")
    if not draft.appeal_arguments:
        raise ValueError("At least one appeal argument is required.")
    if not draft.evidence_references:
        raise ValueError("At least one evidence reference is required.")
    if evidence_ids is not None:
        missing = [ref for ref in draft.evidence_references if ref not in evidence_ids]
        if missing:
            raise ValueError(f"Evidence references must match retrieved policy evidence: {missing}")
