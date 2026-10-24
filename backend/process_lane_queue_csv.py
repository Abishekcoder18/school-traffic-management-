
import csv
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
SIM = ROOT / "data" / "simulations" / "school_demo"
DIAG = SIM / "experiment_diagnostics"
OUT = SIM / "FINAL_HANDOFF_RATHI"
OUT.mkdir(parents=True, exist_ok=True)

SCENARIOS = ["baseline", "uniform", "optimized", "stress_1_3x"]
SEED = 20261024
ENGINE = "SUMO"

FIELDS = [
    "scenario_id",
    "run_id",
    "timestamp_seconds",
    "lane_id",
    "lane_type",
    "queueing_time_seconds",
    "queueing_length_m",
    "queueing_length_experimental_m",
    "source_engine",
    "source_file",
    "seed",
]


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def classify_lane(lane_id):
    lane = lane_id.upper()

    if "ZONE" in lane or "BUS_BAY" in lane:
        return "pickup_zone"
    if "APPROACH" in lane or "_IN_" in lane:
        return "approach"
    return "other"


rows = []
scenario_stats = {}

for scenario in SCENARIOS:
    path = DIAG / scenario / "queues.xml"

    if not path.exists():
        raise FileNotFoundError(f"Missing queue file: {path}")

    root = ET.parse(path).getroot()
    timestep_count = 0
    lane_count = 0
    maxima = defaultdict(float)
    type_counts = defaultdict(int)

    for data in root.findall("data"):
        timestamp = number(data.get("timestep"))
        if timestamp is None:
            continue

        timestep_count += 1
        lanes = data.find("lanes")

        if lanes is None:
            continue

        for lane in lanes.findall("lane"):
            lane_id = lane.get("id")
            if not lane_id:
                continue

            queue_time = number(lane.get("queueing_time"))
            queue_length = number(lane.get("queueing_length"))
            experimental_length = number(
                lane.get("queueing_length_experimental")
            )

            lane_type = classify_lane(lane_id)
            lane_count += 1
            type_counts[lane_type] += 1

            if queue_length is not None:
                maxima[lane_type] = max(
                    maxima[lane_type], queue_length
                )

            rows.append({
                "scenario_id": scenario,
                "run_id": f"{scenario}_seed{SEED}",
                "timestamp_seconds": round(timestamp, 3),
                "lane_id": lane_id,
                "lane_type": lane_type,
                "queueing_time_seconds": (
                    "" if queue_time is None else round(queue_time, 3)
                ),
                "queueing_length_m": (
                    "" if queue_length is None
                    else round(queue_length, 3)
                ),
                "queueing_length_experimental_m": (
                    "" if experimental_length is None
                    else round(experimental_length, 3)
                ),
                "source_engine": ENGINE,
                "source_file": "queues.xml",
                "seed": SEED,
            })

    scenario_stats[scenario] = {
        "queue_timesteps": timestep_count,
        "observed_lane_records": lane_count,
        "lane_records_by_type": dict(type_counts),
        "peak_observed_queue_length_m_by_lane_type": dict(maxima),
    }

output_file = OUT / "lane_queue_observations.csv"

with output_file.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)

with (OUT / "lane_queue_quality_report.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump({
        "source_engine": ENGINE,
        "seed": SEED,
        "output_rows": len(rows),
        "columns": FIELDS,
        "scenarios": scenario_stats,
        "definitions": {
            "approach": (
                "Lane ID contains APPROACH or _IN_; confirm against "
                "the network definition before interpreting."
            ),
            "pickup_zone": (
                "Lane ID contains ZONE or BUS_BAY; classification is "
                "based on lane naming."
            ),
            "queueing_length_m": (
                "SUMO queueing_length reported in metres, not vehicles."
            ),
            "queueing_length_experimental_m": (
                "SUMO experimental queue length, kept separate from "
                "the standard queueing_length measurement."
            ),
        },
        "limitations": [
            "Only lane records present in queues.xml are exported.",
            "Missing lane records are not assumed to mean zero queue.",
            "Queue length is not converted into vehicle counts.",
            "This file does not establish actual pickup-zone occupancy.",
            "A queue alone does not prove traffic spillback.",
        ],
    }, f, indent=2)

with output_file.open(
    newline="", encoding="utf-8-sig"
) as f:
    reader = csv.DictReader(f)
    assert reader.fieldnames == FIELDS
    verified_rows = list(reader)
    assert len(verified_rows) == len(rows)

assert {row["scenario_id"] for row in rows} == set(SCENARIOS)

print("\nLANE QUEUE CSV COMPLETE")
print("Output:", output_file)
print("Rows:", len(rows))
print("Columns:", len(FIELDS))

for scenario, stats in scenario_stats.items():
    print(
        scenario,
        "timesteps=", stats["queue_timesteps"],
        "lane_records=", stats["observed_lane_records"],
        "peak_queue_m=", stats["peak_observed_queue_length_m_by_lane_type"],
    )

print("Validation: schema, row count, and scenario coverage passed.")
