# Codebase Structure & Conventions (v2)

**Companion to `SOLUTION_DESIGN_v2.md`.** This doc answers one question precisely: **what goes in each folder, why, and how that choice improves our best-practice / rubric posture.** It also fixes the conventions, config hierarchy, and test strategy so an AI coding assistant (and a human reviewer) can navigate the repo without guessing.

---

## 1. The five principles the structure encodes

Every folder exists to serve one of these. If a proposed file doesn't serve one, it doesn't belong.

| Principle | What it means here | How the structure enforces it |
| --- | --- | --- |
| Separation of concerns | agent logic ≠ tools ≠ prompts ≠ schemas ≠ eval ≠ config | each is its own package; no cross-imports upward |
| Portability | orchestrator could move to LangGraph later | `agents/` + `core/` expose graph-node-shaped interfaces |
| Testability | tests never need a live API key | LLM/tool calls sit behind interfaces that are mocked in unit tests |
| Config-driven | no model name, temperature, or key in code | everything tunable lives in `config/` + env (§4) |
| Inspectability | every run is a readable trace | `observability/` is cross-cutting, emitted by every stage |

**Anti-pattern we explicitly avoid** (checklist: "avoid creating empty modules just to mirror the diagram"): folders are created only when they hold real, used code. Retrieval/aggregation are a tool + a function, not an empty `agents/retrieval_agent.py` shell.

---

## 2. Repository tree (tiered P0 / P1 / P2)

```text
claims-appeal-agent/
├── README.md                          # P0  domain rationale, diagram, setup, run, eval, limits
├── .env.example                       # P0  placeholder keys + provider selection
├── requirements.txt                   # P0  pinned deps
├── pyproject.toml                     # P1  ruff + mypy/pyright + pytest config
├── Makefile                           # P1  setup / run / eval / test / lint shortcuts
├── Dockerfile                         # P1  reproducible runtime
├── docker-compose.yml                 # P2
├── .github/workflows/ci.yml           # P2  lint + type + test on PR
├── config/
│   ├── models.yaml                    # P0  role → capability-tier → provider/model + fallbacks
│   └── settings.yaml                  # P1  timeouts, retries, cost ceiling, cache TTLs
├── src/agent/
│   ├── cli.py                         # P0  entrypoint; flags mirror the assignment's example
│   ├── config.py                      # P0  pydantic-settings loader (env + yaml + defaults)
│   ├── core/
│   │   ├── orchestrator.py            # P0  the bounded state machine (the loop)
│   │   ├── state.py                   # P0  AgentState + the plan-as-data
│   │   └── router.py                  # P0  capability-tier model routing + fallback chain
│   ├── agents/
│   │   ├── base.py                    # P0  BaseAgent.run(state) -> state
│   │   ├── extraction.py              # P0
│   │   ├── planner.py                 # P0
│   │   ├── synthesis.py               # P0
│   │   └── critique.py                # P1  self-critique / bounded revision + ensembling hook
│   ├── tools/
│   │   ├── base.py                    # P0  BaseTool (name, description, run)
│   │   ├── cms_coverage.py            # P0  live CMS API (incl. license-token flow)
│   │   ├── fixture_retrieval.py       # P0  deterministic local fallback
│   │   └── registry.py                # P0  tool discovery/registration
│   ├── llm/
│   │   ├── base_provider.py           # P0  provider-agnostic interface
│   │   ├── groq_provider.py           # P0  free-tier (personal laptop)
│   │   ├── frontier_provider.py       # P0  work-laptop provider (OpenAI/Anthropic)
│   │   ├── gemini_provider.py         # P1  second family (ensembling)
│   │   └── retry.py                   # P0  tenacity backoff + timeout wrapper
│   ├── prompts/
│   │   ├── extraction_system.md       # P0  versioned; never inline strings
│   │   ├── planner_system.md          # P0
│   │   ├── synthesis_system.md        # P0
│   │   ├── critique_system.md         # P1
│   │   └── examples/                  # P0  few-shot edge cases (missing/no-match/injection)
│   ├── schemas/
│   │   └── io_models.py               # P0  Pydantic contracts (§6 of design doc)
│   ├── guardrails/
│   │   ├── input_guard.py             # P0  length/type/empty + injection isolation
│   │   └── output_guard.py            # P0  overclaim + citation checks
│   ├── cache/
│   │   └── cache_service.py           # P0  exact-match LLM + tool-result cache
│   ├── memory/
│   │   └── store.py                   # P1  session + long-term policy store
│   ├── observability/
│   │   ├── tracer.py                  # P0  OTel-shaped spans + correlation IDs
│   │   ├── logger.py                  # P0  tabular structured logging
│   │   └── cost_tracker.py            # P1  tokens + est. cost + budget ceiling
│   └── evaluation/
│       ├── evaluator.py               # P0  runs scenarios, expected vs actual
│       ├── metrics.py                 # P0  faithfulness/completeness/guardrail checks
│       └── llm_judge.py               # P1  optional judge (different family)
├── tests/
│   ├── unit/                          # P1  mock LLM + tools; no key needed
│   ├── integration/                   # P1  fixture-mode end-to-end
│   └── fixtures/
│       ├── scenarios.json             # P0  the 5 scenarios + assertions
│       ├── denial_letters/            # P0  synthetic inputs + known-answer ground truth
│       └── policies/                  # P0  curated CMS fixtures for offline runs
├── traces/
│   └── sample_run.json                # P0  required deliverable: one full run
└── docs/
    ├── AGENT_RUN_REPORT.md            # P0  required deliverable
    ├── ARCHITECTURE.md                # P0  (or fold into README)
    ├── PROMPT_DESIGN.md               # P1  prompt rationale + versions
    └── AI_ASSISTED_DEVELOPMENT.md     # P1  provenance/review note
```

---

## 3. Folder-by-folder rationale (the "what & why" table)

| Path | What lives here | Why it's separated | How it improves best-practice / rubric | Tier |
| --- | --- | --- | --- | --- |
| `config/models.yaml` | role → capability-tier → provider/model + fallback chain | model choice is a *policy*, not logic | satisfies "config externalized"; enables work↔personal env swap with zero code change | P0 |
| `config/settings.yaml` | timeouts, retry caps, cost ceiling, cache TTL | operational knobs change per env | tune reliability/cost without redeploying logic | P1 |
| `src/agent/cli.py` | argument parsing + wiring only | keep I/O out of business logic | clean entrypoint; reproducible commands = "Working Software" | P0 |
| `src/agent/config.py` | pydantic-settings loader (env → yaml → defaults) | one typed place to resolve config | no hardcoding; fail-fast on bad config | P0 |
| `core/orchestrator.py` | the bounded state machine | one place owns control flow + termination | proves "no infinite loops"; the heart of "decision flow" | P0 |
| `core/state.py` | `AgentState`, plan-as-data | state is explicit and typed, not globals | inspectable handoffs; portable to LangGraph nodes | P0 |
| `core/router.py` | capability-tier routing + fallback | routing decoupled from agents | purpose-based model invocation; graceful degradation | P0 |
| `agents/base.py` | `BaseAgent.run(state)->state` | uniform composition contract | orchestrator treats agents interchangeably (SOLID) | P0 |
| `agents/*.py` | one reasoning agent each | different agents have different failure modes | genuine multi-agent decomposition (advanced technique) | P0/P1 |
| `tools/base.py` + `registry.py` | tool interface + discovery | tools are pluggable, not hardwired | tool-based architecture; add tools without touching agents | P0 |
| `tools/cms_coverage.py` | live CMS API incl. license-token flow | isolate the one real external dependency | ≥1 real tool/function call; validated auth (ADR-4) | P0 |
| `tools/fixture_retrieval.py` | deterministic offline evidence | demo must run without network/token | reliable, repeatable eval; failure-resilience | P0 |
| `llm/base_provider.py` | provider-agnostic call interface | swap providers behind one seam | testability (mockable); portability | P0 |
| `llm/*_provider.py` | one adapter per provider | isolate SDK quirks (Groq "mostly" OpenAI-compatible) | dual-environment support; error normalization | P0/P1 |
| `llm/retry.py` | timeout + backoff wrapper | retry policy in one place | "graceful API failure handling" rubric line | P0 |
| `prompts/*.md` | versioned system prompts | prompts are data, diff-able, attributable | "Prompt Craft" rubric; trace records prompt_version | P0 |
| `prompts/examples/` | few-shot edge cases | robustness comes from seams, not happy paths | prompt-craft evidence (closes checklist gap) | P0 |
| `schemas/io_models.py` | Pydantic contracts | typed boundaries, not NL handoffs | "structured outputs" rubric; observable failures | P0 |
| `guardrails/input_guard.py` | validation + injection isolation | treat source text as data | "input validation & guardrails"; threat model | P0 |
| `guardrails/output_guard.py` | overclaim + citation checks | domain safety at the exit | healthcare overclaim guardrail = the actual job | P0 |
| `cache/cache_service.py` | exact + tool-result cache | reuse is orthogonal to logic | reliability under free-tier RPD; cost optimization | P0 |
| `memory/store.py` | session + long-term store | persistence is optional, isolated | "memory across sessions" bonus; cheap given cache | P1 |
| `observability/tracer.py` | OTel-shaped spans | tracing is cross-cutting | "inspectable trace" deliverable; OTel-swappable | P0 |
| `observability/logger.py` | tabular structured logs | consistent, greppable logs | clean logging; no secrets/PHI leakage | P0 |
| `observability/cost_tracker.py` | tokens + cost + ceiling | cost is a first-class metric | enterprise cost artifact; budget enforcement | P1 |
| `evaluation/evaluator.py` | scenario runner | eval separated from app | "lightweight evaluation" deliverable | P0 |
| `evaluation/metrics.py` | deterministic scorers | objective, repeatable scoring | measured (not proposed) results | P0 |
| `evaluation/llm_judge.py` | optional judge | advisory only, gated | faithfulness spot-check without bias risk | P1 |
| `tests/unit/` | mocked component tests | fast, key-less, CI-safe | "Clean Code"; tests never hit real APIs | P1 |
| `tests/integration/` | fixture-mode end-to-end | prove the loop without network | reproducibility; regression safety | P1 |
| `tests/fixtures/` | scenarios + letters + policies + ground truth | inputs are versioned data | objective eval; deterministic demos | P0 |
| `traces/sample_run.json` | one captured full run | the required artifact | "full agent run" deliverable | P0 |
| `docs/AGENT_RUN_REPORT.md` | arch + traces + results + trade-offs | required second deliverable | graded artifact; lift from design doc | P0 |
| `docs/AI_ASSISTED_DEVELOPMENT.md` | provenance/review note | shows modern build method | GenAI-leadership signal | P1 |

---

## 4. Configuration hierarchy (no hardcoding, ever)

Resolution order, later overrides earlier: **defaults in `config.py` → `config/*.yaml` → environment variables → CLI flags.** All resolved once into a typed `Settings` object (pydantic-settings) at startup; the rest of the app reads `Settings`, never `os.environ` directly.

| Concern | Lives in | Never in |
| --- | --- | --- |
| API keys, provider selection, active env | `.env` (from `.env.example`) | code, yaml, git |
| Role → model/tier + fallbacks | `config/models.yaml` | agent code |
| Timeouts, retries, cost ceiling, TTLs | `config/settings.yaml` | agent code |
| Run-time overrides (`--input`, `--scenarios`) | CLI flags | hardcoded paths |

`config/models.yaml` shape (illustrative):
```yaml
environment: personal            # personal | work
roles:
  extraction: { tier: fast,     primary: groq:llama-3.1-8b-instant }
  planner:    { tier: mid,      primary: groq:llama-3.3-70b-versatile }
  synthesis:  { tier: strong,   primary: groq:gpt-oss-120b, fallbacks: [aistudio:gemini-2.5-flash] }
  critique:   { tier: reason,   primary: aistudio:gemini-2.5-flash-lite, fallbacks: [groq:deepseek-r1-distill] }
```

---

## 5. Naming & code conventions

| Element | Convention | Example |
| --- | --- | --- |
| Modules / functions | `snake_case` | `cms_coverage.py`, `run_extraction()` |
| Classes | `PascalCase` | `ExtractionAgent`, `PolicyEvidence` |
| Pydantic models | domain noun + role suffix | `*Request`, `*Response`, `*State`, `*Config` |
| Agents | `BaseAgent.run(state) -> state` | uniform, composable |
| Tools | `BaseTool` with `name`, `description`, `run()` | registry-discoverable |
| Prompts | `<role>_system.md`, versioned | `synthesis_system.md` |
| Constants / env | `UPPER_SNAKE` | `CMS_API_BASE_URL` |
| Commits | Conventional Commits | `feat:`, `fix:`, `docs:`, `test:`, `refactor:` |
| Types | full type hints; `mypy`/`pyright` clean | — |
| Docstrings | every public module/class/function | Google or NumPy style, one style repo-wide |

---

## 6. Test strategy (the pyramid)

| Layer | Scope | Doubles | Needs API key? | Tier |
| --- | --- | --- | --- | --- |
| Unit | one function/agent/tool | mock LLM + mock tools | no | P1 |
| Integration | full loop in fixture mode | real code, fixture data | no | P1 |
| Evaluation | 5 scenarios, expected vs actual | fixtures + (optional) live | optional | P0 |
| Golden trace | regression vs `sample_run.json` | committed baseline | no | P1 |

Rule: **CI must be green with no secrets.** Live-provider tests are opt-in via an env flag so the default test run is deterministic and key-less.

---

## 7. Quality gates & tooling

| Gate | Tool | When |
| --- | --- | --- |
| Format + lint | `ruff` | pre-commit / `make lint` |
| Types | `mypy` or `pyright` | `make typecheck` |
| Tests | `pytest` | `make test` |
| Run | `make run INPUT=...` | local demo |
| Eval | `make eval` → `python src/evaluate.py --scenarios tests/scenarios.json` | before submission |
| Container | `docker build` | P1 |
| CI | GitHub Actions (lint+type+test) | P2 |

---

## 8. Portability note (custom orchestrator ↔ framework)

The custom orchestrator is chosen to expose mechanics (ADR-1), but every interface is shaped to be framework-portable:
- `BaseAgent.run(state) -> state` maps directly to a LangGraph node.
- `core/state.py` is the graph state object.
- `tools/registry.py` maps to a framework tool registry.
- `core/router.py` is provider-agnostic and orthogonal to orchestration.

So "we could port to LangGraph if workflow complexity grows" is an honest, one-refactor claim — not a rewrite. That is the point of the structure: **it demonstrates understanding of what frameworks abstract, while staying migration-ready.**

---

*End of `CODEBASE_STRUCTURE_v2.md`.*
