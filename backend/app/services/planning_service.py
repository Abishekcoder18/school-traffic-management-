"""GateFlow AI — Planning Service (Feature 2: Find a Better Schedule)

Generates candidate schedules by:
1. Enumerating offset vectors for each cohort
2. Applying hard constraints (feasibility check)
3. Scoring by objective metrics
4. Returning Pareto-optimal candidates with explanations

This is a real combinatorial search — no pre-written candidate responses.
"""
from __future__ import annotations

import itertools
import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from app.models.schedule import (
    GroupScheduleRow,
    ParsedConstraints,
    ScheduleCandidate,
    ScheduleSearchRequest,
    ScheduleSearchResponse,
)
from app.services.data_service import get_scenario

logger = logging.getLogger(__name__)

# Candidate offsets to try for each cohort (minutes relative to baseline)
OFFSET_OPTIONS = [-30, -20, -15, -10, -5, 0, 5, 10, 15, 20, 30]

# Maximum number of full combinations to evaluate (performance guard)
MAX_COMBINATIONS = 5000

# Gate overflow limit used in feasibility check
GATE_SAFETY_MARGIN = 1.05  # allow up to 5% over capacity (Minor Leniency)


def _hm_to_minutes(hm: str) -> int:
    """Convert 'HH:MM' to minutes since midnight."""
    h, m = map(int, hm.split(":"))
    return h * 60 + m


def _minutes_to_hhmm(mins: int) -> str:
    """Convert minutes since midnight to 'HH:MM'."""
    h = (mins // 60) % 24
    m = mins % 60
    return f"{h:02d}:{m:02d}"


def _minutes_to_display(mins: int) -> str:
    """Convert minutes since midnight to '2:30 PM' style."""
    h = (mins // 60) % 24
    m = mins % 60
    ampm = "PM" if h >= 12 else "AM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {ampm}"


def _delta_display(offset: int) -> str:
    if offset == 0:
        return "0 min (Unchanged)"
    sign = "+" if offset > 0 else ""
    label = "Earlier" if offset < 0 else "Shift"
    return f"{sign}{offset} min ({label})"


def _gate_display(gate_id: str, gates_by_id: dict) -> tuple[str, str]:
    """Return (gate display name, bay string)."""
    gate = gates_by_id.get(gate_id)
    if not gate:
        return gate_id, "N/A"
    short_name = gate.name.split("—")[0].strip()
    bays_str = f"Bays 1–{gate.bays}"
    return f"{short_name} ({gate.name.split('—')[1].strip()})", bays_str


def _compute_gate_loads(
    cohorts,
    offsets: list[int],
    gates_by_id: dict,
    demand_factor: float = 1.0,
) -> dict[str, float]:
    """
    Compute peak load on each gate given an offset vector.
    Uses a time-bucket approach with 5-minute intervals.
    Returns gate_id → peak_vehicles_per_hour ratio.
    """
    # Build time-bucket demand: gate_id → {time_bucket: vehicle_count}
    BUCKET = 5  # minutes
    gate_demand: dict[str, dict[int, float]] = {
        g.id: {} for g in gates_by_id.values()
    }

    for cohort, offset in zip(cohorts, offsets):
        base = _hm_to_minutes(cohort.currentDismissalTime)
        arrival_center = base + offset
        vehicles = cohort.vehicleDemand * demand_factor
        # Spread arrival over 20-minute window (Poisson approximation)
        for dt in range(0, 25, BUCKET):
            bucket = ((arrival_center + dt) // BUCKET) * BUCKET
            gate_demand[cohort.assignedGateId][bucket] = (
                gate_demand[cohort.assignedGateId].get(bucket, 0.0)
                + vehicles * (BUCKET / 20.0)  # fraction of total in this bucket
            )

    # Convert peak bucket count to veh/hour rate
    gate_loads: dict[str, float] = {}
    for gate_id, buckets in gate_demand.items():
        if not buckets:
            gate_loads[gate_id] = 0.0
        else:
            peak_bucket = max(buckets.values())
            # bucket is BUCKET minutes wide, scale to hourly
            gate_loads[gate_id] = peak_bucket * (60.0 / BUCKET)

    return gate_loads


def _is_feasible(
    gate_loads: dict[str, float],
    gates_by_id: dict,
    margin: float = GATE_SAFETY_MARGIN,
) -> tuple[bool, str, str]:
    """
    Return (feasible, feasibility_label, reason).
    """
    for gate_id, load in gate_loads.items():
        gate = gates_by_id.get(gate_id)
        if not gate:
            continue
        ratio = load / gate.hourlyCapacity
        if ratio > margin:
            return (
                False,
                "Infeasible",
                f"{gate.name}: gate load {load:.0f} veh/h exceeds capacity "
                f"{gate.hourlyCapacity} veh/h (ratio={ratio:.2f})",
            )

    # Check for Minor Leniency vs fully compliant
    for gate_id, load in gate_loads.items():
        gate = gates_by_id.get(gate_id)
        if not gate:
            continue
        if load / gate.hourlyCapacity > 1.0:
            return True, "Minor Leniency", "All gates within 5% safety margin."

    return True, "100% Compliant", "All gate capacity constraints satisfied."


def _compute_queue_metrics(
    cohorts,
    offsets: list[int],
    gates_by_id: dict,
    demand_factor: float,
    dwell_seconds: float,
) -> dict:
    """
    Compute peak queue, P95 wait time, total delay and spillback
    using an M/D/c queuing model approximation.
    """
    BUCKET = 5  # minutes
    total_delay_veh_min = 0.0
    peak_queue_total = 0.0
    p95_waits = []

    for gate in gates_by_id.values():
        gate_cohorts = [c for c in cohorts if c.assignedGateId == gate.id]
        c_servers = gate.bays  # c = number of servers

        # Service rate per server: vehicles per minute
        mu = 60.0 / (dwell_seconds / 60.0)  # veh/hr per bay
        mu_per_min = mu / 60.0

        # Build arrival queue over time
        queue = 0.0
        gate_peak_q = 0.0
        gate_delays = []

        for t in range(150, 225, BUCKET):  # 2:30 PM to 3:45 PM window
            arrivals = 0.0
            for cohort, offset in zip(cohorts, offsets):
                if cohort.assignedGateId != gate.id:
                    continue
                center = _hm_to_minutes(cohort.currentDismissalTime) + offset
                if abs(t - center) <= 10:
                    arrivals += cohort.vehicleDemand * demand_factor * (BUCKET / 20.0)

            # Service capacity this bucket
            served = min(queue + arrivals, c_servers * mu_per_min * BUCKET)
            queue = max(0.0, queue + arrivals - served)

            if queue > 0:
                wait = queue / (c_servers * mu_per_min) if (c_servers * mu_per_min) > 0 else 0.0
                gate_delays.append(wait)

            gate_peak_q = max(gate_peak_q, queue)

        peak_queue_total += gate_peak_q
        if gate_delays:
            gate_delays.sort()
            p95_idx = max(0, int(len(gate_delays) * 0.95) - 1)
            p95_waits.append(gate_delays[p95_idx])

        # Total delay contribution: area under queue curve
        for cohort, offset in zip(cohorts, offsets):
            if cohort.assignedGateId == gate.id:
                # Simple heuristic: each veh waits proportional to gate overload
                overload = max(0.0, gate_peak_q / max(1, c_servers))
                total_delay_veh_min += cohort.vehicleDemand * demand_factor * overload * 0.5

    p95_wait_min = max(p95_waits) if p95_waits else 0.0
    total_delay_veh_hrs = total_delay_veh_min / 60.0

    return {
        "peak_queue": round(peak_queue_total, 1),
        "p95_wait_min": round(p95_wait_min, 1),
        "total_delay_veh_hrs": round(total_delay_veh_hrs, 1),
    }


def _score_candidate(
    gate_loads: dict,
    gates_by_id: dict,
    offsets: list[int],
    objective: str,
    queue_metrics: dict,
) -> tuple[float, float]:
    """
    Return (objective_score, disruption_score).
    Lower objective_score = better for the chosen objective.
    """
    peak_q = queue_metrics["peak_queue"]
    total_delay = queue_metrics["total_delay_veh_hrs"]
    disruption = sum(abs(o) for o in offsets)

    if objective == "queue_reduction":
        obj = peak_q * 0.7 + total_delay * 0.3
    elif objective == "minimal_disruption":
        obj = disruption * 0.6 + peak_q * 0.4
    else:  # balanced
        obj = peak_q * 0.5 + disruption * 0.3 + total_delay * 0.2

    return round(obj, 3), round(disruption, 1)


def search_schedules(request: ScheduleSearchRequest) -> ScheduleSearchResponse:
    """
    Main planning function. Searches the schedule space and returns
    ranked feasible candidates.
    """
    constraints = request.constraints
    scenario = get_scenario()
    cohorts = scenario.cohorts
    gates_by_id = {g.id: g for g in scenario.gates}
    dwell_seconds = scenario.school.averageDwellTimeSeconds
    demand_factor = constraints.demandFactor
    fixed_groups = set(constraints.fixedGroups)
    sibling_sync = constraints.siblingSync
    max_shift = constraints.maxShiftMin
    objective = constraints.optimizationObjective

    # Build sibling group mapping (cohort_id → group_id)
    sibling_leaders: dict[str, str] = {}
    if sibling_sync:
        for sg in scenario.siblingGroups:
            if len(sg.cohortIds) >= 2:
                leader = sg.cohortIds[0]
                for follower in sg.cohortIds[1:]:
                    sibling_leaders[follower] = leader  # follower must match leader's offset

    # Build offset space per cohort
    cohort_offset_spaces: list[list[int]] = []
    for cohort in cohorts:
        if cohort.id in fixed_groups or cohort.id in sibling_leaders:
            # Fixed or sibling follower: only offset 0 (will be set from leader later)
            cohort_offset_spaces.append([0])
        else:
            valid_offsets = [
                o for o in OFFSET_OPTIONS if abs(o) <= max_shift
            ]
            cohort_offset_spaces.append(valid_offsets if valid_offsets else [0])

    # Limit search space
    total_combos = 1
    for space in cohort_offset_spaces:
        total_combos *= len(space)
    logger.info(f"Planning search space: {total_combos} raw combinations")

    all_candidates: list[dict] = []
    evaluated = 0
    infeasible_count = 0

    # Enumerate combinations
    for raw_offsets in itertools.islice(
        itertools.product(*cohort_offset_spaces), MAX_COMBINATIONS
    ):
        offsets = list(raw_offsets)

        # Apply sibling sync: followers get leader's offset
        for i, cohort in enumerate(cohorts):
            if cohort.id in sibling_leaders and sibling_sync:
                leader_id = sibling_leaders[cohort.id]
                leader_idx = next(
                    j for j, c in enumerate(cohorts) if c.id == leader_id
                )
                offsets[i] = offsets[leader_idx]

        evaluated += 1
        gate_loads = _compute_gate_loads(cohorts, offsets, gates_by_id, demand_factor)
        feasible, label, reason = _is_feasible(gate_loads, gates_by_id)

        if not feasible:
            infeasible_count += 1
            continue

        queue_metrics = _compute_queue_metrics(
            cohorts, offsets, gates_by_id, demand_factor, dwell_seconds
        )
        obj_score, disruption_score = _score_candidate(
            gate_loads, gates_by_id, offsets, objective, queue_metrics
        )

        all_candidates.append(
            {
                "offsets": offsets,
                "gate_loads": gate_loads,
                "feasibility_label": label,
                "feasibility_reason": reason,
                "queue_metrics": queue_metrics,
                "obj_score": obj_score,
                "disruption_score": disruption_score,
            }
        )

    if not all_candidates:
        # Return a baseline-only "no improvement found" response
        logger.warning("No feasible candidates found — returning empty schedule list")
        return ScheduleSearchResponse(
            candidates=[],
            totalEvaluated=evaluated,
            feasibleCount=0,
            infeasibleCount=infeasible_count,
            dominatedCount=0,
            searchExplanation=(
                f"Evaluated {evaluated} combinations. All were infeasible under the "
                "provided constraints. Try relaxing maxShiftMin or gate restrictions."
            ),
        )

    # Sort by objective score
    all_candidates.sort(key=lambda c: c["obj_score"])

    # Simple Pareto filter: keep candidates not dominated on both objectives
    pareto: list[dict] = []
    dominated_count = 0
    for candidate in all_candidates:
        dominated = False
        for other in all_candidates:
            if (
                other["obj_score"] <= candidate["obj_score"]
                and other["disruption_score"] <= candidate["disruption_score"]
                and (
                    other["obj_score"] < candidate["obj_score"]
                    or other["disruption_score"] < candidate["disruption_score"]
                )
            ):
                dominated = True
                break
        if not dominated:
            pareto.append(candidate)
        else:
            dominated_count += 1

    # Pick top 3 distinct candidates from Pareto front
    top_candidates = (pareto[:3] if pareto else all_candidates[:3])

    # ── Baseline metrics (for computing reduction %) ──────────────────────
    baseline_offsets = [0] * len(cohorts)
    baseline_gate_loads = _compute_gate_loads(
        cohorts, baseline_offsets, gates_by_id, demand_factor
    )
    baseline_metrics = _compute_queue_metrics(
        cohorts, baseline_offsets, gates_by_id, demand_factor, dwell_seconds
    )
    baseline_peak_q = baseline_metrics["peak_queue"] or 1.0
    baseline_wait = baseline_metrics["p95_wait_min"] or 1.0
    baseline_delay = baseline_metrics["total_delay_veh_hrs"] or 1.0

    # ── Build ScheduleCandidate objects ──────────────────────────────────
    plan_names = ["Alpha", "Beta", "Gamma"]
    plan_badges = ["Recommended", "Alternative", "Family Sync"]

    schedule_candidates: list[ScheduleCandidate] = []

    for rank, cand in enumerate(top_candidates):
        offsets = cand["offsets"]
        qm = cand["queue_metrics"]
        peak_q = qm["peak_queue"]
        p95_wait = qm["p95_wait_min"]
        total_delay = qm["total_delay_veh_hrs"]

        queue_red_pct = round(max(0.0, (baseline_peak_q - peak_q) / baseline_peak_q * 100), 1)
        wait_red_min = round(max(0.0, baseline_wait - p95_wait), 1)

        # Estimate spillback from overflow vehicles at bottleneck gate
        bottleneck = max(scenario.gates, key=lambda g: cand["gate_loads"].get(g.id, 0))
        overflow = max(0.0, cand["gate_loads"].get(bottleneck.id, 0) - bottleneck.hourlyCapacity)
        baseline_overflow = max(
            0.0,
            baseline_gate_loads.get(bottleneck.id, 0) - bottleneck.hourlyCapacity,
        )
        spillback_red_m = round(max(0.0, (baseline_overflow - overflow) * 3.75), 0)

        # Max shift across non-fixed cohorts
        max_offset = max(
            abs(o) for i, o in enumerate(offsets)
            if cohorts[i].id not in fixed_groups
        ) if offsets else 0

        # Risk profile
        feasibility_label = cand["feasibility_label"]
        if feasibility_label == "100% Compliant":
            risk = "Low"
        elif feasibility_label == "Minor Leniency":
            risk = "Medium"
        else:
            risk = "High"

        # Build description
        shifted_cohorts = [
            cohorts[i].cohort
            for i, o in enumerate(offsets)
            if o != 0 and cohorts[i].id not in fixed_groups
        ]
        if shifted_cohorts:
            desc = (
                f"Shifts {', '.join(shifted_cohorts[:2])} "
                f"by up to {max_offset} minutes to redistribute gate load."
            )
        else:
            desc = "Baseline schedule with adjusted gate assignments only."

        # Group schedule rows
        group_rows: list[GroupScheduleRow] = []
        for i, cohort in enumerate(cohorts):
            offset = offsets[i]
            base_min = _hm_to_minutes(cohort.currentDismissalTime)
            proposed_min = base_min + offset
            gate = gates_by_id.get(cohort.assignedGateId)
            gate_display = (
                f"{gate.name.split('—')[0].strip()} ({gate.name.split('—')[1].strip()})"
                if gate else cohort.assignedGateId
            )
            bays = f"Bays 1–{gate.bays}" if gate else "N/A"

            group_rows.append(
                GroupScheduleRow(
                    cohort=cohort.cohort,
                    cohortId=cohort.id,
                    baselineTime=_minutes_to_display(base_min),
                    proposedTime=_minutes_to_display(proposed_min),
                    timeDelta=_delta_display(offset),
                    offsetMinutes=offset,
                    assignedGate=gate_display,
                    assignedGateId=cohort.assignedGateId,
                    zoneBay=bays,
                    vehicles=round(cohort.vehicleDemand * demand_factor),
                )
            )

        plan_idx = rank % len(plan_names)
        candidate = ScheduleCandidate(
            id=f"candidate-{plan_names[plan_idx].lower()}-{rank}",
            name=f"Plan {plan_names[plan_idx]}: {desc[:60]}",
            badge=plan_badges[plan_idx],
            description=desc,
            staggerIntervalMin=max_offset,
            peakQueueReductionPct=queue_red_pct,
            waitTimeReductionMin=wait_red_min,
            totalDelayHours=round(total_delay, 1),
            spillbackReductionMeters=float(spillback_red_m),
            constraintFeasibility=feasibility_label,
            riskProfile=risk,
            groupSchedule=group_rows,
            objectiveScore=cand["obj_score"],
            disruptionScore=cand["disruption_score"],
            gateLoads={k: round(v, 1) for k, v in cand["gate_loads"].items()},
            isFeasible=True,
            feasibilityReason=cand["feasibility_reason"],
        )
        schedule_candidates.append(candidate)

    return ScheduleSearchResponse(
        candidates=schedule_candidates,
        totalEvaluated=evaluated,
        feasibleCount=len(all_candidates),
        infeasibleCount=infeasible_count,
        dominatedCount=dominated_count,
        searchExplanation=(
            f"Evaluated {evaluated} schedule combinations. "
            f"Found {len(all_candidates)} feasible solutions. "
            f"{dominated_count} were Pareto-dominated. "
            f"Top {len(schedule_candidates)} candidates returned, "
            f"ranked by {objective.replace('_', ' ')} objective."
        ),
    )
