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
        self.logger.info("starting orchestrator run")

        span = self.tracer.start_span("extraction")
        state = self.extraction.run(state)
        span.finish()
        if state.extracted_claim is None or state.extracted_claim.confidence < 0.5:
            state.escalation_reason = "Extraction failed or confidence too low"
            self.logger.info("escalation: extraction failure")
            state.metadata["trace"] = self.tracer.get_trace()
            return state

        span = self.tracer.start_span("planning")
        state = self.planner.run(state)
        span.finish()
        if state.retrieval_plan is None or state.retrieval_plan.escalate_before_draft:
            state.escalation_reason = "Planning determined escalation"
            self.logger.info("escalation: planning required")
            state.metadata["trace"] = self.tracer.get_trace()
            return state

        span = self.tracer.start_span("retrieval")
        state = self._retrieve_policy_evidence(state)
        span.finish()

        span = self.tracer.start_span("synthesis")
        state = self.synthesis.run(state)
        span.finish()
        try:
            validate_appeal_draft(state.appeal_draft, [item.source_id for item in state.policy_evidence])
        except ValueError as exc:
            state.escalation_reason = f"Output guardrail failed: {exc}"
            self.logger.info("escalation: output guardrail failure")
            state.metadata["trace"] = self.tracer.get_trace()
            return state

        span = self.tracer.start_span("critique")
        state = self.critique.run(state)
        span.finish()

        if state.critique_result is None or state.critique_result.escalation_required:
            state.escalation_reason = "Critique failed or escalation required"
            self.logger.info("escalation: critique required")
            state.metadata["trace"] = self.tracer.get_trace()
            return state

        state.metadata["trace"] = self.tracer.get_trace()
        state.metadata["cost"] = self.cost_tracker.summary()
        self.logger.info("orchestrator run complete")
        return state

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
