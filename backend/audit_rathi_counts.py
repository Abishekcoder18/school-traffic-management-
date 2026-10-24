from pathlib import Path
import csv
import xml.etree.ElementTree as ET

base = Path(r"E:\School_Traffic_Management\data\simulations\school_demo")
handoff = base / "FINAL_HANDOFF_RATHI"

print("=" * 72)
print("A. PICKUP ZONE DEFINITIONS")
print("=" * 72)

zones_file = handoff / "pickup_zones.csv"
with zones_file.open("r", newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        print(row)

for scenario in ["baseline", "uniform", "optimized", "stress_1_3x"]:
    folder = base / "experiment_fcd" / scenario
    print(f"\n{'=' * 72}")
    print("B. SCENARIO:", scenario)
    print("=" * 72)

    trip_root = ET.parse(folder / "tripinfo.xml").getroot()
    trips = trip_root.findall(".//tripinfo")
    completed = [t for t in trips if t.get("arrival") not in (None, "")]
    unfinished = [t for t in trips if t.get("arrival") in (None, "")]

    print("Tripinfo records:", len(trips))
    print("With arrival:", len(completed))
    print("Without arrival:", len(unfinished))

    if unfinished:
        print("Unfinished sample:", unfinished[0].attrib)

    summary_root = ET.parse(folder / "summary.xml").getroot()
    steps = summary_root.findall(".//step")

    print("Summary timestep count:", len(steps))
    print("Last 5 summary steps:")
    for step in steps[-5:]:
        print(step.attrib)

    queue_root = ET.parse(folder / "queues.xml").getroot()
    queue_rows = queue_root.findall(".//lane")
    print("Queue lane records:", len(queue_rows))

    printed = 0
    for lane in queue_rows:
        if lane.get("id", "").startswith("E_APPROACH"):
            print("Approach queue sample:", lane.attrib)
            printed += 1
            if printed >= 5:
                break

    fcd = folder / "fcd.xml"
    print("FCD file size:", fcd.stat().st_size)

print("\nAudit complete. No files were modified.")
