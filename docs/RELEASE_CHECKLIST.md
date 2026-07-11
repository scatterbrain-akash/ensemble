# Release Checklist — v1.0.0

This checklist maps release requirements to concrete repository artifacts to demonstrate completeness for demos and audits.

- [x] Core functionality implemented
  - Retrieval tool: [src/agent/tools/cms_coverage.py](src/agent/tools/cms_coverage.py)
  - Fallback fixtures: [src/agent/tools/fixture_retrieval.py](src/agent/tools/fixture_retrieval.py)

- [x] Resilience & retries
  - Retry/backoff with jitter implemented in `CMSCoverageTool` (see [src/agent/tools/cms_coverage.py](src/agent/tools/cms_coverage.py)).

- [x] Token acquisition & TTL handling
  - License token flow implemented and cached with TTL: [src/agent/tools/cms_coverage.py](src/agent/tools/cms_coverage.py)

- [x] Caching & persistence
  - In-memory and file-backed cache: [src/agent/cache/cache_service.py](src/agent/cache/cache_service.py)
  - Optional Redis backend (configurable via `config/settings.yaml` `cache.backend`)

- [x] Observability & cost
  - `Tracer`: [src/agent/observability/tracer.py](src/agent/observability/tracer.py)
  - `CostTracker`: [src/agent/observability/cost_tracker.py](src/agent/observability/cost_tracker.py)
  - LLM usage propagation in providers: [src/agent/llm/groq_provider.py](src/agent/llm/groq_provider.py), [src/agent/llm/aistudio_provider.py](src/agent/llm/aistudio_provider.py), [src/agent/llm/mock_provider.py](src/agent/llm/mock_provider.py)

- [x] Tests & CI
  - Unit tests: [tests/unit](tests/unit)
  - Integration tests: [tests/integration](tests/integration)
  - CI workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml) (includes Redis smoke test)

- [x] Documentation
  - Code flow and entrypoints: [docs/CODE_FLOW.md](docs/CODE_FLOW.md)
  - README references example config: [README.md](README.md)

- [x] Contributor docs & governance
  - Add `CONTRIBUTING.md`, `CODE_OF_CONDUCT`, LICENSE. These files are now present.

- [x] Sample run artifact
  - Add `traces/sample_run.json` as an inspectable runtime trace artifact.

- [x] Observability guidance
  - Document trace and execution summary viewing in `README.md`.

Status: Release-ready for v1.0.0. Remaining deferred items are CI polish and optional contributor templates.
