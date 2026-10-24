"""GateFlow AI — Simulation Router

POST /api/simulation/run         — run simulation for a schedule
GET  /api/simulation/{run_id}    — get simulation result
GET  /api/simulation/compare/{run_id} — baseline vs optimized comparison
POST /api/stress/run             — stress test a selected plan
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.models.simulation import (
    ComparisonReport,
    SimulationResult,
    SimulationRunRequest,
    StressTestRequest,
    StressTestResponse,
)
from app.services.simulation_service import (
    get_comparison_report,
    get_simulation_result,
    run_simulation,
)
from app.services.stress_service import run_stress_tests

router = APIRouter(prefix="/api", tags=["simulation"])
logger = logging.getLogger(__name__)


@router.post("/simulation/run", response_model=SimulationResult)
def run_sim(body: SimulationRunRequest):
    """
    Run a deterministic queuing simulation for the given schedule.
    The schedule must have been returned by /api/schedules/search first.

    IMPORTANT: Results are labeled DeterministicEstimate.
    SUMO is not installed. No SUMO metrics are fabricated.
    """
    try:
        result = run_simulation(body)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": str(e),
                    "details": ["Call POST /api/schedules/search to generate and register a schedule."],
                }
            },
        )
    except Exception as e:
        logger.exception("Simulation failed unexpectedly")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "SIMULATION_FAILED",
                    "message": "Simulation encountered an internal error.",
                    "details": [str(e)],
                }
            },
        )


@router.get("/simulation/{run_id}", response_model=SimulationResult)
def get_sim_result(run_id: str):
    """Retrieve a completed simulation result by run ID."""
    result = get_simulation_result(run_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "RUN_NOT_FOUND",
                    "message": f"Simulation run '{run_id}' not found.",
                    "details": [],
                }
            },
        )
    return result


@router.get("/simulation/compare/{run_id}", response_model=ComparisonReport)
def get_comparison(run_id: str):
    """Return the baseline vs. optimized comparison for a completed run."""
    report = get_comparison_report(run_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "RUN_NOT_FOUND",
                    "message": f"Simulation run '{run_id}' not found.",
                    "details": [],
                }
            },
        )
    return report


@router.post("/stress/run", response_model=StressTestResponse)
def run_stress(body: StressTestRequest):
    """
    Run stress tests against the selected schedule.
    Uses the same plan that was submitted to simulation — not independent data.
    """
    try:
        return run_stress_tests(body)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": str(e),
                    "details": [],
                }
            },
        )
