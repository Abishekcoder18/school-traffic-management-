GATEFLOW AI - RATHI FOUR-SCENARIO DATA HANDOFF

This package contains synthetic SUMO simulation data for baseline, uniform,
optimized-candidate, and 1.3x stress scenarios.

Primary files:
- simulation_run_summary.csv: four scenario rows.
- traffic_observations.csv: 960 rows across four scenarios, four zones, and
  60 one-minute intervals.
- lane_queue_observations.csv: lane-level queue lengths in metres.
- rathi_measured_csv_quality_report.json: current measured-dataset quality
  report and metric definitions.
- scenario_manifest.json: scenario configuration and reproducibility details.

The network and demand are fictional and synthetic. Seed: 20261024.
Simulation horizon: 3600 seconds.

Generated demand, SUMO summary insertion counters, FCD-observed vehicles,
completed trips, and unfinished observed vehicles are distinct metrics.
The last SUMO summary sample is at 3540 seconds; baseline and stress have
additional FCD-observed vehicles first appearing after that sample.

Zone capacities are provisional assumptions. Queue length is in metres and
does not itself prove physical spillback. The optimized scenario is a
candidate plan, not proof of a globally optimal result. These single-run
simulation results are not field-validated.

The diagnostic_vehicle_demand.csv and diagnostic_vehicle_results.csv files
refer to an earlier diagnostic run and are not the four-scenario comparison.
