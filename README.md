# Claims Denial & Appeal Intelligence Agent

A lightweight agentic pipeline for transforming a denial letter/EOB into an evidence-grounded appeal preparation package.

## What it does

- Extracts structured claim data from unstructured denial letters
- Retrieves matched CMS coverage policy evidence
- Synthesizes a draft appeal package with explicit citations
- Applies bounded self-critique and guardrails
- Escalates safely when evidence or confidence is insufficient

## Repo structure

- `src/agent/`: application code
- `config/`: runtime settings and model routing
- `tests/`: unit and integration tests
- `tests/fixtures/`: synthetic denial letters and policy fixtures
- `traces/`: sample run and trace artifacts
- `docs/`: architecture and report artifacts

## Setup

1. Create a Python environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Create `.env` from `.env.example` and set your API keys.

## Run

```bash
python -m src.agent.cli --input "path/to/denial.txt"
```

## Evaluation

A simple scenario evaluator is available using `tests/fixtures/scenarios.json`.

```bash
python -c "from pathlib import Path; from src.agent.config import Settings; from src.agent.evaluation.evaluator import Evaluator; print(Evaluator(Settings(env='personal')).run_scenarios(Path('tests/fixtures/scenarios.json')))"
```

## Test

```bash
pytest
```
