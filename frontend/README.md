<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/651c6885-9752-4c15-9945-ceb935d7ef22

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Run the app:
   `npm run dev`

The frontend uses the FastAPI service through the Vite `/api` proxy. The
default backend URL is `http://127.0.0.1:8000`; override it with
`GATEFLOW_API_TARGET` when the backend uses another port. For example, in
PowerShell:

```powershell
$env:GATEFLOW_API_TARGET = "http://127.0.0.1:8001"
npm run dev
```

The Oakridge demo scenario is synthetic. Planning and simulation results are
deterministic estimates, not live traffic observations.

## Optional Chennai school map

Copy `.env.example` to `.env.local` and set `VITE_GOOGLE_MAPS_API_KEY` to a
newly issued browser key to enable Chennai school search and the Google traffic
layer. This key is visible in browser requests by design; restrict it to the
frontend's approved HTTP referrers and required Maps JavaScript/Places APIs.
Without it, the rest of the demo remains usable and the map reports that it is
not configured.

OpenRouter credentials belong only in the backend environment. Never put an
OpenRouter key in a Vite environment variable or frontend source. The map and
GateFlow explanations are optional integrations; the deterministic scenario,
planning, simulation, and comparison remain authoritative.
