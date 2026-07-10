# System Diagrams (v2)

**Companion to `SOLUTION_DESIGN_v2.md` and `CODEBASE_STRUCTURE_v2.md`.** A visual walkthrough of the whole system — context, components, the solution story, data flow, and every important behavior (routing, caching, resilience, guardrails, evaluation, deployment). Each diagram has a one-line **What it shows** and a **How to explain it** cue for interviews.

> All diagrams are Mermaid; they render in the companion `Ensemble_Solution_v2.html` and in any Mermaid-aware Markdown viewer.

---

## 1. System context (who talks to what)

**What it shows:** the system as one box and everything it touches — the analyst, the CMS policy source, the LLM providers, and local storage.

```mermaid
flowchart LR
    A["Denials / Appeals Analyst"] -->|"denial letter / EOB"| SYS
    SYS -->|"appeal package or escalation"| A
    subgraph SYS["Claims Appeal Intelligence Agent"]
      direction TB
      CORE["Orchestrated multi-agent pipeline"]
    end
    SYS -->|"policy lookup — NCD open / LCD needs license token"| CMS["CMS Coverage API"]
    CMS -->|"LCD / NCD evidence"| SYS
    SYS <-->|"LLM calls routed by role"| LLM["LLM providers: Frontier | Groq | AI Studio"]
    SYS <-->|"fixtures / cache / memory"| STORE[("Local fixtures + cache + store")]
```

**How to explain it:** "One system, one human, three dependencies. The only mutable external is the CMS API — and I isolated that behind a tool with a fixture fallback, so a network or license-token failure never breaks the demo."

---

## 2. Component / container view (maps 1:1 to the repo)

**What it shows:** the internal modules and how they wire together — this is the codebase structure as a picture.

```mermaid
flowchart TB
    CLI["cli.py"] --> ORCH["core/orchestrator.py<br/>bounded state machine"]
    CFG["config.py + config/*.yaml"] -.-> ORCH
    ORCH --> EXT["agents/extraction"]
    ORCH --> PLN["agents/planner"]
    ORCH --> SYN["agents/synthesis"]
    ORCH --> CRT["agents/critique"]
    EXT --> ROUT["core/router<br/>capability tiers"]
    PLN --> ROUT
    SYN --> ROUT
    CRT --> ROUT
    ROUT --> LLM["llm/*_provider + retry"]
    ORCH --> TOOLS["tools/registry"]
    TOOLS --> CMST["tools/cms_coverage"]
    TOOLS --> FIX["tools/fixture_retrieval"]
    PR["prompts/*.md"] -.-> EXT
    PR -.-> PLN
    PR -.-> SYN
    PR -.-> CRT
    SCH["schemas/io_models"] -.-> ORCH
    EVAL["evaluation/*"] --> ORCH
    subgraph CROSS["Cross-cutting services"]
      CACHE["cache"]
      MEM["memory"]
      GRD["guardrails"]
      OBS["observability<br/>tracer / logger / cost"]
    end
    ORCH -.-> CROSS
```

**How to explain it:** "Strict separation of concerns: orchestration owns control flow, agents only reason, tools only do I/O, and routing/caching/observability are cross-cutting. Every arrow is a real dependency — no empty modules."

---

## 3. Solution flow (the story, end-to-end)

**What it shows:** the happy path as a numbered narrative — the single most useful diagram for explaining the product.

```mermaid
flowchart TB
    U["1 - Denial letter / EOB"] --> V["2 - Validate + normalize + isolate text as data"]
    V --> E["3 - Extract fields (LLM) -> ExtractedClaim"]
    E --> Q{"4 - Required fields present + confident?"}
    Q -- "no" --> ESC["Escalate to human (reason-coded)"]
    Q -- "yes" --> P["5 - Plan retrieval (LLM) -> RetrievalPlan"]
    P --> R["6 - Retrieve policy in parallel (CMS tool)"]
    R --> AG["7 - Aggregate + rank evidence (deterministic)"]
    AG --> S["8 - Draft appeal (LLM) -> AppealDraft (cited)"]
    S --> C{"9 - Critique: faithful + supported?"}
    C -- "gap, 1 revision left" --> S
    C -- "unresolved" --> ESC
    C -- "pass" --> G["10 - Output guardrails: overclaim + citation check"]
    G --> O["11 - Structured appeal package + confidence + trace"]
```

**How to explain it:** "Extract → plan → retrieve → draft → verify → guard. Two exits: a review-ready package, or a reason-coded escalation. The system escalates instead of inventing whenever facts or evidence are missing."

---

## 4. Agent loop as a bounded state machine

**What it shows:** the rubric's reason → plan → act → observe → respond loop, with the guarantee it can't run forever.

```mermaid
stateDiagram-v2
    [*] --> VALIDATE
    VALIDATE --> EXTRACT: input ok
    VALIDATE --> ESCALATE: invalid / empty / oversized
    EXTRACT --> PLAN: fields valid
    EXTRACT --> ESCALATE: missing field / low confidence
    PLAN --> RETRIEVE
    RETRIEVE --> AGGREGATE
    AGGREGATE --> SYNTHESIZE
    SYNTHESIZE --> CRITIQUE
    CRITIQUE --> SYNTHESIZE: gap AND revisions_used < 1
    CRITIQUE --> GUARD: passed
    CRITIQUE --> ESCALATE: gap AND revisions_used == 1
    GUARD --> RESPOND: clean
    GUARD --> ESCALATE: overclaim / citation failure
    RESPOND --> [*]
    ESCALATE --> [*]
```

**How to explain it:** "Every transition moves forward except one back-edge — critique → synthesis — bounded to a single revision. A global step ceiling and per-call timeouts are backstops. No infinite loops by construction."

---

## 5. Sequence of one run (with cache + fallback)

**What it shows:** the runtime call order, including a cache check and the CMS → fixture fallback.

```mermaid
sequenceDiagram
    autonumber
    actor An as Analyst
    participant O as Orchestrator
    participant E as Extraction
    participant P as Planner
    participant Ca as Cache
    participant T as CMS Tool
    participant F as Fixtures
    participant S as Synthesis
    participant C as Critique
    An->>O: denial letter
    O->>E: normalized text
    E-->>O: ExtractedClaim
    O->>P: ExtractedClaim
    P-->>O: RetrievalPlan
    O->>Ca: lookup(policy query)
    alt cache hit
        Ca-->>O: PolicyEvidence (cached)
    else cache miss
        O->>T: query(code)
        alt API + token ok
            T-->>O: PolicyEvidence
        else API / token fails
            O->>F: fixture lookup
            F-->>O: PolicyEvidence (fixture)
        end
        O->>Ca: store (TTL)
    end
    O->>S: claim + aggregated evidence
    S-->>O: AppealDraft
    O->>C: draft + claim + evidence
    C-->>O: CritiqueResult
    O-->>An: appeal package / escalation
```

**How to explain it:** "Retrieval is cache-first and failure-tolerant: cache hit → reuse; miss → live CMS; live failure → deterministic fixtures. The trace records which path served each call."

---

## 6. Data flow — typed contracts (what moves between stages)

**What it shows:** the Pydantic contracts and how each one relates to the next. Typed boundaries = observable failures.

```mermaid
erDiagram
    EXTRACTED_CLAIM ||--o{ RETRIEVAL_QUERY : "drives"
    RETRIEVAL_QUERY ||--o{ POLICY_EVIDENCE : "returns"
    EXTRACTED_CLAIM ||--|| APPEAL_DRAFT : "grounds"
    POLICY_EVIDENCE ||--o{ APPEAL_DRAFT : "cited by"
    APPEAL_DRAFT ||--|| CRITIQUE_RESULT : "verified by"
    EXTRACTED_CLAIM {
      string claim_id
      string payer
      list procedure_codes
      list diagnosis_codes
      string denial_reason
      list missing_fields
      float confidence
    }
    POLICY_EVIDENCE {
      string source_id
      string source_type
      string relevance
      string url
    }
    APPEAL_DRAFT {
      string summary
      list appeal_arguments
      list evidence_references
      list limitations
    }
    CRITIQUE_RESULT {
      bool passed
      list unsupported_claims
      bool escalation_required
    }
```

**Contract pipeline (linear view):**

```mermaid
flowchart LR
    T["raw text"] --> EC["ExtractedClaim"]
    EC --> RP["RetrievalPlan"]
    RP --> PE["PolicyEvidence[]"]
    PE --> AD["AppealDraft"]
    AD --> CR["CritiqueResult"]
    CR --> FP["Final envelope<br/>status + confidence + flags"]
```

**How to explain it:** "Every handoff is a validated Pydantic object, not free text. If a boundary breaks, the trace shows exactly which contract failed and why."

---

## 7. Purpose-based model routing (dual environment + fallback)

**What it shows:** how one agent role resolves to an actual model — work vs personal laptop — and degrades gracefully.

```mermaid
flowchart TB
    RQ["Agent role needs an LLM call"] --> RL["router: role -> capability tier"]
    RL --> ENV{"environment (config)"}
    ENV -- "work" --> WF["Frontier-tier model"]
    ENV -- "personal" --> PF["Free-tier model (Groq / AI Studio)"]
    WF --> CALL["provider call"]
    PF --> CALL
    CALL --> OK{"ok?"}
    OK -- "429 / timeout" --> FB["next in fallback chain"]
    FB --> CALL
    OK -- "yes" --> LAD{"schema valid?"}
    LAD -- "yes" --> DONE["return"]
    LAD -- "no" --> REP["1 repair retry"]
    REP --> SAFE["else safe templated + low-confidence flag"]
```

**How to explain it:** "Roles map to capability tiers, not hard model names. Switching my work laptop's frontier models for free-tier open models at home is a one-line config edit — plus a fallback chain and a structured-output degrade ladder."

---

## 8. Caching & memory (why it's reliability, not just cost)

**What it shows:** the cache lookup order and the three memory layers.

```mermaid
flowchart TB
    REQ["step needs data (LLM or tool)"] --> EX{"exact-match cache?"}
    EX -- "hit" --> RET["return cached (log cache=hit)"]
    EX -- "miss" --> TC{"tool-result cache? (policy query)"}
    TC -- "hit" --> RET
    TC -- "miss" --> DO["execute call"]
    DO --> ST["store in cache (TTL)"]
    ST --> RET
    subgraph MEM["Memory layers"]
      WM["working: AgentState (in-run)"]
      SM["session store (P1)"]
      LT["long-term policy store (P1)"]
    end
    DO -.-> LT
```

**How to explain it:** "Free-tier daily request caps (RPD) are the binding limit, so caching is what keeps the demo runnable at all — not a nice-to-have. Every cache hit is logged so reviewers can tell fresh calls from reuse."

---

## 9. Error handling & resilience

**What it shows:** the failure ladder — timeout, bounded retry, circuit breaker, fallback, safe terminal.

```mermaid
flowchart TB
    C["provider / tool call"] --> TO{"timeout?"}
    TO -- "yes" --> RT["retry: backoff + jitter (bounded)"]
    TO -- "no" --> ER{"error?"}
    ER -- "transient" --> RT
    ER -- "none" --> OKK["success"]
    RT --> CB{"repeated failures?"}
    CB -- "yes (circuit open, P1)" --> FBK["fallback: fixtures / cached / smaller model"]
    CB -- "no" --> C
    FBK --> TERM{"recoverable?"}
    TERM -- "yes" --> OKK
    TERM -- "no" --> SAFE["failed_safely terminal + trace"]
```

**How to explain it:** "Nothing hangs, nothing loops, nothing crashes silently. Every failure resolves to success, a safe fallback, or a clearly-traced `failed_safely` state."

---

## 10. Guardrails & threat mitigation

**What it shows:** how untrusted input and evidence are contained, and how the output is checked before release.

```mermaid
flowchart TB
    IN["denial-letter text"] --> ISO["isolate as DATA (delimited)"]
    ISO --> ICHK["input checks: length / type / empty + injection patterns"]
    ICHK --> PIPE["agents run; evidence treated as quoted data, never obeyed"]
    PIPE --> OG["output guardrails"]
    OG --> OC{"overclaim / certainty language?"}
    OC -- "yes" --> ESC["strip + escalate"]
    OC -- "no" --> CIT{"every claim cites a real source_id?"}
    CIT -- "no" --> ESC
    CIT -- "yes" --> PASS["release package"]
```

**How to explain it:** "Two trust boundaries: input (the letter) and tool output (retrieved policy) are both treated as data, never instructions. On the way out, I block overconfident claims and unsourced statements — the actual job in a healthcare workflow."

---

## 11. Evaluation flow (measured, not proposed)

**What it shows:** how scenarios turn into a results table, plus the optional judge and golden-trace regression.

```mermaid
flowchart TB
    FX["fixtures: letters + known-answer ground truth"] --> EVAL["evaluator.py runs 5 scenarios"]
    EVAL --> DET["deterministic metrics:<br/>schema / completeness / faithfulness / guardrail"]
    DET --> RUB["rubric: pass/fail per scenario"]
    RUB --> JUDGE{"LLM judge? (P1, different family)"}
    JUDGE -- "advisory only" --> REP["results table: expected vs actual"]
    DET --> REP
    GOLD["golden trace baseline"] --> REG["regression vs sample_run.json"]
    REG --> REP
```

**How to explain it:** "Deterministic checks are authoritative; the LLM judge is advisory and uses a different model family to avoid self-grading bias. Golden traces catch regressions between runs."

---

## 12. Deployment & production roadmap

**What it shows:** what's built now vs the credible path to production (stated, not built — signals forward thinking).

```mermaid
flowchart LR
    subgraph NOW["Now (assessment scope)"]
      direction TB
      L1["CLI + fixtures"]
      L2["Docker (P1)"]
      L3["JSON traces + cost table"]
    end
    subgraph PROD["Production roadmap (described only)"]
      direction TB
      R1["OpenTelemetry -> Langfuse / Phoenix"]
      R2["Vector store for policy corpus"]
      R3["Human-in-the-loop review queue"]
      R4["Prompt-version A/B + red-team suite"]
    end
    NOW ==> PROD
```

**How to explain it:** "The lightweight tracer is OTel-shaped on purpose, so the jump to Langfuse/Phoenix is a config change, not a rewrite. I named the production path without over-building it into a take-home."

---

## Diagram index (what to show when)

| # | Diagram | Best used to explain |
| --- | --- | --- |
| 1 | System context | scope + dependency isolation |
| 2 | Component view | code organization / separation of concerns |
| 3 | Solution flow | the product story (start here in an interview) |
| 4 | State machine | termination guarantees / the agent loop |
| 5 | Sequence | runtime order, cache + fallback |
| 6 | Data flow / contracts | typed boundaries, structured outputs |
| 7 | Model routing | dual-environment + purpose-based invocation |
| 8 | Caching & memory | cost + reliability under free tiers |
| 9 | Resilience | error awareness / graceful failure |
| 10 | Guardrails | safety / injection / overclaim |
| 11 | Evaluation | measured results + anti-bias judging |
| 12 | Deployment | production maturity / roadmap |

*End of `DIAGRAMS_v2.md`.*
