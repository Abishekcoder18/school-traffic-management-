import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from app.planner import GROUP_IDS, GROUP_VEHICLES, VEHICLES
from app.scenario import GROUPS
from app.zones import DWELL_SECONDS

ROOT = Path(__file__).resolve().parents[3]
SIM_DIR = ROOT / "data" / "simulations" / "school_demo"
SUMO_HOME = Path(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\SUMO"))
SUMO = SUMO_HOME / "bin" / "sumo.exe"
SEED = 20261024

ROUTES = {
    "Z1": ("r1", "E_APPROACH E_IN_1 E_ZONE_1"),
    "Z2": ("r2", "E_APPROACH E_IN_2 E_ZONE_2"),
    "Z3": ("r3", "E_APPROACH E_IN_1 E_ZONE_3"),
    "Z4": ("r4", "E_APPROACH E_IN_2 E_BUS_BAY"),
}
DEFAULT_ZONES = {
    "car": "Z3",
    "two_wheeler": "Z1",
    "auto_van": "Z2",
    "bus": "Z4",
}


def generate_routes(offsets=None, surge=1.0, seed=SEED, zones=None):
    offsets = offsets or {g: 0 for g in GROUP_IDS}
    zones = zones or DEFAULT_ZONES
    root = ET.Element("routes")

    vehicle_types = {
        "car": ("passenger", 5.0, 13.9),
        "two_wheeler": ("motorcycle", 2.2, 13.9),
        "auto_van": ("passenger", 5.5, 11.1),
        "bus": ("bus", 12.0, 8.33),
    }
    for name, (vclass, length, speed) in vehicle_types.items():
        ET.SubElement(
            root, "vType", id=name, vClass=vclass, length=str(length),
            accel="2.6", decel="4.5", maxSpeed=str(speed),
        )

    for route_id, edges in ROUTES.values():
        ET.SubElement(root, "route", id=route_id, edges=edges)

    rng_state = seed
    def next_random():
        nonlocal rng_state
        rng_state = (1103515245 * rng_state + 12345) & 0x7fffffff
        return rng_state / 0x80000000

    vehicles = []
    for group in GROUPS:
        minute = offsets[group.id]
        for vehicle in VEHICLES:
            count = round(GROUP_VEHICLES[group.id][vehicle] * surge)
            zone_id = zones[vehicle]
            route_id = ROUTES[zone_id][0]
            dwell = DWELL_SECONDS[vehicle]
            for j in range(count):
                # Reproducible arrivals over a 5-minute group window.
                depart = max(
                    0.0,
                    (minute + 15) * 60 + next_random() * 300
                )
                vehicles.append((depart, group.id, vehicle, route_id, dwell))

    vehicles.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    for i, (depart, group_id, vehicle, route_id, dwell) in enumerate(vehicles):
        ET.SubElement(
            root, "vehicle", id=f"{group_id}_{vehicle}_{i}",
            type=vehicle, route=route_id, depart=f"{depart:.2f}",
            departLane="best", departSpeed="max",
        )
        stop_edge = ROUTES[zones[vehicle]][1].split()[-1]
        ET.SubElement(
            root[-1], "stop", lane=f"{stop_edge}_0",
            duration=str(dwell),
        )

    return ET.tostring(root, encoding="utf-8", xml_declaration=True), len(vehicles)


def run_simulation(offsets=None, surge=1.0, seed=SEED, zones=None):
    if not SUMO.exists():
        raise FileNotFoundError(f"SUMO executable not found: {SUMO}")
    SIM_DIR.mkdir(parents=True, exist_ok=True)

    xml_data, generated = generate_routes(offsets, surge, seed, zones)
    with tempfile.TemporaryDirectory(prefix="gateflow_sumo_") as tmp:
        route_file = Path(tmp) / "demand.rou.xml"
        trip_file = Path(tmp) / "tripinfo.xml"
        queue_file = Path(tmp) / "queue.xml"
        route_file.write_bytes(xml_data)

        cmd = [
            str(SUMO), "-n", str(SIM_DIR / "network.net.xml"),
            "-r", str(route_file), "--seed", str(seed),
            "--end", "3600", "--tripinfo-output", str(trip_file),
            "--queue-output", str(queue_file),
            "--duration-log.disable", "true", "--no-step-log", "true",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=240
        )
        if result.returncode:
            raise RuntimeError(
                "SUMO failed:\n" + result.stderr[-4000:]
            )

        trips = []
        if trip_file.exists():
            for elem in ET.parse(trip_file).getroot().findall("tripinfo"):
                trips.append({
                    "duration": float(elem.get("duration", 0)),
                    "waiting": float(elem.get("waitingTime", 0)),
                    "time_loss": float(elem.get("timeLoss", 0)),
                })

        mean_wait = (
            sum(t["waiting"] for t in trips) / len(trips) if trips else 0
        )
        mean_duration = (
            sum(t["duration"] for t in trips) / len(trips) if trips else 0
        )
        sorted_wait = sorted(t["waiting"] for t in trips)
        p95_index = max(0, int(0.95 * len(sorted_wait) + 0.999999) - 1)
        p95_wait = sorted_wait[p95_index] if sorted_wait else 0

        metrics = {
            "engine": "SUMO",
            "source_label": "Synthetic demand on fictional network",
            "seed": seed,
            "surge_multiplier": surge,
            "vehicles_generated": generated,
            "vehicles_completed": len(trips),
            "completion_rate": round(len(trips) / generated, 4) if generated else 0,
            "mean_wait_seconds": round(mean_wait, 3),
            "p95_wait_seconds": round(p95_wait, 3),
            "mean_trip_duration_seconds": round(mean_duration, 3),
            "mean_time_loss_seconds": round(
                sum(t["time_loss"] for t in trips) / len(trips), 3
            ) if trips else 0,
            "trip_metrics_available": bool(trips),
        }
        output = SIM_DIR / "last_run_metrics.json"
        output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return metrics


if __name__ == "__main__":
    print(json.dumps(run_simulation(), indent=2))
