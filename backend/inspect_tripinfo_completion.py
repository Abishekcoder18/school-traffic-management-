from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter

base = Path(r"E:\School_Traffic_Management\data\simulations\school_demo")

for scenario in ["baseline", "uniform", "optimized", "stress_1_3x"]:
    path = base / "experiment_fcd" / scenario / "tripinfo.xml"
    root = ET.parse(path).getroot()
    trips = root.findall("tripinfo")

    arrivals = Counter()
    vaporized = Counter()
    valid = []

    for t in trips:
        arrivals[t.get("arrival")] += 1
        vaporized[t.get("vaporized")] += 1

        arrival = t.get("arrival")
        vap = t.get("vaporized")

        try:
            arrival_ok = float(arrival) >= 0
        except (TypeError, ValueError):
            arrival_ok = False

        if arrival_ok and not vap:
            valid.append(t.get("id"))

    print(f"\n{scenario}")
    print("Tripinfo records:", len(trips))
    print("Arrival attribute values:", arrivals.most_common(5))
    print("Vaporized attribute values:", vaporized)
    print("Pass current completion filter:", len(valid))
    print("First trip attributes:", trips[0].attrib if trips else None)
