"""Project-grounded, optional explanation calls to OpenRouter."""
from __future__ import annotations

import json
import logging

import httpx

from app.config import settings
from app.models.integrations import ExplanationRequest
from app.services.diagnosis_service import compute_diagnosis
from app.services.simulation_service import get_registered_schedule, get_simulation_result
from app.services.stress_service import run_stress_tests
from app.models.simulation import StressTestRequest

logger = logging.getLogger(__name__)


class ExplanationUnavailable(RuntimeError):
    """The optional explanation provider is not configured or failed."""


def build_project_evidence(request: ExplanationRequest) -> tuple[dict, list[str]]:
    """Resolve only known GateFlow records; never accept free-form client context."""
    if request.source == "diagnosis":
        diagnosis = compute_diagnosis()
        return diagnosis.model_dump(mode="json"), ["GateFlow diagnosis"]

    if not request.referenceId:
        raise ValueError(f"A referenceId is required for {request.source} explanations.")

    if request.source == "schedule":
        schedule = get_registered_schedule(request.referenceId)
        if not schedule:
            raise LookupError("The requested GateFlow schedule was not found.")
        return schedule.model_dump(mode="json"), [
            f"Schedule candidate {schedule.id}",
            "Deterministic planner gate loads and capacities",
        ]

    if request.source == "simulation":
        result = get_simulation_result(request.referenceId)
        if not result:
            raise LookupError("The requested GateFlow simulation was not found.")
        return {
            "candidateName": result.candidateName,
            "simulationMethod": result.simulationMethod,
            "metrics": result.metrics.model_dump(mode="json"),
            "improvements": result.improvements,
            "remainingRisks": result.remainingRisks,
        }, [
            f"Deterministic simulation run {result.runId}",
            "Baseline-versus-candidate metrics",
        ]

    if request.source == "stress":
        stress = run_stress_tests(StressTestRequest(scheduleId=request.referenceId))
        return stress.model_dump(mode="json"), [
            f"Deterministic stress test for schedule {stress.scheduleId}",
            "Configured demand, dwell, and compliance scenarios",
        ]

    raise ValueError("Unsupported explanation source.")


def explain_with_openrouter(request: ExplanationRequest) -> tuple[str, list[str]]:
    if not settings.openrouter_api_key.strip():
        raise ExplanationUnavailable(
            "OpenRouter is not configured. Set OPENROUTER_API_KEY on the backend."
        )

    evidence, sources = build_project_evidence(request)
    system_message = (
        "You are GateFlow's evidence explainer. Answer only from the JSON "
        "GateFlow evidence supplied by the application. Do not use web search, "
        "outside facts, assumptions, or general traffic knowledge. Do not alter "
        "or invent metrics, gate capacities, school facts, safety rules, or "
        "recommendations. If the evidence does not answer the question, say so "
        "plainly. Explain the result in clear language and identify the supplied "
        "GateFlow evidence labels that support your explanation. Your response "
        "is an explanation, not an operational decision."
    )
    user_content = json.dumps(
        {
            "question": request.question,
            "available_evidence_labels": sources,
            "gateflow_evidence": evidence,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    endpoint = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.openrouter_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content},
        ],
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(endpoint, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        explanation = data["choices"][0]["message"]["content"]
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("OpenRouter explanation request failed: %s", type(exc).__name__)
        raise ExplanationUnavailable(
            "The OpenRouter explanation service is unavailable or returned an invalid response."
        ) from exc

    if not isinstance(explanation, str) or not explanation.strip():
        raise ExplanationUnavailable(
            "The OpenRouter explanation service returned an empty response."
        )
    return explanation.strip()[:8000], sources
