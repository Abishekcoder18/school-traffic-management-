
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
INTERVAL = 60


def read_xml(path):
    return ET.parse(path).getroot()


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n >= 0 else None
    except (TypeError, ValueError):
        return None


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    return round(values[max(0, math.ceil(p * len(values)) - 1)], 3)


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="raise"
        )
        writer.writeheader()
        writer.writerows(rows)


def valid_completed_trip(trip):
    arrival = number(trip.get("arrival"))
    duration = number(trip.get("duration"))
    return (
        arrival is not None
        and duration is not None
        and not trip.get("vaporized")
    )


def clean_value(value):
    return "" if value is None else value


summary_rows = []
observation_rows = []
quality = []

for scenario_id, plan_type, multiplier in SCENARIOS:
    folder = DIAG / scenario_id
    demand_file = folder / "demand.rou.xml"
    summary_file = folder / "summary.xml"
    trip_file = folder / "tripinfo.xml"
    queue_file = folder / "queues.xml"

    missing = [
        p.name
        for p in (demand_file, summary_file, trip_file, queue_file)
        if not p.exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"{scenario_id}: missing required files: {missing}"
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
        if number(e.get("time")) is not None
    ]
    if not steps:
        raise ValueError(f"{scenario_id}: summary.xml has no steps")

    inserted_values = []
    for step in steps:
        value = number(step.get("inserted"))
        if value is not None:
            inserted_values.append(int(value))

    inserted = max(inserted_values, default=0)

    trip_root = read_xml(trip_file)
    trips = trip_root.findall("tripinfo")
    completed = [t for t in trips if valid_completed_trip(t)]

    completed_count = len(completed)
    unfinished_trip_records = len(trips) - completed_count

    if completed_count > inserted:
        raise ValueError(
            f"{scenario_id}: completed trip records ({completed_count}) "
            f"exceed inserted counter ({inserted}). Inspect source outputs."
        )

    # This is an inserted-vehicle estimate, distinct from trip-record count.
    unfinished_vehicles = inserted - completed_count

    waits = [
        n for t in completed
        if (n := number(t.get("waitingTime"))) is not None
    ]
    durations = [
        n for t in completed
        if (n := number(t.get("duration"))) is not None
    ]
    losses = [
        n for t in completed
        if (n := number(t.get("timeLoss"))) is not None
    ]

    completion_rate = completed_count / generated if generated else None

    summary_row = {
        "scenario_id": scenario_id,
        "run_id": f"{scenario_id}_seed{SEED}",
        "plan_type": plan_type,
        "demand_multiplier": multiplier,
        "seed": SEED,
        "simulation_horizon_seconds": HORIZON,
        "vehicles_generated": generated,
        "vehicles_inserted": inserted,
        "vehicles_completed": completed_count,
        "vehicles_unfinished": unfinished_vehicles,
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
    }
    summary_rows.append(summary_row)

    previous_arrived = 0
    previous_time = None

    for step in steps:
        timestamp = float(step.get("time", "0"))
        arrived_value = number(step.get("arrived"))
        arrived = int(arrived_value) if arrived_value is not None else None

        if arrived is not None:
            delta_arrived = max(0, arrived - previous_arrived)
            previous_arrived = max(previous_arrived, arrived)
        else:
            delta_arrived = ""

        interval = (
            timestamp - previous_time
            if previous_time is not None
            else INTERVAL
        )

        mean_wait = number(step.get("meanWaitingTime"))

        observation_rows.append({
            "scenario_id": scenario_id,
            "run_id": f"{scenario_id}_seed{SEED}",
            "timestamp_seconds": int(timestamp),
            "interval_seconds": int(interval) if interval >= 0 else "",
            "approach_queue_vehicles": "",
            "zone_id": "",
            "zone_occupancy_vehicles": "",
            "arrivals_vehicles": delta_arrived,
            "departures_vehicles": "",
            "mean_wait_seconds": clean_value(mean_wait),
            "p95_wait_seconds": "",
            "spillback_detected": "",
            "source_engine": ENGINE,
            "source_file": "summary.xml",
            "seed": SEED,
        })

        previous_time = timestamp

    queue_root = read_xml(queue_file)
    queue_timesteps = [
        d for d in queue_root.findall("data")
        if number(d.get("timestep")) is not None
    ]
    nonempty_queue_timesteps = sum(
        1 for d in queue_timesteps
        if d.find("lanes") is not None and len(d.find("lanes")) > 0
    )

    quality.append({
        "scenario_id": scenario_id,
        "generated_demand_ids": generated,
        "summary_final_inserted_counter": inserted,
        "tripinfo_records": len(trips),
        "completed_trip_records": completed_count,
        "unfinished_trip_records": unfinished_trip_records,
        "estimated_unfinished_inserted_vehicles": unfinished_vehicles,
        "queue_timesteps": len(queue_timesteps),
        "queue_timesteps_with_lane_records": nonempty_queue_timesteps,
        "approach_queue_vehicle_count": "UNAVAILABLE",
        "zone_occupancy": "UNAVAILABLE",
        "spillback_duration": "UNAVAILABLE",
        "zone_capacity_violations": "UNAVAILABLE",
        "status": "PARTIAL_REQUIRES_REVIEW",
    })

write_csv(
    OUT / "simulation_run_summary.csv",
    SUMMARY_FIELDS,
    summary_rows,
)

write_csv(
    OUT / "traffic_observations.csv",
    OBS_FIELDS,
    observation_rows,
)

quality_report = {
    "source_engine": ENGINE,
    "seed": SEED,
    "simulation_horizon_seconds": HORIZON,
    "summary_rows": len(summary_rows),
    "observation_rows": len(observation_rows),
    "summary_columns": SUMMARY_FIELDS,
    "observation_columns": OBS_FIELDS,
    "scenario_checks": quality,
    "metric_definitions": {
        "vehicles_generated": "Unique vehicle IDs in demand.rou.xml.",
        "vehicles_inserted": (
            "Maximum inserted counter reported by SUMO summary.xml."
        ),
        "vehicles_completed": (
            "Trip records with valid non-negative arrival and duration, "
            "excluding records with a vaporized attribute."
        ),
        "vehicles_unfinished": (
            "Inserted counter minus completed trip-record count. "
            "This is an estimate and assumes completed records belong "
            "to the inserted population."
        ),
        "completion_rate": (
            "Completed trip records divided by generated unique demand IDs."
        ),
        "unfinished_trip_records": (
            "Reported separately in this quality report; this can differ "
            "from estimated unfinished inserted vehicles."
        ),
        "arrivals_vehicles": (
            "Interval change in SUMO's cumulative arrived counter."
        ),
        "mean_wait_seconds": (
            "Network-level mean waiting time from summary.xml when valid."
        ),
    },
    "limitations": [
        "Queue output reports lane queue lengths, not directly vehicle counts.",
        "Approach-specific vehicle queues are not currently measured.",
        "Pickup-zone occupancy and capacity violations are not measured.",
        "Spillback duration is not calculated without a validated definition.",
        "Observation rows are network-level records; zone fields remain blank.",
        "Departures from pickup zones are not measured by summary.xml.",
        "Observation p95 waiting time is blank because summary.xml does not "
        "provide interval-level waiting-time distributions.",
        "The inserted-minus-completed estimate should be interpreted alongside "
        "the source trip-record counts.",
    ],
}

with (OUT / "csv_quality_report.json").open("w", encoding="utf-8") as f:
    json.dump(quality_report, f, indent=2)

for filename, fields, expected_rows in [
    ("simulation_run_summary.csv", SUMMARY_FIELDS, 4),
    ("traffic_observations.csv", OBS_FIELDS, len(observation_rows)),
]:
    with (OUT / filename).open(
        newline="", encoding="utf-8-sig"
    ) as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == fields, (
            f"{filename}: column names/order do not match"
        )
        rows = list(reader)
        assert len(rows) == expected_rows, (
            f"{filename}: unexpected row count"
        )

assert {r["scenario_id"] for r in summary_rows} == {
    "baseline", "uniform", "optimized", "stress_1_3x"
}
assert len(observation_rows) == len(SCENARIOS) * len(steps)

print("\nCSV PROCESSING COMPLETE")
print("Output folder:", OUT)
print("Summary rows:", len(summary_rows), "| columns:", len(SUMMARY_FIELDS))
print(
    "Observation rows:",
    len(observation_rows),
    "| columns:",
    len(OBS_FIELDS)
)

for r in summary_rows:
    print(
        r["scenario_id"],
        "generated=", r["vehicles_generated"],
        "inserted=", r["vehicles_inserted"],
        "completed=", r["vehicles_completed"],
        "estimated_unfinished=", r["vehicles_unfinished"],
        "completion_rate=", r["completion_rate"],
    )

print("Validation: schemas, row counts, and scenario coverage passed.")
print("Review csv_quality_report.json before sharing.")
