from pathlib import Path
import csv
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SIM = ROOT / "data" / "simulations" / "school_demo"
OUT = SIM / "experiment_runs"
HANDOFF = SIM / "FINAL_HANDOFF_RATHI"
HANDOFF.mkdir(parents=True, exist_ok=True)

def write_csv(name, fields, rows):
    with (HANDOFF / name).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

groups = [
    {"group_id": "G1", "group_name": "Kindergarten", "student_count": 150, "sibling_pair": "", "fixed_offset_minutes": 0, "allowed_offsets_minutes": "[0]"},
    {"group_id": "G2", "group_name": "Grades 1-2", "student_count": 200, "sibling_pair": "", "fixed_offset_minutes": "", "allowed_offsets_minutes": "[-15,-10,-5,0,5,10,15]"},
    {"group_id": "G3", "group_name": "Grades 3-4", "student_count": 220, "sibling_pair": "SIBLING_A", "fixed_offset_minutes": "", "allowed_offsets_minutes": "[-15,-10,-5,0,5,10,15]"},
    {"group_id": "G4", "group_name": "Grades 5-6", "student_count": 230, "sibling_pair": "SIBLING_A", "fixed_offset_minutes": "", "allowed_offsets_minutes": "[-15,-10,-5,0,5,10,15]"},
    {"group_id": "G5", "group_name": "Grades 7-8", "student_count": 200, "sibling_pair": "", "fixed_offset_minutes": "", "allowed_offsets_minutes": "[-15,-10,-5,0,5,10,15]"},
    {"group_id": "G6", "group_name": "Grades 9-10", "student_count": 200, "sibling_pair": "", "fixed_offset_minutes": "", "allowed_offsets_minutes": "[-5,0,5]"}
]
write_csv("student_groups.csv", list(groups[0]), groups)

zones = [
    {"zone_id": "Z1", "zone_name": "Main gate kerb", "capacity": 10, "allowed_vehicle_types": "car;two_wheeler", "capacity_unit": "vehicles", "assumption_source": "Project specification; capacity unit interpreted as simultaneous vehicles; unverified"},
    {"zone_id": "Z2", "zone_name": "Side lane", "capacity": 3, "allowed_vehicle_types": "car;two_wheeler;auto_van", "capacity_unit": "vehicles", "assumption_source": "Project specification; capacity unit interpreted as simultaneous vehicles; unverified"},
    {"zone_id": "Z3", "zone_name": "Rear lot", "capacity": 12, "allowed_vehicle_types": "car;two_wheeler;auto_van", "capacity_unit": "vehicles", "assumption_source": "Project specification; capacity unit interpreted as simultaneous vehicles; unverified"},
    {"zone_id": "Z4", "zone_name": "Bus bay", "capacity": 4, "allowed_vehicle_types": "bus", "capacity_unit": "vehicles", "assumption_source": "Project specification; capacity unit interpreted as simultaneous vehicles; unverified"}
]
write_csv("pickup_zones.csv", list(zones[0]), zones)

scenario_manifest = {
    "project": "GateFlow AI",
    "scenario_id": "gateflow_school_demo",
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "network_type": "fictional synthetic SUMO network",
    "baseline_start": "08:00",
    "simulation_horizon_seconds": 3600,
    "seed": 20261024,
    "offset_options_minutes": [-15, -10, -5, 0, 5, 10, 15],
    "constraints": {
        "G1_fixed_offset_minutes": 0,
        "G3_G4_same_offset": True,
        "G6_allowed_offsets_minutes": [-5, 0, 5]
    },
    "uniform_benchmark_offsets": {"G1": 0, "G2": 5, "G3": 10, "G4": 10, "G5": 15, "G6": 5},
    "optimized_candidate_offsets": {"G1": 0, "G2": -10, "G3": -5, "G4": -5, "G5": 10, "G6": 5},
    "stress_demand_multiplier": 1.3,
    "notes": [
        "Synthetic demonstration only; not field-validated.",
        "Optimized offsets are a planner-selected candidate, not proof of globally optimal SUMO performance.",
        "Pickup-zone capacities are assumptions pending confirmation."
    ]
}
(HANDOFF / "scenario_manifest.json").write_text(json.dumps(scenario_manifest, indent=2), encoding="utf-8")

obs_fields = ["scenario_id", "run_id", "timestamp_seconds", "interval_seconds", "approach_queue_vehicles", "zone_id", "zone_occupancy_vehicles", "arrivals_vehicles", "departures_vehicles", "mean_wait_seconds", "p95_wait_seconds", "spillback_detected", "source_engine", "source_file", "seed"]
write_csv("traffic_observations.csv", obs_fields, [])

summary_fields = ["scenario_id", "run_id", "plan_type", "demand_multiplier", "seed", "simulation_horizon_seconds", "vehicles_generated", "vehicles_inserted", "vehicles_completed", "vehicles_unfinished", "completion_rate", "mean_wait_seconds", "p95_wait_seconds", "mean_trip_duration_seconds", "mean_time_loss_seconds", "peak_approach_queue_vehicles", "peak_zone_occupancy_vehicles", "spillback_duration_seconds", "zone_capacity_violations", "source_engine", "validation_status"]

summary_rows = []
for run_id, multiplier, plan_type in [
    ("baseline", 1.0, "baseline"),
    ("uniform", 1.0, "uniform"),
    ("optimized", 1.0, "planner_candidate"),
    ("stress_1_3x", 1.3, "stress")
]:
    metrics_path = OUT / run_id / "run_metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        generated = metrics.get("generated", "")
        completed = metrics.get("completed", "")
        unfinished = metrics.get("unfinished", "")
        rate = metrics.get("completion_rate", "")
    else:
        generated = completed = unfinished = rate = ""
    summary_rows.append({
        "scenario_id": "gateflow_school_demo",
        "run_id": run_id,
        "plan_type": plan_type,
        "demand_multiplier": multiplier,
        "seed": 20261024,
        "simulation_horizon_seconds": 3600,
        "vehicles_generated": generated,
        "vehicles_inserted": "",
        "vehicles_completed": completed,
        "vehicles_unfinished": unfinished,
        "completion_rate": rate,
        "mean_wait_seconds": "",
        "p95_wait_seconds": "",
        "mean_trip_duration_seconds": "",
        "mean_time_loss_seconds": "",
        "peak_approach_queue_vehicles": "",
        "peak_zone_occupancy_vehicles": "",
        "spillback_duration_seconds": "",
        "zone_capacity_violations": "",
        "source_engine": "SUMO",
        "validation_status": "PARTIAL"
    })

write_csv("simulation_run_summary.csv", summary_fields, summary_rows)

quality_report = {
    "report_status": "PARTIAL",
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "checks": {
        "student_groups_csv_created": (HANDOFF / "student_groups.csv").exists(),
        "pickup_zones_csv_created": (HANDOFF / "pickup_zones.csv").exists(),
        "scenario_manifest_created": (HANDOFF / "scenario_manifest.json").exists(),
        "summary_has_four_scenarios": len(summary_rows) == 4,
        "traffic_observations_are_header_only": True
    },
    "warnings": [
        "Traffic observations are empty because verified time-series queue and zone measurements are not yet available.",
        "Vehicle insertion counts are not inferred from generated demand.",
        "Pickup-zone capacities are assumptions and need confirmation.",
        "Simulation results use a fictional network and synthetic demand.",
        "Review raw tripinfo records before treating unfinished or missing records as explained."
    ]
}
(HANDOFF / "data_quality_report.json").write_text(json.dumps(quality_report, indent=2), encoding="utf-8")

readme = """# GateFlow AI — Rathi Data Handoff

This folder contains preliminary canonical scenario datasets and a partial simulation summary.

- `student_groups.csv`: school group counts and allowed offsets.
- `pickup_zones.csv`: pickup-zone configuration; capacity units are assumptions pending confirmation.
- `scenario_manifest.json`: reproducibility metadata and scenario constraints.
- `data_quality_report.json`: current quality status and known limitations.
- `simulation_run_summary.csv`: four scenario rows using the available run metrics.
- `traffic_observations.csv`: required schema only; intentionally no fabricated measurements.

All simulation outputs are synthetic and use a fictional network. Queue, occupancy, spillback, insertion, and capacity-violation metrics remain blank until measured from suitable SUMO outputs. Status is PARTIAL, not PASS.
"""
(HANDOFF / "README_DATA.md").write_text(readme, encoding="utf-8")

print("Created preliminary handoff:", HANDOFF)
print("Files:", len(list(HANDOFF.iterdir())))
print("Summary scenarios:", len(summary_rows))
print("Status: PARTIAL — validation scripts and real queue/zone measurements are still required.")
