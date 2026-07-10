from pathlib import Path

from src.agent.config import Settings
from src.agent.core.orchestrator import Orchestrator


def test_full_pipeline_uses_fixture_evidence() -> None:
    settings = Settings(env="personal")
    orchestrator = Orchestrator(settings=settings)
    denial_text = Path("tests/fixtures/denial_letters/basic_denial.txt").read_text(encoding="utf-8")

    state = orchestrator.run(denial_text)

    assert state.extracted_claim is not None
    assert state.extracted_claim.claim_id == "12345"
    assert state.retrieval_plan is not None
    assert state.retrieval_plan.queries
    assert state.policy_evidence
    assert state.appeal_draft is not None
    assert state.appeal_draft.evidence_references
    assert state.critique_result is not None
    assert state.critique_result.passed
    assert state.critique_result.escalation_required is False
