from pathlib import Path
import xml.etree.ElementTree as ET

sim=Path(r"E:\School_Traffic_Management\data\simulations\school_demo")
lanes={"E_APPROACH_0","E_APPROACH_1"}
metrics=("queueing_length","queueing_length_experimental")

for scenario in ["baseline","uniform","optimized","stress_1_3x"]:
    path=sim/"experiment_fcd"/scenario/"queues.xml"
    best={}
    for _,el in ET.iterparse(path,events=("end",)):
        if el.tag=="data":
            t=el.get("timestep","unknown")
            for lane_el in el.iter("lane"):
                lane=lane_el.get("id")
                if lane not in lanes:
                    continue
                for metric in metrics:
                    try:
                        value=float(lane_el.get(metric,""))
                    except (TypeError,ValueError):
                        continue
                    key=(lane,metric)
                    if key not in best or value>best[key][0]:
                        best[key]=(value,t)
            el.clear()

    print(f"\n--- {scenario} ---")
    for (lane,metric),(value,t) in sorted(best.items()):
        print(f"{lane} | {metric} | max={value:.2f} m | time={t}s")
