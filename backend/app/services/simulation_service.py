"""GateFlow AI — Simulation Service (Feature 3: Test the Schedule)

Uses deterministic queuing theory (M/D/c approximation) to compute
simulation metrics for the selected schedule vs. baseline.

IMPORTANT: All results are labeled 'DeterministicEstimate'.
SUMO is not installed — no SUMO results are fabricated.
"""
from __future__ import annotations

import logging
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
    dwell_seconds: float,
    interval_min: int = 15,
) -> tuple[list[TimeInterval], dict]:
    """
    Simulate queue evolution using a time-bucket M/D/c model.
    Returns (time_series, peak_metrics).
    """
    BUCKET = 5  # internal simulation step (minutes)
    START = 150  # 2:30 PM in minutes from midnight
    END = 225    # 3:45 PM

    # Per-gate queue simulation
    gate_queues: dict[str, list[float]] = {g.id: [] for g in gates_by_id.values()}

    for gate in gates_by_id.values():
        gate_cohorts = [c for c in cohorts if c.assignedGateId == gate.id]
        c_servers = gate.bays
        mu_per_min = gate.hourlyCapacity / (gate.bays * 60.0)

        queue = 0.0
        for t in range(START, END + BUCKET, BUCKET):
            arrivals = 0.0
            for cohort in gate_cohorts:
                offset = offsets_by_cohort_id.get(cohort.id, 0)
                center = _hm_to_minutes(cohort.currentDismissalTime) + offset
                spread = 20  # minutes
                if abs(t - center) <= spread:
                    arrivals += (
                        cohort.vehicleDemand * demand_factor * (BUCKET / (spread * 2))
                    )

            served = min(queue + arrivals, c_servers * mu_per_min * BUCKET)
            queue = max(0.0, queue + arrivals - served)
            gate_queues[gate.id].append(queue)

    # Build time series at `interval_min` steps
    # Aggregate across all gates
    time_points = list(range(START, END + BUCKET, BUCKET))
    interval_buckets = range(START, END + BUCKET, interval_min)

    intervals: list[TimeInterval] = []
    for t_start in range(START, END, interval_min):
        # Average queue in this interval across all gates
        total_q = 0.0
        for gate in gates_by_id.values():
            step_indices = [
                i for i, t in enumerate(time_points) if t_start <= t < t_start + interval_min
            ]
            if step_indices:
                gate_q = sum(gate_queues[gate.id][i] for i in step_indices if i < len(gate_queues[gate.id])) / len(step_indices)
                total_q += gate_q

        intervals.append(
            TimeInterval(
                time=_minutes_to_display(t_start),
                baselineQueue=0.0,  # filled in later
                candidateQueue=round(total_q, 1),
                gateCapacity=float(gates_by_id["gate-2"].hourlyCapacity // 4),  # per-gate queue limit
            )
        )

    # Summary metrics
    all_queues = [iv.candidateQueue for iv in intervals]
    peak_q = max(all_queues) if all_queues else 0.0

    # P95 wait estimate via queuing formula
    # For M/D/c, approx wait ≈ queue / (effective service rate)
    bottleneck = max(gates_by_id.values(), key=lambda g: g.peakDemand / g.hourlyCapacity)
    eff_rate = bottleneck.bays * bottleneck.hourlyCapacity / bottleneck.bays / 60.0
    p95_wait_min = round(peak_q / max(eff_rate, 0.1) * 0.5, 1)

    # Total delay: area under queue curve × avg dwell
    total_delay_veh_hrs = round(
        sum(all_queues) * (interval_min / 60.0) * 0.5, 1
    )

    # Spillback estimate
    gate2 = gates_by_id.get("gate-2")
    gate2_q_index = next(
        (i for i, t in enumerate(time_points) if t == 180), None  # 3:00 PM
    )
    gate2_q_at_peak = gate_queues["gate-2"][gate2_q_index] if (gate2_q_index is not None and gate2_q_index < len(gate_queues.get("gate-2", []))) else 0.0
    spillback = round(max(0.0, gate2_q_at_peak - (gate2.bays * 5 if gate2 else 0)) * 3.75, 0)

    metrics = {
        "peak_queue": round(peak_q, 1),
        "p95_wait_min": p95_wait_min,
        "total_delay_veh_hrs": total_delay_veh_hrs,
        "spillback_meters": spillback,
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
    dwell_seconds = scenario.school.averageDwellTimeSeconds
    demand_factor = request.demandFactor

    # Extract offsets from the selected candidate's group schedule
    offsets_by_cohort_id: dict[str, int] = {}
    for row in schedule.groupSchedule:
        offsets_by_cohort_id[row.cohortId] = row.offsetMinutes

    # ── Run CANDIDATE simulation ──────────────────────────────────────────
    cand_intervals, cand_metrics = _simulate_queue_timeseries(
        cohorts, offsets_by_cohort_id, gates_by_id, demand_factor, dwell_seconds
    )

    # ── Run BASELINE simulation (identical conditions, zero offsets) ──────
    baseline_offsets = {c.id: 0 for c in cohorts}
    base_intervals, base_metrics = _simulate_queue_timeseries(
        cohorts, baseline_offsets, gates_by_id, demand_factor, dwell_seconds
    )

    # Inject baseline queue into the combined time series
    for i, iv in enumerate(cand_intervals):
        base_q = base_intervals[i].candidateQueue if i < len(base_intervals) else 0.0
        iv.baselineQueue = base_q

    # ── Compute delta % ───────────────────────────────────────────────────
    def _delta(base: float, cand: float) -> float:
        if base == 0:
            return 0.0
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
        improvements.append(
            f"Peak queue reduced from {base_metrics['peak_queue']:.0f} to "
            f"{cand_metrics['peak_queue']:.0f} vehicles "
            f"({abs(_delta(base_metrics['peak_queue'], cand_metrics['peak_queue'])):.1f}% improvement)."
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
        "Dwell time is fixed at the assumed average; variance will affect actual queues.",
    ]

    run_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = SimulationResult(
        runId=run_id,
        candidateId=schedule.id,
        candidateName=schedule.name,
        simulatedAt=now,
        fidelityNote=(
            "Deterministic planning estimate using M/D/c queuing theory with "
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
    return ComparisonReport(
        baselineRunId=f"{run_id}-baseline",
        optimizedRunId=run_id,
        candidateId=result.candidateId,
        candidateName=result.candidateName,
        queueReductionPct=abs(m.peakQueue.deltaPct),
        waitReductionPct=abs(m.waitTimeP95.deltaPct),
        delayReductionPct=abs(m.totalDelay.deltaPct),
        spillbackEliminated=m.spillbackDistance.candidate == 0,
        overallImprovement=(
            f"Queue: {m.peakQueue.deltaPct:.1f}%, "
            f"Wait: {m.waitTimeP95.deltaPct:.1f}%, "
            f"Delay: {m.totalDelay.deltaPct:.1f}%"
        ),
    )


def reset_simulations() -> None:
    """Clear all simulation cache (used by reset endpoint)."""
    _simulation_cache.clear()
    _schedule_store.clear()
    logger.info("Simulation cache and schedule store cleared.")
