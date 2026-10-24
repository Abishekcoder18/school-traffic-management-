
from pathlib import Path
import json
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent.parent
runs = root / "data" / "simulations" / "school_demo" / "experiment_runs"

for run_id in ["baseline", "uniform", "optimized", "stress_1_3x"]:
    folder = runs / run_id
    demand_file = folder / "demand.rou.xml"
    trip_file = folder / "tripinfo.xml"
    metrics_file = folder / "run_metrics.json"

    print(f"\n--- {run_id} ---")

    if not all(p.exists() for p in [demand_file, trip_file, metrics_file]):
        print("BLOCKED: required input file missing")
        continue

    demand_root = ET.parse(demand_file).getroot()
    trip_root = ET.parse(trip_file).getroot()
    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))

    vehicles = demand_root.findall("vehicle")
    trips = trip_root.findall("tripinfo")

    demand_ids = [v.get("id") for v in vehicles]
    trip_ids = [t.get("id") for t in trips]
    demand_set = set(demand_ids)
    trip_set = set(trip_ids)

    completed = [
        t for t in trips
        if float(t.get("arrival", "-1")) >= 0
        and not t.get("vaporized")
    ]
    unfinished = [t for t in trips if t not in completed]

    missing = demand_set - trip_set
    unknown = trip_set - demand_set
    duplicate_demand_ids = len(demand_ids) - len(demand_set)
    duplicate_trip_ids = len(trip_ids) - len(trip_set)

    print("Generated vehicles:", len(vehicles))
    print("Trip records:", len(trips))
    print("Completed records:", len(completed))
    print("Unfinished records:", len(unfinished))
    print("Generated IDs without trip records:", len(missing))
    print("Unknown trip IDs:", len(unknown))
    print("Duplicate demand IDs:", duplicate_demand_ids)
    print("Duplicate trip IDs:", duplicate_trip_ids)
    print("Raw metrics completed:", metrics.get("vehicles_completed"))
    print("Raw metrics unfinished:", metrics.get("vehicles_unfinished"))

    if len(trips) != len(trip_set):
        print("WARNING: duplicate trip IDs need investigation")
    if unknown:
        print("WARNING: trip records contain IDs absent from demand")
    if len(completed) != metrics.get("vehicles_completed"):
        print("WARNING: completed count differs from metrics JSON")
    if len(unfinished) != metrics.get("vehicles_unfinished"):
        print("WARNING: unfinished count differs from metrics JSON")

    print("Accounting status:",
          "CHECK" if missing or unknown or duplicate_demand_ids or duplicate_trip_ids
          else "ID SETS CONSISTENT")
