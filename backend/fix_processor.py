
import csv
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
SIM = ROOT / "data" / "simulations" / "school_demo"
DIAG = SIM / "experiment_diagnostics"
OUT = SIM / "FINAL_HANDOFF_RATHI"
OUT.mkdir(parents=True, exist_ok=True)

SCENARIOS = [
    ("baseline", "current", 1.0),
    ("uniform", "uniform_stagger", 1.0),
    ("optimized", "proposed", 1.0),
    ("stress_1_3x", "stress_test", 1.3),
]

SUMMARY_FIELDS = [
    "scenario_id", "run_id", "plan_type", "demand_multiplier",
    "seed", "simulation_horizon_seconds", "vehicles_generated",
    "vehicles_inserted", "vehicles_completed", "vehicles_unfinished",
    "completion_rate", "mean_wait_seconds", "p95_wait_seconds",
    "mean_trip_duration_seconds", "mean_time_loss_seconds",
    "peak_approach_queue_vehicles", "peak_zone_occupancy_vehicles",
    "spillback_duration_seconds", "zone_capacity_violations",
    "source_engine", "validation_status"
]

OBS_FIELDS = [
    "scenario_id", "run_id", "timestamp_seconds", "interval_seconds",
    "approach_queue_vehicles", "zone_id", "zone_occupancy_vehicles",
    "arrivals_vehicles", "departures_vehicles", "mean_wait_seconds",
    "p95_wait_seconds", "spillback_detected", "source_engine",
    "source_file", "seed"
]

SEED = 20261024
HORIZON = 3600
ENGINE = "SUMO"
EXPECTED_INTERVAL = 60


def read_xml(path):
    return ET.parse(path).getroot()


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def nonnegative(value):
    n = number(value)
    return n if n is not None and n >= 0 else None


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    return values[max(0, math.ceil(p * len(values)) - 1)]


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=fields, extrasaction="raise"
        )
        writer.writeheader()
        writer.writerows(rows)


summary_rows = []
observation_rows = []
quality = []

for scenario_id, plan_type, multiplier in SCENARIOS:
    folder = DIAG / scenario_id
    demand_file = folder / "demand.rou.xml"
    summary_file = folder / "summary.xml"
    trip_file = folder / "tripinfo.xml"
    queue_file = folder / "queues.xml"

    required = [demand_file, summary_file, trip_file, queue_file]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"{scenario_id}: missing diagnostic files: {missing}"
        )

    demand_root = read_xml(demand_file)
    demand_ids = {
        e.get("id")
        for e in demand_root.iter("vehicle")
        if e.get("id")
    }
    generated = len(demand_ids)

    summary_root = read_xml(summary_file)
    steps = [
        e for e in summary_root.findall("step")
        if nonnegative(e.get("time")) is not None
    ]
    if not steps:
        raise ValueError(f"{scenario_id}: summary.xml has no steps")

    last_step = max(steps, key=lambda e: float(e.get("time", "0")))
    last_summary_time = float(last_step.get("time", "0"))

    # SUMO cumulative counters at the last recorded summary timestep.
    summary_inserted = int(float(last_step.get("inserted", "0")))
    summary_arrived = int(float(last_step.get("arrived", "0")))

    trip_root = read_xml(trip_file)
    trips = trip_root.findall("tripinfo")

    # SUMO tripinfo includes trip records for completed and unfinished
    # vehicles when write-unfinished is enabled. Arrival presence identifies
    # completed trips; do not infer completion solely from record count.
    completed = [
        t for t in trips
        if nonnegative(t.get("arrival")) is not None
        and nonnegative(t.get("duration")) is not None
    ]
    completed_count = len(completed)
    trip_record_count = len(trips)

    waits = [
        nonnegative(t.get("waitingTime"))
        for t in completed
        if nonnegative(t.get("waitingTime")) is not None
    ]
    durations = [
        nonnegative(t.get("duration"))
        for t in completed
        if nonnegative(t.get("duration")) is not None
    ]
    losses = [
        nonnegative(t.get("timeLoss"))
        for t in completed
        if nonnegative(t.get("timeLoss")) is not None
    ]

    # Use trip records for a record-based unfinished estimate. Keep the
    # summary insertion counter separately in the quality report because
    # its final timestep may be earlier than the simulation horizon.
    unfinished_estimate = max(0, trip_record_count - completed_count)
    completion_rate = (
        completed_count / generated if generated else None
    )

    summary_rows.append({
        "scenario_id": scenario_id,
        "run_id": f"{scenario_id}_seed{SEED}",
        "plan_type": plan_type,
        "demand_multiplier": multiplier,
        "seed": SEED,
        "simulation_horizon_seconds": HORIZON,
        "vehicles_generated": generated,
        "vehicles_inserted": summary_inserted,
        "vehicles_completed": completed_count,
        "vehicles_unfinished": unfinished_estimate,
        "completion_rate": (
            round(completion_rate, 6)
            if completion_rate is not None else ""
        ),
        "mean_wait_seconds": round(mean(waits), 3) if waits else "",
        "p95_wait_seconds": percentile(waits, 0.95) if waits else "",
        "mean_trip_duration_seconds": (
            round(mean(durations), 3) if durations else ""
        ),
        "mean_time_loss_seconds": (
            round(mean(losses), 3) if losses else ""
        ),
        "peak_approach_queue_vehicles": "",
        "peak_zone_occupancy_vehicles": "",
        "spillback_duration_seconds": "",
        "zone_capacity_violations": "",
        "source_engine": ENGINE,
        "validation_status": "PARTIAL",
    })

    # Network-level time series from SUMO summary.xml.
    # Arrivals/departures here mean SUMO vehicles arriving at their final
    # destination during the interval; they do not mean pickup-zone events.
    previous_time = None
    previous_arrived = 0
    previous_inserted = 0

    for step in sorted(steps, key=lambda e: float(e.get("time", "0"))):
        timestamp = float(step.get("time", "0"))
        arrived = int(float(step.get("arrived", "0")))
        inserted = int(float(step.get("inserted", "0")))

        if previous_time is None:
            interval = EXPECTED_INTERVAL
            arrivals = arrived
            departures = inserted
        else:
            interval = timestamp - previous_time
            arrivals = max(0, arrived - previous_arrived)
            departures = max(0, inserted - previous_inserted)

        waiting = nonnegative(step.get("meanWaitingTime"))

        observation_rows.append({
            "scenario_id": scenario_id,
            "run_id": f"{scenario_id}_seed{SEED}",
            "timestamp_seconds": int(timestamp),
            "interval_seconds": (
                int(interval) if interval >= 0 else ""
            ),
            "approach_queue_vehicles": "",
            "zone_id": "",
            "zone_occupancy_vehicles": "",
            "arrivals_vehicles": arrivals,
            "departures_vehicles": departures,
            "mean_wait_seconds": waiting if waiting is not None else "",
            "p95_wait_seconds": "",
            "spillback_detected": "",
            "source_engine": ENGINE,
            "source_file": "summary.xml",
            "seed": SEED,
        })

        previous_time = timestamp
        previous_arrived = arrived
        previous_inserted = inserted

    queue_root = read_xml(queue_file)
    nonempty_queue_steps = [
        d for d in queue_root
        if d.find("lanes") is not None and len(d.find("lanes")) > 0
    ]

    # Preserve measured queue LENGTH values as separate diagnostic details.
    # Do not convert metres into vehicle counts without a validated method.
    approach_lanes = {
        "E_APPROACH_0", "E_APPROACH_1"
    }
    approach_queue_lengths = []
    lane_queue_records = 0

    for timestep in queue_root:
        lanes = timestep.find("lanes")
        if lanes is None:
            continue
        for lane in lanes.findall("lane"):
            lane_queue_records += 1
            if lane.get("id") in approach_lanes:
                qlen = nonnegative(lane.get("queueing_length"))
                if qlen is not None:
                    approach_queue_lengths.append(qlen)

    quality.append({
        "scenario_id": scenario_id,
        "generated_demand_ids": generated,
        "summary_last_timestep_seconds": last_summary_time,
        "summary_inserted_counter_at_last_timestep": summary_inserted,
        "summary_arrived_counter_at_last_timestep": summary_arrived,
        "tripinfo_record_count": trip_record_count,
        "completed_trip_records": completed_count,
        "unfinished_trip_record_estimate": unfinished_estimate,
        "queue_timesteps_with_lane_records": len(nonempty_queue_steps),
        "lane_queue_records": lane_queue_records,
        "approach_queue_length_max_meters": (
            max(approach_queue_lengths)
            if approach_queue_lengths else None
        ),
        "approach_queue_vehicle_count": "UNAVAILABLE",
        "pickup_zone_occupancy": "UNAVAILABLE",
        "pickup_zone_arrivals_departures": "UNAVAILABLE",
        "spillback_duration": "UNAVAILABLE",
        "zone_capacity_violations": "UNAVAILABLE",
        "status": "PARTIAL_REQUIRES_REVIEW",
    })

summary_path = OUT / "simulation_run_summary.csv"
observations_path = OUT / "traffic_observations.csv"
quality_path = OUT / "csv_quality_report.json"

write_csv(summary_path, SUMMARY_FIELDS, summary_rows)
write_csv(observations_path, OBS_FIELDS, observation_rows)

with quality_path.open("w", encoding="utf-8") as f:
    json.dump({
        "source_engine": ENGINE,
        "seed": SEED,
        "configured_horizon_seconds": HORIZON,
        "summary_rows": len(summary_rows),
        "observation_rows": len(observation_rows),
        "summary_columns": SUMMARY_FIELDS,
        "observation_columns": OBS_FIELDS,
        "scenario_checks": quality,
        "limitations": [
            "Summary counters are cumulative values at the last recorded timestep.",
            "The last summary timestep may be earlier than the configured horizon.",
            "vehicles_inserted is the final sampled SUMO insertion counter.",
            "vehicles_unfinished is estimated from tripinfo records minus completed records.",
            "completion_rate is completed trip records divided by generated demand.",
            "Mean and percentile trip metrics use completed trips only.",
            "Queue lengths are reported by SUMO as lengths, not vehicle counts.",
            "Pickup-zone occupancy, zone-level arrivals/departures, spillback duration, and capacity violations are unavailable from the current outputs.",
            "The traffic observations are network-level summary observations, not zone-specific observations.",
            "The departures_vehicles column records changes in SUMO's cumulative insertion counter; it does not represent vehicles departing pickup zones.",
            "All results are synthetic SUMO simulation outputs, not real-world school traffic observations."
        ],
    }, f, indent=2)

# Validate exact CSV schemas and scenario coverage.
for path, expected_fields in [
    (summary_path, SUMMARY_FIELDS),
    (observations_path, OBS_FIELDS),
]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected_fields:
            raise ValueError(
                f"Invalid schema in {path.name}: {reader.fieldnames}"
            )
        rows = list(reader)
        if not rows:
            raise ValueError(f"{path.name} has no data rows")

if len(summary_rows) != 4:
    raise ValueError("Expected exactly four scenario summary rows.")

if {
    row["scenario_id"] for row in summary_rows
} != {"baseline", "uniform", "optimized", "stress_1_3x"}:
    raise ValueError("Scenario coverage check failed.")

print("\nCSV PROCESSING COMPLETE")
print("Output folder:", OUT)
print(f"Summary: {len(summary_rows)} rows, {len(SUMMARY_FIELDS)} columns")
print(
    f"Observations: {len(observation_rows)} rows, "
    f"{len(OBS_FIELDS)} columns"
)
for row in summary_rows:
    print(
        row["scenario_id"],
        "generated=", row["vehicles_generated"],
        "summary_inserted=", row["vehicles_inserted"],
        "completed=", row["vehicles_completed"],
        "unfinished_estimate=", row["vehicles_unfinished"],
        "completion_rate=", row["completion_rate"]
    )
print("Exact schema checks passed.")
print("Quality report:", quality_path)
print("Status: PARTIAL — review limitations before sharing.")
