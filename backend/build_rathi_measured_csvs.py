import csv
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "data" / "simulations" / "school_demo"
FCD_ROOT = SIM / "experiment_fcd"
DIAG_ROOT = SIM / "experiment_diagnostics"
OUT = SIM / "FINAL_HANDOFF_RATHI"

SEED = 20261024
HORIZON = 3600
INTERVAL = 60

SCENARIOS = {
    "baseline": ("current", 1.0),
    "uniform": ("uniform_benchmark", 1.0),
    "optimized": ("optimized", 1.0),
    "stress_1_3x": ("stress", 1.3),
}

LANE_TO_ZONE = {
    "E_ZONE_1_0": "Z1",
    "E_ZONE_2_0": "Z2",
    "E_ZONE_3_0": "Z3",
    "E_BUS_BAY_0": "Z4",
}

APPROACH_LANES = {"E_APPROACH_0", "E_APPROACH_1"}

SUMMARY_FIELDS = [
    "scenario_id", "run_id", "plan_type", "demand_multiplier", "seed",
    "simulation_horizon_seconds", "vehicles_generated", "vehicles_inserted",
    "vehicles_completed", "vehicles_unfinished", "completion_rate",
    "mean_wait_seconds", "p95_wait_seconds", "mean_trip_duration_seconds",
    "mean_time_loss_seconds", "peak_approach_queue_vehicles",
    "peak_zone_occupancy_vehicles", "spillback_duration_seconds",
    "zone_capacity_violations", "source_engine", "validation_status",
]

OBS_FIELDS = [
    "scenario_id", "run_id", "timestamp_seconds", "interval_seconds",
    "approach_queue_vehicles", "zone_id", "zone_occupancy_vehicles",
    "arrivals_vehicles", "departures_vehicles", "mean_wait_seconds",
    "p95_wait_seconds", "spillback_detected", "source_engine",
    "source_file", "seed",
]


def percentile(values, p):
    if not values:
        return ""
    values = sorted(values)
    return values[max(0, math.ceil(p * len(values)) - 1)]


def number(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_capacities():
    path = OUT / "pickup_zones.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Cannot calculate capacity comparisons safely."
        )

    capacities = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            zone = row.get("zone_id", "").strip()
            capacity = number(row.get("capacity"))
            if zone and capacity is not None:
                capacities[zone] = int(capacity)

    missing = set(LANE_TO_ZONE.values()) - set(capacities)
    if missing:
        raise ValueError(f"Missing capacity definitions for: {sorted(missing)}")
    return capacities


def load_demand(path):
    root = ET.parse(path).getroot()
    vehicles = root.findall("vehicle")
    return root, vehicles


def load_tripinfo(path):
    root = ET.parse(path).getroot()
    trips = root.findall("tripinfo")
    completed = [
        t for t in trips
        if number(t.get("arrival"), -1) >= 0
        and not t.get("vaporized")
    ]
    return trips, completed


def process_fcd(path, capacities):
    counts = {z: 0 for z in capacities}
    arrivals = Counter()
    departures = Counter()
    occupancy_at_end = {}
    max_occupancy = Counter()
    capacity_exceed_samples = Counter()
    approach_counts = []
    all_wait_samples = []
    interval_waits = {i: [] for i in range(HORIZON // INTERVAL)}
    interval_approach = Counter()
    interval_zone_peak = Counter()
    interval_zone_waits = {i: [] for i in range(HORIZON // INTERVAL)}
    inserted_ids = set()
    previous_lanes = {}
    rows = []
    peak_approach = 0
    timestep_count = 0
    vehicle_sample_count = 0
    first_time = None
    last_time = None

    for _, step in ET.iterparse(path, events=("end",)):
        if step.tag != "timestep":
            continue

        t = int(float(step.get("time", "0")))
        bucket = min(t // INTERVAL, HORIZON // INTERVAL - 1)
        if first_time is None:
            first_time = t
        last_time = t
        timestep_count += 1

        current_lanes = {}
        zone_counts = Counter()
        approach_queue = 0
        step_waits = []
        zone_waits = {z: [] for z in capacities}

        for vehicle in step.findall("vehicle"):
            vehicle_sample_count += 1
            vid = vehicle.get("id", "")
            lane = vehicle.get("lane", "")
            speed = number(vehicle.get("speed"), 0.0)
            waiting = number(vehicle.get("waiting"))
            inserted_ids.add(vid)
            current_lanes[vid] = lane

            if lane in APPROACH_LANES and speed <= 0.1:
                approach_queue += 1

            zone = LANE_TO_ZONE.get(lane)
            if zone:
                zone_counts[zone] += 1
                if waiting is not None:
                    zone_waits[zone].append(waiting)

            if waiting is not None:
                step_waits.append(waiting)
                all_wait_samples.append(waiting)
                interval_waits[bucket].append(waiting)

            previous_lane = previous_lanes.get(vid)
            previous_zone = LANE_TO_ZONE.get(previous_lane)
            current_zone = LANE_TO_ZONE.get(lane)

            if current_zone and previous_zone != current_zone:
                arrivals[(bucket, current_zone)] += 1
            if previous_zone and previous_zone != current_zone:
                departures[(bucket, previous_zone)] += 1

        for vid, previous_lane in previous_lanes.items():
            if vid not in current_lanes:
                previous_zone = LANE_TO_ZONE.get(previous_lane)
                if previous_zone:
                    departures[(bucket, previous_zone)] += 1

        previous_lanes = current_lanes

        peak_approach = max(peak_approach, approach_queue)
        interval_approach[bucket] = max(
            interval_approach[bucket], approach_queue
        )

        for zone, count in zone_counts.items():
            max_occupancy[zone] = max(max_occupancy[zone], count)
            interval_zone_peak[(bucket, zone)] = max(
                interval_zone_peak[(bucket, zone)], count
            )
            if count > capacities[zone]:
                capacity_exceed_samples[zone] += 1

        occupancy_at_end[t] = dict(zone_counts)

        rows.append({
            "time": t,
            "bucket": bucket,
            "approach_queue": approach_queue,
            "zone_counts": dict(zone_counts),
            "waits": step_waits,
            "zone_waits": zone_waits,
        })
        step.clear()

    if timestep_count != HORIZON:
        raise ValueError(
            f"{path}: expected {HORIZON} timesteps, got {timestep_count}"
        )

    observations = []
    for bucket in range(HORIZON // INTERVAL):
        end_time = (bucket + 1) * INTERVAL
        end_sample_time = end_time - 1
        snapshot = occupancy_at_end.get(end_sample_time, {})

        for zone in sorted(capacities):
            zone_waits = []
            for record in rows:
                if record["bucket"] == bucket:
                    zone_waits.extend(record["zone_waits"].get(zone, []))

            observations.append({
                "timestamp_seconds": end_time,
                "interval_seconds": INTERVAL,
                "approach_queue_vehicles": interval_approach[bucket],
                "zone_id": zone,
                "zone_occupancy_vehicles": snapshot.get(zone, 0),
                "arrivals_vehicles": arrivals[(bucket, zone)],
                "departures_vehicles": departures[(bucket, zone)],
                "mean_wait_seconds": (
                    round(mean(zone_waits), 3) if zone_waits else ""
                ),
                "p95_wait_seconds": percentile(zone_waits, 0.95),
                "spillback_detected": "",
                "source_engine": "SUMO",
                "source_file": f"experiment_fcd/{path.parent.name}/fcd.xml",
                "seed": SEED,
            })

    return {
        "observations": observations,
        "inserted_ids": inserted_ids,
        "peak_approach": peak_approach,
        "peak_zone": max(max_occupancy.values(), default=0),
        "capacity_exceed_samples": dict(capacity_exceed_samples),
        "zone_peak": dict(max_occupancy),
        "timesteps": timestep_count,
        "vehicle_samples": vehicle_sample_count,
        "first_time": first_time,
        "last_time": last_time,
    }


def main():
    capacities = load_capacities()
    summary_rows = []
    observation_rows = []
    quality = {
        "project": "GateFlow AI",
        "dataset": "Rathi measured CSV handoff",
        "seed": SEED,
        "horizon_seconds": HORIZON,
        "interval_seconds": INTERVAL,
        "zone_capacities": capacities,
        "capacity_source_warning": (
            "Capacity values are marked unverified in pickup_zones.csv. "
            "Violations are exceedance samples against those provisional limits."
        ),
        "definitions": {
            "approach_queue_vehicles": (
                "Vehicles on E_APPROACH lanes with speed <= 0.1 m/s; "
                "interval value is the maximum one-second count."
            ),
            "zone_occupancy_vehicles": (
                "Number of vehicles on the zone's designated lane at the "
                "final sample of each 60-second interval."
            ),
            "arrivals_vehicles": (
                "Observed transition into the designated zone lane. "
                "A vehicle already on that lane in the first FCD sample "
                "is not counted as a new arrival."
            ),
            "departures_vehicles": (
                "Observed transition out of the designated zone lane or "
                "disappearance from FCD while last observed in that zone."
            ),
            "zone_capacity_violations": (
                "Count of one-second zone occupancy snapshots above the "
                "provisional capacity, summed across all zones."
            ),
            "spillback": (
                "Unavailable: FCD stopped-vehicle counts do not alone prove "
                "physical spillback. Fields are left blank."
            ),
            "waiting_statistics": (
                "FCD waiting attribute sampled per vehicle per second; "
                "interval statistics are sample-weighted, not unique-trip metrics."
            ),
        },
        "runs": [],
    }

    for run_id, (plan_type, multiplier) in SCENARIOS.items():
        print(f"\nProcessing {run_id}...")
        fcd_path = FCD_ROOT / run_id / "fcd.xml"
        trip_path = FCD_ROOT / run_id / "tripinfo.xml"
        demand_path = DIAG_ROOT / run_id / "demand.rou.xml"

        for required in (fcd_path, trip_path, demand_path):
            if not required.exists():
                raise FileNotFoundError(f"Required input missing: {required}")

        _, demand_vehicles = load_demand(demand_path)
        trips, completed = load_tripinfo(trip_path)
        fcd = process_fcd(fcd_path, capacities)

        completed_ids = {t.get("id") for t in completed}
        observed_ids = fcd["inserted_ids"]
        completed_observed = len(completed_ids & observed_ids)
        unfinished = len(observed_ids - completed_ids)

        waits = [number(t.get("waitingTime")) for t in completed]
        waits = [x for x in waits if x is not None]
        durations = [number(t.get("duration")) for t in completed]
        durations = [x for x in durations if x is not None]
        losses = [number(t.get("timeLoss")) for t in completed]
        losses = [x for x in losses if x is not None]

        scenario_id = run_id
        run_label = f"{run_id}_seed{SEED}"

        summary_rows.append({
            "scenario_id": scenario_id,
            "run_id": run_label,
            "plan_type": plan_type,
            "demand_multiplier": multiplier,
            "seed": SEED,
            "simulation_horizon_seconds": HORIZON,
            "vehicles_generated": len(demand_vehicles),
            "vehicles_inserted": len(observed_ids),
            "vehicles_completed": completed_observed,
            "vehicles_unfinished": unfinished,
            "completion_rate": (
                round(completed_observed / len(demand_vehicles), 6)
                if demand_vehicles else ""
            ),
            "mean_wait_seconds": round(mean(waits), 3) if waits else "",
            "p95_wait_seconds": percentile(waits, 0.95),
            "mean_trip_duration_seconds": (
                round(mean(durations), 3) if durations else ""
            ),
            "mean_time_loss_seconds": round(mean(losses), 3) if losses else "",
            "peak_approach_queue_vehicles": fcd["peak_approach"],
            "peak_zone_occupancy_vehicles": fcd["peak_zone"],
            "spillback_duration_seconds": "",
            "zone_capacity_violations": sum(
                fcd["capacity_exceed_samples"].values()
            ),
            "source_engine": "SUMO",
            "validation_status": "MEASURED_WITH_LIMITATIONS",
        })

        for obs in fcd["observations"]:
            observation_rows.append({
                "scenario_id": scenario_id,
                "run_id": run_label,
                **obs,
            })

        quality["runs"].append({
            "scenario_id": scenario_id,
            "run_id": run_label,
            "generated": len(demand_vehicles),
            "fcd_observed_unique_vehicles": len(observed_ids),
            "tripinfo_records": len(trips),
            "completed_tripinfo_ids_observed_in_fcd": completed_observed,
            "unfinished_observed_vehicles": unfinished,
            "fcd_timesteps": fcd["timesteps"],
            "fcd_vehicle_samples": fcd["vehicle_samples"],
            "fcd_time_range": [fcd["first_time"], fcd["last_time"]],
            "peak_approach_queue_vehicles": fcd["peak_approach"],
            "peak_zone_occupancy_vehicles": fcd["peak_zone"],
            "peak_occupancy_by_zone": fcd["zone_peak"],
            "capacity_exceedance_samples_by_zone": fcd["capacity_exceed_samples"],
            "capacity_values_unverified": True,
            "spillback_duration_seconds": "UNAVAILABLE",
        })

        print("Generated:", len(demand_vehicles))
        print("FCD-observed vehicles:", len(observed_ids))
        print("Completed observed trip IDs:", completed_observed)
        print("Peak stopped approach queue:", fcd["peak_approach"])
        print("Peak single-zone occupancy:", fcd["peak_zone"])
        print("Capacity exceedance samples:", sum(fcd["capacity_exceed_samples"].values()))

    write_csv(OUT / "simulation_run_summary.csv", SUMMARY_FIELDS, summary_rows)
    write_csv(OUT / "traffic_observations.csv", OBS_FIELDS, observation_rows)

    quality["summary_rows"] = len(summary_rows)
    quality["observation_rows"] = len(observation_rows)
    quality["expected_observation_rows"] = (
        len(SCENARIOS) * (HORIZON // INTERVAL) * len(LANE_TO_ZONE)
    )
    quality["schema_validation"] = (
        "PASS" if all(
            list(row.keys()) == SUMMARY_FIELDS for row in summary_rows
        ) and all(
            list(row.keys()) == OBS_FIELDS for row in observation_rows
        ) else "FAIL"
    )
    quality["observation_row_count_validation"] = (
        "PASS" if len(observation_rows) == quality["expected_observation_rows"]
        else "FAIL"
    )

    report_path = OUT / "rathi_measured_csv_quality_report.json"
    report_path.write_text(
        json.dumps(quality, indent=2),
        encoding="utf-8",
    )

    print("\n=== CSV BUILD COMPLETE ===")
    print("Summary:", OUT / "simulation_run_summary.csv")
    print("Observation:", OUT / "traffic_observations.csv")
    print("Quality report:", report_path)
    print("Summary rows:", len(summary_rows))
    print("Observation rows:", len(observation_rows))
    print("Expected observation rows:", quality["expected_observation_rows"])
    print("Schema validation:", quality["schema_validation"])
    print("Row-count validation:", quality["observation_row_count_validation"])
    print("\nNOTE: Spillback remains blank; capacities are provisional.")
    print("Review the quality report before packaging the ZIP.")


if __name__ == "__main__":
    main()
