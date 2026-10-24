
from pathlib import Path
import xml.etree.ElementTree as ET

p = Path("../data/simulations/school_demo/experiment_diagnostics")

for scenario in ["baseline", "uniform", "optimized", "stress_1_3x"]:
    f = p / scenario / "queues.xml"
    print(f"\nSCENARIO: {scenario}")

    if not f.exists():
        print("MISSING queues.xml")
        continue

    root = ET.parse(f).getroot()
    nonempty = 0

    for timestep in root:
        lanes = timestep.find("lanes")
        if lanes is not None and len(lanes) > 0:
            print("TIMESTEP:", timestep.attrib)
            print(ET.tostring(timestep, encoding="unicode")[:2000])
            nonempty += 1
            if nonempty == 3:
                break

    print("NONEMPTY_TIMESTEPS_FOUND:", nonempty)
