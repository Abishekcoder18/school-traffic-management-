"""GateFlow AI — Diagnosis Service (Feature 1: Find the Cause)

Computes the bottleneck diagnosis from the loaded scenario data.
Every statement is traceable to a calculated value — no AI paragraphs.
Data quality is always labeled as Synthetic.
"""
from __future__ import annotations

import logging

from app.models.diagnosis import (
    BottleneckDiagnosis,
    DataQuality,
    DiagnosisEvidence,
    DiagnosisResponse,
)
from app.models.school import GateInfo
from app.services.data_service import get_scenario

logger = logging.getLogger(__name__)


def compute_diagnosis() -> DiagnosisResponse:
    """
    Analyze gates and cohorts to identify the primary bottleneck.
    Returns a fully traceable diagnosis backed by numeric evidence.
    """
    scenario = get_scenario()
    gates = scenario.gates
    cohorts = scenario.cohorts

    # ── Step 1: Identify most over-capacity gate ────────────────────────────
    bottleneck_gate = max(gates, key=lambda g: g.utilizationRate)
    overload_ratio = round(bottleneck_gate.peakDemand / bottleneck_gate.hourlyCapacity, 2)

    # ── Step 2: Identify cohorts assigned to that gate ─────────────────────
    gate_cohorts = [c for c in cohorts if c.assignedGateId == bottleneck_gate.id]
    total_gate_vehicles = sum(c.vehicleDemand for c in gate_cohorts)

    # ── Step 3: Simultaneous dismissal check ───────────────────────────────
    dismissal_times = [c.currentDismissalTime for c in gate_cohorts]
    unique_times = set(dismissal_times)
    simultaneous_conflict = len(unique_times) < len(gate_cohorts)

    conflict_time_str = ""
    if simultaneous_conflict:
        from collections import Counter
        most_common_time = Counter(dismissal_times).most_common(1)[0][0]
        h, m = map(int, most_common_time.split(":"))
        ampm = "PM" if h >= 12 else "AM"
        h12 = h - 12 if h > 12 else h
        conflict_time_str = f"{h12}:{m:02d} {ampm}"

    # ── Step 4: Dwell time analysis ────────────────────────────────────────
    scenario_school = scenario.school
    avg_dwell = scenario_school.averageDwellTimeSeconds
    design_dwell = scenario_school.designDwellTimeSeconds
    dwell_ratio = round(avg_dwell / design_dwell, 2)
    dwell_excess_pct = round((avg_dwell - design_dwell) / design_dwell * 100, 1)

    # ── Step 5: Underutilized adjacent gate ────────────────────────────────
    underutilized = min(gates, key=lambda g: g.utilizationRate)
    idle_pct = round(100 - underutilized.utilizationRate)

    # ── Step 6: Read the scenario-provided queue baseline ───────────────────
    metric = next((m for m in scenario.trafficMetrics if m.id == "peak-queue"), None)
    peak_queue = (
        f"{metric.numericValue:g} vehicles"
        if metric else "No peak-queue value is provided."
    )
    peak_queue_detail = (
        f"The synthetic scenario supplies a peak-queue baseline of {peak_queue}. "
        "It is not derived from hourly demand in this diagnosis."
        if metric else peak_queue
    )

    # ── Step 8: Build primary cause statement ──────────────────────────────
    cohort_names = " and ".join(c.cohort for c in gate_cohorts)
    if simultaneous_conflict:
        primary_cause = (
            f"Synchronized {conflict_time_str} Dismissal at "
            f"{bottleneck_gate.name.split('—')[0].strip()}"
        )
        explanation = (
            f"{cohort_names} share the same dismissal time at {conflict_time_str} and are "
            f"assigned to the {bottleneck_gate.bays}-bay {bottleneck_gate.name}. "
            f"The scenario reports peak demand of {bottleneck_gate.peakDemand} veh/h "
            f"against {bottleneck_gate.hourlyCapacity} veh/h capacity. The cohorts contain "
            f"{total_gate_vehicles} synthetic vehicles over the dismissal window; its duration "
            f"is not specified, so that count is not an hourly rate. {peak_queue_detail}"
        )
    else:
        primary_cause = (
            f"Sustained Demand Overload at {bottleneck_gate.name.split('—')[0].strip()}: "
            f"{overload_ratio}x Design Capacity"
        )
        explanation = (
            f"{bottleneck_gate.name} has scenario peak demand of "
            f"{bottleneck_gate.peakDemand} veh/h against "
            f"{bottleneck_gate.hourlyCapacity} veh/h capacity "
            f"({bottleneck_gate.bays} bays; {overload_ratio}x). The assigned cohorts contain "
            f"{total_gate_vehicles} synthetic vehicles over a dismissal window whose duration "
            f"is not specified, so the count is not an hourly rate. {peak_queue_detail}"
        )

    # ── Step 9: Compile evidence ────────────────────────────────────────────
    evidence: list[DiagnosisEvidence] = [
        DiagnosisEvidence(
            title="Hourly Arrival Demand vs Gate Capacity",
            detail=(
                f"The assigned cohorts contain {total_gate_vehicles} synthetic dismissal-window "
                f"vehicles (not an hourly rate). The scenario reports "
                f"{bottleneck_gate.peakDemand} veh/h against {bottleneck_gate.hourlyCapacity} "
                f"veh/h capacity. Assumed average dwell is {avg_dwell:.0f} seconds versus a "
                f"{design_dwell:.1f}-second design value."
            ),
            metric=f"{bottleneck_gate.utilizationRate:.0f}% of capacity",
        ),
        DiagnosisEvidence(
            title="Scenario-Provided Peak Queue",
            detail=peak_queue_detail,
            metric=peak_queue,
        ),
        DiagnosisEvidence(
            title="Lowest Modeled Gate Utilization",
            detail=(
                f"{underutilized.name} has the lowest listed utilization at "
                f"{underutilized.utilizationRate:.0f}% with {underutilized.bays} bays. "
                "This indicates modeled spare capacity, not automatic eligibility for reassignment."
            ),
            metric=f"{idle_pct}% Idle Capacity at {underutilized.name.split('—')[0].strip()}",
        ),
    ]

    diagnosis = BottleneckDiagnosis(
        gateId=bottleneck_gate.id,
        gateName=bottleneck_gate.name,
        overloadRatio=overload_ratio,
        peakDemandRate=float(bottleneck_gate.peakDemand),
        maxThroughputCapacity=float(bottleneck_gate.hourlyCapacity),
        primaryCause=primary_cause,
        explanation=explanation,
        evidence=evidence,
    )

    data_quality = DataQuality(
        source="Synthetic",
        validationStatus=(
            "All values derived from synthetic scenario data. "
            "No field measurements were used."
        ),
        limitations=[
            "Vehicle demand counts are assumed estimates, not field observations.",
            "The scenario does not specify the time window represented by cohort vehicle counts; they are not directly comparable to hourly rates.",
            "Dwell time is a fixed assumed value, not a measured sample distribution.",
            "This diagnosis does not infer queue length or spillback distance from hourly demand alone.",
            "Gate hourly capacity assumes uniform service; real throughput varies by bay count and staff.",
        ],
    )

    return DiagnosisResponse(diagnosis=diagnosis, dataQuality=data_quality)
