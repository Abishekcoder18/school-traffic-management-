"""GateFlow AI — FastAPI Application Entry Point

Start with:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Health check:
    GET /api/health
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import check_db_connection
from app.routers import diagnosis, scenario, schedules, simulation
from app.routers import auth
from app.services.auth_service import create_tables
from app.services.data_service import get_scenario

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the scenario cache and verify MySQL on startup."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # ── MySQL ─────────────────────────────────────────────────────────────────
    db_ok = check_db_connection()
    if db_ok:
        create_tables()  # idempotent — creates users table if not present
    else:
        logger.warning("⚠️  MySQL unavailable — auth endpoints will return 503.")

    # ── Scenario cache ────────────────────────────────────────────────────────
    try:
        scenario = get_scenario()
        logger.info(
            f"Scenario loaded: {scenario.school.name} | "
            f"{len(scenario.gates)} gates | {len(scenario.cohorts)} cohorts"
        )
    except Exception as e:
        logger.error(f"Failed to load scenario on startup: {e}")
    yield
    logger.info("GateFlow AI backend shutting down.")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "GateFlow AI backend — school traffic management decision-support system. "
        "All data is synthetic. Results are deterministic planning estimates."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ── Request Logging Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000)
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} [{duration_ms}ms]"
    )
    return response


# ── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Return structured errors — never expose Python stack traces or
    internal filesystem paths to the frontend.
    """
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please check the server logs.",
                "details": [],
            }
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)          # POST /api/auth/login | GET /api/auth/me
app.include_router(scenario.router)
app.include_router(diagnosis.router)
app.include_router(schedules.router)
app.include_router(simulation.router)


# ── Health Endpoint ───────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
def health_check():
    """
    Health check endpoint.
    Returns 200 if the backend is running and the scenario is loaded.
    """
    try:
        sc = get_scenario()
        db_status = "connected" if check_db_connection() else "unavailable"
        return {
            "status": "ok",
            "version": settings.app_version,
            "scenario": sc.school.name,
            "gates": len(sc.gates),
            "cohorts": len(sc.cohorts),
            "dataSource": "Synthetic",
            "sumo": "not_installed",
            "database": db_status,
            "dbHost": settings.db_host,
            "simulationMethod": "DeterministicEstimate",
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "error": "Scenario data unavailable",
                "detail": str(e),
            },
        )
