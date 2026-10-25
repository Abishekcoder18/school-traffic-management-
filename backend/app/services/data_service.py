"""GateFlow AI — Data Service
Loads and caches the canonical synthetic scenario from scenario.json.
This is the single source of truth for all backend computations.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models.school import (
    DemandCohort,
    DriverAssignment,
    DriverNotice,
    GateInfo,
    School,
    ScenarioResponse,
    SiblingGroup,
    TrafficMetric,
)

logger = logging.getLogger(__name__)


def _load_raw() -> dict:
    path = settings.scenario_data_path
    if not path.exists():
        # Try relative to this file's parent (common dev scenario)
        alt = Path(__file__).parent.parent.parent / "data" / "scenario.json"
        if alt.exists():
            path = alt
        else:
            raise FileNotFoundError(
                f"Scenario data not found at {path}. "
                "Ensure data/scenario.json exists and SCENARIO_DATA_PATH is set correctly."
            )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_scenario() -> ScenarioResponse:
    """Load and cache the full scenario. Call `get_scenario.cache_clear()` on reset."""
    raw = _load_raw()

    school = School(**raw["school"])
    gates = [GateInfo(**g) for g in raw["gates"]]
    cohorts = [DemandCohort(**c) for c in raw["cohorts"]]
    sibling_groups = [SiblingGroup(**sg) for sg in raw["siblingGroups"]]
    metrics = [TrafficMetric(**m) for m in raw["trafficMetrics"]]

    return ScenarioResponse(
        school=school,
        gates=gates,
        cohorts=cohorts,
        siblingGroups=sibling_groups,
        trafficMetrics=metrics,
    )


def get_driver_assignment() -> DriverAssignment:
    """Return the default driver assignment (synthetic demo data)."""
    raw = _load_raw()
    da = raw["driverAssignment"]
    today = datetime.now()
    today_str = f"Today, {today.strftime('%b')} {today.day}, {today.year}"
    return DriverAssignment(
        driverName=da["driverName"],
        driverId=da["driverId"],
        studentName=da["studentName"],
        grade=da["grade"],
        vehiclePlate=da["vehiclePlate"],
        scheduleTitle=da["scheduleTitle"],
        date=today_str,
        arrivalWindow=da["arrivalWindow"],
        officialSlot=da["officialSlot"],
        gateName=da["gateName"],
        gateNumber=da["gateNumber"],
        pickupZone=da["pickupZone"],
        bayNumber=da["bayNumber"],
        laneColor=da["laneColor"],
        routeInstructions=da["routeInstructions"],
        approachStreet=da["approachStreet"],
        queueStatus=da["queueStatus"],
        assignmentStatus=da["assignmentStatus"],
        hasCheckedIn=False,
        instructions=da["instructions"],
        notices=[DriverNotice(**n) for n in da["notices"]],
    )


def reset_scenario() -> None:
    """Clear the cache so scenario is reloaded from disk on next call."""
    get_scenario.cache_clear()
    logger.info("Scenario cache cleared — will reload from disk on next request.")
