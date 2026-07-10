from pathlib import Path

from src.agent.config import Settings
from src.agent.core.orchestrator import Orchestrator


def test_orchestrator_runs_with_empty_input(tmp_path: Path) -> None:
    settings = Settings(env="personal")
    orchestrator = Orchestrator(settings=settings)
    state = orchestrator.run("Test denial letter")

    assert state.input_text == "Test denial letter"
    assert state.extracted_claim is not None
    assert state.retrieval_plan is not None
    assert state.retrieval_plan.escalate_before_draft is True
    assert state.critique_result is None
    assert state.escalation_reason == "Planning determined escalation"
