from pathlib import Path
import xml.etree.ElementTree as ET

base = Path(r"E:\School_Traffic_Management\data\simulations\school_demo")
network_files = list(base.rglob("*.net.xml"))

print("=" * 70)
print("1. NETWORK FILES")
print("=" * 70)

for p in network_files:
    print(p)

if not network_files:
    print("No .net.xml files found.")
    raise SystemExit(0)

for netfile in network_files:
    print(f"\nNETWORK: {netfile}")
    root = ET.parse(netfile).getroot()

    for edge in root.findall("edge"):
        edge_id = edge.get("id", "")
        if "APPROACH" in edge_id.upper():
            for lane in edge.findall("lane"):
                print("APPROACH EDGE:", edge_id, "LANE:", lane.attrib)

    for edge in root.findall("edge"):
        edge_id = edge.get("id", "")
        if "APPROACH" in edge_id.upper():
            print("APPROACH EDGE ATTRIBUTES:", edge.attrib)

print("\n" + "=" * 70)
print("2. QUEUE LENGTH DISTRIBUTION")
print("=" * 70)

for scenario in ["baseline", "uniform", "optimized", "stress_1_3x"]:
    qfile = base / "experiment_fcd" / scenario / "queues.xml"
    root = ET.parse(qfile).getroot()
    values = []

    for lane in root.iter("lane"):
        lane_id = lane.get("id", "")
        if lane_id in ("E_APPROACH_0", "E_APPROACH_1"):
            value = lane.get("queueing_length_experimental")
            if value is None:
                value = lane.get("queueing_length")
            if value is not None:
                values.append((float(value), lane_id, lane.get("queueing_time")))

    print(f"\n{scenario}: approach queue samples={len(values)}")
    if values:
        values.sort(reverse=True)
        print("Maximum queue length:", values[0])
        print("Top 10 queue samples:")
        for item in values[:10]:
            print(item)

print("\nInspection only; no files modified.")
