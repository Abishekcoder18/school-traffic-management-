import csv
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "data" / "simulations" / "school_demo"
OUT = SIM / "FINAL_HANDOFF_RATHI"
ZIP_PATH = SIM / "RATHI_CSV_DATASET.zip"

EXPECTED = {
    "simulation_run_summary.csv": {
        "columns": 21,
        "rows": 4,
    },
    "traffic_observations.csv": {
        "columns": 15,
        "rows": 960,
    },
    "lane_queue_observations.csv": {
        "columns": 11,
        "rows": 1401,
    },
    "scenario_queue_metrics.csv": {
        "columns": 13,
        "rows": 4,
    },
}

REPORTS = [
    "csv_quality_report.json",
    "lane_queue_quality_report.json",
    "scenario_queue_metrics_report.json",
    "rathi_measured_csv_quality_report.json",
]

SUPPORTING_FILES = [
    "pickup_zones.csv",
    "diagnostic_vehicle_demand.csv",
    "diagnostic_vehicle_results.csv",
    "student_groups.csv",
    "scenario_manifest.json",
    "data_quality_report.json",
    "README_DATA.md",
    "README_DATA.txt",
    "handoff_validation_report.csv",
]


def validate_csv(path, expected_columns, expected_rows):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    if fields is None or len(fields) != expected_columns:
        raise ValueError(
            f"{path.name}: expected {expected_columns} columns, "
            f"found {0 if fields is None else len(fields)}"
        )

    if len(rows) != expected_rows:
        raise ValueError(
            f"{path.name}: expected {expected_rows} rows, "
            f"found {len(rows)}"
        )

    if any(None in row for row in rows):
        raise ValueError(f"{path.name}: row contains extra values")

    if any(
        value is None
        for row in rows
        for value in row.values()
    ):
        raise ValueError(f"{path.name}: malformed CSV row")

    print(
        f"PASS {path.name}: {len(fields)} columns, "
        f"{len(rows)} data rows"
    )


def validate_observation_groups(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    groups = {}
    for row in rows:
        key = (row["scenario_id"], row["timestamp_seconds"])
        groups.setdefault(key, []).append(row["zone_id"])

    invalid = {
        key: zones
        for key, zones in groups.items()
        if len(zones) != 4 or len(set(zones)) != 4
    }

    if len(groups) != 240 or invalid:
        raise ValueError(
            f"Observation group validation failed: "
            f"{len(groups)} groups; invalid groups={len(invalid)}"
        )

    print("PASS observations: 240 groups, 4 unique zone records per group")


def validate_measured_report(path):
    report = json.loads(path.read_text(encoding="utf-8"))

    if report.get("schema_validation") != "PASS":
        raise ValueError("Measured report schema validation did not pass")

    if report.get("observation_row_count_validation") != "PASS":
        raise ValueError("Measured report row-count validation did not pass")

    if report.get("observation_rows") != 960:
        raise ValueError("Measured report does not confirm 960 observations")

    if len(report.get("runs", [])) != 4:
        raise ValueError("Measured report does not contain four scenarios")

    if "spillback" not in report.get("definitions", {}):
        raise ValueError("Report must document the spillback limitation")

    print("PASS rathi_measured_csv_quality_report.json")


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    for filename, spec in EXPECTED.items():
        validate_csv(
            OUT / filename,
            spec["columns"],
            spec["rows"],
        )

    validate_observation_groups(OUT / "traffic_observations.csv")

    for filename in REPORTS:
        path = OUT / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing report: {path}")

        json.loads(path.read_text(encoding="utf-8"))
        print(f"PASS {filename}: valid JSON")

    validate_measured_report(OUT / "rathi_measured_csv_quality_report.json")

    for filename in SUPPORTING_FILES:
        if not (OUT / filename).exists():
            raise FileNotFoundError(f"Missing supporting file: {OUT / filename}")

    package_files = (
        list(EXPECTED.keys())
        + REPORTS
        + SUPPORTING_FILES
    )

    if len(package_files) != len(set(package_files)):
        raise ValueError("Duplicate file names in package configuration")

    temporary_zip = ZIP_PATH.with_suffix(".tmp.zip")

    with zipfile.ZipFile(
        temporary_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for filename in package_files:
            archive.write(OUT / filename, arcname=filename)

    with zipfile.ZipFile(temporary_zip, "r") as archive:
        bad_file = archive.testzip()
        contents = set(archive.namelist())
        expected_contents = set(package_files)

        if bad_file:
            temporary_zip.unlink(missing_ok=True)
            raise RuntimeError(f"ZIP integrity failed: {bad_file}")

        if contents != expected_contents:
            temporary_zip.unlink(missing_ok=True)
            raise RuntimeError(
                f"ZIP contents mismatch. "
                f"Missing={sorted(expected_contents - contents)}; "
                f"unexpected={sorted(contents - expected_contents)}"
            )

    temporary_zip.replace(ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        print("\n=== FINAL PACKAGE ===")
        print("ZIP:", ZIP_PATH)
        print("Files:", len(archive.namelist()))
        print("ZIP integrity: PASS")
        for info in archive.infolist():
            print(f" - {info.filename} ({info.file_size:,} bytes)")


if __name__ == "__main__":
    main()
