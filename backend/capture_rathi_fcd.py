import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "data" / "simulations" / "school_demo"
SOURCE = SIM / "experiment_diagnostics"
OUTPUT = SIM / "experiment_fcd"
SUMO = Path(r"C:\Program Files (x86)\SUMO\bin\sumo.exe")
NETWORK = SIM / "network.net.xml"
SEED = 20261024
HORIZON = 3600
PERIOD = 1

SCENARIOS = ("baseline", "uniform", "optimized", "stress_1_3x")


def main():
    if not SUMO.exists():
        raise FileNotFoundError(f"SUMO executable missing: {SUMO}")
    if not NETWORK.exists():
        raise FileNotFoundError(f"Network missing: {NETWORK}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = []

    for scenario in SCENARIOS:
        source_dir = SOURCE / scenario
        route_file = source_dir / "demand.rou.xml"

        if not route_file.exists():
            raise FileNotFoundError(f"Demand file missing: {route_file}")

        run_dir = OUTPUT / scenario
        run_dir.mkdir(parents=True, exist_ok=True)

        fcd_file = run_dir / "fcd.xml"
        trip_file = run_dir / "tripinfo.xml"
        summary_file = run_dir / "summary.xml"
        queue_file = run_dir / "queues.xml"
        log_file = run_dir / "capture_log.json"

        for path in (fcd_file, trip_file, summary_file, queue_file):
            if path.exists():
                path.unlink()

        command = [
            str(SUMO),
            "-n", str(NETWORK),
            "-r", str(route_file),
            "--seed", str(SEED),
            "--begin", "0",
            "--end", str(HORIZON),
            "--fcd-output", str(fcd_file),
            "--device.fcd.period", str(PERIOD),
            "--fcd-output.attributes", "id,type,route, speed, pos, lane, waiting",
            "--tripinfo-output", str(trip_file),
            "--tripinfo-output.write-unfinished", "true",
            "--summary-output", str(summary_file),
            "--summary-output.period", "60",
            "--queue-output", str(queue_file),
            "--queue-output.period", "60",
            "--duration-log.disable", "true",
            "--no-step-log", "true",
        ]

        print(f"\n=== Capturing {scenario} ===")
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired:
            result = {
                "scenario": scenario,
                "success": False,
                "error": "SUMO timed out after 300 seconds",
            }
            log_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
            results.append(result)
            print(result)
            continue

        log = {
            "scenario": scenario,
            "success": process.returncode == 0 and fcd_file.exists(),
            "return_code": process.returncode,
            "seed": SEED,
            "horizon_seconds": HORIZON,
            "fcd_period_seconds": PERIOD,
            "fcd_file": str(fcd_file),
            "fcd_bytes": fcd_file.stat().st_size if fcd_file.exists() else 0,
            "tripinfo_exists": trip_file.exists(),
            "summary_exists": summary_file.exists(),
            "queue_exists": queue_file.exists(),
            "stdout": process.stdout[-4000:],
            "stderr": process.stderr[-4000:],
        }

        log_file.write_text(json.dumps(log, indent=2), encoding="utf-8")
        results.append(log)

        print("Success:", log["success"])
        print("Return code:", process.returncode)
        print("FCD bytes:", log["fcd_bytes"])
        if process.stderr.strip():
            print("SUMO stderr:", process.stderr[-1200:])

        if log["success"]:
            try:
                root = ET.parse(fcd_file).getroot()
                steps = root.findall("timestep")
                first_vehicle = None
                for step in steps:
                    vehicles = step.findall("vehicle")
                    if vehicles:
                        first_vehicle = vehicles[0]
                        break

                print("FCD timesteps:", len(steps))
                print("First sample time:", steps[0].get("time") if steps else None)
                print(
                    "First vehicle attributes:",
                    sorted(first_vehicle.attrib) if first_vehicle is not None else "No vehicle samples",
                )
            except ET.ParseError as error:
                log["success"] = False
                log["parse_error"] = str(error)
                log_file.write_text(json.dumps(log, indent=2), encoding="utf-8")
                print("FCD XML parse failed:", error)

    report = {
        "project": "GateFlow AI",
        "measurement": "SUMO Floating Car Data",
        "network_and_demand_are_synthetic": True,
        "seed": SEED,
        "horizon_seconds": HORIZON,
        "fcd_period_seconds": PERIOD,
        "output_directory": str(OUTPUT),
        "runs": results,
        "all_runs_succeeded": all(item.get("success", False) for item in results),
    }

    (OUTPUT / "fcd_capture_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    print("\n=== CAPTURE REPORT ===")
    print(json.dumps({
        "output_directory": str(OUTPUT),
        "all_runs_succeeded": report["all_runs_succeeded"],
        "runs": [
            {
                "scenario": item["scenario"],
                "success": item.get("success", False),
                "fcd_bytes": item.get("fcd_bytes", 0),
            }
            for item in results
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
