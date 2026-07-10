from pathlib import Path

from src.agent.config import Settings
from src.agent.evaluation.evaluator import Evaluator


def test_evaluator_runs_scenarios() -> None:
    settings = Settings(env="personal")
    evaluator = Evaluator(settings=settings)
    results = evaluator.run_scenarios(Path("tests/fixtures/scenarios.json"))

    assert len(results) == 1
    assert results[0]["name"] == "basic denial with fixture evidence"
    assert results[0]["evaluation"]["passed"] is True
