from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.scenario import GROUPS, MODE_SHARE, OFFSET_OPTIONS, MAX_GROUP_SHIFT
from app.zones import ZONES, VEHICLE_OCCUPANCY, DWELL_SECONDS
from app.planner import search_plans, validate_offsets, validate_zone_assignments

app = FastAPI(title="GateFlow AI API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class PlanRequest(BaseModel):
    offsets: dict[str, int] | None = None
    zone_assignments: dict[str, str] | None = None
    limit: int = Field(default=100, ge=1, le=100)

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "application": "GateFlow AI",
        "api_version": "0.2.0",
        "sumo_version": "1.28.0",
    }

@app.get("/api/scenario")
def scenario():
    return {
        "label": "SYNTHETIC DEMO — NOT REAL SCHOOL DATA",
        "baseline_time": "08:00",
        "groups": [
            {
                "id": g.id,
                "name": g.name,
                "students": g.students,
                "sibling_pair": g.sibling_pair,
                "max_shift": MAX_GROUP_SHIFT[g.id],
            }
            for g in GROUPS
        ],
        "mode_share": MODE_SHARE,
        "offset_options": OFFSET_OPTIONS,
        "zones": ZONES,
        "vehicle_occupancy_assumptions": VEHICLE_OCCUPANCY,
        "dwell_seconds_assumptions": DWELL_SECONDS,
    }

@app.post("/api/plans/search")
def plans(req: PlanRequest):
    assignments = req.zone_assignments or {
        "car": "Z3",
        "two_wheeler": "Z1",
        "auto_van": "Z2",
        "bus": "Z4",
    }

    if req.offsets is not None:
        errors = validate_offsets(req.offsets)
        if errors:
            raise HTTPException(status_code=422, detail=errors)

    errors = validate_zone_assignments(assignments)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    try:
        result = search_plans(assignments=assignments, limit=req.limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result["engine"] = "F1 deterministic planning estimate; not SUMO output"
    result["source_label"] = "Synthetic / assumed inputs"
    return result
