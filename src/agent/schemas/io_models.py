from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class ExtractedClaim(BaseModel):
    claim_id: str | None = None
    payer: str | None = None
    procedure_codes: list[str] = Field(default_factory=list)
    diagnosis_codes: list[str] = Field(default_factory=list)
    denial_reason: str | None = None
    service_dates: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class RetrievalPlan(BaseModel):
    queries: list[dict[str, Any]] = Field(default_factory=list)
    escalate_before_draft: bool = False


class PolicyEvidence(BaseModel):
    source_id: str
    source_type: str
    title: str
    excerpt: str
    relevance: str
    retrieval_query: dict[str, Any]
    url: str


class AppealDraft(BaseModel):
    summary: str
    appeal_arguments: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    passed: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    revision_instructions: list[str] = Field(default_factory=list)
    escalation_required: bool = False
