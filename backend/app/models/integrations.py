"""Safe integration status and project-grounded explanation contracts."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProviderStatus(BaseModel):
    configured: bool
    model: str | None = None


class IntegrationStatusResponse(BaseModel):
    openRouter: ProviderStatus


class ExplanationRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    source: Literal["diagnosis", "schedule", "simulation", "stress"] = "diagnosis"
    referenceId: str | None = Field(default=None, max_length=100)


class ExplanationResponse(BaseModel):
    explanation: str
    sources: list[str]
    model: str
    provider: str = "OpenRouter"
    generated: Literal[True] = True
    disclaimer: str = (
        "AI-generated explanation based only on the GateFlow evidence listed. "
        "It does not change deterministic planning or simulation results."
    )
