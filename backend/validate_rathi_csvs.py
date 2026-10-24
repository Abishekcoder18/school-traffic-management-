import csv
from pathlib import Path
from collections import Counter

out = Path(r"E:\School_Traffic_Management\data\simulations\school_demo\FINAL_HANDOFF_RATHI")

expected = {
    "simulation_run_summary.csv": [
        "scenario_id", "run_id", "plan_type", "demand_multiplier", "seed",
        "simulation_horizon_seconds", "vehicles_generated", "vehicles_inserted",
        "vehicles_completed", "vehicles_unfinished", "completion_rate",
        "mean_wait_seconds", "p95_wait_seconds", "mean_trip_duration_seconds",
        "mean_time_loss_seconds", "peak_approach_queue_vehicles",
        "peak_zone_occupancy_vehicles", "spillback_duration_seconds",
        "zone_capacity_violations", "source_engine", "validation_status"
    ],
    "traffic_observations.csv": [
        "scenario_id", "run_id", "timestamp_seconds", "interval_seconds",
        "approach_queue_vehicles", "zone_id", "zone_occupancy_vehicles",
        "arrivals_vehicles", "departures_vehicles", "mean_wait_seconds",
        "p95_wait_seconds", "spillback_detected", "source_engine",
        "source_file", "seed"
    ]
}

def read_csv(name):
    with (out / name).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    return fields, rows

ok = True

for name, columns in expected.items():
    fields, rows = read_csv(name)
    passed = fields == columns
    print(f"\n{name}")
    print("Columns:", len(fields or []), "| Expected:", len(columns))
    print("Rows:", len(rows))
    print("Exact schema:", "PASS" if passed else "FAIL")
    if not passed:
        print("Actual headers:", fields)
        ok = False

summary_fields, summary = read_csv("simulation_run_summary.csv")
obs_fields, obs = read_csv("traffic_observations.csv")

print("\nSUMMARY CHECKS")
print("Expected 4 scenario rows:", "PASS" if len(summary) == 4 else "FAIL")
ok &= len(summary) == 4

for row in summary:
    inserted = int(row["vehicles_inserted"])
    completed = int(row["vehicles_completed"])
    unfinished = int(row["vehicles_unfinished"])
    generated = int(row["vehicles_generated"])
    rate = float(row["completion_rate"])
    checks = (
        completed + unfinished == inserted
        and completed <= inserted <= generated
        and abs(rate - completed / generated) < 0.000002
    )
    print(
        row["scenario_id"],
        "| inserted:", inserted,
        "| completed:", completed,
        "| not completed:", unfinished,
        "| consistency:", "PASS" if checks else "FAIL"
    )
    ok &= checks

print("\nOBSERVATION CHECKS")
scenarios = Counter(r["scenario_id"] for r in obs)
print("Rows per scenario:", dict(scenarios))
print("240 rows per scenario:", "PASS" if len(obs) == 960 and all(scenarios[s] == 240 for s in scenarios) and len(scenarios) == 4 else "FAIL")
ok &= len(obs) == 960 and len(scenarios) == 4 and all(scenarios[s] == 240 for s in scenarios)

zones = {"Z1", "Z2", "Z3", "Z4"}
keys = [(r["scenario_id"], r["timestamp_seconds"], r["zone_id"]) for r in obs]
unique_keys = len(keys) == len(set(keys))
print("Unique scenario/time/zone rows:", "PASS" if unique_keys else "FAIL")
ok &= unique_keys

grid_ok = True
for scenario in scenarios:
    subset = [r for r in obs if r["scenario_id"] == scenario]
    times = {int(r["timestamp_seconds"]) for r in subset}
    if times != set(range(60, 3601, 60)):
        grid_ok = False
    for t in times:
        if {r["zone_id"] for r in subset if int(r["timestamp_seconds"]) == t} != zones:
            grid_ok = False
print("Complete 60-second × 4-zone grid:", "PASS" if grid_ok else "FAIL")
ok &= grid_ok

numeric_fields = [
    "timestamp_seconds", "interval_seconds", "approach_queue_vehicles",
    "zone_occupancy_vehicles", "arrivals_vehicles", "departures_vehicles",
    "seed"
]
numeric_ok = True
for row in obs:
    for field in numeric_fields:
        try:
            value = float(row[field])
            if value < 0:
                numeric_ok = False
        except (ValueError, TypeError):
            numeric_ok = False

print("Required observation numbers valid and nonnegative:", "PASS" if numeric_ok else "FAIL")
ok &= numeric_ok

print("Spillback fields left blank:", "PASS" if all(not r["spillback_detected"] for r in obs) else "FAIL")
ok &= all(not r["spillback_detected"] for r in obs)

print("\nOVERALL:", "PASS" if ok else "FAIL")
