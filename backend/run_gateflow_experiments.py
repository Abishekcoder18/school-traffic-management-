
import csv
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import mean
from math import ceil
from app.planner import search_plans, validate_offsets

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "data" / "simulations" / "school_demo"
OUT = SIM / "experiment_runs"
SUMO = Path(r"C:\Program Files (x86)\SUMO\bin\sumo.exe")
NET = SIM / "network.net.xml"
SEED = 20261024
HORIZON = 3600

BASELINE = {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0, "G6": 0}
UNIFORM = {"G1": 0, "G2": 5, "G3": 10, "G4": 10, "G5": 15, "G6": 5}
ZONES = {"car": "Z3", "two_wheeler": "Z1", "auto_van": "Z2", "bus": "Z4"}

def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    return values[max(0, ceil(p * len(values)) - 1)]

def main():
    if not SUMO.exists():
        raise FileNotFoundError(f"SUMO executable not found: {SUMO}")
    if not NET.exists():
        raise FileNotFoundError(f"Network missing: {NET}")

    planner = search_plans(limit=100)
    candidates = [
        p for p in planner["plans"]
        if p["offsets"] != BASELINE
        and p["offsets"] != UNIFORM
        and not validate_offsets(p["offsets"])
    ]
    candidates.sort(key=lambda p: (
        p["estimated_delay"],
        p["disruption"],
        tuple(p["offsets"][g] for g in BASELINE)
    ))
    if not candidates:
        raise RuntimeError("No distinct valid planner candidate was found.")

    optimized = candidates[0]["offsets"]
    scenarios = [
        ("baseline", "baseline", BASELINE, 1.0),
        ("uniform", "uniform_benchmark", UNIFORM, 1.0),
        ("optimized", "optimized", optimized, 1.0),
        ("stress_1_3x", "stress", optimized, 1.3),
    ]

    # Import the existing route generator; don't create a competing generator.
    from app.simulation.runner import generate_routes

    OUT.mkdir(parents=True, exist_ok=True)
    summaries = []
    demand_rows = []

    for run_id, plan_type, offsets, multiplier in scenarios:
        run_dir = OUT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        route_xml, generated = generate_routes(
            offsets=offsets, surge=multiplier, seed=SEED, zones=ZONES
        )
        route_file = run_dir / "demand.rou.xml"
        trip_file = run_dir / "tripinfo.xml"
        route_file.write_bytes(route_xml)

        routes_root = ET.fromstring(route_xml)
        route_map = {
            r.get("id"): r.get("edges", "")
            for r in routes_root.findall("route")
        }
        for v in routes_root.findall("vehicle"):
            demand_rows.append({
                "scenario_id": "gateflow_school_demo",
                "run_id": run_id,
                "plan_type": plan_type,
                "demand_multiplier": multiplier,
                "seed": SEED,
                "vehicle_id": v.get("id"),
                "depart_seconds": v.get("depart"),
                "vehicle_type": v.get("type"),
                "route_edges": route_map.get(v.get("route"), ""),
                "source_file": str(route_file.relative_to(SIM)),
            })

        cmd = [
            str(SUMO), "-n", str(NET), "-r", str(route_file),
            "--seed", str(SEED), "--begin", "0", "--end", str(HORIZON),
            "--tripinfo-output", str(trip_file), "--tripinfo-output.write-unfinished", "true",
            "--duration-log.disable", "true", "--no-step-log", "true",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        (run_dir / "stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
        (run_dir / "stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
        if proc.returncode != 0 or not trip_file.exists():
            summaries.append({
                "scenario_id": "gateflow_school_demo",
                "run_id": run_id,
                "plan_type": plan_type,
                "demand_multiplier": multiplier,
                "seed": SEED,
                "simulation_horizon_seconds": HORIZON,
                "vehicles_generated": generated,
                "source_engine": "SUMO",
                "validation_status": "FAIL",
            })
            continue

        trips = ET.parse(trip_file).getroot().findall("tripinfo")
        completed = [
            t for t in trips
            if float(t.get("arrival", "-1")) >= 0
            and not t.get("vaporized")
        ]
        unfinished = [
            t for t in trips
            if float(t.get("arrival", "-1")) < 0 or bool(t.get("vaporized"))
        ]

        waits = [float(t.get("waitingTime", "0")) for t in completed]
        durations = [float(t.get("duration", "0")) for t in completed]
        losses = [float(t.get("timeLoss", "0")) for t in completed]

        metrics = {
            "scenario_id": "gateflow_school_demo",
            "run_id": run_id,
            "plan_type": plan_type,
            "offsets": offsets,
            "demand_multiplier": multiplier,
            "seed": SEED,
            "simulation_horizon_seconds": HORIZON,
            "vehicles_generated": generated,
            "trip_records_written": len(trips),
            "vehicles_completed": len(completed),
            "vehicles_unfinished": len(unfinished),
            "completion_rate_of_generated": round(len(completed) / generated, 4) if generated else None,
            "vehicles_inserted": None,
            "mean_wait_seconds_completed_only": round(mean(waits), 3) if waits else None,
            "p95_wait_seconds_completed_only": percentile(waits, 0.95),
            "mean_trip_duration_seconds_completed_only": round(mean(durations), 3) if durations else None,
            "mean_time_loss_seconds_completed_only": round(mean(losses), 3) if losses else None,
            "peak_approach_queue_vehicles": None,
            "peak_zone_occupancy_vehicles": None,
            "spillback_duration_seconds": None,
            "zone_capacity_violations": None,
            "source_engine": "SUMO",
            "source_demand_file": str(route_file.relative_to(SIM)),
            "source_tripinfo_file": str(trip_file.relative_to(SIM)),
            "metric_notes": "Queue, occupancy, spillback and inserted counts not measured by this run configuration.",
            "validation_status": "PARTIAL",
        }
        (run_dir / "run_metrics.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8"
        )
        summaries.append(metrics)

    if demand_rows:
        with (OUT / "vehicle_demand_all_runs.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=list(demand_rows[0]))
            writer.writeheader()
            writer.writerows(demand_rows)

    summary_fields = [
        "scenario_id", "run_id", "plan_type", "demand_multiplier", "seed",
        "simulation_horizon_seconds", "vehicles_generated", "vehicles_inserted",
        "vehicles_completed", "vehicles_unfinished", "completion_rate_of_generated",
        "mean_wait_seconds_completed_only", "p95_wait_seconds_completed_only",
        "mean_trip_duration_seconds_completed_only", "mean_time_loss_seconds_completed_only",
        "peak_approach_queue_vehicles", "peak_zone_occupancy_vehicles",
        "spillback_duration_seconds", "zone_capacity_violations",
        "source_engine", "validation_status"
    ]
    with (OUT / "simulation_run_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)

    (OUT / "experiment_manifest.json").write_text(json.dumps({
        "network": str(NET),
        "seed": SEED,
        "horizon_seconds": HORIZON,
        "network_and_demand_are_synthetic": True,
        "optimized_offsets": optimized,
        "planner_candidate_estimates_are_not_simulation_measurements": True,
        "runs": [s["run_id"] for s in summaries],
    }, indent=2), encoding="utf-8")

    print(json.dumps({
        "output_directory": str(OUT),
        "runs": [{
            "run_id": s["run_id"],
            "generated": s.get("vehicles_generated"),
            "completed": s.get("vehicles_completed"),
            "unfinished": s.get("vehicles_unfinished"),
            "completion_rate": s.get("completion_rate_of_generated"),
            "status": s.get("validation_status")
        } for s in summaries],
    }, indent=2))

if __name__ == "__main__":
    main()
