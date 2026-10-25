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
from app.models.school import DemandCohort, GateInfo
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


def compute_calibrated_gate_arrivals(
    cohorts: list[DemandCohort],
    offsets: list[int],
    gates_by_id: dict[str, GateInfo],
    demand_factor: float = 1.0,
    gate_assignments: Optional[list[str]] = None,
) -> dict[str, dict[int, float]]:
    """Return calibrated arrivals in vehicles/hour for each gate and 5-minute bucket.

    ``DemandCohort.vehicleDemand`` is a synthetic dismissal-window volume,
    whereas ``GateInfo.peakDemand`` and ``hourlyCapacity`` are hourly gate
    rates. Apportion each source gate's configured peak rate by cohort volume,
    then use the same profile for feasibility and queue estimates.
    """
    gate_demand: dict[str, dict[int, float]] = {
        gate_id: {} for gate_id in gates_by_id
    }

    cohorts_by_gate: dict[str, list] = {g.id: [] for g in gates_by_id.values()}
    for cohort in cohorts:
        if cohort.assignedGateId in cohorts_by_gate:
            cohorts_by_gate[cohort.assignedGateId].append(cohort)

    PROFILE = ((-10, 0.2), (-5, 0.6), (0, 1.0), (5, 0.6), (10, 0.2))

    assignments = gate_assignments or [c.assignedGateId for c in cohorts]
    for cohort, offset, assigned_gate_id in zip(cohorts, offsets, assignments):
        source_gate = gates_by_id.get(cohort.assignedGateId)
        gate = gates_by_id.get(assigned_gate_id)
        gate_cohorts = cohorts_by_gate.get(cohort.assignedGateId, [])
        total_gate_volume = sum(c.vehicleDemand for c in gate_cohorts)
        if not source_gate or not gate or total_gate_volume <= 0:
            continue

        base = _hm_to_minutes(cohort.currentDismissalTime)
        arrival_center = base + offset
        calibrated_peak = (
            source_gate.peakDemand * (cohort.vehicleDemand / total_gate_volume) * demand_factor
        )
        for dt, weight in PROFILE:
            bucket = ((arrival_center + dt) // 5) * 5
            gate_demand[assigned_gate_id][bucket] = (
                gate_demand[assigned_gate_id].get(bucket, 0.0)
                + calibrated_peak * weight
            )

    return gate_demand


def _compute_gate_loads(
    cohorts: list[DemandCohort],
    offsets: list[int],
    gates_by_id: dict[str, GateInfo],
    demand_factor: float = 1.0,
    gate_assignments: Optional[list[str]] = None,
) -> dict[str, float]:
    gate_arrivals = compute_calibrated_gate_arrivals(
        cohorts, offsets, gates_by_id, demand_factor, gate_assignments
    )
    gate_loads = {
        gate_id: max(buckets.values(), default=0.0)
        for gate_id, buckets in gate_arrivals.items()
    }

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
    cohorts: list[DemandCohort],
    offsets: list[int],
    gates_by_id: dict[str, GateInfo],
    demand_factor: float,
    gate_assignments: Optional[list[str]] = None,
) -> dict:
    """
    Estimate queues from the same hourly arrival rates used by the capacity
    feasibility check.
    """
    assignments = gate_assignments or [c.assignedGateId for c in cohorts]
    gate_arrivals = compute_calibrated_gate_arrivals(
        cohorts, offsets, gates_by_id, demand_factor, assignments
    )
    arrival_buckets = [
        bucket for arrivals in gate_arrivals.values() for bucket in arrivals
    ]
    buckets = (
        range(min(arrival_buckets), max(arrival_buckets) + 5, 5)
        if arrival_buckets else []
    )
    queues = {gate_id: 0.0 for gate_id in gates_by_id}
    peak_queue = 0.0
    spillback_meters = 0.0
    total_delay_veh_min = 0.0
    wait_samples: list[float] = []

    for bucket in buckets:
        total_queue = 0.0
        for gate_id, gate in gates_by_id.items():
            arrival_vehicles = gate_arrivals[gate_id].get(bucket, 0.0) * 5.0 / 60.0
            capacity_vehicles = gate.hourlyCapacity * 5.0 / 60.0
            queues[gate_id] = max(
                0.0, queues[gate_id] + arrival_vehicles - capacity_vehicles
            )
            total_queue += queues[gate_id]
            if queues[gate_id] > 0:
                wait_samples.append(queues[gate_id] * 60.0 / gate.hourlyCapacity)
            spillback_meters = max(
                spillback_meters,
                max(0.0, queues[gate_id] - gate.bays * 5) * 3.75,
            )

        peak_queue = max(peak_queue, total_queue)
        total_delay_veh_min += total_queue * 5.0

    wait_samples.sort()
    p95_wait_min = (
        wait_samples[max(0, math.ceil(len(wait_samples) * 0.95) - 1)]
        if wait_samples else 0.0
    )
    total_delay_veh_hrs = total_delay_veh_min / 60.0

    return {
        "peak_queue": round(peak_queue, 1),
        "p95_wait_min": round(p95_wait_min, 1),
        "total_delay_veh_hrs": round(total_delay_veh_hrs, 1),
        "spillback_meters": round(spillback_meters, 1),
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
    cohort_gate_spaces: list[list[str]] = []
    for cohort in cohorts:
        if cohort.id in fixed_groups or cohort.id in sibling_leaders:
            # Fixed or sibling follower: only offset 0 (will be set from leader later)
            cohort_offset_spaces.append([0])
        else:
            valid_offsets = [
                o for o in OFFSET_OPTIONS if abs(o) <= max_shift
            ]
            cohort_offset_spaces.append(valid_offsets if valid_offsets else [0])

        eligible_gates = cohort.eligibleGateIds or [cohort.assignedGateId]
        if not constraints.allowGateReassignment:
            eligible_gates = [cohort.assignedGateId]
        if constraints.zoneRestrictions:
            restricted_gate_ids = {
                restriction.removesuffix("-only")
                for restriction in constraints.zoneRestrictions
            }
            eligible_gates = [
                gate_id for gate_id in eligible_gates
                if gate_id in restricted_gate_ids
            ]
        valid_gates = [
            gate_id for gate_id in eligible_gates
            if gate_id in gates_by_id
            and (gate_id == cohort.assignedGateId or gates_by_id[gate_id].bays >= cohort.bayRequirement)
        ]
        cohort_gate_spaces.append(valid_gates)

    cohorts_without_eligible_gates = [
        cohort.cohort for cohort, gate_space in zip(cohorts, cohort_gate_spaces)
        if not gate_space
    ]
    if cohorts_without_eligible_gates:
        return ScheduleSearchResponse(
            candidates=[],
            totalEvaluated=0,
            feasibleCount=0,
            infeasibleCount=0,
            dominatedCount=0,
            searchExplanation=(
                "No eligible gate assignment satisfies the requested gate restrictions "
                "and scenario eligibility/bay requirements for: "
                f"{', '.join(cohorts_without_eligible_gates)}. "
                "Current gate assignments are retained as grandfathered assignments."
            ),
        )

    # Limit search space
    total_combos = 1
    for space in cohort_offset_spaces:
        total_combos *= len(space)
    for space in cohort_gate_spaces:
        total_combos *= len(space)
    logger.info(f"Planning search space: {total_combos} raw combinations")

    all_candidates: list[dict] = []
    evaluated = 0
    infeasible_count = 0
    infeasibility_reasons: dict[str, int] = {}
    infeasible_gate_counts: dict[str, int] = {}

    # Enumerate combinations
    search_space = itertools.product(*cohort_offset_spaces, *cohort_gate_spaces)
    for raw_candidate in itertools.islice(
        search_space, MAX_COMBINATIONS
    ):
        offsets = list(raw_candidate[:len(cohorts)])
        gate_assignments = list(raw_candidate[len(cohorts):])

        # Apply sibling sync: followers get leader's offset
        for i, cohort in enumerate(cohorts):
            if cohort.id in sibling_leaders and sibling_sync:
                leader_id = sibling_leaders[cohort.id]
                leader_idx = next(
                    j for j, c in enumerate(cohorts) if c.id == leader_id
                )
                offsets[i] = offsets[leader_idx]

        evaluated += 1
        gate_loads = _compute_gate_loads(
            cohorts, offsets, gates_by_id, demand_factor, gate_assignments
        )
        feasible, label, reason = _is_feasible(gate_loads, gates_by_id)

        if not feasible:
            infeasible_count += 1
            infeasibility_reasons[reason] = infeasibility_reasons.get(reason, 0) + 1
            for gate_id, load in gate_loads.items():
                gate = gates_by_id[gate_id]
                if load / gate.hourlyCapacity > GATE_SAFETY_MARGIN:
                    infeasible_gate_counts[gate_id] = (
                        infeasible_gate_counts.get(gate_id, 0) + 1
                    )
            continue

        queue_metrics = _compute_queue_metrics(
            cohorts, offsets, gates_by_id, demand_factor, gate_assignments
        )
        obj_score, disruption_score = _score_candidate(
            gate_loads, gates_by_id, offsets, objective, queue_metrics
        )

        all_candidates.append(
            {
                "offsets": offsets,
                "gate_assignments": gate_assignments,
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
        common_reason = max(
            infeasibility_reasons, key=infeasibility_reasons.get, default="No candidate satisfied the gate constraints."
        )
        capacity_blockers = "; ".join(
            f"{gates_by_id[gate_id].name}: over the existing 105% limit "
            f"in {count} evaluated combinations"
            for gate_id, count in sorted(
                infeasible_gate_counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )
        return ScheduleSearchResponse(
            candidates=[],
            totalEvaluated=evaluated,
            feasibleCount=0,
            infeasibleCount=infeasible_count,
            dominatedCount=0,
            searchExplanation=(
                f"Evaluated {evaluated} combinations. All were infeasible under the "
                f"provided constraints. Most common rejection: {common_reason}. "
                f"Capacity blockers: {capacity_blockers or 'none identified'}. "
                "Gate capacities were not increased; reassignment was limited to "
                "scenario-eligible gates that satisfy bay requirements."
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
    baseline_metrics = _compute_queue_metrics(
        cohorts, baseline_offsets, gates_by_id, demand_factor
    )
    baseline_peak_q = baseline_metrics["peak_queue"]
    baseline_wait = baseline_metrics["p95_wait_min"]

    # ── Build ScheduleCandidate objects ──────────────────────────────────
    plan_names = ["Alpha", "Beta", "Gamma"]
    plan_badges = ["Recommended", "Alternative", "Family Sync"]

    schedule_candidates: list[ScheduleCandidate] = []

    for rank, cand in enumerate(top_candidates):
        offsets = cand["offsets"]
        gate_assignments = cand["gate_assignments"]
        qm = cand["queue_metrics"]
        peak_q = qm["peak_queue"]
        p95_wait = qm["p95_wait_min"]
        total_delay = qm["total_delay_veh_hrs"]

        queue_red_pct = (
            round((baseline_peak_q - peak_q) / baseline_peak_q * 100, 1)
            if baseline_peak_q > 0 else None
        )
        wait_red_min = round(baseline_wait - p95_wait, 1)
        spillback_red_m = round(
            baseline_metrics["spillback_meters"] - qm["spillback_meters"], 1
        )

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
        reassigned_cohorts = [
            cohorts[i].cohort for i, gate_id in enumerate(gate_assignments)
            if gate_id != cohorts[i].assignedGateId
        ]
        if shifted_cohorts:
            desc = (
                f"Shifts {', '.join(shifted_cohorts[:2])} "
                f"by up to {max_offset} minutes to redistribute gate load."
            )
        else:
            desc = "Baseline schedule with adjusted gate assignments only."
        if reassigned_cohorts:
            desc += f" Routes {', '.join(reassigned_cohorts)} to an eligible overflow gate."

        # Group schedule rows
        group_rows: list[GroupScheduleRow] = []
        for i, cohort in enumerate(cohorts):
            offset = offsets[i]
            base_min = _hm_to_minutes(cohort.currentDismissalTime)
            proposed_min = base_min + offset
            assigned_gate_id = gate_assignments[i]
            gate = gates_by_id.get(assigned_gate_id)
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
                    assignedGateId=assigned_gate_id,
                    zoneBay=bays,
                    vehicles=round(cohort.vehicleDemand * demand_factor),
                    requiredBays=cohort.bayRequirement,
                    availableBays=gate.bays if gate else 0,
                    bayConstraintStatus=(
                        "grandfathered"
                        if gate and assigned_gate_id == cohort.assignedGateId
                        and gate.bays < cohort.bayRequirement
                        else "satisfied"
                    ),
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
            gateCapacities={g.id: float(g.hourlyCapacity) for g in scenario.gates},
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
