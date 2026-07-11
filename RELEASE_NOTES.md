# Release v1.0.0 — Initial public release

Release date: 2026-07-10

Summary
- Initial public release of the Ensemble Claims Denial & Appeal Intelligence Agent.
- Focus: robust retrieval of CMS coverage policies, resilient tooling, reproducible evaluation harness, and developer ergonomics.

Highlights
- CMS integration: `src/agent/tools/cms_coverage.py` — mapped to `/v1/data/{policy_type}/` endpoints, token acquisition, TTL-aware token caching, and retry/backoff with jitter.
- Fallback: deterministic `FixtureRetrievalTool` for offline or empty results.
- Resilience: configurable retry/backoff, token refresh on 401, and explicit empty-response handling.
- Caching: tiered caching (LLM exact-match cache + tool-result cache) via `src/agent/cache/cache_service.py` with optional Redis backend and file-backed fallback.
- Cost & observability: `CostTracker` records call counts and token estimates; `Tracer` records stage spans; LLM providers surface usage when available and `BaseAgent` records costs.
- Tests: unit and integration tests added (`tests/unit`, `tests/integration`) with a local stub server exercising token flow and transient errors.
- CI: GitHub Actions workflow `.github/workflows/ci.yml` runs tests and includes a Redis service and a smoke test.
- Documentation: `docs/CODE_FLOW.md` describes entrypoints, dataflow, instrumentation, and caching strategy.

Notes for maintainers
- Release tag: `v1.0.0` (semantic versioning). Future releases use MAJOR.MINOR.PATCH.
- To run locally: copy `config/settings.example.yaml` -> `config/settings.yaml` and adjust `cache.redis_url` or `cache.backend`.

Security & privacy
- No secrets checked in. Tokens from CMS license-agreement are short-lived and stored only in memory with TTL.

Known limitations (deferred items)
- CONTRIBUTING, PR/Issue templates, pre-commit hooks, formal CODE_OF_CONDUCT and LICENSE files are intentionally left as a focused next step and can be added before public distribution.
