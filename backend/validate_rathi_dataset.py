
import csv
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIM = ROOT / "data" / "simulations" / "school_demo"
OUT = SIM / "FINAL_HANDOFF_RATHI"
ZIP_PATH = SIM / "RATHI_CSV_DATASET.zip"

EXPECTED_SCENARIOS = {
    "baseline", "uniform", "optimized", "stress_1_3x"
}


def read_csv(name):
    with (OUT / name).open(
        newline="", encoding="utf-8-sig"
    ) as f:
        return list(csv.DictReader(f))


summary = read_csv("simulation_run_summary.csv")
observations = read_csv("traffic_observations.csv")
lane_rows = read_csv("lane_queue_observations.csv")
metrics = read_csv("scenario_queue_metrics.csv")

assert len(summary) == 4, "Summary should contain four scenarios"
assert len(observations) == 240, "Expected 240 network observations"
assert len(lane_rows) == 1401, "Expected 1401 lane observations"
assert len(metrics) == 4, "Expected four scenario metric rows"

summary_ids = {r["scenario_id"] for r in summary}
metric_ids = {r["scenario_id"] for r in metrics}
lane_ids = {r["scenario_id"] for r in lane_rows}
observation_ids = {r["scenario_id"] for r in observations}

assert summary_ids == EXPECTED_SCENARIOS
assert metric_ids == EXPECTED_SCENARIOS
assert lane_ids == EXPECTED_SCENARIOS
assert observation_ids == EXPECTED_SCENARIOS

metric_by_scenario = {r["scenario_id"]: r for r in metrics}
summary_by_scenario = {r["scenario_id"]: r for r in summary}

for scenario in sorted(EXPECTED_SCENARIOS):
    scenario_lanes = [r for r in lane_rows if r["scenario_id"] == scenario]
    approach = [
        float(r["queueing_length_m"])
        for r in scenario_lanes
        if r["lane_type"] == "approach"
        and r["queueing_length_m"] != ""
    ]
    pickup = [
        float(r["queueing_length_m"])
        for r in scenario_lanes
        if r["lane_type"] == "pickup_zone"
        and r["queueing_length_m"] != ""
    ]

    recorded = metric_by_scenario[scenario]
    peak_approach = max(approach) if approach else None
    peak_pickup = max(pickup) if pickup else None

    if peak_approach is not None:
        assert abs(
            float(recorded["peak_approach_queue_length_m"]) - peak_approach
        ) <= 0.002, f"{scenario}: approach peak mismatch"

    if peak_pickup is not None:
        assert abs(
            float(recorded["peak_pickup_zone_queue_length_m"]) - peak_pickup
        ) <= 0.002, f"{scenario}: pickup-zone peak mismatch"

    s = summary_by_scenario[scenario]
    generated = int(s["vehicles_generated"])
    completed = int(s["vehicles_completed"])
    inserted = int(s["vehicles_inserted"])

    assert completed <= inserted, (
        f"{scenario}: completed exceeds inserted"
    )
    assert completed <= generated, (
        f"{scenario}: completed exceeds generated"
    )

    print(
        scenario,
        "generated=", generated,
        "inserted=", inserted,
        "completed=", completed,
        "peak approach m=", peak_approach,
        "peak pickup-zone m=", peak_pickup,
    )

with (OUT / "csv_quality_report.json").open(encoding="utf-8") as f:
    json.load(f)

with (OUT / "lane_queue_quality_report.json").open(encoding="utf-8") as f:
    json.load(f)

with (OUT / "scenario_queue_metrics_report.json").open(
    encoding="utf-8"
) as f:
    json.load(f)

assert ZIP_PATH.exists(), "Dataset ZIP is missing"

with zipfile.ZipFile(ZIP_PATH) as archive:
    assert archive.testzip() is None, "ZIP integrity test failed"
    contents = set(archive.namelist())

expected_files = {
    "simulation_run_summary.csv",
    "traffic_observations.csv",
    "lane_queue_observations.csv",
    "scenario_queue_metrics.csv",
    "csv_quality_report.json",
    "lane_queue_quality_report.json",
    "scenario_queue_metrics_report.json",
}

assert contents == expected_files, "ZIP file list does not match expected files"

print("\nCROSS-FILE VALIDATION: PASS")
print("Scenario IDs, queue peaks, counts, reports, and ZIP verified.")
