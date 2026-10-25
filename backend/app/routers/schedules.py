"""GateFlow AI — Constraints & Schedule Router

POST /api/constraints/parse      — NL → structured constraints (deterministic)
POST /api/schedules/search       — search for feasible schedules
GET  /api/schedules/{id}         — retrieve a specific candidate
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.routers.schools import require_traffic_admin
from app.models.schedule import (
    ConstraintParseRequest,
    ConstraintValidationResult,
    ScheduleCandidate,
    ScheduleSearchRequest,
    ScheduleSearchResponse,
)
from app.services.ai_service import parse_constraints_deterministic
from app.services.constraint_service import validate_constraints
from app.services.planning_service import search_schedules
from app.services.simulation_service import register_schedule

router = APIRouter(prefix="/api", tags=["planning"])
logger = logging.getLogger(__name__)

# In-memory candidate store for retrieval by ID
_candidate_store: dict[str, ScheduleCandidate] = {}


@router.post("/constraints/parse", response_model=ConstraintValidationResult, dependencies=[Depends(require_traffic_admin)])
def parse_constraints(body: ConstraintParseRequest):
    """
    Parse a natural-language optimization request into structured constraints.
    Uses deterministic rule-based parsing (no external AI calls).

    Pipeline:
        USER PROMPT
            ↓ deterministic regex parser (ai_service)
            ↓ Pydantic validation
            ↓ canonical scenario validation (constraint_service)
            ↓ ConstraintValidationResult
    """
    logger.info(f"Parsing constraint prompt: '{body.prompt[:80]}...'")
    # Step 1: deterministic parse
    parsed = parse_constraints_deterministic(body.prompt)
    if not parsed.valid or parsed.constraints is None:
        # Parser itself found contradictions — return without further validation
        return parsed
    # Step 2: canonical scenario validation
    validated = validate_constraints(parsed.constraints)
    logger.info(
        f"Constraint validation result: valid={validated.valid}, "
        f"errors={validated.errors}, warnings={validated.warnings}"
    )
    return validated


@router.post("/schedules/search", response_model=ScheduleSearchResponse, dependencies=[Depends(require_traffic_admin)])
def search_schedule(body: ScheduleSearchRequest):
    """
    Search for feasible schedules given validated constraints.
    Returns real computed candidates — not pre-written responses.
    """
    # Re-validate constraints at this boundary
    validated = validate_constraints(body.constraints)
    if not validated.valid:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INVALID_CONSTRAINTS",
                    "message": "Constraints failed validation and cannot be sent to the planner.",
                    "details": validated.errors,
                }
            },
        )

    logger.info(
        f"Starting schedule search — objective={body.constraints.optimizationObjective}, "
        f"demand={body.constraints.demandFactor:.2f}x, "
        f"fixed={body.constraints.fixedGroups}, "
        f"sibling_sync={body.constraints.siblingSync}"
    )
    result = search_schedules(body)

    if not result.candidates:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INFEASIBLE_PLAN",
                    "message": "No feasible schedule was found under the provided constraints.",
                    "details": [result.searchExplanation],
                }
            },
        )

    # Register all returned candidates for future simulation calls
    for candidate in result.candidates:
        _candidate_store[candidate.id] = candidate
        register_schedule(candidate)
        logger.info(f"Registered candidate '{candidate.id}' for simulation.")

    return result


@router.get("/schedules/{schedule_id}", response_model=ScheduleCandidate, dependencies=[Depends(require_traffic_admin)])
def get_schedule(schedule_id: str):
    """Retrieve a specific schedule candidate by ID."""
    candidate = _candidate_store.get(schedule_id)
    if not candidate:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": f"Schedule '{schedule_id}' not found. Run /api/schedules/search first.",
                    "details": [],
                }
            },
        )
    return candidate
