
import csv
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import mean
from math import ceil

from app.planner import search_plans, validate_offsets
from app.simulation.runner import generate_routes

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "data" / "simulations" / "school_demo"
OUT = SIM / "experiment_diagnostics"
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


def read_tripinfo(path):
    trips = ET.parse(path).getroot().findall("tripinfo")
    completed = [
        t for t in trips
        if float(t.get("arrival", "-1")) >= 0
        and not t.get("vaporized")
    ]
    unfinished = [t for t in trips if t not in completed]
    return trips, completed, unfinished


def main():
    if not SUMO.exists():
        raise FileNotFoundError(f"SUMO executable not found: {SUMO}")
    if not NET.exists():
        raise FileNotFoundError(f"Network missing: {NET}")

    # Keep original experiment_runs intact.
    OUT.mkdir(parents=True, exist_ok=True)

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

    summaries = []
    demand_rows = []
    all_ok = True

    for run_id, plan_type, offsets, multiplier in scenarios:
        run_dir = OUT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        route_xml, generated = generate_routes(
            offsets=offsets,
            surge=multiplier,
            seed=SEED,
            zones=ZONES
        )

        route_file = run_dir / "demand.rou.xml"
        trip_file = run_dir / "tripinfo.xml"
        summary_file = run_dir / "summary.xml"
        queue_file = run_dir / "queues.xml"

        route_file.write_bytes(route_xml)
        routes_root = ET.fromstring(route_xml)
        route_map = {
            r.get("id"): r.get("edges", "")
            for r in routes_root.findall("route")
        }

        for v in routes_root.findall("vehicle"):
            route_edges = route_map.get(v.get("route"), "")
            vehicle_type = v.get("type", "")
            zone = ZONES.get(vehicle_type, "")

            demand_rows.append({
                "scenario_id": "gateflow_school_demo",
                "run_id": run_id,
                "plan_type": plan_type,
                "demand_multiplier": multiplier,
                "seed": SEED,
                "vehicle_id": v.get("id"),
                "depart_seconds": v.get("depart"),
                "vehicle_type": vehicle_type,
                "zone_id": zone,
                "route_edges": route_edges,
                "source_file": str(route_file.relative_to(SIM))
            })

        cmd = [
            str(SUMO),
            "-n", str(NET),
            "-r", str(route_file),
            "--seed", str(SEED),
            "--begin", "0",
            "--end", str(HORIZON),
            "--tripinfo-output", str(trip_file),
            "--tripinfo-output.write-unfinished", "true",
            "--summary-output", str(summary_file),
            "--summary-output.period", "60",
            "--queue-output", str(queue_file),
            "--queue-output.period", "60",
            "--duration-log.disable", "true",
            "--no-step-log", "true"
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=240
            )
        except subprocess.TimeoutExpired:
            (run_dir / "stderr.txt").write_text(
                "SUMO process timed out after 240 seconds.",
                encoding="utf-8"
            )
            all_ok = False
            summaries.append({
                "scenario_id": "gateflow_school_demo",
                "run_id": run_id,
                "plan_type": plan_type,
                "demand_multiplier": multiplier,
                "seed": SEED,
                "simulation_horizon_seconds": HORIZON,
                "vehicles_generated": generated,
                "source_engine": "SUMO",
                "validation_status": "FAIL"
            })
            continue

        (run_dir / "stdout.txt").write_text(
            proc.stdout or "", encoding="utf-8"
        )
        (run_dir / "stderr.txt").write_text(
            proc.stderr or "", encoding="utf-8"
        )

        if proc.returncode != 0 or not trip_file.exists():
            all_ok = False
            summaries.append({
                "scenario_id": "gateflow_school_demo",
                "run_id": run_id,
                "plan_type": plan_type,
                "demand_multiplier": multiplier,
                "seed": SEED,
                "simulation_horizon_seconds": HORIZON,
                "vehicles_generated": generated,
                "source_engine": "SUMO",
                "validation_status": "FAIL"
            })
            continue

        trips, completed, unfinished = read_tripinfo(trip_file)
        waits = [float(t.get("waitingTime", "0")) for t in completed]
        durations = [float(t.get("duration", "0")) for t in completed]
        losses = [float(t.get("timeLoss", "0")) for t in completed]

        demand_ids = [
            v.get("id") for v in routes_root.findall("vehicle")
        ]
        trip_ids = [t.get("id") for t in trips]
        missing_records = len(set(demand_ids) - set(trip_ids))
        duplicate_demand_ids = len(demand_ids) - len(set(demand_ids))
        duplicate_trip_ids = len(trip_ids) - len(set(trip_ids))

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
            "vehicles_without_tripinfo_record": missing_records,
            "duplicate_demand_ids": duplicate_demand_ids,
            "duplicate_trip_ids": duplicate_trip_ids,
            "completion_rate_of_generated": (
                round(len(completed) / generated, 4) if generated else None
            ),
            "vehicles_inserted": None,
            "mean_wait_seconds_completed_only": (
                round(mean(waits), 3) if waits else None
            ),
            "p95_wait_seconds_completed_only": percentile(waits, 0.95),
            "mean_trip_duration_seconds_completed_only": (
                round(mean(durations), 3) if durations else None
            ),
            "mean_time_loss_seconds_completed_only": (
                round(mean(losses), 3) if losses else None
            ),
            "summary_output_created": summary_file.exists(),
            "queue_output_created": queue_file.exists(),
            "peak_approach_queue_vehicles": None,
            "peak_zone_occupancy_vehicles": None,
            "spillback_duration_seconds": None,
            "zone_capacity_violations": None,
            "source_engine": "SUMO",
            "source_demand_file": str(route_file.relative_to(SIM)),
            "source_tripinfo_file": str(trip_file.relative_to(SIM)),
            "metric_notes": (
                "Generated vehicles without tripinfo are not automatically "
                "classified as unfinished or failed insertions. Queue output "
                "is junction queue data, not pickup-zone occupancy. "
                "Inspect XML before deriving additional metrics."
            ),
            "validation_status": (
                "PARTIAL" if missing_records or not summary_file.exists()
                or not queue_file.exists() else "REVIEW_REQUIRED"
            )
        }

        (run_dir / "run_metrics.json").write_text(
            json.dumps(metrics, indent=2),
            encoding="utf-8"
        )
        summaries.append(metrics)

    if demand_rows:
        with (OUT / "vehicle_demand_all_runs.csv").open(
            "w", newline="", encoding="utf-8-sig"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=list(demand_rows[0]))
            writer.writeheader()
            writer.writerows(demand_rows)

    summary_fields = [
        "scenario_id", "run_id", "plan_type", "demand_multiplier", "seed",
        "simulation_horizon_seconds", "vehicles_generated", "vehicles_inserted",
        "vehicles_completed", "vehicles_unfinished",
        "vehicles_without_tripinfo_record", "completion_rate_of_generated",
        "mean_wait_seconds_completed_only", "p95_wait_seconds_completed_only",
        "mean_trip_duration_seconds_completed_only",
        "mean_time_loss_seconds_completed_only",
        "summary_output_created", "queue_output_created",
        "peak_approach_queue_vehicles", "peak_zone_occupancy_vehicles",
        "spillback_duration_seconds", "zone_capacity_violations",
        "source_engine", "validation_status"
    ]

    with (OUT / "simulation_run_summary.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=summary_fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(summaries)

    manifest = {
        "project": "GateFlow AI",
        "network": str(NET),
        "seed": SEED,
        "horizon_seconds": HORIZON,
        "network_and_demand_are_synthetic": True,
        "optimized_offsets": optimized,
        "planner_candidate_estimates_are_not_simulation_measurements": True,
        "diagnostic_outputs": [
            "summary.xml",
            "queues.xml",
            "tripinfo.xml"
        ],
        "runs": [s["run_id"] for s in summaries]
    }
    (OUT / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    print(json.dumps({
        "output_directory": str(OUT),
        "all_processes_succeeded": all_ok,
        "runs": [{
            "run_id": s["run_id"],
            "generated": s.get("vehicles_generated"),
            "trip_records": s.get("trip_records_written"),
            "completed": s.get("vehicles_completed"),
            "unfinished": s.get("vehicles_unfinished"),
            "without_tripinfo": s.get("vehicles_without_tripinfo_record"),
            "summary_xml": s.get("summary_output_created", False),
            "queue_xml": s.get("queue_output_created", False),
            "status": s.get("validation_status")
        } for s in summaries]
    }, indent=2))


if __name__ == "__main__":
    main()
