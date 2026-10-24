"""GateFlow AI — Stress Testing Service

Applies scenario perturbations to the selected schedule and
evaluates fragility under demand surges, dwell increases, and
compliance failures.

All results are labeled DeterministicEstimate.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.models.simulation import (
    StressScenarioResult,
    StressTestRequest,
    StressTestResponse,
)
from app.services.data_service import get_scenario
from app.services.simulation_service import _simulate_queue_timeseries, get_registered_schedule

logger = logging.getLogger(__name__)

# Stress scenarios: each is a perturbation of the selected schedule
STRESS_SCENARIO_DEFINITIONS = [
    {
        "id": "normal",
        "name": "Normal Demand",
        "demandFactor": 1.0,
        "dwellFactor": 1.0,
        "complianceRate": 1.0,
        "description": "Baseline synthetic demand with full schedule compliance.",
    },
    {
        "id": "demand-surge-20",
        "name": "+20% Demand Surge",
        "demandFactor": 1.20,
        "dwellFactor": 1.0,
        "complianceRate": 1.0,
        "description": "20% more vehicles than baseline (e.g., event day, sibling pickup).",
    },
    {
        "id": "demand-surge-30",
        "name": "+30% Demand Surge",
        "demandFactor": 1.30,
        "dwellFactor": 1.0,
        "complianceRate": 1.0,
        "description": "30% demand increase — tests planner's pre-set demand factor.",
    },
    {
        "id": "extended-dwell",
        "name": "Extended Dwell Time (+50%)",
        "demandFactor": 1.0,
        "dwellFactor": 1.50,
        "complianceRate": 1.0,
        "description": "Dwell time 50% longer (adverse weather, injured student, school bags).",
    },
    {
        "id": "low-compliance",
        "name": "Reduced Schedule Compliance (80%)",
        "demandFactor": 1.0,
        "dwellFactor": 1.0,
        "complianceRate": 0.80,
        "description": "20% of drivers arrive outside their assigned window — common on first days.",
    },
    {
        "id": "rainy-day",
        "name": "Rainy Day Sensitivity",
        "demandFactor": 1.10,
        "dwellFactor": 1.30,
        "complianceRate": 0.90,
        "description": "Combined: +10% vehicles, +30% dwell, 90% compliance (covered bay protocol).",
    },
]


def run_stress_tests(request: StressTestRequest) -> StressTestResponse:
    """
    Run all stress scenarios against the selected plan.
    The plan MUST be registered in simulation_service first.
    """
    schedule = get_registered_schedule(request.scheduleId)
    if not schedule:
        raise ValueError(
            f"Schedule '{request.scheduleId}' not found. "
            "Submit via POST /api/schedules/search first."
        )

    scenario = get_scenario()
    cohorts = scenario.cohorts
    gates_by_id = {g.id: g for g in scenario.gates}
    base_dwell = scenario.school.averageDwellTimeSeconds
    threshold = scenario.school.vehicleCapacityThreshold

    # Extract offsets from the selected plan
    offsets_by_cohort_id: dict[str, int] = {}
    for row in schedule.groupSchedule:
        offsets_by_cohort_id[row.cohortId] = row.offsetMinutes

    results: list[StressScenarioResult] = []

    for defn in STRESS_SCENARIO_DEFINITIONS:
        demand_factor = defn["demandFactor"]
        dwell_factor = defn["dwellFactor"]
        compliance = defn["complianceRate"]
        effective_dwell = base_dwell * dwell_factor

        # Compliance failure: late arrivals spread demand over a wider window
        # We model this by increasing effective demand factor slightly
        effective_demand = demand_factor * (1.0 + (1.0 - compliance) * 0.2)

        _, metrics = _simulate_queue_timeseries(
            cohorts,
            offsets_by_cohort_id,
            gates_by_id,
            effective_demand,
            effective_dwell,
        )

        peak_q = metrics["peak_queue"]
        p95_wait = metrics["p95_wait_min"]
        worst_q = peak_q * 1.15  # 15% headroom for stochastic variance

        is_fragile = peak_q > threshold
        if peak_q > threshold * 1.3:
            status = "critical"
        elif peak_q > threshold:
            status = "degraded"
        else:
            status = "stable"

        if is_fragile:
            explanation = (
                f"Under this scenario the peak queue ({peak_q:.0f} vehicles) "
                f"exceeds the {threshold}-vehicle campus threshold. "
                f"The schedule is fragile to {defn['name'].lower()}."
            )
        else:
            explanation = (
                f"Peak queue ({peak_q:.0f} vehicles) stays within the "
                f"{threshold}-vehicle limit. The schedule is stable under "
                f"{defn['name'].lower()}."
            )

        results.append(
            StressScenarioResult(
                scenarioId=defn["id"],
                scenarioName=defn["name"],
                demandFactor=demand_factor,
                dwellFactor=dwell_factor,
                complianceRate=compliance,
                meanQueue=round(peak_q * 0.6, 1),  # mean ≈ 60% of peak for typical bell curve
                p95Wait=p95_wait,
                worstCaseQueue=round(worst_q, 1),
                isFragile=is_fragile,
                explanation=explanation,
                status=status,
            )
        )

    stable_count = sum(1 for r in results if r.status == "stable")
    critical_count = sum(1 for r in results if r.status == "critical")

    if critical_count == 0 and stable_count >= len(results) - 1:
        overall = (
            f"The selected schedule is robust to most tested perturbations. "
            f"{stable_count}/{len(results)} scenarios remain within the queue threshold. "
            "Synthetic estimate — field conditions may differ."
        )
    elif critical_count > 0:
        overall = (
            f"{critical_count} scenario(s) put the schedule in a critical state. "
            "Consider increasing stagger intervals or additional gate capacity before adoption. "
            "Synthetic estimate — field conditions may differ."
        )
    else:
        overall = (
            f"The schedule degrades under some stress scenarios. "
            f"{stable_count} of {len(results)} scenarios are stable. "
            "Synthetic estimate — field conditions may differ."
        )

    return StressTestResponse(
        scheduleId=request.scheduleId,
        scheduleName=schedule.name,
        scenarios=results,
        overallAssessment=overall,
    )
