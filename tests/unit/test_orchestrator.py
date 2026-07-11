from pathlib import Path

from src.agent.config import Settings
from src.agent.core.orchestrator import Orchestrator


_MINIMAL_DENIAL = (
    "Claim denial notice. Payer: Medicare. "
    "The submitted claim has been denied due to lack of medical necessity. "
    "Procedure code 99213 was not covered under the current policy."
)


def test_orchestrator_runs_with_empty_input(tmp_path: Path) -> None:
    settings = Settings(env="personal")
    orchestrator = Orchestrator(settings=settings)
    state = orchestrator.run(_MINIMAL_DENIAL)

    assert state.input_text == _MINIMAL_DENIAL
    assert state.extracted_claim is not None
    assert state.retrieval_plan is not None
    assert state.critique_result is None
