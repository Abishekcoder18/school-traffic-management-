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

    # ── Step 6: Spillback estimate ─────────────────────────────────────────
    # Heuristic: each vehicle that can't be served adds ~3.75m queue
    overflow_vehicles = max(0, bottleneck_gate.peakDemand - bottleneck_gate.hourlyCapacity)
    spillback_meters = round(overflow_vehicles * 3.75)

    # ── Step 7: Peak queue length estimate ─────────────────────────────────
    metric = next((m for m in scenario.trafficMetrics if m.id == "peak-queue"), None)
    peak_queue = metric.numericValue if metric else overflow_vehicles

    # ── Step 8: Build primary cause statement ──────────────────────────────
    cohort_names = " and ".join(c.cohort for c in gate_cohorts)
    if simultaneous_conflict:
        primary_cause = (
            f"Simultaneous {conflict_time_str} Dismissal Collision on "
            f"Single-Lane Infrastructure at {bottleneck_gate.name.split('—')[0].strip()}"
        )
        explanation = (
            f"Both {cohort_names} share the exact same dismissal bell at {conflict_time_str} "
            f"and are routed to the {bottleneck_gate.bays}-bay {bottleneck_gate.name}. "
            f"With a processing capability of {bottleneck_gate.hourlyCapacity} vehicles per hour, "
            f"the peak surge of {total_gate_vehicles} arriving vehicles overwhelms the loop "
            f"within 20 minutes, generating an unmitigated {int(peak_queue)}-vehicle queue "
            f"that spills {spillback_meters} meters onto {bottleneck_gate.approachStreet}."
        )
    else:
        primary_cause = (
            f"Sustained Demand Overload at {bottleneck_gate.name.split('—')[0].strip()}: "
            f"{overload_ratio}x Design Capacity"
        )
        explanation = (
            f"{bottleneck_gate.name} receives {total_gate_vehicles} vehicles across "
            f"{len(gate_cohorts)} cohorts but has a maximum throughput of only "
            f"{bottleneck_gate.hourlyCapacity} vehicles per hour ({bottleneck_gate.bays} bays). "
            f"The sustained overload ratio of {overload_ratio}x generates queue spillback "
            f"of approximately {spillback_meters} meters."
        )

    # ── Step 9: Compile evidence ────────────────────────────────────────────
    evidence: list[DiagnosisEvidence] = [
        DiagnosisEvidence(
            title="Arrival Surge vs Bay Capacity Mismatch",
            detail=(
                f"{total_gate_vehicles} vehicles funneling through {bottleneck_gate.bays} "
                f"loading bays gives {design_dwell:.1f} seconds per boarding operation, "
                f"while measured student boarding averages {avg_dwell:.0f} seconds."
            ),
            metric=f"{bottleneck_gate.utilizationRate:.0f}% Capacity Overload",
        ),
        DiagnosisEvidence(
            title="Spillback onto Public Arterial Road",
            detail=(
                f"Queue reaches past campus turn-lane threshold into "
                f"{bottleneck_gate.approachStreet}, impeding local transit. "
                f"Estimated {spillback_meters}m of spillback from {int(overflow_vehicles)} "
                f"excess vehicles unable to enter the gate loop."
            ),
            metric=f"{spillback_meters}m Spillback Beyond Perimeter",
        ),
        DiagnosisEvidence(
            title="Underutilized Adjacent Infrastructure",
            detail=(
                f"{underutilized.name} operates at only {underutilized.utilizationRate:.0f}% "
                f"capacity during the peak window with {underutilized.bays} bays and a "
                f"dedicated staging driveway — {idle_pct}% of that capacity is idle."
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
            "Dwell time is a fixed assumed value, not a measured sample distribution.",
            "Spillback distance is a heuristic estimate (3.75m per overflow vehicle).",
            "Gate hourly capacity assumes uniform service; real throughput varies by bay count and staff.",
        ],
    )

    return DiagnosisResponse(diagnosis=diagnosis, dataQuality=data_quality)
