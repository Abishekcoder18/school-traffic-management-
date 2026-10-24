
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIM = ROOT / "data" / "simulations" / "school_demo"
OUT = SIM / "FINAL_HANDOFF_RATHI"

INPUT = OUT / "lane_queue_observations.csv"
OUTPUT = OUT / "scenario_queue_metrics.csv"
REPORT = OUT / "scenario_queue_metrics_report.json"

SCENARIOS = ["baseline", "uniform", "optimized", "stress_1_3x"]
SPILLBACK_PROXY_THRESHOLD_M = 100.0


def as_float(value):
    try:
        result = float(value)
        return result if result >= 0 else None
    except (TypeError, ValueError):
        return None


with INPUT.open(newline="", encoding="utf-8-sig") as f:
    observations = list(csv.DictReader(f))

if not observations:
    raise ValueError("Lane queue observations CSV is empty")

groups = defaultdict(list)

for row in observations:
    groups[row["scenario_id"]].append(row)

missing = set(SCENARIOS) - set(groups)
if missing:
    raise ValueError(f"Missing scenarios: {sorted(missing)}")

results = []
report = {
    "input_file": INPUT.name,
    "queue_length_unit": "metres",
    "spillback_proxy_threshold_m": SPILLBACK_PROXY_THRESHOLD_M,
    "scenarios": {},
    "limitations": [
        "Lane classification follows lane ID naming conventions.",
        "Queue length is not a vehicle count.",
        "A queue above the proxy threshold does not prove physical spillback.",
        "Queue durations are estimated from sampled timestamps.",
        "Missing lane records are not assumed to have zero queue.",
    ],
}

for scenario in SCENARIOS:
    rows = groups[scenario]
    approach = []
    pickup = []

    for row in rows:
        length = as_float(row.get("queueing_length_m"))
        if length is None:
            continue

        if row["lane_type"] == "approach":
            approach.append((float(row["timestamp_seconds"]), length, row["lane_id"]))
        elif row["lane_type"] == "pickup_zone":
            pickup.append((float(row["timestamp_seconds"]), length, row["lane_id"]))

    peak_approach = max(approach, key=lambda x: x[1], default=None)
    peak_pickup = max(pickup, key=lambda x: x[1], default=None)

    # Compute an observed queue-threshold proxy from approach lanes.
    # Only timestamps with at least one recorded approach lane are considered.
    by_time = defaultdict(list)
    for timestamp, length, lane_id in approach:
        by_time[timestamp].append(length)

    observed_times = sorted(by_time)
    proxy_duration = 0.0
    proxy_intervals = 0

    for index in range(len(observed_times) - 1):
        timestamp = observed_times[index]
        next_timestamp = observed_times[index + 1]
        interval = next_timestamp - timestamp

        if interval <= 0:
            continue

        if max(by_time[timestamp]) >= SPILLBACK_PROXY_THRESHOLD_M:
            proxy_duration += interval
            proxy_intervals += 1

    result = {
        "scenario_id": scenario,
        "observed_lane_records": len(rows),
        "approach_lane_records": sum(
            1 for row in rows if row["lane_type"] == "approach"
        ),
        "pickup_zone_lane_records": sum(
            1 for row in rows if row["lane_type"] == "pickup_zone"
        ),
        "peak_approach_queue_length_m": (
            round(peak_approach[1], 3) if peak_approach else ""
        ),
        "peak_approach_queue_timestamp_seconds": (
            peak_approach[0] if peak_approach else ""
        ),
        "peak_approach_lane_id": (
            peak_approach[2] if peak_approach else ""
        ),
        "peak_pickup_zone_queue_length_m": (
            round(peak_pickup[1], 3) if peak_pickup else ""
        ),
        "peak_pickup_zone_queue_timestamp_seconds": (
            peak_pickup[0] if peak_pickup else ""
        ),
        "peak_pickup_zone_lane_id": (
            peak_pickup[2] if peak_pickup else ""
        ),
        "approach_queue_threshold_proxy_duration_seconds": round(
            proxy_duration, 3
        ),
        "approach_queue_threshold_proxy_threshold_m": (
            SPILLBACK_PROXY_THRESHOLD_M
        ),
        "validation_status": "DERIVED_PROXY_REQUIRES_REVIEW",
    }
    results.append(result)

    report["scenarios"][scenario] = {
        "observed_approach_timestamps": len(observed_times),
        "timestamps_above_threshold": proxy_intervals,
        "peak_approach_queue": (
            {
                "length_m": round(peak_approach[1], 3),
                "timestamp_seconds": peak_approach[0],
                "lane_id": peak_approach[2],
            }
            if peak_approach else None
        ),
        "peak_pickup_zone_queue": (
            {
                "length_m": round(peak_pickup[1], 3),
                "timestamp_seconds": peak_pickup[0],
                "lane_id": peak_pickup[2],
            }
            if peak_pickup else None
        ),
    }

fields = list(results[0].keys())

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

with REPORT.open("w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

with OUTPUT.open(newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    checked = list(reader)
    assert reader.fieldnames == fields
    assert len(checked) == len(SCENARIOS)

print("\nSCENARIO QUEUE METRICS COMPLETE")
print("Output:", OUTPUT)
print("Report:", REPORT)

for row in results:
    print(
        row["scenario_id"],
        "peak_approach_m=", row["peak_approach_queue_length_m"],
        "peak_pickup_zone_m=", row["peak_pickup_zone_queue_length_m"],
        "threshold_proxy_seconds=",
        row["approach_queue_threshold_proxy_duration_seconds"],
    )

print("Validation: 4 scenarios, exact schema, valid JSON.")
