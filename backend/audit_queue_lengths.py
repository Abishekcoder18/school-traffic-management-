from pathlib import Path
import xml.etree.ElementTree as ET

sim = Path(r"E:\School_Traffic_Management\data\simulations\school_demo")
scenarios = ["baseline", "uniform", "optimized", "stress_1_3x"]
approach_lanes = {"E_APPROACH_0", "E_APPROACH_1"}

for scenario in scenarios:
    path = sim / "experiment_fcd" / scenario / "queues.xml"
    if not path.exists():
        print(f"\n{scenario}: queues.xml MISSING")
        continue

    maxima = {}
    samples = 0
    for event, element in ET.iterparse(path, events=("end",)):
        if element.tag == "lane" and element.get("id") in approach_lanes:
            samples += 1
            lane = element.get("id")
            for attr in ("queueing_length", "queueing_length_experimental"):
                try:
                    value = float(element.get(attr, ""))
                except (TypeError, ValueError):
                    continue
                maxima[attr, lane] = max(maxima.get((attr, lane), 0.0), value)
        if element.tag == "data":
            element.clear()

    print(f"\n--- {scenario} ---")
    print("Approach-lane records:", samples)
    for (metric, lane), value in sorted(maxima.items()):
        print(f"{lane} | {metric} max: {value:.2f} m")
