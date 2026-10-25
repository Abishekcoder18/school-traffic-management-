# Chennai School Map and Project-Grounded AI Requirements

## Purpose

Extend the existing GateFlow AI demo to let a school administrator find a
school in Chennai, add verified-by-the-operator gate and pickup-area
annotations, and share the selected school map with the driver portal. Add an
optional AI explainer for GateFlow-generated evidence without replacing
deterministic planning or simulation.

All school-search and map details supplied by Google Maps are third-party map
data. Gate/pickup annotations are administrator-authored and are not claims of
legal parking permission or safety certification. AI explanations are generated
from bounded project evidence and are not authoritative decisions.

## Requirements

### REQ-001 — Chennai school discovery

The administrator must be able to search for and select a school in Chennai
using Google Places. Search results must identify the selected place without
exposing credentials or searching outside the Chennai school context.

**Acceptance criteria**

- Search can return school/place results in Chennai and the administrator can
  select one.
- The map and active school context update to the selected place.
- The UI makes clear that the place details and map come from Google.

### REQ-002 — Focused school map and traffic

The map must be centered and bounded around the selected school and display the
Google Maps traffic layer for the visible surrounding area, rather than a
general city-wide traffic view.

**Acceptance criteria**

- Selecting a school focuses the map viewport on that school and its immediate
  surroundings.
- Traffic display is visibly identified as a Google traffic layer, not as
  GateFlow sensor or school-gate measurements.
- The view does not claim that traffic data is limited to the school property.

### REQ-003 — Administrator gate and pickup annotations

An administrator must be able to add named gate markers and draw, revise, and
remove pickup/queue-area polygons on the selected school map.

**Acceptance criteria**

- Gate markers are associated with the active Google Place ID.
- Pickup-area polygons can be created and revised from map points.
- The UI labels these as administrator-authored annotations and does not imply
  Google verified that they are authorized/safe parking areas.

### REQ-004 — Shared school and map annotations

The backend must persist selected school identity and authored annotations so
the current school and its saved map data remain available after reload and in
both administrator and driver portals.

**Acceptance criteria**

- Saved annotation data is keyed by Google Place ID.
- The driver portal displays the administrator's currently selected school and
  its annotations; no per-driver school assignment is implied.
- The core demo does not require PostgreSQL to load or read the synthetic
  scenario or map annotations.

### REQ-005 — Project-evidence-only explanation request

The backend must accept a bounded question tied to selected GateFlow evidence
and construct the OpenRouter request from project-provided scenario, diagnosis,
planning, simulation, or stress-test data only.

**Acceptance criteria**

- The browser cannot supply an arbitrary system prompt, API key, or unconstrained
  model context.
- The request does not include the full vehicle CSV, unrelated source files,
  web search, or external retrieval.
- The explainer does not alter schedule candidates, constraint checks, or
  deterministic simulation metrics.

### REQ-006 — Explainable and limited model output

The explainer must identify its answers as AI-generated, cite supplied
GateFlow evidence labels, and state when the evidence is insufficient.

**Acceptance criteria**

- Responses include traceable source labels from the context provided to the
  model.
- Unsupported school, traffic, safety, or operational facts are not stated as
  GateFlow measurements.
- The UI says explanations are non-authoritative; deterministic backend
  calculations remain the source of truth.

### REQ-007 — Safe provider configuration and status

OpenRouter and Google Maps configuration must be sourced from environment
settings and never hard-coded or returned as secret values. The application
must show non-secret provider/model availability to both role portals.

**Acceptance criteria**

- The OpenRouter key remains server-side and is never included in API responses,
  frontend assets, UI, or logs.
- The Google Maps browser key is treated as public, documented for HTTP-referrer
  and API restrictions, and never presented as a hidden secret.
- Status responses and both portal views expose only safe status/provider/model
  fields, never key values or partial keys.
- Previously exposed credentials are not reused; the owner rotates them and
  configures replacements locally.

### REQ-008 — Graceful optional integrations

Core scenario loading, diagnosis, schedule planning, deterministic simulation,
and comparison must remain usable when Google Maps or OpenRouter configuration
is absent or a provider is unavailable.

**Acceptance criteria**

- Missing integrations are reported explicitly in status and relevant UI.
- AI and map failures do not fabricate success, metrics, or map annotations.
- A failed explainer request does not alter or block deterministic planning and
  simulation.

### REQ-009 — Demo authorization boundary

Map editing must be presented as a local demo administrator feature, not as a
production-secured capability, because the current role selector is not real
authentication.

**Acceptance criteria**

- Documentation and UI do not claim the administrator/driver role selector
  authenticates users or protects map edits.
- The lack of backend authorization is documented as a production limitation.

### REQ-010 — Provider and data transparency

The application must disclose that OpenRouter receives the minimal selected
evidence used for an explanation, that the hosted model may have broader
pretraining, and that the app cannot guarantee training or retention behavior.

**Acceptance criteria**

- The explanation UI identifies OpenRouter/model use and the project evidence
  scope.
- The application does not claim the model was trained only on GateFlow data.
- No key values or full experiment dataset are included in disclosures or
  provider requests.

## Constraints

- Preserve the existing React/Vite and FastAPI architecture.
- Keep schedule parsing, optimization, gate eligibility, bay checks, and
  deterministic simulation authoritative and unchanged by the LLM.
- Keep the synthetic scenario usable without database-backed authentication.
- Use administrator-authored geometry rather than inferring pickup areas from
  a place result.
- The Google Maps JavaScript key is visible in browser traffic by design and
  must be restricted by the project owner to approved origins and required
  APIs.
- The exposed keys must be revoked/reissued before configuration; key values
  must not be entered in chat or committed to source.

## Out of scope

- Production authentication/authorization and role-based map-edit protection.
- Confirming legal parking, curb regulations, school permission, or safety from
  Google data.
- Live school-owned traffic sensors or measured school queue data.
- Fine-tuning a model on private project data or guaranteeing the hosted model's
  training corpus.
