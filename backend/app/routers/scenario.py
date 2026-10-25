"""GateFlow AI — Scenario Router
GET /api/scenario — full scenario
GET /api/scenario/gates — gate list
GET /api/scenario/cohorts — cohort list
GET /api/scenario/metrics — traffic metrics
GET /api/scenario/driver — driver assignment
POST /api/reset — reset in-memory state
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.models.school import (
    DemandCohort,
    DriverAssignment,
    GateInfo,
    ScenarioResponse,
    TrafficMetric,
)
from app.services.data_service import (
    get_driver_assignment,
    get_scenario,
    reset_scenario,
)
from app.services.simulation_service import reset_simulations
from app.routers.auth import require_admin
from app.routers.schools import require_school_admin, require_traffic_admin

router = APIRouter(prefix="/api", tags=["scenario"])
logger = logging.getLogger(__name__)


@router.get("/scenario", response_model=ScenarioResponse, dependencies=[Depends(require_traffic_admin)])
def get_full_scenario():
    """Return the full synthetic school scenario."""
    return get_scenario()


@router.get("/scenario/gates", response_model=list[GateInfo], dependencies=[Depends(require_traffic_admin)])
def get_gates():
    return get_scenario().gates


@router.get("/scenario/cohorts", response_model=list[DemandCohort], dependencies=[Depends(require_traffic_admin)])
def get_cohorts():
    return get_scenario().cohorts


@router.get("/scenario/metrics", response_model=list[TrafficMetric], dependencies=[Depends(require_traffic_admin)])
def get_metrics():
    return get_scenario().trafficMetrics


@router.get("/scenario/driver", response_model=DriverAssignment, dependencies=[Depends(require_traffic_admin)])
def get_driver():
    """Return the synthetic driver assignment for the Driver Dashboard."""
    return get_driver_assignment()


@router.post("/reset", dependencies=[Depends(require_traffic_admin)])
def reset_demo():
    """
    Reset all in-memory state to the canonical synthetic scenario.
    Clears scenario cache, simulation cache, and schedule store.
    """
    reset_scenario()
    reset_simulations()
    logger.info("Demo state reset to canonical synthetic scenario.")
    return {"status": "reset", "message": "Scenario and simulations reset to synthetic baseline."}
