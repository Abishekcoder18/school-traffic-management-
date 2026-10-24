from pathlib import Path
import csv
import json
import xml.etree.ElementTree as ET

root = Path(r"E:\School_Traffic_Management")
sim = root / "data" / "simulations" / "school_demo"

print("=" * 70)
print("1. LOCATING PICKUP ZONE FILES")
print("=" * 70)

for p in root.rglob("pickup_zones.csv"):
    if ".venv" not in p.parts and "node_modules" not in p.parts:
        print(p)

print("\n" + "=" * 70)
print("2. VERIFYING SUMO TRIPINFO")
print("=" * 70)

for scenario in ["baseline", "uniform", "optimized", "stress_1_3x"]:
    folder = sim / "experiment_fcd" / scenario
    tripfile = folder / "tripinfo.xml"
    summaryfile = folder / "summary.xml"
    queuefile = folder / "queues.xml"
    logfile = folder / "capture_log.json"

    print(f"\n--- {scenario} ---")

    if tripfile.exists():
        root_xml = ET.parse(tripfile).getroot()
        trips = root_xml.findall(".//tripinfo")
        print("Tripinfo records:", len(trips))
        print("Completed trip records:", sum(1 for t in trips if t.get("arrival") is not None))
        print("Sample trip:", ET.tostring(trips[0], encoding="unicode")[:600] if trips else "None")
    else:
        print("tripinfo.xml MISSING")

    if summaryfile.exists():
        xml_root = ET.parse(summaryfile).getroot()
        steps = xml_root.findall(".//step")
        print("Summary steps:", len(steps))
        if steps:
            print("Last summary step:", steps[-1].attrib)

    if queuefile.exists():
        xml_root = ET.parse(queuefile).getroot()
        print("Queue XML root:", xml_root.tag)
        print("Queue record tags:", sorted({el.tag for el in xml_root.iter()}))
        for el in list(xml_root.iter()):
            if el is not xml_root:
                print("Queue sample:", el.tag, el.attrib)
                break

    if logfile.exists():
        try:
            print("Capture log:", json.dumps(json.loads(logfile.read_text(encoding="utf-8")), indent=2))
        except Exception as e:
            print("Could not parse capture log:", e)

print("\n" + "=" * 70)
print("3. CHECKING CAPACITY FILES IN HANDOFF FOLDER")
print("=" * 70)

handoff = sim / "FINAL_HANDOFF_RATHI"
for p in handoff.glob("*zone*"):
    print(p.name, p.stat().st_size, "bytes")

print("\nAudit finished. No files were modified.")
