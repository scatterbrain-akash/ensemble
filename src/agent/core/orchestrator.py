from __future__ import annotations

from src.agent.config import Settings
from src.agent.core.router import ModelRouter
from src.agent.core.state import AgentState
from src.agent.guardrails.input_guard import validate_input_text
from src.agent.guardrails.output_guard import validate_appeal_draft
from src.agent.agents.extraction import ExtractionAgent
from src.agent.agents.planner import PlannerAgent
from src.agent.agents.synthesis import SynthesisAgent
from src.agent.agents.critique import CritiqueAgent
from src.agent.schemas.io_models import PolicyEvidence
from src.agent.tools.registry import load_tool
from src.agent.observability.cost_tracker import CostTracker
from src.agent.observability.tracer import Tracer
from src.agent.observability.logger import get_logger
from src.agent.cache.cache_service import CacheService


class Orchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)
        self.tracer = Tracer()
        self.cost_tracker = CostTracker()
        self.cache = CacheService(settings=settings)
        self.model_router = ModelRouter(settings=settings)
        self.extraction = ExtractionAgent(
            settings=settings, model_router=self.model_router, cache_service=self.cache, cost_tracker=self.cost_tracker
        )
        self.planner = PlannerAgent(
            settings=settings, model_router=self.model_router, cache_service=self.cache, cost_tracker=self.cost_tracker
        )
        self.synthesis = SynthesisAgent(
            settings=settings, model_router=self.model_router, cache_service=self.cache, cost_tracker=self.cost_tracker
        )
        self.critique = CritiqueAgent(
            settings=settings, model_router=self.model_router, cache_service=self.cache, cost_tracker=self.cost_tracker
        )
        self.cms_tool = load_tool("cms_coverage", settings=settings)
        self.fixture_tool = load_tool("fixture_retrieval")

    def run(self, input_text: str) -> AgentState:
        validate_input_text(input_text)
        state = AgentState(input_text=input_text)
        self._step_cost_snapshots = []
        self._previous_cost_snapshot = self.cost_tracker.snapshot()
        self.logger.info("starting orchestrator run")

        span = self.tracer.start_span("extraction")
        state = self.extraction.run(state)
        span.finish()
        self._capture_step_metrics("extraction")
        if state.extracted_claim is None or state.extracted_claim.confidence < 0.5:
            state.escalation_reason = "Extraction failed or confidence too low"
            self.logger.info("escalation: extraction failure")
            return self._finalize_state(state)

        span = self.tracer.start_span("planning")
        state = self.planner.run(state)
        span.finish()
        self._capture_step_metrics("planning")
        if state.retrieval_plan is None or state.retrieval_plan.escalate_before_draft:
            state.escalation_reason = "Planning determined escalation"
            self.logger.info("escalation: planning required")
            return self._finalize_state(state)

        span = self.tracer.start_span("retrieval")
        state = self._retrieve_policy_evidence(state)
        span.finish()
        self._capture_step_metrics("retrieval")

        span = self.tracer.start_span("synthesis")
        state = self.synthesis.run(state)
        span.finish()
        self._capture_step_metrics("synthesis")
        try:
            validate_appeal_draft(state.appeal_draft, [item.source_id for item in state.policy_evidence])
        except ValueError as exc:
            state.escalation_reason = f"Output guardrail failed: {exc}"
            self.logger.info("escalation: output guardrail failure")
            return self._finalize_state(state)

        span = self.tracer.start_span("critique")
        state = self.critique.run(state)
        span.finish()
        self._capture_step_metrics("critique")

        if state.critique_result is None or state.critique_result.escalation_required:
            state.escalation_reason = "Critique failed or escalation required"
            self.logger.info("escalation: critique required")
            return self._finalize_state(state)

        state.metadata["cost"] = self.cost_tracker.summary()
        self.logger.info("orchestrator run complete")
        return self._finalize_state(state)

    def _capture_step_metrics(self, step_name: str) -> None:
        current = self.cost_tracker.snapshot()
        snapshot = {
            "step": step_name,
            "llm_calls": current["llm_calls"] - self._previous_cost_snapshot["llm_calls"],
            "cache_hits": current["cache_hits"] - self._previous_cost_snapshot["cache_hits"],
            "tokens_in": current["tokens_in"] - self._previous_cost_snapshot["tokens_in"],
            "tokens_out": current["tokens_out"] - self._previous_cost_snapshot["tokens_out"],
            "cost_usd": round(current["est_cost_usd"] - self._previous_cost_snapshot["est_cost_usd"], 8),
        }
        self._step_cost_snapshots.append(snapshot)
        self._previous_cost_snapshot = current

    def _finalize_state(self, state: AgentState) -> AgentState:
        state.metadata["trace"] = self.tracer.get_trace()
        state.metadata["execution_summary"] = self._build_execution_summary(state)
        return state

    def _build_execution_summary(self, state: AgentState) -> dict[str, object]:
        trace_map = {span["name"]: span for span in self.tracer.get_trace()}
        metrics_map = {metric["step"]: metric for metric in self._step_cost_snapshots}

        def span_duration(name: str) -> float:
            span = trace_map.get(name)
            return span["duration"] or 0.0 if span else 0.0

        def step_metric(name: str) -> dict[str, object]:
            return metrics_map.get(name, {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "llm_calls": 0, "cache_hits": 0})

        extraction_ok = state.extracted_claim is not None and state.extracted_claim.confidence >= 0.5
        planning_ok = state.retrieval_plan is not None and not state.retrieval_plan.escalate_before_draft
        retrieval_executed = "retrieval" in trace_map
        retrieval_ok = retrieval_executed and bool(state.policy_evidence)
        synthesis_executed = "synthesis" in trace_map
        synthesis_ok = synthesis_executed and state.appeal_draft is not None
        critique_executed = "critique" in trace_map
        critique_ok = critique_executed and state.critique_result is not None and not state.critique_result.escalation_required

        steps = [
            {
                **step_metric("extraction"),
                "step": "extraction",
                "status": "completed" if extraction_ok else "failed",
                "duration": span_duration("extraction"),
                "result": "claim data extracted" if extraction_ok else "failed to extract or low confidence",
            },
            {
                **step_metric("planning"),
                "step": "planning",
                "status": "completed" if planning_ok else ("escalated" if state.retrieval_plan is not None else "failed"),
                "duration": span_duration("planning"),
                "result": (
                    f"generated {len(state.retrieval_plan.queries)} query(s)"
                    if state.retrieval_plan and not state.retrieval_plan.escalate_before_draft
                    else "escalation required before retrieval"
                ),
            },
            {
                **step_metric("retrieval"),
                "step": "retrieval",
                "status": "completed" if retrieval_ok else ("skipped" if not retrieval_executed else "no_evidence"),
                "duration": span_duration("retrieval"),
                "result": (
                    f"retrieved {len(state.policy_evidence)} evidence item(s)"
                    if retrieval_executed
                    else "not executed"
                ),
            },
            {
                **step_metric("synthesis"),
                "step": "synthesis",
                "status": "completed" if synthesis_ok else ("skipped" if not synthesis_executed else "failed"),
                "duration": span_duration("synthesis"),
                "result": "appeal draft generated" if synthesis_ok else "not generated",
            },
            {
                **step_metric("critique"),
                "step": "critique",
                "status": "completed" if critique_ok else ("skipped" if not critique_executed else "escalated"),
                "duration": span_duration("critique"),
                "result": "critique passed" if critique_ok else "critique failed or escalation required",
            },
        ]

        overall_status = "completed" if all(step["status"] == "completed" for step in steps) else "escalated"
        total_cost = self.cost_tracker.summary().get("est_cost_usd", 0.0)
        total_tokens_in = self.cost_tracker.summary().get("tokens_in", 0)
        total_tokens_out = self.cost_tracker.summary().get("tokens_out", 0)
        return {
            "overall_status": overall_status,
            "escalation_reason": state.escalation_reason,
            "steps": steps,
            "input_length": len(state.input_text) if state.input_text else 0,
            "total_llm_calls": self.cost_tracker.summary().get("llm_calls", 0),
            "total_cache_hits": self.cost_tracker.summary().get("cache_hits", 0),
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_cost_usd": total_cost,
        }

    def _retrieve_policy_evidence(self, state: AgentState) -> AgentState:
        state.policy_evidence = []
        for query in state.retrieval_plan.queries:
            # Tool-result cache key
            cache_key = f"tool:cms:{query.get('policy_type')}:{query.get('code')}"
            evidence_data = self.cache.get(cache_key) if self.cache else None
            if evidence_data is None:
                evidence_data = self.cms_tool.run(query)
                self.cost_tracker.record_tool_call()
                if not evidence_data:
                    self.logger.info("cms_tool returned no evidence, falling back to fixture retrieval")
                    evidence_data = self.fixture_tool.run(query)
                    self.cost_tracker.record_tool_call()
                # store successful findings in cache
                try:
                    ttl = int(self.settings.cache.get("policy_ttl_seconds", 3600))
                    if evidence_data:
                        self.cache.set(cache_key, evidence_data, ttl)
                except Exception:
                    pass
            else:
                # cache hit
                pass
            for item in evidence_data:
                state.policy_evidence.append(PolicyEvidence(**item))
        return state
