# GateFlow AI — Prototype Implementation Handover

**Purpose:** Evidence-based source material for the MRD, PRD, Jira breakdown, and
jury demo. This describes the repository as inspected, not a target-state
product promise.

**Evidence boundary:** The active product is a local prototype using synthetic
scenario data and deterministic estimates. External map and LLM calls were not
live-verified. Unknown external decisions are marked **Pending Confirmation**.
No credentials are included.

**Current multi-school update:** The code now includes school administrator
memberships, stable school IDs, school profile and parent-access settings,
admin-entered student pickup records, one-time manual parent invitations,
parent dashboards, school-scoped map storage, and school-scoped role checks.
These are prototype flows tested with local API tests; the frontend has not
been browser-E2E tested. Only the seeded Oakridge school has an active traffic
scenario. Parent email ownership and the family relationship are not
independently verified.

## Prototype snapshot

- Active scenario: Oakridge Academy & Secondary Campus; 775 modeled students,
  540 modeled vehicles, four gates, and five cohorts.
- Active core workflow: scenario overview → bottleneck diagnosis → schedule
  search → deterministic simulation and comparison → optional stress test.
- Authentication roles: school administrator and parent. Administrators select
  only schools they manage; parents select only schools attached to their
  invitation-backed memberships.
- Current schedule search and simulation workflow was reproduced through the
  FastAPI test client during this handover. It is not a field trial.
- The source repository contains a separate six-group SUMO prototype and
  synthetic SUMO artifacts. Those are not connected to the active `/api`
  schedule/simulation workflow.
- Live Google Maps and OpenRouter requests/rendering have not been verified.

## A. Product definition and approved scope

### 1. What problem does GateFlow AI solve, and what is the proposed solution?

**Current prototype problem framing:** Help a school operations user inspect a
modeled dismissal scenario, find a gate bottleneck, generate a schedule/gate
assignment candidate under explicit constraints, and compare that candidate
with the modeled baseline.

**Current solution:** A local React/Vite interface backed by FastAPI. The
seeded Oakridge scenario supports bottleneck diagnosis, constrained schedule
search, and deterministic queue estimates. The prototype also has
school-scoped administrator settings, parent memberships linked to
administrator-entered student records, pickup dashboards, and per-school map
annotations. New school profiles do not receive a copy of Oakridge's traffic
scenario.

This is a prototype decision-support workflow, not evidence that the system
has reduced actual school traffic. Market problem validation is **Pending
Confirmation**.

### 2. Who are the primary and secondary users, and what are their goals?

- **Primary, as implied by the interface:** School administrator/traffic
  coordinator. Goals: review a scenario, inspect the modeled cause, request a
  schedule, and compare modeled outcomes.
- **Secondary:** Parent. Goals: view only linked-school pickup time, gate,
  instructions, notices, and map.

These user groups are represented by JWT-backed roles and prototype screens;
they are not confirmed through user research. Parent access comes from a
one-time invitation created against an administrator-entered student record.
The prototype does not independently verify parent email ownership or the
family relationship. Research, personas, and market validation are **Pending
Confirmation**.

### 3. What are the agreed core features, supporting features, and future enhancements?

**Core prototype workflow**

1. Scenario overview and modeled baseline metrics.
2. Bottleneck diagnosis with evidence from the scenario.
3. Deterministic parsing of a schedule request and constrained schedule search.
4. Deterministic schedule simulation, baseline comparison, and six stress cases.

**Supporting prototype features**

- Multi-school administrator access, school profile and parent-access settings,
  invitation-linked parent membership, and a school-scoped parent dashboard.
- Optional Google Places/Maps school selection, traffic overlay, and
  administrator-authored school-specific gate and blue pickup-zone
  annotations, labeled for buses, cars, two-wheelers, or general pickup.
- Optional OpenRouter explanations grounded in selected GateFlow evidence.
- PostgreSQL-backed administrator/parent login with JWT bearer tokens,
  health/status display, and FastAPI API documentation.

**Not implemented / future work**

- Independent parent email verification, actual email delivery, and
  verification of the family relationship. Invitation links are manually
  shared; the school administrator attests the student/parent email record.
- Traffic-scenario data authoring/import for schools other than Oakridge.
- Capacity, legal parking, or safety validation for map zones; the map stores
  operator-drawn annotations and vehicle-type labels only.
- Connecting the active five-cohort planner to the separate SUMO model.
- Real school traffic, sensor, attendance, or driver-arrival data.
- Production identity management, password reset, administrator-managed user
  accounts beyond the prototype flows, deployment, durable run history, and
  operational safety/legal verification.

The multi-school and vehicle-label map work is prototype implementation, not an
approved production requirement or verified operations capability.

### 4. What is included in the hackathon MVP, and what is explicitly out of scope?

**What this repository can demonstrate now:** A synthetic Oakridge scenario,
modeled bottleneck diagnosis, a feasible schedule candidate, cohort times and
gate assignments, a deterministic baseline-versus-candidate estimate, and
stress-case output. The map and explainer are optional and require working
provider configuration.

**Explicitly not demonstrated as working:** Live school traffic measurement,
real route calculation, verified school parking/safety zones, real driver
assignments or individualized driver pickup data, a SUMO-backed evaluation of
the active candidate, or a measured real-world improvement.

The official hackathon MVP boundary is **Pending Confirmation**; the above
describes the working prototype boundary only.

### 5. Are there official problem statements, judging criteria, approved decisions, or mandatory requirements?

- An older design document refers to a frozen PRD, MRD, and Complete Solution
  as authorities, but those authority documents were not found in the
  repository.
- The 2026-10-25 map/AI design and spec record the prior selected approach:
  restricted Google browser key, backend-only OpenRouter key, operator-authored
  map geometry, shared active school, and bounded project evidence. See
  [map/AI design](./docs/superpowers/specs/2026-10-25-chennai-school-map-grounded-ai-design.md)
  and [map/AI requirements](./docs/superpowers/specs/2026-10-25-chennai-school-map-grounded-ai-spec.md).
- The older [SUMO-first design](./docs/superpowers/specs/2026-10-24-gateflow-ai-design.md)
  proposes a materially different six-group, SUMO-centric MVP. It conflicts
  with the current active five-cohort API prototype and must not be treated as
  proof that the SUMO flow is integrated.
- Official challenge statement, judging rubric, and mandatory submission
  requirements: **Pending Confirmation**.

## B. Current implementation and demo workflow

### 6. Relevant features and implementation status

| Feature | Status | Evidence / boundary |
|---|---|---|
| Oakridge scenario load and overview | **Implemented and tested** | Scenario comes from [scenario.json](./backend/data/scenario.json); active data loader is [data_service.py](./backend/app/services/data_service.py). |
| Bottleneck diagnosis | **Implemented and tested** | [diagnosis_service.py](./backend/app/services/diagnosis_service.py); uses synthetic scenario fields. |
| Natural-language schedule constraint parsing | **Implemented and tested; deterministic only** | [ai_service.py](./backend/app/services/ai_service.py); parser is rule/regex based, not an LLM. |
| Schedule search and eligible gate reassignment | **Implemented and tested** | [planning_service.py](./backend/app/services/planning_service.py); one reproducible candidate was returned in the current smoke run. |
| Queue simulation and comparison | **Implemented and tested; deterministic estimate** | [simulation_service.py](./backend/app/services/simulation_service.py); active API does not call SUMO. |
| Six stress cases | **Implemented and tested; deterministic estimate** | [stress_service.py](./backend/app/services/stress_service.py). |
| Scenario, diagnosis, schedule, simulation UI | **Implemented; type-check/build passed** | [AdminDashboard.tsx](./frontend/src/pages/AdminDashboard.tsx), [FindCausePage.tsx](./frontend/src/pages/FindCausePage.tsx), [FindSchedulePage.tsx](./frontend/src/pages/FindSchedulePage.tsx), [TestSchedulePage.tsx](./frontend/src/pages/TestSchedulePage.tsx). No current-run browser E2E was completed. |
| Multi-school administrator/parent authorization | **Implemented and API-tested** | [school_access.py](./backend/app/models/school_access.py), [schools.py](./backend/app/routers/schools.py), [test_school_access.py](./backend/tests/test_school_access.py). Membership and disabled-access scenarios are tested; full PostgreSQL login/browser flow is not. |
| School profile, parent-access switch, student records, one-time parent invitations | **Implemented; invitation delivery and identity verification limited** | [SchoolManagementPage.tsx](./frontend/src/pages/SchoolManagementPage.tsx), [schools.py](./backend/app/routers/schools.py). Invitations are returned as manually shared links; admins enter/attest the student record. |
| Parent login, authorized-school selection, pickup dashboard | **Implemented; browser E2E unverified** | [LoginPage.tsx](./frontend/src/pages/LoginPage.tsx), [App.tsx](./frontend/src/App.tsx), [ParentDashboard.tsx](./frontend/src/pages/ParentDashboard.tsx). Server checks parent-school membership on protected requests. |
| School-scoped map annotations and file persistence | **Implemented and unit-tested** | [schools.py](./backend/app/routers/schools.py), [map_state_service.py](./backend/app/services/map_state_service.py), [test_map_integrations.py](./backend/tests/test_map_integrations.py). Legacy global `/api/maps` routes were removed. |
| Google Places/Maps/traffic layer | **Implemented but live-unverified** | [SchoolMapPage.tsx](./frontend/src/pages/SchoolMapPage.tsx); browser rendering and provider configuration need live verification. |
| OpenRouter evidence explainer | **Implemented but live-unverified / currently unconfigured** | [openrouter_service.py](./backend/app/services/openrouter_service.py); tests mock the provider. |
| Blue pickup-zone labels by vehicle type | **Implemented as annotations only** | Map polygons are blue and labeled buses, cars, two-wheelers, or general pickup; no capacity, access eligibility, or legal parking rules are enforced. |
| Login and role enforcement | **Implemented; local API tests pass** | [auth.py](./backend/app/routers/auth.py) issues JWTs; roles are `admin` and `parent`. School-specific permissions are checked by [schools.py](./backend/app/routers/schools.py). Parent email ownership is not independently verified. |
| Active SUMO evaluation | **Blocked / disconnected** | SUMO-related runner is separate; active `/api/simulation/run` is deterministic. |
| Jira project records | **Pending Confirmation** | No Jira IDs or records were found in the repository. |

### 7. For each implemented feature, what are its inputs, processing, and outputs?

1. **Scenario and overview** — Reads the cached synthetic JSON scenario:
   school, gates, cohorts, listed traffic metrics, sibling group, and sample
   driver assignment. Returns it from `GET /api/scenario`; the overview renders
   these fields. See [scenario router](./backend/app/routers/scenario.py),
   [data loader](./backend/app/services/data_service.py), and
   [overview](./frontend/src/pages/AdminDashboard.tsx).
2. **Diagnosis** — Inputs are scenario gate utilization/capacity/demand,
   cohort gate/time assignments, dwell assumptions, and scenario-provided queue
   metric. The service selects the highest listed utilization gate and checks
   shared dismissal times. Output is a structured bottleneck, explanation,
   evidence list, and synthetic-data limitations. It does not derive a real
   queue from sensors. See [diagnosis service](./backend/app/services/diagnosis_service.py).
3. **Constraint parsing/validation** — Input is a bounded natural-language
   prompt or structured `ParsedConstraints`. The parser produces deterministic
   constraints; a validator checks known cohort/gate IDs and ranges. Output is
   the parsed/validated constraints or errors/warnings. See [parser](./backend/app/services/ai_service.py),
   [validator](./backend/app/services/constraint_service.py), and
   [schedule models](./backend/app/models/schedule.py).
4. **Schedule search** — Inputs are validated constraints and scenario
   cohorts/gates. The planner enumerates fixed time offsets and eligible gate
   assignments, checks calibrated hourly gate load and bay requirements,
   scores candidates, and filters dominated plans. Output includes candidate
   cohort time/gate rows, loads/capacities, feasibility, and search counts.
   See [planner service](./backend/app/services/planning_service.py) and
   [schedules router](./backend/app/routers/schedules.py).
5. **Simulation/comparison** — Input is a previously registered schedule ID.
   A five-minute deterministic queue model calculates queue, queue-derived
   p95 wait, delay, spillback heuristic, and threshold violations for baseline
   and candidate. The comparison endpoint returns deltas. Results and schedule
   registrations are held in process memory, not a durable run database. See
   [simulation service](./backend/app/services/simulation_service.py) and
   [simulation router](./backend/app/routers/simulation.py).
6. **Stress test** — Input is a registered schedule ID. The service applies
   normal, +20% demand, +30% demand, +50% dwell, reduced-compliance, and rainy
   day assumption factors. Output is six deterministic scenario rows and an
   overall assessment. These are modeled perturbations, not observed incidents.
   See [stress service](./backend/app/services/stress_service.py).
7. **Map** — Inputs are a Google Place ID and operator-authored gate points and
   pickup polygon points. Places search/map/traffic are browser-side; selected
   Place ID and annotations are shared through FastAPI and a JSON file.
   Outputs are a focused map and saved generic annotations, if Google is
   configured. See [map page](./frontend/src/pages/SchoolMapPage.tsx),
   [map API](./backend/app/routers/maps.py), and
   [annotation model](./backend/app/models/map_annotations.py).
8. **Explainer** — Input is a question plus a source/reference ID. FastAPI
   resolves an existing diagnosis, candidate, simulation, or stress result,
   serializes only selected evidence, and sends it to the configured OpenRouter
   model. Output is a labeled non-authoritative explanation and evidence labels.
   It does not alter deterministic calculations. See [explanation router](./backend/app/routers/explanations.py)
   and [OpenRouter service](./backend/app/services/openrouter_service.py).

### 8. What is the exact end-to-end demo workflow?

1. Start PostgreSQL, then start backend and frontend using section F. Open
   `http://127.0.0.1:3000` and sign in with the credentials generated in
   `backend/.seed-users.json` at the first successful backend startup.
2. Review the Oakridge overview: 4 gates, 5 cohorts, scenario-provided metrics,
   and synthetic/deterministic labels.
3. Open **Find the Cause** and show Gate 2 as the listed bottleneck. Explain
   that the 48-vehicle peak queue is a scenario-supplied baseline, not a fresh
   measurement.
4. Open **Find a Better Schedule**. For a reproducible sibling-synchronized
   example, enter “Keep Kindergarten fixed and synchronize sibling groups;
   prioritize queue reduction using current scenario demand.” Generate plans and inspect the
   cohort table and gate assignment. The default UI request fixes Kindergarten
   but leaves sibling synchronization off; both constraints are conditional,
   not universal hard rules.
5. Select the returned candidate and open **Test the Schedule**. Run
   simulation, view baseline/candidate metrics, then stress-test results.
   Describe every result as a deterministic estimate from synthetic inputs.
6. Optionally open **School Map**. This works only after a restricted Maps
   browser key is locally configured and the Google APIs are enabled. Select a
   Chennai school, inspect the traffic overlay, and add only operator-verified
   gate/pickup annotations. Current polygons are generic; do not label them
   bus/car/two-wheeler capacity zones.
7. Optionally ask the explainer about a displayed diagnosis, schedule, or
   simulation. It requires backend OpenRouter configuration and outbound
   provider access. If not configured, show the explicit unavailable state
   rather than implying AI succeeded.

### 9. Known bugs, incomplete screens, setup problems, failure cases, and demo limitations

- **Synthetic-only core:** no live school traffic or field-observed measurements.
- **Baseline mismatch:** scenario overview/diagnosis reports the supplied
  48-vehicle queue, 16.4-minute p95 wait, and 138 vehicle-hours. Active
  simulation independently computes a 3.8-vehicle queue and 2.5-minute
  queue-derived p95 wait for its baseline. They are different sources/models
  and must not be combined as if they were the same baseline.
- **Constraint range mismatch:** the parser/model may accept a requested
  `maxShiftMin` above 30 (up to 60 in parsing), but planner offset options are
  only −30 through +30 minutes. A 60-minute setting does not create ±60-minute
  candidates.
- **Kindergarten/sibling rules are conditional:** Kindergarten is fixed only
  when its cohort is in `fixedGroups`; sibling offsets are synchronized only
  when `siblingSync` is true. The UI's default prompt requests Kindergarten
  fixed, but this is not globally enforced by the backend.
- **Map scope gap:** generic pickup polygons are not distinct blue bus/car/
  two-wheeler zones and do not carry vehicle compatibility/capacity constraints.
- **External providers:** keys are present in the local environment, but live
  Google rendering and OpenRouter calls were not validated. A configured key
  does not prove billing, API enablement, referrer restrictions, or provider
  availability.
- **Auth:** demo login depends on PostgreSQL and a configured `JWT_SECRET`.
  Driver demo records beyond the sample Sarah Jenkins assignment are synthetic;
  all drivers currently see the same sample assignment. There is no user
  management or password-reset screen. This is not production identity
  management.
- **SUMO status inconsistency:** SUMO 1.28.0 executable exists on this machine,
  but `/api/health` hardcodes `sumo: not_installed`, simulation documentation
  says it is unavailable, and the active endpoint does not run it.
- **Database dependency:** the active protected demo screens now require a
  reachable PostgreSQL database for login and role checks. Startup creates
  missing user tables and demo users; a database outage prevents login.
- **Stale environment example:** `backend/.env.example` contains
  `VITE_API_BASE_URL`, but the frontend client uses the `/api` path and the
  Vite proxy reads `GATEFLOW_API_TARGET`; the former is not used by the active
  frontend.
- **No saved current browser screenshot or live-provider log was found for this
  handover.** The reproducible evidence is the API test-client run and
  automated checks described below.
- **Build warning:** Vite reports a non-blocking `__dirname` compatibility
  warning in [vite.config.ts](./frontend/vite.config.ts).

## C. Congestion diagnosis and scheduling

### 10. How does the system identify congestion and determine its causes?

The active diagnosis picks the gate with the highest scenario `utilizationRate`.
For Gate 2, the scenario lists 135 vehicles/hour demand against 90
vehicles/hour capacity (150%). It then finds assigned cohorts, checks for
shared dismissal times, reports assumed average/design dwell, and displays the
least-utilized gate. The 48-vehicle peak queue is read from a separate
scenario-provided metric.

This is a rule-based explanation of synthetic fields. It does not receive
live traffic, infer incident causes, observe a school curb, or prove that the
reported queue resulted from the gate demand. See [diagnosis service](./backend/app/services/diagnosis_service.py)
and [scenario inputs](./backend/data/scenario.json).

### 11. How does it generate, optimize, or select an arrival schedule?

The active planner performs bounded deterministic enumeration, not machine
learning or a general-purpose solver:

- Time offsets are selected from `[-30, -20, -15, -10, -5, 0, 5, 10, 15, 20, 30]`
  minutes and constrained by `maxShiftMin`.
- It combines offset choices with each cohort's eligible gate choices, checks
  the calibrated hourly gate-load profile, scores candidates against the
  selected objective, and filters Pareto-dominated candidates.
- The full combination search is capped at 5,000 evaluations.
- Gate load uses source-gate hourly demand apportioned by cohort
  dismissal-window vehicle volumes, then a fixed five-bucket arrival profile.
  This avoids treating the cohort volume itself as an hourly rate.
- The feasibility threshold is 105% of each gate's listed hourly capacity.
  It does not silently increase capacities.

**Why the reproduced candidate changes only one cohort's gate:** In the
canonical [scenario](./backend/data/scenario.json), `c-g45` (Elementary Upper
Cohort) alone lists alternate eligibility at Gate 2 or Gate 4. Other cohorts
without `eligibleGateIds` retain their current gate. `c-g13` needs five bays
while Gate 2 has four; its current assignment is grandfathered, but a new
assignment must satisfy the destination gate's bay requirement. The planner
does not invent alternate eligibility.

The search is candidate generation/ranking, not proof of global optimality.
The exact implementation is in [planning_service.py](./backend/app/services/planning_service.py).

### 12. How are Kindergarten timing, sibling synchronization, permitted shifts, pickup-zone allocation, and zone capacity enforced?

- **Kindergarten:** Fixed when `c-prek` is present in `fixedGroups`. The default
  schedule prompt includes that rule; arbitrary requests need to include it.
- **Sibling synchronization:** When `siblingSync=true`, configured sibling
  cohorts share an offset. The data group is `c-g13`/`c-g45`. This applies to
  time offsets; each cohort still has its own gate assignment.
- **Permitted shifts:** The planner filters its discrete ±30-minute offset
  options by `maxShiftMin`. It cannot generate a 60-minute shift even if that
  maximum is supplied.
- **Gate allocation:** `eligibleGateIds`, current assignment, optional gate
  restrictions, and the `allowGateReassignment` flag bound choices. Missing
  eligibility means current gate only.
- **Gate capacity/bays:** A calculated hourly load above 105% capacity rejects
  a candidate. New destination assignments need enough bays. The current
  undersized Gate 2 assignment for `c-g13` is labeled `grandfathered`.
- **Pickup/parking zones:** The active five-cohort planner does not allocate
  vehicle-type parking zones. Its `zoneRestrictions` field is effectively a
  gate-ID restriction. The map polygons are presentation annotations, not
  capacity-constrained zones. Vehicle/zone compatibility exists only in the
  separate SUMO-oriented planner described in section E.

### 13. Which parts are rule-based, optimization-based, simulation-based, or ML-based?

- **Rule-based:** natural-language constraint parsing in
  [ai_service.py](./backend/app/services/ai_service.py), constraint validation,
  diagnosis selection, gate eligibility, bay checks, and feasibility limits.
- **Search/optimization-like:** exhaustive enumeration, objective scoring,
  and Pareto filtering in the active planner. It is deterministic bounded
  combinatorial search, not a learned optimizer or a proof of optimum.
- **Simulation-based:** deterministic five-minute queue recurrence for
  active baseline/candidate comparison and stress tests.
- **Optional LLM:** OpenRouter generates a natural-language explanation from
  server-selected evidence. It does not parse authoritative schedule
  constraints or change candidate metrics.
- **Machine learning trained on GateFlow traffic:** **None found in the active
  implementation.**

### 14. What happens when no feasible schedule satisfies the mandatory constraints?

`POST /api/schedules/search` returns HTTP 422 with error code
`INFEASIBLE_PLAN`, a plain-language message, and a search explanation including
capacity blockers where available. Invalid constraints return
`INVALID_CONSTRAINTS` with validation details. If no cohort has an eligible
assignment meeting a requested gate restriction and bay requirement, the
planner returns an explanation before enumerating candidates. It does not
raise capacity values or silently relax the constraints. See
[schedules.py](./backend/app/routers/schedules.py).

### 15. How are baseline and candidate schedules evaluated, and which metrics are actually calculated?

The active simulation runs the same deterministic arrival profile and gate
capacity assumptions for an all-zero-offset baseline and the selected
candidate. It reports:

- peak queue (vehicles);
- queue-derived p95 wait (minutes);
- total delay (vehicle-hours);
- spillback distance (a bay/queue heuristic, metres);
- zone violations (modeled threshold exceedance count/value);
- time-interval queue series, plus derived comparison percentages.

The field named `zoneViolations` is calculated as
`max(0, peakQueue - vehicleCapacityThreshold)` and labeled in “incidents”; it
is not a count of observed incidents.

Stress scenarios change synthetic demand, dwell, and compliance factors. None
of these values are sensor observations. The scenario's separately supplied
overview metrics do not come from this same simulation run.

## D. Data, testing, and measurable results

### 16. Which datasets, files, databases, and APIs are connected to the running application?

- **Active scenario input:** [backend/data/scenario.json](./backend/data/scenario.json),
  loaded and cached by [data_service.py](./backend/app/services/data_service.py).
- **Active map persistence:** backend-managed JSON file configured by
  `MAP_STATE_PATH`/the settings default, keyed by Google Place ID. It is not
  PostgreSQL.
- **Optional external APIs:** Google Maps JavaScript/Places in the browser and
  OpenRouter from FastAPI, when configured.
- **Database:** PostgreSQL `schooltraffic` stores the demo users/password
  hashes used by login and role checks. Scenario, diagnosis, planning, and
  simulation inputs remain in the synthetic JSON scenario; map annotations
  remain file-backed JSON.
- **Not connected to the active service:** `data/friend_dataset` and the
  separate SUMO output/handoff files under `data/simulations`.

### 17. Which inputs are real, synthetic, hardcoded, assumed, or dynamically generated?

- **Synthetic/hardcoded:** Oakridge school identity, 775 student/540 vehicle
  totals, gate capacities/demands, cohort volumes/times/bay needs, listed
  utilization, supplied baseline metrics, dwell values, driver profile and
  directions. The scenario metadata explicitly labels it synthetic.
- **Assumed/model parameters:** arrival profile weights, five-minute queue
  recurrence, 105% feasibility margin, bay-to-queue spillback conversion,
  stress multipliers, and threshold.
- **Generated dynamically:** search combinations/candidate response, simulation
  run ID/timestamp, comparison, stress output, user-authored map annotations,
  and (if configured) an LLM explanation.
- **Third-party data, optional and currently unverified:** Google Place/map/
  traffic layer data. Google traffic display is not a school-owned sensor
  measurement.
- **LLM provider, optional and currently unverified:** OpenRouter receives
  bounded GateFlow evidence for an explanation. The model may have broader
  pretraining; the application cannot guarantee provider retention/training.
- **Field-measured school traffic or observed driver data:** none connected.

### 18. Which fields does the application use, and where do they originate?

| Field group | Examples | Origin / active use |
|---|---|---|
| School | name, total students/vehicles, session window, dwell assumptions | Synthetic JSON scenario; overview, diagnosis, planning/simulation configuration |
| Gate | ID, bays, hourly capacity, peak demand, utilization, assigned grades | Synthetic JSON scenario; diagnosis, feasibility, simulation |
| Cohort | ID, grade span, students, dismissal-window vehicle volume, time, assigned/eligible gates, bay requirement | Synthetic JSON scenario; parser validation, planning and simulation |
| Sibling relation | cohort IDs and shared pickup description | Synthetic scenario; used only if sibling synchronization is requested |
| Baseline traffic metrics | queue, p95 wait, utilization, delay | Static scenario values; overview and diagnosis, not active simulation baseline |
| Constraints | demand factor, fixed cohort IDs, sibling sync, max shift, gate restrictions, reassignment flag, objective | Frontend prompt/controls parsed deterministically or request model; validated before planning |
| Candidate | offsets, gate assignments, calculated loads/capacity, bay status, score | Produced by active planner at request time; registered in process memory |
| Simulation | baseline/candidate queue, wait, delay, spillback heuristic, threshold values | Active deterministic service; run result held in process memory |
| Map | Google Place ID, gate marker names/coordinates, pickup polygon points | Google supplies place/map context; operator authors annotations; backend stores JSON |
| Explanation | source, reference ID, question | UI request; backend resolves evidence. Provider output is not authoritative |

### 19. What tests have been completed, and what were the actual results?

Checks run for this handover:

- `python -m pytest tests\ -q --tb=short -p no:cacheprovider` from `backend` —
  **48 passed**, including unauthenticated rejection and driver role-policy
  tests.
- `npm run lint` from `frontend` — **passed** (`tsc --noEmit`).
- `npm run build` from `frontend` — **passed**; Vite emitted a non-blocking
  `__dirname` warning.
- A live local `TestClient` startup against PostgreSQL `schooltraffic`
  provisioned four demo accounts and verified admin JWT login/access, driver
  JWT login/read-only access, and rejection of unauthenticated admin routes.
- `python tests\test_planner.py` from `backend` with `PYTHONPATH=.` — **6
  standalone unit tests passed** for the separate planner prototype. These do
  not establish SUMO integration with the active API.
- `python test_constraints.py` from `backend` — printed **5 PASS** checks for
  the separate planner/zone helper.
- Active API workflow reproduced with FastAPI `TestClient`: scenario, provider
  status, constraint parse, schedule search, simulation, comparison, and stress
  endpoints all returned HTTP 200 for the demonstrated baseline-demand case.
- `python -m compileall -q app tests` and `git diff --check` — passed after
  the authentication changes.

The mocked OpenRouter integration tests do not prove a live provider request.
No live Maps request or current browser E2E was completed for this handover.

### 20. Do we have reproducible comparisons, screenshots, logs, or sample outputs?

**Reproducible API sample from the local FastAPI test client:**

- Parsed prompt: “Keep Kindergarten fixed and synchronize sibling groups;
  prioritize queue reduction using current scenario demand.”
- Parser: HTTP 200, valid; `maxShiftMin=30`, `fixedGroups=["c-prek"]`,
  `siblingSync=true`.
- Search: HTTP 200; 2,662 combinations evaluated, 1,331 feasible, 1,331
  infeasible, 1,330 dominated; one candidate returned.
- Candidate: `candidate-alpha-0`; Kindergarten remains at 2:30 PM; lower
  elementary remains at Gate 2; upper elementary remains at 3:00 PM but is
  assigned Gate 4; other cohort times/gates remain at baseline.
- Candidate gate loads: Gate 1 110/140, Gate 2 70/90, Gate 3 82/100, Gate 4
  65/130 vehicles/hour. The lower elementary Gate 2 assignment is
  `grandfathered`; the upper elementary Gate 4 bay requirement is satisfied.
- Simulation: HTTP 200, `DeterministicEstimate`; queue 3.8→0 vehicles, modeled
  p95 wait 2.5→0 minutes, total delay 0.6→0 vehicle-hours, spillback estimate
  0→0 metres, modeled zone violations 0→0.
- Comparison: HTTP 200; model reports 100% queue reduction for this specific
  synthetic run; stress endpoint returns six cases.

This is a local deterministic output, **not a measured or validated
improvement**. The apparently large percentage is from a small model baseline
and must not be presented as real-world performance.

An existing separate SUMO record is
[last_run_metrics.json](./data/simulations/school_demo/last_run_metrics.json).
It records 583 vehicles generated, 97 completed (16.64%), mean wait 936.165
seconds, p95 wait 1,844 seconds, and mean trip duration 1,232.433 seconds on a
fictional synthetic network. It is not the active API candidate run and should
not be presented as a positive operational result.

No saved screenshot or current live-provider log was identified as evidence in
this handover. API sample details above are reproducible through the scenario,
constraints, and endpoints listed in section F.

### 21. Which metrics can we safely present to judges?

**Safe when labeled precisely:**

- Scenario inputs: 4 gates, 5 cohorts, 775 modeled students, 540 modeled
  vehicles.
- Scenario-listed Gate 2 demand/capacity: 135/90 vehicles per hour, 150% as
  recorded in synthetic scenario data.
- Search count and candidate gate/time assignments from the reproduced
  deterministic API run.
- The queue/wait/delay output of that same run, but only as a
  **deterministic synthetic estimate** and with its baseline values shown.
- Test/build pass counts as software validation, not as traffic validation.

**Do not present as observed or guaranteed:** the scenario-provided 48-vehicle
queue, 16.4-minute p95 wait, and 138 vehicle-hour delay as field measurements;
the 100% modeled queue reduction as an actual improvement; or old SUMO output
as evidence that the active candidate was simulated.

Metric caveats: cohort vehicle counts are dismissal-window volumes with no
window duration specified and are not hourly rates. Simulation p95 is derived
from queue samples, not unique vehicle trip records. Spillback distance is a
heuristic derived from modeled queue/bay storage, not a measured road queue.
The “zone violations” metric is modeled threshold exceedance, not observed
incidents. Market impact, accuracy, safety, and operational benefit are
**Pending Confirmation**.

## E. Simulation, maps, and integrations

### 22. Is SUMO the primary engine or an additional validation tool? Is the proposed schedule passed into SUMO?

SUMO is **not** the active engine for the current web/API workflow. The active
`POST /api/simulation/run` uses the deterministic queue estimate and returns
`simulationMethod: DeterministicEstimate`. The active search's candidate ID
and schedule are not passed into `backend/app/simulation/runner.py`.

There is a separate SUMO-oriented code path using a different six-group
scenario. SUMO could be treated as a separate validation prototype, but the
repository does not currently implement the planned active-candidate handoff.
The README and health response say SUMO is not installed, while this machine
has a SUMO 1.28.0 executable at the runner's default Windows path. The binary's
presence does not establish an integrated or validated workflow.

### 23. Which SUMO outputs are available and supported by actual test evidence?

The separate artifact [last_run_metrics.json](./data/simulations/school_demo/last_run_metrics.json)
records an engine label of SUMO and the values listed in answer 20. The
four-scenario handoff
[README_DATA.md](./data/simulations/school_demo/FINAL_HANDOFF_RATHI/README_DATA.md)
documents synthetic demand, fictional network, single-run outputs, provisional
zone capacities, and metric limitations.

These are existing artifacts, not a newly reproduced run of the active
candidate. The six standalone tests validate helper/planner constraints and
repeatability, not SUMO execution, metric extraction, or schedule integration.
No active-schedule SUMO output is supported by test evidence found here.

### 24. Which map and routing providers are used? Does map display or route calculation work?

- Map implementation uses the Google Maps JavaScript API, Places text search,
  and the Google traffic overlay in
  [SchoolMapPage.tsx](./frontend/src/pages/SchoolMapPage.tsx).
- Search is bounded around Chennai; selecting a Place ID focuses the map around
  that place. Traffic is Google map-layer context, not school-specific
  measurement.
- The map page has gate markers and operator-authored pickup polygons; the
  current polygon fill is generic purple, not separate vehicle-class blue
  zones.
- No Directions API, route calculation, turn-by-turn route, or live
  driver-to-gate routing is implemented in this flow. Sample driver
  instructions are scenario text.
- A Maps browser key is configured locally, but map rendering and Places/traffic
  provider calls have not been live-verified. Annotation API persistence and
  validation are covered by tests.

### 25. What environment-variable names and provider configuration are expected?

- **OpenRouter backend:** `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
  (default `moonshotai/kimi-k2:free`), and optional
  `OPENROUTER_BASE_URL` (default OpenRouter API URL). Keep the key in an
  uncommitted backend `.env`; the browser must not receive it.
- **Google Maps browser key:** `VITE_GOOGLE_MAPS_API_KEY` in
  `frontend/.env.local`. This Vite key is visible in browser assets by design.
  Restrict it by approved HTTP referrers and only the Maps JavaScript and
  Places APIs used by the app.
- **Frontend API proxy:** `GATEFLOW_API_TARGET`, default
  `http://127.0.0.1:8000`.
- **Backend data paths:** optional `SCENARIO_DATA_PATH` and `MAP_STATE_PATH`;
  defaults are `./data/scenario.json` and `./data/map_state.json`.
- **Demo authentication:** PostgreSQL settings `DB_HOST`, `DB_PORT`, `DB_NAME`,
  `DB_USER`, `DB_PASSWORD`, plus a private `JWT_SECRET` are required for login.

`VITE_API_BASE_URL` appears in the backend example file but is not consumed by
the active frontend; use `GATEFLOW_API_TARGET` to change the Vite proxy target.

Safe example values, not credentials:

```dotenv
# backend/.env (optional OpenRouter and database settings)
OPENROUTER_API_KEY=
OPENROUTER_MODEL=moonshotai/kimi-k2:free
DB_HOST=localhost
DB_PORT=5432
DB_NAME=schooltraffic
DB_USER=postgres
DB_PASSWORD=
JWT_SECRET=
```

```dotenv
# frontend/.env.local (optional Google Maps browser key)
VITE_GOOGLE_MAPS_API_KEY=
```

The current `backend/.env.example` has blank provider-key values. Because
credentials were previously pasted into chat and a provider key was present in
an example file, the owner should revoke/rotate both provider keys and check
repository history before using them. No key values are repeated here.

### 26. Which integrations are working, mocked, configured but untested, or planned?

| Integration | Current status |
|---|---|
| FastAPI core endpoints | Working in tests and current local TestClient workflow |
| Scenario JSON | Working; synthetic; independent of PostgreSQL |
| PostgreSQL/JWT auth | Implemented and smoke-tested against local `schooltraffic`: one admin and three demo drivers seeded; admin login/access, driver read-only denial, driver assignment access, and unauthenticated denial verified |
| Google Maps/Places/traffic | Code present; browser key configured locally; live calls/rendering unverified |
| Map annotation API/file storage | Implemented and covered by local backend tests; read/write routes require authenticated roles, edits are admin-only |
| OpenRouter | Code present; test uses mocked response; key configured locally; no live provider call |
| SUMO executable | SUMO 1.28.0 binary present on this machine; active web API does not invoke it |
| SUMO artifacts | Separate synthetic results/handoff exist; not linked to active candidate ID |
| Jira | No records in repository; external board status Pending Confirmation |

## F. Technical setup and Jira status

### 27. What frontend, backend, database, frameworks, APIs, libraries, and deployment services are actually used?

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS plugin, and Lucide
  icons; `npm run dev`, `npm run lint` (TypeScript check), and `npm run build`.
  See [package.json](./frontend/package.json).
- **Backend:** Python FastAPI, Pydantic/Pydantic Settings, Uvicorn, HTTPX.
  Authentication uses SQLAlchemy, PostgreSQL/psycopg, bcrypt, and python-jose
  JWTs. See [requirements.txt](./backend/requirements.txt).
- **Data store:** static scenario JSON for active planning; file-backed JSON
  for map state; process-local dictionaries for schedules and simulation
  results. PostgreSQL stores demo identities/password hashes; scenario and
  traffic data remain synthetic JSON.
- **External services:** optional Google Maps JavaScript/Places and OpenRouter.
- **Deployment:** local development commands only were found; cloud hosting or
  a production deployment service is **Pending Confirmation**.

### 28. Where are the repository, entry points, core logic, configuration, and tests?

- Repository root: `E:\School_Traffic_Management`.
- Backend entry point: [backend/app/main.py](./backend/app/main.py).
- Frontend entry point: [frontend/src/main.tsx](./frontend/src/main.tsx) and
  [frontend/src/App.tsx](./frontend/src/App.tsx).
- Scenario: [backend/data/scenario.json](./backend/data/scenario.json).
- Core planner/simulation: [planning_service.py](./backend/app/services/planning_service.py),
  [simulation_service.py](./backend/app/services/simulation_service.py),
  [stress_service.py](./backend/app/services/stress_service.py).
- API routers: [backend/app/routers](./backend/app/routers).
- Settings/database: [config.py](./backend/app/config.py),
  [db.py](./backend/app/db.py), `backend/.env.example`,
  `frontend/.env.example`, and [vite.config.ts](./frontend/vite.config.ts).
- Active automated tests: [backend/tests](./backend/tests), especially
  [test_backend.py](./backend/tests/test_backend.py) and
  [test_map_integrations.py](./backend/tests/test_map_integrations.py).
- Separate SUMO planner/runner: [planner.py](./backend/app/planner.py),
  [scenario.py](./backend/app/scenario.py),
  [zones.py](./backend/app/zones.py), and
  [runner.py](./backend/app/simulation/runner.py).
- Existing project overview/run notes: [README.md](./README.md).

### 29. What are the exact steps to run and demonstrate the current application?

From PowerShell, in separate terminals:

```powershell
Set-Location E:\School_Traffic_Management\backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
Set-Location E:\School_Traffic_Management\frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:3000`. Check API health at
`http://127.0.0.1:8000/api/health` and interactive API docs at
`http://127.0.0.1:8000/api/docs`.

PostgreSQL and a private `JWT_SECRET` are required for the authenticated demo
workflow. On first startup, the backend writes generated initial account
credentials to the ignored `backend/.seed-users.json` file; read it locally
and remove it after securely recording credentials. Google/OpenRouter keys
are optional. Configure optional providers only after rotating/restricting
keys as described in answer 25. Run the demo in the sequence in answer 8.

### 30. Which environment variables and setup steps are required?

**Required for the authenticated local demo:** PostgreSQL database
`schooltraffic`, backend dependencies from `backend/requirements.txt`, frontend
dependencies from its lockfile, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
`DB_PASSWORD`, a private `JWT_SECRET`, and local ports 8000/3000. Google and
OpenRouter keys are optional for the scenario/planning/simulation workflow.

**Optional:** `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`,
`OPENROUTER_BASE_URL`, `VITE_GOOGLE_MAPS_API_KEY`, `GATEFLOW_API_TARGET`,
`SCENARIO_DATA_PATH`, `MAP_STATE_PATH`, and database variables `DB_HOST`,
`DB_PORT`, `DB_NAME`, `DB_USER`,
`DB_PASSWORD`, `JWT_SECRET`.

Backend settings load `.env` from the backend working directory when started
as shown above. Frontend Vite variables must be present when Vite starts; use
`frontend/.env.local` for the Maps key. Never commit either local `.env` file.
Use restricted, rotated credentials and never show secret values in the UI.

### 31. If Jira work already exists, what are the current epic/story names, statuses, dependencies, and ownership?

No Jira issue key, epic/story record, status, dependency, or owner was found in
the repository materials reviewed. No Jira board was queried for this
handover. Existing Jira records and ownership are therefore **Pending
Confirmation**; none are invented here.

## G. Final demo and remaining decisions

### 32. What exact sequence should be followed during the demo?

1. Open `http://127.0.0.1:3000` and sign in using the locally generated admin
   credentials in `backend/.seed-users.json`.
2. State up front: “This is the synthetic Oakridge scenario; the planner and
   simulation are deterministic estimates.”
3. Show the 4 gates, 5 cohorts, synthetic demand, and listed Gate 2
   150%-utilization bottleneck.
4. Show the diagnosis evidence and distinguish the scenario's supplied queue
   metric from model-calculated results.
5. Generate the candidate with the explicit Kindergarten-fixed,
   sibling-synchronization prompt from answer 33; point out the one eligible
   alternate, Gate 4, and the grandfathered Gate 2 bay mismatch. The default
   UI prompt does not enable sibling synchronization.
6. Run simulation and comparison; show model values and say explicitly they
   are not measured traffic reduction.
7. Show the six stress cases as sensitivity assumptions, not forecasts.
8. Only if provider configuration works, show the Chennai map and ask an
   evidence-bounded explainer question. Otherwise show the visible unavailable
   status and keep the core flow moving.
9. Do not present the separate SUMO artifact as evaluation of the candidate
   generated in this workflow.

### 33. Which sample inputs, screens, outputs, and measured results should be presented?

- **Input prompt:** “Keep Kindergarten fixed and synchronize sibling groups;
  prioritize queue reduction using current scenario demand.”
- **Screens:** Overview, Find the Cause, Find a Better Schedule, Test the
  Schedule; optional School Map and project explainer only if provider checks
  pass.
- **Schedule output:** five cohort rows; `c-g45` moves from Gate 2 to eligible
  Gate 4; times remain unchanged in the reproduced top candidate. Gate loads
  are 110/140, 70/90, 82/100, and 65/130 veh/h.
- **Simulation output:** baseline→candidate queue 3.8→0 vehicles, p95
  queue-derived wait 2.5→0 minutes, total delay 0.6→0 vehicle-hours, modeled
  spillback 0→0 m, and modeled violations 0→0.
- **Search output:** 2,662 evaluated, 1,331 feasible, 1,331 infeasible, 1,330
  dominated, one returned candidate.

These are outputs of the reproduced synthetic deterministic run, not
field-measured results. There are no verified live provider results to present.

### 34. What claims should be avoided?

- “Real-time school traffic monitoring,” “live school queue,” or “sensor
  measured” — no school sensor feed is connected.
- “The system reduced traffic/wait by 100%” — this is one deterministic
  comparison with a small modeled baseline, not a real-world outcome.
- “The active candidate was validated in SUMO” — it was not passed to the
  separate SUMO runner.
- “The AI is trained only on GateFlow” or “knows only this project” — the
  hosted model may have broader pretraining. The application constrains the
  supplied request context but cannot control model training or provider
  retention.
- “AI optimized the schedule” — constraint parsing/search are deterministic;
  the optional LLM only explains selected evidence.
- “Gate 4 is safe/approved/available for every cohort” — only explicit
  scenario eligibility and modeled bay/capacity checks are applied.
- “Blue bus, car, and two-wheeler zones are implemented” — only generic map
  polygons exist.
- “Real school drivers have authenticated accounts,” “routes are live,” or
  “parking is legally verified” — accounts are synthetic demo users, and the
  route/parking claims are not supported.
- Any claim that synthetic assumptions constitute market validation or
  operational readiness.

### 35. What essential work or decisions remain before the jury presentation?

1. **Credential hygiene:** revoke/rotate keys previously shared in chat or
   found in example configuration; apply referrer/API restrictions to the
   Google key; keep OpenRouter server-side; verify only safe configured status
   after local setup.
2. **Decide map scope:** either present generic operator-drawn pickup
   annotations honestly, or implement and test the requested distinct blue
   bus/car/two-wheeler zones, their vehicle compatibility, and capacity
   constraints. Do not imply the latter exists now.
3. **Resolve SUMO story:** either describe SUMO as a separate prototype and
   show its limitations, or integrate the active candidate-to-SUMO pipeline,
   persist its inputs/outputs, test it end-to-end, and correct the stale
   health/README “not installed” messaging.
4. **Resolve source-of-truth metrics:** explain or reconcile the static
   scenario baseline values versus active simulation baseline before
   presenting a single chart.
5. **Confirm requirements:** obtain official challenge statement, judging
   rubric, current MRD/PRD/Complete Solution, and Jira board/ownership (if
   any). All are **Pending Confirmation** here.
6. **Demo verification:** run the app in the target presentation environment,
   verify API health and a fresh schedule/simulation, capture screenshots, and
   test Maps/OpenRouter live only if keys are configured and restricted.
7. **Set demo boundaries:** use the seeded demo login; avoid real student,
   driver, school, traffic, or safety claims.
