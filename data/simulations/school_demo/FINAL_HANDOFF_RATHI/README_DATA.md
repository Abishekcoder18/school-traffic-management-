# GateFlow AI ? Rathi Four-Scenario Data Handoff

## Purpose
This package contains synthetic SUMO simulation data for four scenarios:
baseline, uniform, optimized candidate, and stress demand (1.3x).

## Main files
- `simulation_run_summary.csv`: one row per scenario.
- `traffic_observations.csv`: 960 rows across four scenarios, four zones, and 60 one-minute intervals.
- `lane_queue_observations.csv`: lane-level queue measurements reported in metres.
- `pickup_zones.csv`: pickup-zone configuration; capacities are provisional assumptions.
- `student_groups.csv`: school-group configuration.
- `scenario_manifest.json`: scenario settings and reproducibility metadata.
- `rathi_measured_csv_quality_report.json`: current measured-dataset definitions, validation results, and limitations.
- `diagnostic_vehicle_demand.csv` and `diagnostic_vehicle_results.csv`: separate earlier diagnostic-run artifacts; do not treat these as the four-scenario comparison.

## Provenance
The network and demand are synthetic and fictional. The scenarios use seed 20261024 and a 3600-second simulation horizon. These are simulation results, not field observations or proof of operational performance.

## Metric definitions
- Generated vehicles are unique vehicle IDs in the scenario demand file.
- The measured report's observed vehicle population is the number of unique IDs seen in the FCD output.
- Completed trips require a valid non-negative arrival and no vaporized attribute.
- Unfinished observed vehicles are observed FCD vehicles not counted as successfully completed.
- Generated-demand completion rate is completed vehicles divided by generated demand. It is not the same as completion among observed/inserted vehicles.
- SUMO summary insertion counters are sampled counters; the last summary sample is at 3540 seconds. In baseline and stress, this sample is lower than the FCD/tripinfo population because additional vehicles first appear after 3540 seconds. The summary counter and FCD-observed population are distinct metrics.

## Important limitations
- The optimized scenario is a planner-selected candidate, not a proven global optimum.
- Zone capacities are unverified assumptions; exceedance counts are samples above those provisional limits, not distinct incidents.
- Queue length is measured in metres, not vehicle count. A long queue alone does not establish physical spillback; spillback fields remain unavailable/unconfirmed.
- Waiting-time observations are sampled from FCD at vehicle-second level and are sample-weighted, not unique-trip statistics.
- Results are single-run synthetic comparisons and do not establish universal superiority or real-world effectiveness.

## Validation status
The measured CSV report records structural and row-count validation. This does not establish field validity, confirmed zone capacity, confirmed spillback, or operational readiness.
