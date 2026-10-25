# GateFlow AI — School Dismissal Traffic Demo

GateFlow AI is a local decision-support demo for school dismissal planning. It
uses a synthetic Oakridge Academy scenario to diagnose modeled gate bottlenecks,
search feasible dismissal schedules, and compare a selected schedule against a
deterministic queue estimate. It also provides school-scoped administrator
settings and invitation-linked parent pickup views.

> **Data and results:** Scenario inputs are synthetic. Planning, diagnosis, and
> simulation results are deterministic estimates, not live traffic observations,
> field measurements, or guaranteed improvements. SUMO is not installed.

## Demo scenario

- Oakridge Academy & Secondary Campus
- 4 gates and 5 dismissal cohorts
- 540 modeled vehicles in the scenario
- Gate 2 is the primary capacity bottleneck: 135 veh/h listed demand against
  90 veh/h capacity (150%)
- Gate 4 is listed as the least-utilized gate

The scenario is defined in [`backend/data/scenario.json`](backend/data/scenario.json).
Its cohort vehicle counts represent synthetic dismissal-window volumes; the
scenario does not specify the duration of that window. Do not interpret those
counts as hourly rates.

## Core features

### 1. Diagnose the cause

The dashboard and diagnostic view load the scenario, gate capacities, cohort
assignments, and scenario-provided baseline metrics from the backend. Diagnosis
identifies the modeled Gate 2 overload and synchronized elementary dismissal.
It distinguishes the hourly demand and capacity values from dismissal-window
vehicle counts, and reports the scenario's 48-vehicle peak queue as a supplied
baseline rather than deriving it from hourly demand.

### 2. Find a better schedule

The planner parses the request and searches dismissal offsets and permitted gate
assignments. At baseline demand, it can route the Grades 4–5 cohort to its
scenario-listed alternate, Gate 4, while retaining other constraints such as
Kindergarten fixed times and sibling synchronization.

Alternate assignments must be listed as eligible and meet the cohort's bay
requirement. The existing Grades 1–3 assignment at Gate 2 requires 5 bays while
Gate 2 has 4; that existing assignment is surfaced as **grandfathered** and is
not treated as a valid new reassignment. Gate capacity is not silently raised.
Search evaluates at most 5,000 combinations and explains capacity blockers when
it cannot find a feasible plan.

### 3. Test and compare a schedule

The simulation endpoint compares the selected candidate to the baseline using
the same calibrated arrival profile as the planner. The UI displays queue,
wait, delay, spillback, and constraint metrics, with synthetic and deterministic
labels. A separate stress test reports modeled demand, dwell-time, and
compliance scenarios, including peak gate utilization and whether it exceeds the
planner's existing 105% limit.

## What changed in this demo work

- **Planning and constraints:** Made hourly gate-load checks and queue estimates
  use a shared calibrated arrival profile; enforced scenario gate eligibility,
  alternate-gate bay fit, zone restrictions, and the gate-reassignment setting.
  Infeasibility responses now include gate-capacity blockers.
- **Simulation and stress testing:** Reused the planner's arrival profile,
  accounted for shifted dismissal times and selected gate assignments, aligned
  candidate reductions with computed queue metrics, and reported capacity-limit
  violations during stress tests.
- **Diagnosis and UI:** Removed unsupported statements that implied measured
  queue/spillback conditions, made bottleneck and underutilized gate details
  scenario-driven, and corrected schedule cards so worsening or unchanged
  metrics are not presented as improvements.
- **Frontend workflow:** Connected the existing scenario, diagnosis, schedule,
  simulation, comparison, and stress-test UI to the FastAPI endpoints. The
  default schedule request uses baseline demand; higher-demand requests remain
  available and can correctly return infeasible.
- **Regression coverage:** Added tests for eligible reassignment, capacity
  constraints, candidate metric calculations, simulation comparison, stress
  tests, and high-demand infeasibility.

Related implementation files:

- Planner and queue metrics: [`backend/app/services/planning_service.py`](backend/app/services/planning_service.py)
- Diagnosis: [`backend/app/services/diagnosis_service.py`](backend/app/services/diagnosis_service.py)
- Simulation and comparison: [`backend/app/services/simulation_service.py`](backend/app/services/simulation_service.py)
- Stress tests: [`backend/app/services/stress_service.py`](backend/app/services/stress_service.py)
- Schedule and simulation API models: [`backend/app/models/schedule.py`](backend/app/models/schedule.py), [`backend/app/models/simulation.py`](backend/app/models/simulation.py)
- Scenario and constraints UI: [`frontend/src/pages/AdminDashboard.tsx`](frontend/src/pages/AdminDashboard.tsx), [`frontend/src/pages/FindCausePage.tsx`](frontend/src/pages/FindCausePage.tsx), [`frontend/src/pages/FindSchedulePage.tsx`](frontend/src/pages/FindSchedulePage.tsx)
- Test and compare UI: [`frontend/src/pages/TestSchedulePage.tsx`](frontend/src/pages/TestSchedulePage.tsx)
- Backend regression tests: [`backend/tests/test_backend.py`](backend/tests/test_backend.py)

## Run locally

### Prerequisites

- Python and pip
- Node.js and npm
- PostgreSQL for JWT login and demo-account provisioning. Protected scenario,
  planning, simulation, and map operations require an authenticated,
  authorized school membership.

### 1. Start the backend

From the repository root, install the backend dependencies and start FastAPI:

```powershell
cd backend
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Configure DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, and a private
# random JWT_SECRET in .env before starting the API.
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On the first successful PostgreSQL startup, the backend creates the seeded
administrator account if missing and records any generated initial credentials
in the ignored local file `backend/.seed-users.json`. Read it locally, record
credentials securely, then delete it. Do not commit or share it. There are no
seeded parent accounts or public school registration. An authorized
administrator enters a verified student record and creates a one-time parent
invitation; the link must be shared manually because email delivery is not
configured.

The API documentation is available at
[`http://127.0.0.1:8000/api/docs`](http://127.0.0.1:8000/api/docs), and health
can be checked at [`http://127.0.0.1:8000/api/health`](http://127.0.0.1:8000/api/health).

### 2. Start the frontend

In a second PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open [`http://127.0.0.1:3000`](http://127.0.0.1:3000). The Vite `/api` proxy
uses `http://127.0.0.1:8000` by default. If the backend uses another port, set
the proxy target before starting Vite; for example:

```powershell
$env:GATEFLOW_API_TARGET = "http://127.0.0.1:8001"
npm run dev
```

To use the second example, start the backend on port 8001 as well.

## Main API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Backend, scenario, and optional database health |
| `POST` | `/api/auth/login` | Verify database credentials and return an 8-hour JWT |
| `GET` | `/api/auth/me` | Return the authenticated user's role/profile |
| `GET` | `/api/schools/mine` | List only the signed-in user's authorized schools |
| `POST/PUT` | `/api/schools` and `/api/schools/{schoolId}` | Create or update an authorized school profile |
| `GET/POST` | `/api/schools/{schoolId}/students` | Manage administrator-entered student pickup records |
| `POST` | `/api/schools/{schoolId}/invitations` | Create a single-use parent invitation |
| `POST` | `/api/schools/invitations/accept` | Accept an invitation and link a parent to its student |
| `GET` | `/api/schools/{schoolId}/parent-dashboard` | Read verified parent-school student pickup details |
| `GET/PUT` | `/api/schools/{schoolId}/map` | Read or save the membership-checked school map |
| `GET` | `/api/scenario` | Scenario, gates, cohorts, and baseline metrics |
| `GET` | `/api/diagnosis` | Scenario-derived bottleneck diagnosis |
| `POST` | `/api/constraints/parse` | Parse a schedule request into constraints |
| `POST` | `/api/schedules/search` | Search for feasible schedule candidates |
| `POST` | `/api/simulation/run` | Run a deterministic estimate for a searched candidate |
| `GET` | `/api/simulation/compare/{runId}` | Retrieve the baseline-versus-candidate comparison |
| `POST` | `/api/stress/run` | Evaluate the selected schedule under stress scenarios |
| `GET` | `/api/integrations/status` | Read non-secret optional-provider readiness |
| `POST` | `/api/explanations` | Explain server-selected GateFlow evidence through optional OpenRouter |

Traffic planning, diagnosis, and simulation are restricted to administrators
who manage the `X-School-ID` school and whose school has a configured traffic
scenario. Parent requests are checked against their database-backed school and
student memberships. Health, login, invitation acceptance, and integration
readiness are public. Schedule search registers candidates for simulation in
the running backend process.

## Optional school map and evidence explainer

The administrator's **School Map** screen searches for Chennai schools with
Google Places, stores the selected Place ID on the school profile, and displays
Google's traffic layer around that school. Gate markers and blue pickup-zone
polygons are stored per school. Zones can be labeled for buses, cars,
two-wheelers, or general pickup; these are operator-authored annotations, not
verified parking permissions, capacity assignments, or safety advice. Parents
can view only their linked school's map; map editing requires administrator
authorization.

Google Maps is optional. From the repository root, create a local environment
file if one does not already exist, then set `VITE_GOOGLE_MAPS_API_KEY` in it:

```powershell
if (-not (Test-Path frontend\.env.local)) {
  Copy-Item frontend\.env.example frontend\.env.local
}
```

Vite reads this browser key when the frontend starts. Browser keys are visible
to users by design: restrict the key by approved HTTP referrers and enable only
the required Maps JavaScript and Places APIs. Do not reuse any key that has
been exposed publicly.

OpenRouter is an optional backend-only explanation service. Set
`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and optionally
`OPENROUTER_BASE_URL` in `backend/.env`. From the repository root, create the
local file if it does not already exist:

```powershell
if (-not (Test-Path backend\.env)) {
  Copy-Item backend\.env.example backend\.env
}
```

Set the key only in this uncommitted local file; the browser never receives
it. The example files intentionally leave API key values blank and must not be
used to store real credentials. The explanation endpoint resolves selected
diagnosis, schedule, simulation, or stress evidence itself; it does not accept
arbitrary client context and does not alter deterministic output. The minimal
selected evidence is sent to OpenRouter. A hosted model can have broader
pretraining, and GateFlow cannot guarantee provider retention or training
behavior. The service is non-authoritative and will report an explicit error
if unconfigured or unavailable.

Administrator and parent login authenticates against PostgreSQL and returns an
8-hour JWT. The frontend loads the schools authorized for the signed-in user;
administrators manage only their memberships, and parents see only schools
linked through a one-time invitation to an administrator-entered student
record. Invitations are not emailed, and the prototype does not independently
verify a parent's email address. This is not production identity management.

## Validation performed

The following automated checks passed:

```powershell
python -m pytest backend\tests -q
npm --prefix frontend run lint
npm --prefix frontend run build
```

Backend test result: **50 passed**, including parent-school membership and
disabled-access checks, school-isolated map persistence, coordinate validation,
safe provider status, evidence selection, and mocked OpenRouter
success/failure. Frontend TypeScript lint and production build passed. The Vite
build emits a non-blocking warning about `__dirname` in
`frontend/vite.config.ts`. A browser E2E and live Google Maps/OpenRouter calls
were not exercised.

## Known limitations

- No live traffic, sensor, or field-measured data is connected.
- Only the seeded Oakridge school has an active traffic scenario. New school
  profiles do not copy Oakridge data; traffic-scenario configuration for
  additional schools remains unimplemented.
- Parent invitations are one-time links returned to administrators for manual
  sharing. Email delivery and independent parent-email verification are not
  configured.
- Parent access is linked to the student record an authorized administrator
  enters and marks as verified; the prototype does not independently validate
  the family relationship.
- Blue map zones can be labeled for buses, cars, two-wheelers, or general
  pickup, but do not represent verified legal parking, safety approval, or
  capacity/vehicle-eligibility enforcement.
- SUMO is not installed; simulation uses a deterministic five-minute queue
  estimate.
- The scenario's supplied baseline metrics and the simulation's computed
  estimates come from different sources and should not be treated as directly
  interchangeable.
- A +30% demand request remains infeasible under current gate capacities: Gate 3
  reaches 106.6 veh/h, above the 105% planning limit of 105 veh/h. The planner
  reports the blocker instead of increasing capacity.
- The existing Gate 2 assignment for Grades 1–3 does not meet its listed bay
  requirement. It is allowed only as the current grandfathered assignment; an
  alternate assignment must satisfy eligibility and bay constraints.
- User provisioning is limited to the startup-seeded demo accounts; there is
  no public registration, password reset, or administrator user-management UI.
