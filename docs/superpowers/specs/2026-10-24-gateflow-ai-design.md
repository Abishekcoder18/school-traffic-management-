# GateFlow AI Implementation Design

## Intent

Build a local, repeatable decision-support demo for one fictional school gate. It must help School Management compare a current schedule, a uniform stagger, and feasible optimized schedules before changing a real operation. It must never claim real-world traffic reduction.

The demo is judged on an end-to-end result: validated assumptions become constrained schedule and zone plans; independent SUMO runs evaluate them; and a dashboard exposes the trade-offs and limits.

## Scope and priority

The PRD, MRD, and Complete Solution are unchanged authorities. This design implements their frozen F1-F3 before any optional capability.

1. **F1, required first:** constrained schedule enumeration, hard-rule validation, compatible pickup-zone assignments, capacity checks, and a Pareto shortlist.
2. **F2, required second:** independent SUMO comparison of existing schedule, uniform stagger, and shortlisted candidates with equivalent demand inputs and saved seeds; include a separate reproducible +30% demand-surge scenario.
3. **F3, required third:** validated configuration, source/engine labelling, queue and trade-off charts, pickup-zone view, plan selection, and a local reproducible run record.
4. **F4/F5, deferred until F1-F3 acceptance:** SUMO re-check remains the preferred simulation path and is attempted first; 60% compliance and longer-dwell scenarios follow only if time remains.
5. **F6, last:** parent-notice generation and verification are deferred implementation work.

Deferred work is not removed from the PRD. Rain scenarios, Bayesian calibration, local LLM features, NSGA-II, CVaR, databases, deployment, authentication, real-world data collection, and multi-school features stay out of this build.

## Architecture

Use one React/Vite/Tailwind/Plotly frontend and one Python/FastAPI backend. There is no database, external service, authentication layer, background worker, or cloud deployment.

The frontend collects/editably displays the prepared synthetic configuration, calls the backend, and renders results. It performs no authoritative feasibility or traffic calculation.

The backend owns schema validation, deterministic demand generation, schedule enumeration, zone assignment, SUMO artifact generation and execution, metrics extraction, fallback simulation, and run-record persistence. JSON configuration and result records, plus CSV exports where useful, are stored locally beneath the application data directory. SUMO artifacts for each run are isolated from `sumo_smoke_test/`.

## Frozen demo scenario

The initial scenario is synthetic and labelled as such. It contains 1,200 students in six groups:

- G1 KG: 150 students, frozen.
- G2 Grades 1-2: 200 students.
- G3 Grades 3-4: 220 students, linked to G4.
- G4 Grades 5-6: 230 students, linked to G3.
- G5 Grades 7-8: 200 students.
- G6 Grades 9-10: 200 students, maximum absolute shift of 5 minutes.

Vehicle-mode shares are cars 30%, two-wheelers 25%, autos/vans 15%, buses 15%, and walk/cycle 15%. Walk/cycle students count in group size but do not enter the vehicle queue. The backend supplies explicit current times, zone capacities, vehicle compatibility, service/dwell assumptions, road/junction geometry, and fixed seed as editable **assumptions**. All generated demand and results carry synthetic/assumed/simulated labels.

### Initial explicit assumptions

These are implementation defaults, not facts about a real school. They are visible and editable before a run and stored in every record.

- All six groups have a current release time of 08:00. This creates the current-peak baseline; G1 remains fixed at 08:00.
- The uniform-stagger baseline is a deterministic 5-minute spread applied in group order while preserving hard constraints: G1 `0`, G2 `+5`, G3/G4 `+10`, G5 `+15`, and G6 `+5` (its permitted limit). It is a benchmark, not an optimized plan.
- Student mode shares become vehicle demand using assumed occupants per vehicle: car 1.5, two-wheeler 1, auto/van 5, bus 30. Each group/mode vehicle count is rounded deterministically and walk/cycle creates no vehicle.
- Zones are concurrent stopping bays with a dwell-based throughput estimate per five-minute planning bin. Z1 (main kerb) supports cars/two-wheelers with 10 bays; Z2 (side lane) supports cars/two-wheelers/autos with 3 bays and is deliberately constrained; Z3 (rear lot) supports cars/two-wheelers/autos with 12 bays; Z4 (bus bay) supports buses with 4 bays. Initial dwell assumptions are car 90 seconds, two-wheeler 45 seconds, auto/van 120 seconds, and bus 180 seconds.
- The planning congestion estimate is a deterministic five-minute, zone-aware queue recurrence using generated arrivals and dwell-derived service capacity. It ranks/filters candidates only. SUMO or the declared fallback is the source of F2 traffic metrics.
- From the Pareto set, Minimal change is the lowest-disruption plan; Congestion-focused is the lowest estimated-delay plan; Balanced is the plan with the lowest equal-weight normalized distance to the ideal of those two objectives. Ties resolve by estimated delay, disruption, then lexicographic offsets and zone identifiers. The full Pareto set remains visible in the trade-off chart.

## F1: planning and feasibility

Each eligible group uses only offsets -15, -10, -5, 0, +5, +10, and +15 minutes. G1 is fixed at zero; G6 permits only -5, 0, and +5; G3 and G4 must receive the same offset. A validator rejects malformed input, mode shares not totaling 100%, non-positive capacity, invalid windows, incompatible zones, over-capacity assignments, and conflicting constraints in plain language.

The planner deterministically enumerates the constrained offset space, calculates schedule disruption as `sum(group_students * abs(offset_minutes))`, and creates vehicle-type-to-zone assignments that satisfy compatibility and projected peak capacity. It keeps non-dominated plans on congestion-estimate versus disruption, then returns a bounded, explainable shortlist labelled Minimal change, Balanced, and Congestion-focused. The estimate only chooses candidates; it is never presented as independent traffic simulation.

## F2: fair simulation comparison

For a selected configuration and seed, generate one canonical deterministic vehicle demand realization for normal demand. Derive the current, uniform-stagger, and candidate route inputs from that same per-group/per-mode demand profile, shifting schedule-related arrivals without altering the underlying draws. Persist the seed, scenario configuration, model version, demand profile identity, and plan identity with every run.

SUMO 1.28 runs a generated, compact network: one approach road, adjacent junction, gate access, and pickup-zone stopping areas. It produces independent vehicle-level metrics from trip and lane/queue outputs: peak queue, queue-over-time, total delay, mean wait, 95th-percentile wait, and zone-capacity violations. SUMO is attempted immediately and time-boxed; if its integration cannot produce usable metrics in time, the backend activates a deterministic event/queue simulator with matching inputs and clearly labels the engine as `custom deterministic fallback`, never SUMO.

The mandatory surge is a separate scenario that increases vehicle demand by 30% deterministically from the same base profile and seed policy. It reruns the current, uniform, and shortlisted optimized plans. It is displayed separately from normal demand. The 60% compliance, longer-dwell, and rain scenarios are deferred.

## F3: dashboard and records

The dashboard uses a short flow: configure assumptions, validate and find plans, run comparison, inspect results, select a plan. It shows:

- Schedule offsets, hard-rule status, zone assignment, capacity/use, and input-source labels.
- Current, uniform, and optimized plan metrics side by side under normal and +30% surge scenarios.
- Queue-over-time, congestion-versus-disruption Pareto scatter, and pickup-zone utilization/capacity views with units.
- Engine labels distinguishing search estimates, SUMO outputs, and any fallback-simulator outputs.
- An explicit banner that results are simulated and synthetic/assumption based.
- A selected-plan record and downloadable/local JSON run record containing configuration, seed, demand identity, scenario, plan, engine, and metrics.

## Acceptance checks

F1 passes when the demo rejects each required invalid case (G1 move, G6 over-shift, G3/G4 mismatch, incompatible zone, and over-capacity zone) and produces only valid plans.

F2 passes when a single action runs current, uniform, and optimized plans with saved identical demand identity/seed, produces simulator-derived metrics for all, and independently reruns the +30% surge scenario. Repeating the same configuration and seed yields identical recorded results.

F3 passes when the local dashboard completes configuration through plan selection, renders all required visualizations and labels, and saves/reloads the run record without code edits.

## Implementation sequence

1. Initialize the frontend/backend structure and shared JSON schemas; protect `docs/` and `sumo_smoke_test/` from application writes.
2. Implement the synthetic scenario, explicit assumptions, validators, F1 enumerator, zone assignment, and planner tests.
3. Build the small SUMO network adapter, deterministic demand writer, metric extractor, and fallback simulator; validate repeated normal and surge runs.
4. Expose FastAPI endpoints for configuration validation, plan search, comparison run, and run-record retrieval.
5. Build the React dashboard around those endpoints and verify the complete F1-F3 flow locally.
6. Only after all acceptance checks pass, assess F4/F5 and F6 against remaining time.

## Builder-owned details

The builder may choose exact file layout, component names, API route names, chart styling, and non-material numeric assumptions for the generated compact network. Every chosen numeric assumption must be visible and editable in the application, marked as assumed, persisted in the run record, and kept constant across compared plans.
