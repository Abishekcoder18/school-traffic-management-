from pathlib import Path
import xml.etree.ElementTree as ET

sim = Path(r"E:\School_Traffic_Management\data\simulations\school_demo")
scenarios = ["baseline", "uniform", "optimized", "stress_1_3x"]

for scenario in scenarios:
    folder = sim / "experiment_fcd" / scenario
    trips = ET.parse(folder / "tripinfo.xml").getroot().findall("tripinfo")
    steps = ET.parse(folder / "summary.xml").getroot().findall(".//step")

    completed = []
    unfinished = []

    for trip in trips:
        try:
            arrival = float(trip.get("arrival", "-1"))
        except (TypeError, ValueError):
            arrival = -1

        if arrival >= 0 and not trip.get("vaporized"):
            completed.append(arrival)
        else:
            unfinished.append(trip.get("id"))

    print(f"\n--- {scenario} ---")
    print("Tripinfo records:", len(trips))
    print("Completed trips in tripinfo:", len(completed))
    print("Not completed in tripinfo:", len(unfinished))
    print("Completed by 3540 seconds:", sum(t <= 3540 for t in completed))
    print("Completed after 3540 seconds:", sum(t > 3540 for t in completed))

    if steps:
        last = steps[-1]
        print("Summary timestamp:", last.get("time"))
        print("Summary inserted:", last.get("inserted"))
        print("Summary arrived:", last.get("arrived"))
        print("Summary running:", last.get("running"))
        print("Summary loaded:", last.get("loaded"))
