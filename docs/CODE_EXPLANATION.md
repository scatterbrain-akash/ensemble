# Code Explanation

This document explains the runtime flow of the Ensemble agent codebase from input text to final output. It follows one concrete example and shows which files are invoked at each step.

## Example scenario

Input: a denial letter text file.

Run command:

```bash
python -m src.agent.cli --input tests/fixtures/denial_letters/basic_denial.txt
```

This command starts the pipeline and returns a JSON result object plus an execution summary.

## 1. Entry point: `src/agent/cli.py`

File: `src/agent/cli.py`

What happens:

- The CLI parses `--input`, `--output`, and `--environment`.
- It creates a `Settings` object from `src.agent.config.Settings`.
- It creates an `Orchestrator` instance from `src.agent.core.orchestrator.Orchestrator`.
- It reads the input file contents into a string.
- It calls `orchestrator.run(text)`.
- It prints either the result JSON or the result JSON plus a formatted execution summary.

## 2. Configuration loading: `src/agent/config.py`

File: `src/agent/config.py`

What happens:

- `Settings.__init__()` loads `.env` using `load_dotenv()` unless `DISABLE_DOTENV=1` is set.
- It calls `_load_yaml()` to read `config/models.yaml` and `config/settings.yaml`.
- It loads runtime values for `timeouts`, `retries`, `cost`, `cache`, and `cms`.
- It also loads API keys from environment variables: `OPENAI_API_KEY`, `GROQ_API_KEY`, and `AI_STUDIO_API_KEY`.
- `model_role_config(role)` returns provider configuration for a given agent role.

## 3. Orchestrator initialization: `src/agent/core/orchestrator.py`

File: `src/agent/core/orchestrator.py`

What happens in `Orchestrator.__init__()`:

- Creates a logger.
- Creates a `Tracer` object from `src.agent.observability.tracer.Tracer`.
- Creates a `CostTracker` object from `src.agent.observability.cost_tracker.CostTracker`.
- Creates a `CacheService` object from `src.agent.cache.cache_service.CacheService`.
- Creates a `ModelRouter` object from `src.agent.core.router.ModelRouter`.
- Instantiates the four pipeline agents:
  - `ExtractionAgent`
  - `PlannerAgent`
  - `SynthesisAgent`
  - `CritiqueAgent`
- Loads the CMS tool using `src.agent.tools.registry.load_tool("cms_coverage", settings=settings)`.
- Loads the fallback fixture tool with `load_tool("fixture_retrieval")`.

## 4. Pipeline run method: `Orchestrator.run()`

File: `src/agent/core/orchestrator.py`

What happens in `run(input_text)`:

- Validates the input text with `validate_input_text()` from `src.agent.guardrails.input_guard`.
- Creates an `AgentState` object from `src.agent.core.state.AgentState`.
- Captures an initial cost snapshot.
- Starts the `extraction` span.
- Calls `self.extraction.run(state)`.
- Finishes the extraction span and captures extraction metrics.
- If extraction fails or confidence is too low, it escalates and returns early.
- Starts the `planning` span.
- Calls `self.planner.run(state)`.
- Finishes planning span and captures metrics.
- If planning decides to escalate before retrieval, it escalates and returns.
- Starts the `retrieval` span.
- Calls `self._retrieve_policy_evidence(state)`.
- Finishes retrieval span and captures metrics.
- Starts the `synthesis` span.
- Calls `self.synthesis.run(state)`.
- Finishes synthesis span and captures metrics.
- Validates the appeal draft with `validate_appeal_draft()` from `src.agent.guardrails.output_guard`.
- If guardrails fail, it escalates and returns.
- Starts the `critique` span.
- Calls `self.critique.run(state)`.
- Finishes critique span and captures metrics.
- If critique fails or requests escalation, it returns.
- Stores final cost summary into `state.metadata["cost"]`.
- Calls `_finalize_state(state)` and returns the state.

## 5. State container: `src/agent/core/state.py`

File: `src/agent/core/state.py`

`AgentState` is the central data container for one run. It holds:

- `input_text`
- `extracted_claim`
- `retrieval_plan`
- `policy_evidence`
- `appeal_draft`
- `critique_result`
- `escalation_reason`
- `metadata`

`AgentState.model_dump()` returns a plain dictionary representation.
`AgentState.model_dump_json()` returns JSON.

## 6. Extraction agent: `src/agent/agents/extraction.py`

File: `src/agent/agents/extraction.py`

What happens in `ExtractionAgent.run(state)`:

- The agent calls `self.call_llm(state.input_text)`.
- It attempts to parse the returned text as JSON using `self.parse_json()`.
- If parsing fails, it uses `_parse_text_response()` to read fields from plain text.
- It builds an `ExtractedClaim` object from `src.agent.schemas.io_models.ExtractedClaim`.
- It stores that object in `state.extracted_claim`.

Key result:

- `state.extracted_claim` contains `claim_id`, `payer`, `procedure_codes`, `diagnosis_codes`, `denial_reason`, `service_dates`, `missing_fields`, and `confidence`.

## 7. Planner agent: `src/agent/agents/planner.py`

File: `src/agent/agents/planner.py`

What happens in `PlannerAgent.run(state)`:

- If `state.extracted_claim` is missing, it returns unchanged.
- It converts the extracted claim to a dictionary payload.
- It calls `self.call_llm(payload)`.
- It parses the provider response as JSON.
- It constructs `RetrievalPlan` from `src.agent.schemas.io_models.RetrievalPlan`.
- It stores that in `state.retrieval_plan`.

The plan contains:

- `queries`: one or more policy lookup query dictionaries.
- `escalate_before_draft`: a boolean that tells the orchestrator whether to stop before retrieval.

## 8. LLM provider routing: `src/agent/core/router.py`

File: `src/agent/core/router.py`

What happens in `ModelRouter.get_provider(role)`:

- It loads role-specific provider configuration with `settings.model_role_config(role)`.
- It builds candidates from `primary` and `fallbacks`.
- It parses each candidate as `provider_name:model_name`.
- It resolves API keys from the `Settings` object.
- It returns the first viable provider.
- If no real provider is available, it returns `MockProvider`.

Providers available in the repository:

- `src.agent.llm.mock_provider.MockProvider`
- `src.agent.llm.groq_provider.GroqProvider`
- `src.agent.llm.aistudio_provider.AIStudioProvider`

## 9. LLM call logic: `src/agent/agents/base.py`

File: `src/agent/agents/base.py`

`BaseAgent.call_llm()` is shared by all agents.

What it does:

- Loads the system prompt from `src/agent/prompts/{role}_system.md`.
- Uses `ModelRouter` to get the provider for the agent role.
- Serializes user prompt payloads to JSON if needed.
- Computes an exact-match cache key using provider, model, system prompt, user prompt, and kwargs.
- If the cache contains a value, it returns the cached response and records a cache hit.
- Otherwise, it calls `provider.generate(system_prompt=..., user_prompt=..., **kwargs)`.
- It handles provider output as either a string or a dict containing `content` and `usage`.
- It extracts token usage from provider metadata or estimates it heuristically.
- It records cost via `CostTracker.record_llm_call()`.
- It caches the response for future identical prompts.
- It returns the provider text response.

The cache TTL for LLM responses comes from `settings.cache.llm_ttl_seconds`.

## 10. Mock provider behavior: `src/agent/llm/mock_provider.py`

File: `src/agent/llm/mock_provider.py`

`MockProvider` is the default safe provider for local test runs.

It recognizes the role from the system prompt and returns deterministic JSON:

- Extraction returns an `ExtractedClaim` JSON object.
- Planner returns a `RetrievalPlan` with queries for procedure and diagnosis codes.
- Synthesis returns an `AppealDraft` built from claim and evidence.
- Critique returns a `CritiqueResult` with `passed` or `escalation_required`.

This provider is useful for understanding the pipeline behavior without external API dependency.

## 11. Retrieval stage: `Orchestrator._retrieve_policy_evidence()`

File: `src/agent/core/orchestrator.py`

What happens:

- It clears `state.policy_evidence`.
- For each query in `state.retrieval_plan.queries`:
  - It computes a cache key: `tool:cms:{policy_type}:{code}`.
  - It checks `CacheService.get(cache_key)`.
  - If the cache is empty, it calls `self.cms_tool.run(query)`.
  - It records a tool call in `CostTracker.record_tool_call()`.
  - If the CMS tool returns no evidence, it calls `self.fixture_tool.run(query)` as a fallback.
  - It caches successful evidence results.
  - It converts each evidence item into a `PolicyEvidence` model and appends to `state.policy_evidence`.

Success means `state.policy_evidence` contains one or more evidence items.

## 12. CMS tool: `src/agent/tools/cms_coverage.py`

File: `src/agent/tools/cms_coverage.py`

What happens in `CMSCoverageTool.run(query)`:

- It validates that the query contains a `code`.
- It determines `policy_type` (`ncd`, `lcd`, or `article`).
- It calls `_fetch_policy(code, policy_type)`.
- It parses the API response into normal evidence records.

`_fetch_policy()` does:

- Builds the CMS URL for the policy type endpoint.
- Adds `Authorization` bearer token for `lcd` or `article` lookups.
- Fetches a license token from `/v1/metadata/license-agreement` when needed.
- Retries on transient failures using configurable backoff and jitter.
- Raises on non-retryable HTTP errors.

`_parse_policy_response()` does:

- Normalizes response formats from CMS into a list of dictionaries.
- Extracts `source_id`, `title`, `excerpt`, `url`, and a `relevance` flag.
- Returns evidence in the shape expected by `PolicyEvidence`.

## 13. Fixture fallback tool: `src/agent/tools/fixture_retrieval.py`

File: `src/agent/tools/fixture_retrieval.py`

What happens:

- Loads `tests/fixtures/policies/policy_fixtures.json` on first use.
- Returns the fixture records for the requested code.
- This tool is only used when the CMS call returns no evidence.

## 14. Synthesis agent: `src/agent/agents/synthesis.py`

File: `src/agent/agents/synthesis.py`

What happens in `SynthesisAgent.run(state)`:

- It builds a payload containing:
  - `claim`: extracted claim data
  - `evidence`: list of evidence item dictionaries
- It calls `self.call_llm(payload)`.
- It parses the returned JSON into an `AppealDraft`.
- It stores the result in `state.appeal_draft`.

If parsing fails, it stores a fallback draft with a failure message.

## 15. Critique agent: `src/agent/agents/critique.py`

File: `src/agent/agents/critique.py`

What happens in `CritiqueAgent.run(state)`:

- It builds a payload containing:
  - `draft`: the appeal draft
  - `claim`: extracted claim
  - `evidence`: the retrieved evidence
- It calls `self.call_llm(payload)`.
- It parses the returned JSON into a `CritiqueResult`.
- It stores it in `state.critique_result`.

If the critique result says `escalation_required=True`, the orchestrator stops and returns the state.

## 16. Finalization and metadata

File: `src/agent/core/orchestrator.py`

What happens in `_finalize_state(state)`:

- It stores the trace data in `state.metadata["trace"]`.
- It builds an execution summary in `state.metadata["execution_summary"]`.
- The summary includes per-step metrics:
  - `step`
  - `status`
  - `duration`
  - `llm_calls`
  - `cache_hits`
  - `tokens_in`
  - `tokens_out`
  - `cost_usd`
- It also includes totals and any escalation reason.

## 17. Observability components

Files:

- `src/agent/observability/tracer.py`
- `src/agent/observability/cost_tracker.py`

Tracer:

- Records spans with start/end timestamps.
- Converts spans to dictionaries with `duration`.

CostTracker:

- Tracks LLM calls, tool calls, cache hits, tokens in/out, and estimated USD cost.
- Provides snapshots used to compute per-step metrics.

## 18. Supporting prompt files

Files:

- `src/agent/prompts/extraction_system.md`
- `src/agent/prompts/planner_system.md`
- `src/agent/prompts/synthesis_system.md`
- `src/agent/prompts/critique_system.md`

Each file contains the system prompt text used by the corresponding agent role.

## 19. Key success and failure branches

Success path:

1. Extraction returns a claim with confidence >= 0.5.
2. Planner returns queries and does not set `escalate_before_draft`.
3. Retrieval returns at least one evidence item.
4. Synthesis produces an appeal draft.
5. Critique passes without escalation.

Failure branches:

- Extraction fails or returns low confidence.
- Planner decides to escalate before retrieval.
- CMS retrieval returns no data and fixture fallback also returns no evidence.
- Output guardrail rejects the appeal draft.
- Critique requests escalation.

In every failure case, `Orchestrator.run()` returns the current state with `escalation_reason` and metadata.

## 20. How to answer codebase questions

If asked what happens when the input is read:

- `src/agent/cli.py` reads the file and calls `Orchestrator.run()`.
- `Orchestrator.run()` creates state and drives the extraction agent.

If asked which file decides the LLM provider:

- `src/agent/core/router.py` uses `config/models.yaml` and environment API keys.

If asked how evidence is fetched:

- `Orchestrator._retrieve_policy_evidence()` first checks cache, then `src/agent/tools/cms_coverage.py`, then `src/agent/tools/fixture_retrieval.py`.

If asked how cost is tracked:

- `src/agent/observability/cost_tracker.py` records each LLM call and creates per-step summaries at runtime.

If asked how the pipeline ends:

- `Orchestrator._finalize_state()` attaches trace and summary to `state.metadata` and returns `AgentState`.

## 21. Recommended file map

- Runtime entrypoint: `src/agent/cli.py`
- Pipeline orchestration: `src/agent/core/orchestrator.py`
- State model: `src/agent/core/state.py`
- Agent base: `src/agent/agents/base.py`
- Agents: `src/agent/agents/*.py`
- Router: `src/agent/core/router.py`
- Prompts: `src/agent/prompts/*.md`
- Tools: `src/agent/tools/*.py`
- Cache: `src/agent/cache/cache_service.py`
- Observability: `src/agent/observability/*.py`
- Configuration: `src/agent/config.py`
- Schemas: `src/agent/schemas/io_models.py`

## 22. Short answer summary

The core flow is:

1. CLI reads denial text.
2. Orchestrator validates and creates state.
3. Extraction agent builds structured claim data.
4. Planner agent creates retrieval queries.
5. Orchestrator fetches policy evidence via CMS / fixtures.
6. Synthesis agent writes the appeal draft.
7. Critique agent reviews the draft.
8. Orchestrator finalizes state with traces and summary.

That is the complete ground-level flow from input to output in this codebase.