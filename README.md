# Claims Denial & Appeal Intelligence Agent

A lightweight agentic pipeline for transforming a denial letter/EOB into an evidence-grounded appeal preparation package.

## What it does

- Extracts structured claim data from unstructured denial letters
- Retrieves matched CMS coverage policy evidence
- Synthesizes a draft appeal package with explicit citations
- Applies bounded self-critique and guardrails
- Escalates safely when evidence or confidence is insufficient

## CMS Integration

- The project wraps the CMS Coverage API (`https://api.coverage.cms.gov`) in a single tool: `src/agent/tools/cms_coverage.py`.
- Endpoints used: `/v1/data/ncd/`, `/v1/data/lcd/`, `/v1/data/article/` (mapped to `ncdid`, `lcdid`, `articleid` query params).
- LCD/Article calls require a license-agreement token obtained from `/v1/metadata/license-agreement`. The token is valid for ~1 hour and must be provided as `Authorization: Bearer <token>`.
- The tool implements configurable retry/backoff with jitter for transient errors. Configure via `config/settings.yaml` under `retries.cms_tool` (attempts) and `cms.retry_backoff_seconds` / `cms.max_backoff_seconds`.

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

### Configuration

- Copy `config/settings.example.yaml` to `config/settings.yaml` and adjust values for your environment (Redis URL, per-token costs, TTLs, API keys).

CI / Badge

- A GitHub Actions workflow `CI` is provided at `.github/workflows/ci.yml` that runs tests and includes a Redis service for integration tests.
- Add a workflow badge to this README by replacing `OWNER` and `REPO` with your repository owner/name:

   ![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)

   Example: `![CI](https://github.com/youruser/ensemble/actions/workflows/ci.yml/badge.svg)`

### Configuration

- `config/settings.yaml` can be used to tune timeouts, retry/backoff, and CMS-specific settings. Example keys:
   - `timeouts.tool_call_seconds`
   - `retries.cms_tool`
   - `cms.retry_backoff_seconds`
   - `cms.max_backoff_seconds`
   - `cms.license_token_ttl_seconds`

## Run

```bash
python -m src.agent.cli --input "path/to/denial.txt"
```

## Observability

The agent emits structured runtime information in two places:

- `metadata.trace` on the final response contains per-stage spans with `name`, `start_time`, `end_time`, `duration`, and optional metadata.
- `metadata.execution_summary` includes per-step `llm_calls`, `cache_hits`, `tokens_in`, `tokens_out`, `cost_usd`, and result statuses.

A sample execution artifact is available at `traces/sample_run.json`.

To view it:

```bash
python -m json.tool traces/sample_run.json | less
```

or open it in a JSON viewer to inspect the trace spans and summary.

## Developer Quick Commands

Run tests:
```bash
python -m pytest -q
```

Run the scenario evaluator:
```bash
python -c "from pathlib import Path; from src.agent.config import Settings; from src.agent.evaluation.evaluator import Evaluator; print(Evaluator(Settings(env='personal')).run_scenarios(Path('tests/fixtures/scenarios.json')))"
```

If tests fail with import errors, install the package in editable mode:
```bash
pip install -e .
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
