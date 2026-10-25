# Chennai School Map and Project-Grounded AI Design

## Intent

Extend the existing GateFlow AI demo so a school administrator can find a
school in Chennai, inspect its immediate map and traffic context, and record
the school's actual gate and pickup areas for the driver portal. Add an
OpenRouter-powered explainer that describes GateFlow's own scenario, planning,
and simulation outputs without web search or unrelated project context.

The current application is a React/Vite frontend and FastAPI backend. The
administrator and driver are demo roles, not separate authenticated accounts.
There is no school search, map, or external LLM integration today. Schedule
constraint parsing is deterministic and should remain so; an LLM must not
replace the planner or change its hard constraints.

## Goals

- Search Google Places for schools in Chennai and let the user select a result.
- Center and bound a Google Map around that school, showing only its immediate
  surroundings and the Google Maps traffic layer in that viewport.
- Let the administrator add gate markers and draw/edit the pickup or queue
  areas in front of the selected school's gates.
- Persist these annotations on the FastAPI host, keyed by Google Place ID, so
  the school/driver views can display the same locations after reload.
- Provide a project-grounded AI explanation of selected GateFlow diagnosis,
  schedule, simulation, or stress-test evidence.
- Show non-secret integration status on both administrator and driver portals.
- Keep scenario diagnosis, schedule planning, and deterministic simulation
  usable if either integration is unconfigured or unavailable.

## Non-goals

- Replacing deterministic scheduling, capacity checks, or simulation with an
  LLM.
- Showing API keys in login forms, browser-rendered UI, responses, logs,
  screenshots, or committed files.
- Claiming that the hosted model is trained only on this project. The prompt can
  be constrained to supplied evidence and the model can be told to decline
  unsupported questions, but its pretraining cannot be controlled through an
  API call.
- Automatically deciding that a curb or parcel is legally safe/available for
  school pickup, or inferring gate frontage geometry from a Places result.
- Making the demo role selector into production authentication or authorization.
- Uploading the full CSV/experiment dataset or unrelated repository data to the
  LLM provider.

## Approaches

1. **Secure integrated demo (recommended and selected).** Use Google Places and
   Maps JavaScript APIs in the browser with a referrer- and API-restricted key;
   use the map's traffic layer and admin-authored gate/pickup geometry. Keep
   OpenRouter calls on FastAPI and send only the minimal selected GateFlow
   evidence to the model. This delivers the school-to-gate-to-explanation flow
   without putting the LLM secret in the browser.
2. **Map-first, defer AI.** Build school discovery and admin-authored map
   annotations first, then add the explainer later. This lowers integration
   risk but does not complete the requested AI feature.
3. **Call both providers directly from the browser.** Rejected because it
   exposes the OpenRouter secret and makes the model harder to constrain and
   observe. The Google Maps browser key is necessarily visible to clients, so
   it must be restricted rather than treated as a private secret.

## User decisions

- Use the secure integrated demo approach.
- Use administrator-authored gate and pickup-area geometry rather than
  presenting unverified parking locations as factual.
- Show provider/model availability on both role portals, never key values.
- Scope the AI explainer to project-provided evidence and do not enable web
  search or external retrieval.
- The driver portal follows the administrator's currently selected school;
  there is no per-driver school assignment in this demo.

## Proposed implementation

### School search and focused map

- Add a school-search/map surface to the existing administrator workflow and a
  read-only view for the driver portal. Keep the active Place ID in shared
  backend state so both portals show the same school after a search or reload.
- Use Google Places search constrained to Chennai, request only fields needed
  to identify and locate the selected school, and display the chosen school's
  map viewport rather than a general city map.
- Display the Google Maps traffic layer only over the visible selected-school
  viewport. Do not label the layer as school-specific measurements.
- Do not persist a bulk copy of Google Places details. Store the selected Place
  ID and administrator-authored GateFlow geometry; resolve display details
  through the permitted Google Maps APIs.
- In the admin editor, place named gate markers and draw pickup/queue polygons
  by clicking map points. Make the distinction clear between an administrator
  annotation and verified legal parking/safety data.
- Persist annotations in a small backend-managed JSON file under the existing
  backend data directory, keyed by Place ID. This keeps core demo operation
  independent from PostgreSQL and shares authored geometry between portal
  views on the same server.

### Project-grounded explainer

- Add a FastAPI explanation endpoint that accepts a bounded question and
  selected GateFlow evidence; do not accept arbitrary prompt context or API
  credentials from the client.
- Build the model context server-side from the selected scenario, diagnosis,
  schedule, simulation, or stress-test result. Send only the values and source
  labels required to answer the question; do not send the full CSV or unrelated
  source files.
- Use the configured OpenRouter model with web search/tools disabled. Instruct
  it to answer only from the supplied evidence, cite the provided field/source
  labels, and explicitly say when evidence is insufficient.
- Keep deterministic outputs authoritative. Validate the model response shape,
  mark it as an AI-generated explanation, and do not use it to approve a
  schedule, set capacities, or alter simulation metrics.
- Surface configuration/provider failures explicitly; the existing three
  core features remain available without the explainer.

### Credentials and integration status

- Read `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and the Google Maps browser key
  from environment configuration. Never hard-code credentials or add real
  values to `.env.example`.
- The OpenRouter key is backend-only. The Google Maps JavaScript key is
  browser-visible by design and must be restricted to approved HTTP referrers
  and only the required Maps/Places APIs, with provider quotas enabled.
- Return only safe status fields such as `configured`, provider name, and model
  identifier. Never return either key or a partial key.
- Show the safe status on the administrator and driver surfaces. This is status
  display, not a claim that demo-role selection provides authentication.
- The keys previously pasted in chat are considered compromised and must be
  revoked/reissued by the owner before setting local environment values.

### Security and privacy boundary

- A third-party OpenRouter service processes the minimal evidence needed for an
  explanation. The project can prevent app-side web search and unrelated
  context from being sent, but cannot guarantee the model has no broader
  pretrained knowledge or control provider retention/training practices.
- Do not represent admin-authored map geometry as verified school-approved
  parking. Do not present it as operationally safe without school confirmation.
- Annotation writes are a local demo capability until real role authentication
  and authorization are implemented; the current UI roles do not secure
  backend endpoints.
- This demo uses one shared active school selection. Changing it in the
  administrator portal changes the school displayed in the driver portal; it
  does not model per-driver school assignments.

## Validation

- Frontend type check/build and focused backend tests.
- Backend tests for safe integration status, missing/failed LLM configuration,
  grounded context construction, and annotation storage/retrieval.
- Browser flow: search Chennai school, select it, verify the map is focused,
  author a gate and pickup polygon, reload and confirm both portals show the
  same annotations, and request a grounded explanation.
- Confirm missing provider configuration leaves the core scenario, planning,
  and simulation workflows usable.
- Inspect API responses, logs, and built frontend assets to ensure no LLM key is
  exposed. Confirm map key restrictions are documented and no key value is
  committed.

## Left to the builder

- Choose the smallest compatible Google Maps loader and typed map integration
  for the current React/Vite dependencies.
- Choose a clear map-editor interaction for adding/removing gate markers and
  closing/revising pickup polygons.
- Keep route contracts bounded, typed, and consistent with existing FastAPI
  service patterns.
- Document the setup and the requirement that the owner configure referrer/API
  restrictions, provider quotas, and newly rotated local keys.
