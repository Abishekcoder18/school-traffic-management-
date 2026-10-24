from pathlib import Path
import csv
import json

root = Path(r"E:\School_Traffic_Management\data\simulations\school_demo")
out = root / "FINAL_HANDOFF_RATHI"
scenarios = ["baseline", "uniform", "optimized", "stress_1_3x"]

files = {
    "summary": out / "simulation_run_summary.csv",
    "observations": out / "traffic_observations.csv",
    "builder": Path("build_rathi_measured_csvs.py"),
    "fcd_builder": Path("capture_rathi_fcd.py"),
    "quality_report": out / "rathi_measured_csv_quality_report.json",
}

for name, path in files.items():
    print(f"\n{'=' * 20} {name} {'=' * 20}")
    print("PATH:", path.resolve())
    print("EXISTS:", path.exists())
    if not path.exists():
        continue
    if path.suffix == ".csv":
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print("ROWS:", len(rows))
        print("COLUMNS:", reader.fieldnames)
        if rows:
            print("FIRST ROW:", json.dumps(rows[0], ensure_ascii=False))
            print("LAST ROW:", json.dumps(rows[-1], ensure_ascii=False))
    elif path.suffix == ".json":
        print(path.read_text(encoding="utf-8"))
    else:
        print("LINES:", len(path.read_text(encoding="utf-8").splitlines()))

print(f"\n{'=' * 20} SCENARIO OUTPUTS {'=' * 20}")
for scenario in scenarios:
    folder = root / "experiment_fcd" / scenario
    print(f"\n[{scenario}] {folder}")
    if not folder.exists():
        print("MISSING DIRECTORY")
        continue
    for p in sorted(folder.iterdir()):
        if p.is_file():
            print(f"{p.name}: {p.stat().st_size:,} bytes")

print(f"\n{'=' * 20} ZONE CAPACITIES {'=' * 20}")
zones = root / "pickup_zones.csv"
if zones.exists():
    print(zones.read_text(encoding="utf-8-sig"))
else:
    print("pickup_zones.csv not found at expected location")
