"""GateFlow AI — Simulation Service (Feature 3: Test the Schedule)

Uses a deterministic five-minute queue estimate to compare the selected
schedule with the baseline.

IMPORTANT: All results are labeled 'DeterministicEstimate'.
SUMO is not installed — no SUMO results are fabricated.
"""
from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime
from typing import Optional

from app.models.schedule import ScheduleCandidate
from app.models.simulation import (
    ComparisonReport,
    MetricComparison,
    SimulationMetrics,
    SimulationResult,
    SimulationRunRequest,
    TimeInterval,
)
from app.services.data_service import get_scenario
from app.services.planning_service import compute_calibrated_gate_arrivals

logger = logging.getLogger(__name__)

# In-memory run cache: run_id → SimulationResult
_simulation_cache: dict[str, SimulationResult] = {}

# In-memory schedule store: schedule_id → ScheduleCandidate
_schedule_store: dict[str, ScheduleCandidate] = {}


def register_schedule(candidate: ScheduleCandidate) -> None:
    """Store a schedule so simulation can retrieve it by ID."""
    _schedule_store[candidate.id] = candidate
    logger.info(f"Registered schedule '{candidate.id}' for simulation.")


def get_registered_schedule(schedule_id: str) -> Optional[ScheduleCandidate]:
    return _schedule_store.get(schedule_id)


def _hm_to_minutes(hm: str) -> int:
    h, m = map(int, hm.split(":"))
    return h * 60 + m


def _minutes_to_display(mins: int) -> str:
    h = (mins // 60) % 24
    m = mins % 60
    ampm = "PM" if h >= 12 else "AM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {ampm}"


def _simulate_queue_timeseries(
    cohorts,
    offsets_by_cohort_id: dict[str, int],
    gates_by_id: dict,
    demand_factor: float,
    assigned_gates_by_cohort_id: Optional[dict[str, str]] = None,
    start_minute: int = 150,
    end_minute: int = 225,
    interval_min: int = 15,
    capacity_factor: float = 1.0,
) -> tuple[list[TimeInterval], dict]:
    """
    Simulate queue evolution from the same calibrated arrivals as the planner.
    Returns (time_series, peak_metrics).
    """
    BUCKET = 5  # internal simulation step (minutes)
    offsets = [offsets_by_cohort_id.get(cohort.id, 0) for cohort in cohorts]
    assignments = [
        (assigned_gates_by_cohort_id or {}).get(cohort.id, cohort.assignedGateId)
        for cohort in cohorts
    ]
    gate_arrivals = compute_calibrated_gate_arrivals(
        cohorts, offsets, gates_by_id, demand_factor, assignments
    )
    time_points = list(range(start_minute, end_minute + BUCKET, BUCKET))
    queues = {gate_id: 0.0 for gate_id in gates_by_id}
    total_queues: list[float] = []
    wait_samples: list[float] = []
    total_delay_veh_min = 0.0
    spillback_meters = 0.0

    for time_point in time_points:
        total_queue = 0.0
        for gate_id, gate in gates_by_id.items():
            arrivals = gate_arrivals[gate_id].get(time_point, 0.0) * BUCKET / 60.0
            service = gate.hourlyCapacity * capacity_factor * BUCKET / 60.0
            queues[gate_id] = max(0.0, queues[gate_id] + arrivals - service)
            total_queue += queues[gate_id]
            if queues[gate_id] > 0:
                wait_samples.append(queues[gate_id] * 60.0 / gate.hourlyCapacity)
            spillback_meters = max(
                spillback_meters,
                max(0.0, queues[gate_id] - gate.bays * 5) * 3.75,
            )

        total_queues.append(total_queue)
        total_delay_veh_min += total_queue * BUCKET

    wait_samples.sort()
    p95_wait_min = (
        wait_samples[max(0, math.ceil(len(wait_samples) * 0.95) - 1)]
        if wait_samples else 0.0
    )

    intervals: list[TimeInterval] = []
    for t_start in range(start_minute, end_minute, interval_min):
        step_indices = [
            i for i, time_point in enumerate(time_points)
            if t_start <= time_point < t_start + interval_min
        ]
        total_q = (
            sum(total_queues[i] for i in step_indices) / len(step_indices)
            if step_indices else 0.0
        )
        intervals.append(
            TimeInterval(
                time=_minutes_to_display(t_start),
                baselineQueue=0.0,  # filled in later
                candidateQueue=round(total_q, 1),
                gateCapacity=(
                    sum(gate.hourlyCapacity for gate in gates_by_id.values())
                    * interval_min / 60.0
                ),
            )
        )

    metrics = {
        "mean_queue": round(
            sum(total_queues) / len(total_queues) if total_queues else 0.0, 1
        ),
        "peak_queue": round(max(total_queues, default=0.0), 1),
        "p95_wait_min": round(p95_wait_min, 1),
        "total_delay_veh_hrs": round(total_delay_veh_min / 60.0, 1),
        "spillback_meters": round(spillback_meters, 1),
    }
    return intervals, metrics


def run_simulation(request: SimulationRunRequest) -> SimulationResult:
    """
    Run a deterministic queuing simulation for the given schedule.
    The schedule MUST have been registered via register_schedule().
    This ensures the selected schedule is what actually gets simulated.
    """
    schedule = _schedule_store.get(request.scheduleId)
    if not schedule:
        raise ValueError(
            f"Schedule '{request.scheduleId}' not found. "
            "Submit the schedule via POST /api/schedules/search first."
        )

    scenario = get_scenario()
    cohorts = scenario.cohorts
    gates_by_id = {g.id: g for g in scenario.gates}
    demand_factor = request.demandFactor

    # Extract offsets from the selected candidate's group schedule
    offsets_by_cohort_id: dict[str, int] = {}
    assigned_gates_by_cohort_id: dict[str, str] = {}
    for row in schedule.groupSchedule:
        offsets_by_cohort_id[row.cohortId] = row.offsetMinutes
        assigned_gates_by_cohort_id[row.cohortId] = row.assignedGateId

    centers = [
        _hm_to_minutes(cohort.currentDismissalTime) + offset
        for cohort in cohorts
        for offset in (0, offsets_by_cohort_id.get(cohort.id, 0))
    ]
    start_minute = ((min(centers) - 10) // 15) * 15
    end_minute = ((max(centers) + 24) // 15) * 15

    # ── Run CANDIDATE simulation ──────────────────────────────────────────
    cand_intervals, cand_metrics = _simulate_queue_timeseries(
        cohorts, offsets_by_cohort_id, gates_by_id, demand_factor,
        assigned_gates_by_cohort_id, start_minute, end_minute,
    )

    # ── Run BASELINE simulation (identical conditions, zero offsets) ──────
    baseline_offsets = {c.id: 0 for c in cohorts}
    base_intervals, base_metrics = _simulate_queue_timeseries(
        cohorts, baseline_offsets, gates_by_id, demand_factor,
        start_minute=start_minute, end_minute=end_minute,
    )

    # Inject baseline queue into the combined time series
    for i, iv in enumerate(cand_intervals):
        base_q = base_intervals[i].candidateQueue if i < len(base_intervals) else 0.0
        iv.baselineQueue = base_q

    # ── Compute delta % ───────────────────────────────────────────────────
    def _delta(base: float, cand: float) -> Optional[float]:
        if base == 0:
            return 0.0 if cand == 0 else None
        return round((cand - base) / base * 100.0, 1)

    threshold = scenario.school.vehicleCapacityThreshold

    metrics = SimulationMetrics(
        peakQueue=MetricComparison(
            baseline=base_metrics["peak_queue"],
            candidate=cand_metrics["peak_queue"],
            unit="vehicles",
            deltaPct=_delta(base_metrics["peak_queue"], cand_metrics["peak_queue"]),
        ),
        waitTimeP95=MetricComparison(
            baseline=base_metrics["p95_wait_min"],
            candidate=cand_metrics["p95_wait_min"],
            unit="minutes",
            deltaPct=_delta(base_metrics["p95_wait_min"], cand_metrics["p95_wait_min"]),
        ),
        totalDelay=MetricComparison(
            baseline=base_metrics["total_delay_veh_hrs"],
            candidate=cand_metrics["total_delay_veh_hrs"],
            unit="veh-hrs",
            deltaPct=_delta(base_metrics["total_delay_veh_hrs"], cand_metrics["total_delay_veh_hrs"]),
        ),
        spillbackDistance=MetricComparison(
            baseline=base_metrics["spillback_meters"],
            candidate=cand_metrics["spillback_meters"],
            unit="meters",
            deltaPct=_delta(base_metrics["spillback_meters"], cand_metrics["spillback_meters"]),
        ),
        zoneViolations=MetricComparison(
            baseline=round(max(0.0, base_metrics["peak_queue"] - threshold)),
            candidate=round(max(0.0, cand_metrics["peak_queue"] - threshold)),
            unit="incidents",
            deltaPct=_delta(
                max(0.0, base_metrics["peak_queue"] - threshold),
                max(0.0, cand_metrics["peak_queue"] - threshold),
            ),
        ),
    )

    # ── Improvements & risks ──────────────────────────────────────────────
    improvements: list[str] = []
    if cand_metrics["peak_queue"] < base_metrics["peak_queue"]:
        peak_queue_delta = _delta(
            base_metrics["peak_queue"], cand_metrics["peak_queue"]
        )
        if peak_queue_delta is not None:
            improvements.append(
                f"Peak queue reduced from {base_metrics['peak_queue']:.1f} to "
                f"{cand_metrics['peak_queue']:.1f} vehicles "
                f"({abs(peak_queue_delta):.1f}% lower in this model)."
            )
    if cand_metrics["spillback_meters"] < base_metrics["spillback_meters"]:
        delta_spill = base_metrics["spillback_meters"] - cand_metrics["spillback_meters"]
        improvements.append(
            f"Spillback reduced by {delta_spill:.0f}m. "
            + ("Zero public-road blockage achieved." if cand_metrics["spillback_meters"] == 0 else "")
        )
    if cand_metrics["p95_wait_min"] < base_metrics["p95_wait_min"]:
        improvements.append(
            f"P95 pickup wait reduced from {base_metrics['p95_wait_min']:.1f} to "
            f"{cand_metrics['p95_wait_min']:.1f} minutes."
        )
    if not improvements:
        improvements.append("No significant improvement over baseline under these constraints.")

    risks: list[str] = [
        "Parent compliance sensitivity: late arrivals may reduce modeled queue benefit.",
        "Estimates based on synthetic data — field conditions may differ.",
        "Configured hourly gate capacities are held constant; real throughput may vary.",
        "Spillback is a heuristic estimate based on modeled queue storage and queue length.",
    ]

    run_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = SimulationResult(
        runId=run_id,
        candidateId=schedule.id,
        candidateName=schedule.name,
        simulatedAt=now,
        fidelityNote=(
            "Deterministic five-minute bucket-queue estimate using "
            "synthetic scenario data. SUMO is not installed on this system. "
            "Results are labeled 'DeterministicEstimate' and do not represent "
            "field-observed or SUMO-simulated traffic."
        ),
        status="deterministic",
        simulationMethod="DeterministicEstimate",
        metrics=metrics,
        timeIntervals=cand_intervals,
        improvements=improvements,
        remainingRisks=risks,
    )

    _simulation_cache[run_id] = result
    logger.info(f"Simulation run '{run_id}' completed for schedule '{schedule.id}'.")
    return result


def get_simulation_result(run_id: str) -> Optional[SimulationResult]:
    return _simulation_cache.get(run_id)


def get_comparison_report(run_id: str) -> Optional[ComparisonReport]:
    result = _simulation_cache.get(run_id)
    if not result:
        return None
    m = result.metrics
    def reduction(delta_pct: Optional[float]) -> float:
        return max(0.0, -delta_pct) if delta_pct is not None else 0.0

    def change(delta_pct: Optional[float]) -> str:
        if delta_pct is None:
            return "not comparable"
        if delta_pct < 0:
            return f"{abs(delta_pct):.1f}% lower"
        if delta_pct > 0:
            return f"{delta_pct:.1f}% higher"
        return "no modeled change"

    return ComparisonReport(
        baselineRunId=f"{run_id}-baseline",
        optimizedRunId=run_id,
        candidateId=result.candidateId,
        candidateName=result.candidateName,
        queueReductionPct=reduction(m.peakQueue.deltaPct),
        waitReductionPct=reduction(m.waitTimeP95.deltaPct),
        delayReductionPct=reduction(m.totalDelay.deltaPct),
        spillbackEliminated=(
            m.spillbackDistance.baseline > 0
            and m.spillbackDistance.candidate == 0
        ),
        overallImprovement=(
            f"Queue: {change(m.peakQueue.deltaPct)}; "
            f"wait: {change(m.waitTimeP95.deltaPct)}; "
            f"delay: {change(m.totalDelay.deltaPct)}"
        ),
    )


def reset_simulations() -> None:
    """Clear all simulation cache (used by reset endpoint)."""
    _simulation_cache.clear()
    _schedule_store.clear()
    logger.info("Simulation cache and schedule store cleared.")
