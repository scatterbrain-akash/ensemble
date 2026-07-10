# Code Flow and Entry Points

This document explains the runtime structure, primary entrypoints, dataflow, and key modules in the Ensemble agent repository. It is intended for maintainers and integrators.

## High-level overview

- Input: denial letter / EOB text file
- Pipeline stages: extraction -> planning -> retrieval -> synthesis -> critique -> output
- Tools isolate external systems: `CMSCoverageTool` (real CMS API) and `FixtureRetrievalTool` (local fallback)
- Orchestration: `Orchestrator` coordinates stages and assembles `PolicyEvidence` and `AppealDraft` artifacts

## Important entrypoints

- CLI: `src/agent/cli.py` — parse args, read input file, call `main()` which uses `Orchestrator` to run pipeline.
- Orchestrator: `src/agent/core/orchestrator.py` — public method `run()` / `run_scenarios()` used by tests and CLI. This is the main conductor.
- Tools: implementations live under `src/agent/tools/` and expose `run(query: dict) -> list[dict]`.
- LLM provider: `src/agent/llm/mock_provider.py` (test/mock). Production providers are pluggable via settings and model routing.

## Data models

- `PolicyEvidence` (pydantic model) — normalized evidence with: `source_id`, `source_type`, `title`, `excerpt`, `relevance`, `retrieval_query`, `url`.
- `ExtractedClaim`, `AppealDraft` — used across extraction and synthesis stages.

## Orchestrator flow (detailed)

1. Extraction stage: calls LLM provider to convert denial text into structured `ExtractedClaim` (patient, codes, claim ids).
2. Planning stage: LLM mock produces retrieval queries (policy_type and code) for the retrieval stage.
3. Retrieval stage: `Orchestrator._retrieve_policy_evidence()` iterates tools in order (configured). For each query:
   - Calls `CMSCoverageTool.run(query)` — returns list of `PolicyEvidence` or empty list.
   - If empty, falls back to `FixtureRetrievalTool.run(query)`.
4. Synthesis stage: LLM provider synthesizes `AppealDraft` using retrieved `PolicyEvidence` items (quotes `source_id`).
5. Critique stage: optional LLM self-critique to verify coverage and confidence.

## Key files

- `src/agent/core/orchestrator.py` — orchestrator and pipeline wiring.
- `src/agent/tools/cms_coverage.py` — CMS integration, token flow, and retry/backoff logic.
- `src/agent/tools/fixture_retrieval.py` — local fixture fallback loader.
- `src/agent/llm/mock_provider.py` — deterministic LLM behavior used by tests.
- `src/agent/evaluation/evaluator.py` — runs scenarios and compares outputs to expected criteria.
- `src/agent/config.py` — settings loader (`.env` + YAML `config/settings.yaml`) that carries timeouts, retries, and `cms` settings.

## Failure modes & fallbacks

- Network/transient errors: `CMSCoverageTool` implements retry/backoff with jitter; configurable via `settings.retries.cms_tool` and `settings.cms.retry_backoff_seconds`.
- Authorization token issues: tool fetches license token from `/v1/metadata/license-agreement`, caches it with TTL (`settings.cms.license_token_ttl_seconds`) and refreshes on 401.
- Empty API responses: treated as "no results" to allow `FixtureRetrievalTool` fallback.

## Caching, cost, and performance

- Exact-match LLM cache: agents use an in-memory exact-match cache keyed by provider+model+system_prompt+user_prompt+params. TTL is configured via `config/settings.yaml` (default `cache.llm_ttl_seconds`). This reduces repeated token usage for identical prompts.
- Tool-result cache: policy lookups (normalized by `policy_type` + `code`) are cached in `CacheService` with TTL (`cache.policy_ttl_seconds`). The `Orchestrator` checks this cache before calling `CMSCoverageTool` and stores successful results.
- Cost tracking: `CostTracker` records approximate `llm_calls`, `tool_calls`, `tokens_in`, `tokens_out`, and estimated USD cost. Agents estimate token counts heuristically and call `CostTracker.record_llm_call()` so runs include a cost summary.
- Redis persistence: `CacheService` supports an optional Redis backend when `config/settings.yaml` sets `cache.backend: redis` and `cache.redis_url` is provided. If Redis is unavailable, the cache falls back to an in-memory TTL store.
- Provider token usage: LLM providers now return `usage` info when available (OpenAI-style `prompt_tokens`/`completion_tokens`) and `BaseAgent` will use provider-reported counts for accurate cost accounting. When providers don't report usage, a heuristic estimator is used as a fallback.
- Latency: `Tracer` records stage spans; per-call spans can be added to pinpoint hotspots. Retrieval attempts use retry/backoff with jitter to improve reliability. Consider async/concurrent retrieval for lower wall-clock latency.

These features are implemented to demonstrate production-grade quality with knobs for TTLs, retry caps, and cost-per-token settings.

## Observability

- Tracing: basic `Tracer` stubs and `CostTracker` exist in the codebase for recording runtime metrics.
- Tests: unit and integration tests exercise the tool and orchestrator flows (`tests/unit`, `tests/integration`).

## How to extend

- Add new tools under `src/agent/tools/` implementing the `run(query)` contract.
- Add production LLM provider implementing the same API as `mock_provider` and wire via `Settings`.

## Quick developer commands

Run tests:
```
python -m pytest -q
```

Run just integration tests:
```
python -m pytest tests/integration -q
```

## Contact / Ownership

Maintainers: see `CODEOWNERS` if present. For questions, open an issue or PR describing the change.
