from pathlib import Path
import xml.etree.ElementTree as ET

base = Path(r"E:\School_Traffic_Management\data\simulations\school_demo")
backend = Path(r"E:\School_Traffic_Management\backend")
scenarios = ["baseline", "uniform", "optimized", "stress_1_3x"]

builder = backend / "build_rathi_measured_csvs.py"

print("=" * 70)
print("1. COMPLETION COUNT LOGIC IN BUILDER")
print("=" * 70)

if builder.exists():
    lines = builder.read_text(encoding="utf-8-sig").splitlines()
    terms = ("completed", "tripinfo", "observed_ids", "unfinished", "completion_rate")
    shown = set()
    for i, line in enumerate(lines):
        if any(term in line.lower() for term in terms):
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            for j in range(start, end):
                if j not in shown:
                    print(f"{j + 1}: {lines[j]}")
                    shown.add(j)
            print("---")
else:
    print("Builder script not found:", builder)

print("\n" + "=" * 70)
print("2. VEHICLE ID RECONCILIATION")
print("=" * 70)

for scenario in scenarios:
    folder = base / "experiment_fcd" / scenario
    trip_file = folder / "tripinfo.xml"
    fcd_file = folder / "fcd.xml"

    trip_root = ET.parse(trip_file).getroot()
    trip_ids = {e.get("id") for e in trip_root.findall(".//tripinfo") if e.get("id")}

    fcd_ids = set()
    first_time = None
    last_time = None
    frames = 0

    for event, elem in ET.iterparse(fcd_file, events=("end",)):
        if elem.tag == "timestep":
            frames += 1
            t = elem.get("time")
            if first_time is None:
                first_time = t
            last_time = t
            for vehicle in elem.findall("vehicle"):
                vid = vehicle.get("id")
                if vid:
                    fcd_ids.add(vid)
            elem.clear()

    print(f"\n{scenario}")
    print("tripinfo unique IDs:", len(trip_ids))
    print("FCD unique IDs:", len(fcd_ids))
    print("IDs in both:", len(trip_ids & fcd_ids))
    print("tripinfo only:", len(trip_ids - fcd_ids))
    print("FCD only:", len(fcd_ids - trip_ids))
    print("First/last FCD time:", first_time, last_time)
    print("FCD frames:", frames)
    print("Example tripinfo-only IDs:", sorted(trip_ids - fcd_ids)[:5])
    print("Example FCD-only IDs:", sorted(fcd_ids - trip_ids)[:5])

print("\nNo files modified.")
