# Release Notes

## v1.0.0 — 2026-07-11

Initial release of the Claims Denial & Appeal Intelligence Agent.

- Multi-stage agentic pipeline: extraction → planning → retrieval → synthesis → critique
- CMS Coverage API integration (NCD/LCD) with token refresh and retry/backoff
- PDF and plain-text denial letter support
- FastAPI web UI with drag-and-drop PDF upload
- Redis-backed LLM and tool-result caching (falls back to file or memory)
- Per-stage observability: trace spans and cost/token tracking
- Dockerfile and docker-compose for containerised deployment
- 8 passing tests; scenario evaluator at `tests/fixtures/scenarios.json`
