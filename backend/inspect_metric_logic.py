from pathlib import Path

backend = Path(r"E:\School_Traffic_Management\backend")
sim = Path(r"E:\School_Traffic_Management\data\simulations\school_demo")

files = [
    backend / "build_rathi_measured_csvs.py",
    backend / "capture_rathi_fcd.py",
]

terms = (
    "def process_fcd",
    "inserted_ids",
    "peak_approach",
    "peak_zone",
    "spillback",
    "queue-output",
    "queue-output.period",
    "tripinfo-output",
    "summary-output",
    "fcd-output",
)

for path in files:
    print(f"\n{'=' * 70}\n{path}\n{'=' * 70}")
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for i, line in enumerate(lines):
        if any(term in line.lower() for term in terms):
            start = max(0, i - 2)
            end = min(len(lines), i + 5)
            print(f"\n--- lines {start + 1}-{end} ---")
            for j in range(start, end):
                print(f"{j + 1}: {lines[j]}")

print("\nInspection complete. No files modified.")
