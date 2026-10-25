# Implementation Plan: Chennai School Map and Project-Grounded AI

**Date**: 2026-10-25 | **Spec**: [requirements](../specs/2026-10-25-chennai-school-map-grounded-ai-spec.md) | **Design**: [approved design](../specs/2026-10-25-chennai-school-map-grounded-ai-design.md)

## Summary

Add a Google Places school search and focused Google Maps traffic view for
Chennai, with admin-authored gate/pickup geometry persisted by the FastAPI
backend and shared to the driver portal. Add an optional OpenRouter explainer
that receives only bounded, server-selected GateFlow evidence. Keep deterministic
planning/simulation authoritative, never expose the OpenRouter key, and report
integration readiness without revealing credentials.

## Technical Context

**Language/Version**: Python 3.11+ (existing backend environment), TypeScript,
React 19, Vite 8
**Primary Dependencies**: FastAPI/Pydantic, `httpx` (already in backend
requirements), Google Maps JavaScript and Places APIs, OpenRouter chat
completions; add a typed Google Maps loader and Google Maps type definitions
only if needed by the selected integration.
**Storage**: Existing synthetic scenario JSON plus a new backend-managed,
atomic JSON state file for active Google Place ID and operator-authored map
annotations; no PostgreSQL dependency for this feature.
**Testing**: pytest/FastAPI TestClient, TypeScript `npm run lint`, Vite
`npm run build`, HTTP and browser walkthrough.
**Target Platform**: Local GateFlow demo, React/Vite SPA and FastAPI service.
**Performance Goals**: School search and map load should remain responsive;
OpenRouter requests must have a bounded timeout and must not block core
deterministic workflows.
**Constraints**: Existing role selection is not authentication. Google Maps
browser keys are public and require referrer/API restrictions. OpenRouter
receives only minimal selected evidence; broader model pretraining and provider
retention cannot be controlled by the app. Do not reuse credentials disclosed
in chat. Keep Maps/OpenRouter optional and do not send the full vehicle CSV.

## Constitution Check

No `constitution.md` was found in the repository. This plan follows the
approved design: preserve the current architecture, use deterministic
calculations as the source of truth, keep secrets out of the frontend and
repository, make external data/model sources explicit, and avoid making safety
or legal parking claims.

## Applied Guidelines

No project `skills/guidelines/` directory or applicable migration guideline
files were found. Existing repository patterns are followed: Pydantic request
and response models, FastAPI routers/services, typed frontend API helpers, and
pytest service/API tests.

## Implementation Steps

### Phase 1 — Backend integration foundation

#### Step 1.1: Configure optional providers and safe status
- **Requirements**: REQ-007, REQ-008
- **Design inputs**: Approved design, “Credentials and integration status”
- **Description**: Add optional backend OpenRouter settings and public-safe
  integration status; expose model name/configuration state only. Configure the
  Vite-exposed Maps key separately as `VITE_GOOGLE_MAPS_API_KEY`; update
  `.env.example` and `.gitignore` for local environment files and the
  generated map state file. Never add actual credential values.

#### Step 1.2: Persist shared school and annotations
- **Requirements**: REQ-003, REQ-004, REQ-008, REQ-009
- **Design inputs**: Approved design, “School search and focused map”
- **Description**: Add typed map-state models and a backend JSON service keyed
  by Place ID. Persist a single active Place ID plus gate markers and
  administrator-authored pickup polygons. Validate coordinate ranges and
  polygon point counts; write atomically. Add typed read/update API routes and
  mount them in FastAPI. Do not persist bulk Google Places data.

### Phase 2 — Chennai school map workflow

#### Step 2.1: Add typed Maps/Places client and map surface
- **Requirements**: REQ-001, REQ-002
- **Design inputs**: Approved design, “School search and focused map”
- **Description**: Load Google Maps and Places using the Vite browser key,
  constrain school search to Chennai, display the selected place, focus the map
  on its surroundings, and add the Google traffic overlay. Clearly label the
  map/traffic as Google-provided. Add only the smallest required frontend
  dependency/type package if necessary.

#### Step 2.2: Add administrator gate and pickup-area editor
- **Requirements**: REQ-003, REQ-004, REQ-009
- **Design inputs**: Approved design; REQ-003 acceptance criteria
- **Description**: Add named gate marker create/move/remove actions and
  pickup-area polygon drawing/edit/removal. Save edits through the backend map
  API and identify the shapes as operator annotations, not verified parking or
  safety boundaries.

#### Step 2.3: Share active map with driver and add navigation/status surfaces
- **Requirements**: REQ-004, REQ-007, REQ-008, REQ-009
- **Design inputs**: User decision that the driver follows the administrator's
  selected school
- **Description**: Add a map workflow entry to the administrator navigation,
  a read-only map view in the driver portal, and safe provider status for both
  role portals/login selection. Both views read the same backend active school
  and saved annotations; display graceful empty/unconfigured states.

### Phase 3 — Project-grounded AI explainer

#### Step 3.1: Build bounded server-side project evidence
- **Requirements**: REQ-005, REQ-006, REQ-010
- **Design inputs**: Approved design, “Project-grounded explainer”
- **Description**: Define a bounded explanation request using a question and
  references to known GateFlow evidence. Resolve scenario, diagnosis, registered
  candidate, simulation, and stress evidence from backend services/caches. Do
  not accept arbitrary context/system prompts from the browser or include
  unrelated files/CSV rows.

#### Step 3.2: Call OpenRouter and validate explanation responses
- **Requirements**: REQ-005, REQ-006, REQ-007, REQ-008, REQ-010
- **Design inputs**: Approved design; REQ-005/006/010 acceptance criteria
- **Description**: Add a backend-only OpenRouter client using `httpx`, a bounded
  timeout, web/tools disabled, and the configured model. Require an answer
  grounded in supplied evidence labels, refusal when evidence is insufficient,
  and a response marked as AI-generated. Surface provider/configuration errors
  explicitly without making core workflows depend on them. Do not log secrets
  or full prompts.

#### Step 3.3: Add contextual explainer UI and disclosure
- **Requirements**: REQ-006, REQ-008, REQ-010
- **Design inputs**: Approved design, “Security and privacy boundary”
- **Description**: Add an explain action to relevant diagnosis, schedule, and
  simulation views. Display the response, source labels, model/provider
  attribution, evidence boundary, non-authoritative disclaimer, and clear
  unavailable/error states.

### Phase 4 — Validation and documentation

#### Step 4.1: Add regression tests and verify user flows
- **Requirements**: REQ-001 through REQ-010
- **Design inputs**: Requirements acceptance criteria
- **Description**: Test map-state persistence and validation, safe provider
  status, missing/failed LLM configuration, server-side evidence selection,
  and error handling. Run frontend typecheck/build and walkthrough the
  Chennai search → map annotation → driver view and diagnosis/schedule/
  simulation → grounded explanation flows. Verify provider outages leave core
  workflows usable.

#### Step 4.2: Document local configuration and demo limitations
- **Requirements**: REQ-007, REQ-009, REQ-010
- **Design inputs**: Approved design, “Known limitations”
- **Description**: Update the root README and frontend setup notes with local
  environment variables, Maps key restrictions, key rotation instructions,
  provider data boundaries, map annotation caveats, demo role limitations, and
  verification steps. Keep secrets out of examples.

## Project Structure

```text
backend/
  .env.example
  app/
    config.py
    main.py
    models/
      integrations.py
      map_annotations.py
    routers/
      integrations.py
      maps.py
      explanations.py
    services/
      map_state_service.py
      openrouter_service.py
    data/
      map_state.json              # generated locally; ignored by Git
  tests/
    test_map_integrations.py
frontend/
  .env.example
  src/
    api/client.ts
    components/
      IntegrationStatus.tsx
      ProjectExplanation.tsx
    pages/
      SchoolMapPage.tsx
      LoginPage.tsx
      DriverDashboard.tsx
      FindCausePage.tsx
      FindSchedulePage.tsx
      TestSchedulePage.tsx
    App.tsx
    components/Sidebar.tsx
  vite.config.ts
README.md
```

## Testing Strategy

- **appType**: Mixed — React SPA and FastAPI JSON API.
- **Critical user journeys**:
  1. Administrator searches a Chennai school, selects it, and sees its focused
     map and Google traffic overlay.
  2. Administrator marks gates and draws a pickup area; reload and driver view
     show the same saved annotations.
  3. Administrator asks for an explanation of diagnosis/schedule/simulation
     evidence; response cites provided GateFlow labels and refuses unsupported
     facts.
  4. With Maps/OpenRouter missing or unavailable, integration status is clear
     and diagnosis, planning, deterministic simulation, and comparison remain
     usable.
- **primaryValidationStack**: pytest with FastAPI TestClient; TypeScript
  `npm run lint`; Vite `npm run build`; live browser and HTTP checks using
  restricted owner-configured keys.
- **fallbackMatrix**:
  - `infra-tier`: local JSON map state and synthetic scenario → no database
    required.
  - `provider-tier`: mocked OpenRouter client and absent Maps key → core tests
    pass without external network/API credentials.
  - `browser-tier`: browser walkthrough when browser automation is available
    → frontend build and API integration tests otherwise.
- **Environment requirements**: Python backend dependencies; Node/npm; newly
  rotated OpenRouter secret configured only on backend; restricted Google Maps
  browser key configured in frontend local environment; provider APIs enabled
  and quota/billing configured for live integration checks.
- **knownGaps**: Without owner-configured valid provider keys, tests can verify
  graceful behavior and mocked OpenRouter requests but cannot certify live
  Places/Traffic coverage, quotas, billing, or provider uptime. Demo roles do
  not authorize map edits.
- **Test data strategy**: Temporary test JSON path for map persistence tests;
  existing deterministic synthetic scenario for planner/simulation tests;
  mocked provider requests; no full CSV upload.
- **Acceptance criteria**: All ten requirement IDs have explicit tests or
  browser-check evidence; all 46 backend tests pass; frontend
  typecheck/build pass; no secrets appear in Git diff, frontend assets, API
  responses, or logs.
- **Validation review expectations**: Confirm Places results stay constrained
  to Chennai search intent, active-school state is shared, annotations are
  clearly operator-authored, all AI source labels refer to the exact supplied
  backend evidence, and provider errors never fabricate output or block the
  existing demo.

## Complexity Tracking

No constitution violations identified. No extra database, LLM-based
optimization, or production auth layer is proposed.

## Tasks

### Phase 1 — Backend integration foundation

- [x] T001 [Plan:1.1] Add optional OpenRouter settings and safe integration status types/routes in `backend/app/config.py`, `backend/app/models/integrations.py`, `backend/app/routers/integrations.py`, and mount the router in `backend/app/main.py`; expose configuration/model status only.
- [x] T002 [P] [Plan:1.1] Add empty environment-variable examples for backend OpenRouter configuration and frontend `VITE_GOOGLE_MAPS_API_KEY` without values in `backend/.env.example` and `frontend/.env.example`.
- [x] T003 [P] [Plan:1.1,1.2] Ignore generated local map state in `.gitignore` and verify existing `.env` patterns cover frontend local environment files.
- [x] T004 [Plan:1.2] Define validated gate-marker, pickup-polygon, and shared active-school models in `backend/app/models/map_annotations.py`.
- [x] T005 [Plan:1.2] Implement locked, atomic JSON persistence keyed by Place ID and shared active-school selection in `backend/app/services/map_state_service.py`.
- [x] T006 [Plan:1.2] Add active-school and per-Place-ID annotation read/update routes in `backend/app/routers/maps.py`, mount in `backend/app/main.py`, and return validation errors explicitly.

### Phase 2 — Chennai school map workflow

- [x] T007 [Plan:2.1] Add the typed Google Maps loader and school search/map/traffic surface in `frontend/src/pages/SchoolMapPage.tsx`; constrain school search to Chennai and label Google map/traffic data.
- [x] T008 [Plan:2.1,2.2] Add typed map-state interfaces and API calls for active school and annotations in `frontend/src/api/client.ts`.
- [x] T009 [Plan:2.2] Add admin gate marker and pickup-polygon create/edit/delete interactions in `frontend/src/pages/SchoolMapPage.tsx`, saving through the map API and labeling all geometry as operator-authored.
- [x] T010 [Plan:2.3] Add the school map navigation route and shared active school workflow in `frontend/src/types.ts`, `frontend/src/components/Sidebar.tsx`, and `frontend/src/App.tsx`.
- [x] T011 [Plan:2.3] Add a read-only map view of shared active school/annotations and unavailable/empty states to `frontend/src/pages/DriverDashboard.tsx`.
- [x] T012 [Plan:2.3] Show non-secret provider/model status on the role-selection login and administrator/driver views in `frontend/src/components/IntegrationStatus.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/App.tsx`, and `frontend/src/pages/DriverDashboard.tsx`.

### Phase 3 — Project-grounded AI explainer

- [x] T013 [Plan:3.1] Define bounded explanation request/response models and server-side evidence selection for scenario, diagnosis, registered schedule, simulation, and stress results in `backend/app/models/integrations.py` and `backend/app/services/openrouter_service.py`.
- [x] T014 [Plan:3.2] Implement the OpenRouter HTTP call with server-only key, configured model, web/tool use disabled, strict timeout, response validation, and redacted error handling in `backend/app/services/openrouter_service.py`.
- [x] T015 [Plan:3.2] Add the bounded explanation endpoint in `backend/app/routers/explanations.py` and register it in `backend/app/main.py`; do not accept client-supplied system prompts or arbitrary source data.
- [x] T016 [Plan:3.3] Add typed explanation API calls and the contextual response/source/disclosure/error UI in `frontend/src/api/client.ts` and `frontend/src/components/ProjectExplanation.tsx`.
- [x] T017 [Plan:3.3] Add contextual explain actions to diagnosis, selected schedule, and simulation views in `frontend/src/pages/FindCausePage.tsx`, `frontend/src/pages/FindSchedulePage.tsx`, and `frontend/src/pages/TestSchedulePage.tsx`.

### Phase 4 — Validation and documentation

- [x] T018 [Plan:4.1] Add backend tests for map validation/persistence, active-school sharing, safe provider status, and missing provider configuration in `backend/tests/test_map_integrations.py`.
- [x] T019 [Plan:4.1] Add mocked OpenRouter tests for bounded evidence context, citations, and error handling in `backend/tests/test_map_integrations.py`.
- [x] T020 [Plan:4.1] Run frontend lint/build, backend tests, and HTTP checks for map and explainer flows; browser automation was attempted but unavailable because the Playwright Chromium executable is not installed. Live providers require rotated keys.
- [x] T021 [Plan:4.2] Document setup, key restrictions/rotation, provider data flow, map annotation caveats, and demo-auth limitations in `README.md` and `frontend/README.md`.

## Requirement Mapping

| REQ ID | Description | Plan Items | Implementation Evidence |
|--------|-------------|------------|------------------------|
| REQ-001 | Chennai school discovery | 2.1, 2.2 | `frontend/src/pages/SchoolMapPage.tsx` |
| REQ-002 | Focused school map and traffic | 2.1 | `frontend/src/pages/SchoolMapPage.tsx` |
| REQ-003 | Admin gate and pickup annotations | 1.2, 2.2 | `backend/app/models/map_annotations.py`, `backend/app/services/map_state_service.py`, `backend/app/routers/maps.py`, `frontend/src/pages/SchoolMapPage.tsx` |
| REQ-004 | Shared active school/map state | 1.2, 2.3 | `backend/app/services/map_state_service.py`, `backend/app/routers/maps.py`, `frontend/src/pages/DriverDashboard.tsx` |
| REQ-005 | Server-selected project evidence | 3.1, 3.2 | `backend/app/services/openrouter_service.py`, `backend/app/routers/explanations.py` |
| REQ-006 | Cited, limited AI explanation | 3.2, 3.3 | `backend/app/services/openrouter_service.py`, `frontend/src/components/ProjectExplanation.tsx` |
| REQ-007 | Safe provider configuration/status | 1.1, 2.3 | `backend/app/config.py`, `backend/app/routers/integrations.py`, `frontend/src/components/IntegrationStatus.tsx` |
| REQ-008 | Graceful optional integration | 1.1, 1.2, 3.2, 4.1 | `backend/app/routers/integrations.py`, `backend/app/routers/maps.py`, `backend/app/routers/explanations.py`, `backend/tests/test_map_integrations.py` |
| REQ-009 | Demo authorization boundary | 1.2, 2.2, 2.3 | `backend/app/routers/maps.py`, `frontend/src/pages/SchoolMapPage.tsx`, `frontend/src/pages/DriverDashboard.tsx`, `README.md` |
| REQ-010 | Provider/data transparency | 3.1, 3.2, 3.3, 4.2 | `backend/app/services/openrouter_service.py`, `frontend/src/components/ProjectExplanation.tsx`, `README.md` |
