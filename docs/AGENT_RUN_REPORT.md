# Agent Run Report

## Overview

This project implements a claims denial / appeal evidence preparation agent.
It converts a denial letter/EOB into structured claim facts, retrieves CMS coverage evidence, and synthesizes an appeal draft with bounded self-critique and guardrails.

## Architecture

- `src/agent/core/orchestrator.py`: bounded pipeline orchestration
- `src/agent/agents/`: extraction, planning, synthesis, critique agents
- `src/agent/tools/`: CMS policy retrieval and deterministic fixture fallback
- `src/agent/schemas/io_models.py`: typed data contracts for claims, plans, evidence, and drafts
- `src/agent/observability/`: trace and cost instrumentation
- `src/agent/evaluation/`: scenario evaluation and metrics

## Current Status

### Implemented
- Structured multi-stage agent pipeline
- Mock-based full run with fixture fallback
- CMS Coverage tool with NCD/LCD token retrieval and refresh support
- Output guardrails requiring evidence references
- Evaluation scaffolding with `tests/fixtures/scenarios.json`
- Tool registry for pluggable retrieval implementations

### Work remaining
- CMS tool response normalization for real CMS payloads beyond simple JSON shapes
- richer output guardrails for citation coherence and overclaim detection
- `AGENT_RUN_REPORT.md` may be extended with run results and performance artifacts

## Notes

The implementation is designed to be deterministic without network access by using fixture fallback.
A future enhancement is to add live integration tests and a full run report artifact using `traces/sample_run.json`.
