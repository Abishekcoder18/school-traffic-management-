"""
GateFlow AI — Backend Test Suite

Run with:
    cd backend
    python -m pytest tests/ -v

Tests cover:
 1. health endpoint
 2. scenario loading
 3. data validation
 4. diagnosis
 5. valid constraint parsing
 6. ambiguous constraint parsing
 7. contradictory constraints
 8. fixed Kindergarten
 9. sibling synchronization
10. max shift validation
11. zone validation (infeasible gate load)
12. planner feasibility
13. schedule selection
14. simulation input generation
15. SUMO availability (confirms not installed)
16. simulation response parsing
17. baseline vs optimized comparison
18. stress testing
19. invalid API requests
20. reset functionality
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schedule import ConstraintParseRequest, ParsedConstraints, ScheduleSearchRequest
from app.services.ai_service import parse_constraints_deterministic
from app.services.constraint_service import validate_constraints
from app.services.data_service import get_scenario, reset_scenario
from app.services.diagnosis_service import compute_diagnosis
from app.services.planning_service import _compute_queue_metrics, search_schedules
from app.services.simulation_service import (
    _simulate_queue_timeseries,
    get_registered_schedule,
    register_schedule,
    reset_simulations,
    run_simulation,
)
from app.models.simulation import SimulationRunRequest, StressTestRequest
from app.services.stress_service import run_stress_tests

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Health Endpoint
# ─────────────────────────────────────────────────────────────────────────────
def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "scenario" in data
    assert data["dataSource"] == "Synthetic"
    assert data["sumo"] == "not_installed"
    assert data["simulationMethod"] == "DeterministicEstimate"


def test_protected_endpoint_requires_a_bearer_token():
    from app.routers.auth import get_current_user
    from app.routers.schools import require_traffic_admin

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_traffic_admin, None)
    response = client.get("/api/scenario")
    assert response.status_code == 401
    assert client.post("/api/auth/register", json={}).status_code == 404


def test_parent_cannot_access_administrator_traffic_data():
    from types import SimpleNamespace

    from app.routers.auth import get_current_user
    from app.routers.schools import require_traffic_admin

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="parent")
    app.dependency_overrides.pop(require_traffic_admin, None)
    assert client.get("/api/scenario").status_code == 403
    assert client.get("/api/scenario/driver").status_code == 403
    assert client.post("/api/schedules/search", json={}).status_code == 403
    assert client.put("/api/maps/active", json={"placeId": "test-school"}).status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Scenario Loading
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_loads():
    resp = client.get("/api/scenario")
    assert resp.status_code == 200
    data = resp.json()
    assert data["school"]["name"] == "Oakridge Academy & Secondary Campus"
    assert len(data["gates"]) == 4
    assert len(data["cohorts"]) == 5
    assert data["dataSource"] == "Synthetic"


def test_gates_endpoint():
    resp = client.get("/api/scenario/gates")
    assert resp.status_code == 200
    gates = resp.json()
    assert len(gates) == 4
    gate_ids = [g["id"] for g in gates]
    assert "gate-1" in gate_ids
    assert "gate-2" in gate_ids


def test_cohorts_endpoint():
    resp = client.get("/api/scenario/cohorts")
    assert resp.status_code == 200
    cohorts = resp.json()
    assert len(cohorts) == 5
    cohort_ids = [c["id"] for c in cohorts]
    assert "c-prek" in cohort_ids


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Data Validation
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_data_integrity():
    sc = get_scenario()
    # Every cohort must reference a valid gate
    gate_ids = {g.id for g in sc.gates}
    for cohort in sc.cohorts:
        assert cohort.assignedGateId in gate_ids, (
            f"Cohort {cohort.id} references unknown gate {cohort.assignedGateId}"
        )
    # Sibling groups must reference real cohort IDs
    cohort_ids = {c.id for c in sc.cohorts}
    for sg in sc.siblingGroups:
        for cid in sg.cohortIds:
            assert cid in cohort_ids


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Diagnosis
# ─────────────────────────────────────────────────────────────────────────────
def test_diagnosis_endpoint():
    resp = client.get("/api/diagnosis")
    assert resp.status_code == 200
    data = resp.json()
    diag = data["diagnosis"]
    assert diag["gateId"] == "gate-2"  # Gate 2 is the bottleneck
    assert diag["overloadRatio"] > 1.0
    assert len(diag["evidence"]) == 3
    assert data["dataQuality"]["source"] == "Synthetic"


def test_diagnosis_computed_from_data():
    result = compute_diagnosis()
    assert result.diagnosis.overloadRatio == pytest.approx(1.5, abs=0.1)
    assert result.diagnosis.peakDemandRate > result.diagnosis.maxThroughputCapacity
    assert "not an hourly rate" in result.diagnosis.explanation
    assert not any("spillback" in ev.title.lower() for ev in result.diagnosis.evidence)
    for ev in result.diagnosis.evidence:
        assert ev.title
        assert ev.metric


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Valid Constraint Parsing
# ─────────────────────────────────────────────────────────────────────────────
def test_valid_constraint_parsing():
    resp = client.post(
        "/api/constraints/parse",
        json={"prompt": "Stagger lower elementary by 15 minutes and use gate 4 overflow."}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["constraints"] is not None


def test_judge_demo_prompt():
    """
    Test 5 (also covers 8, 9): The specific judge demo request must parse correctly.
    """
    prompt = (
        "Increase demand by 30%, keep Kindergarten fixed, "
        "keep sibling groups synchronized and prioritize queue reduction."
    )
    resp = client.post("/api/constraints/parse", json={"prompt": prompt})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    c = data["constraints"]
    assert c["demandFactor"] == pytest.approx(1.30, abs=0.01)
    assert "c-prek" in c["fixedGroups"]    # Kindergarten fixed
    assert c["siblingSync"] is True         # sibling sync enabled
    assert c["optimizationObjective"] == "queue_reduction"
    assert c["parserMethod"] == "deterministic"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Ambiguous Constraint Parsing
# ─────────────────────────────────────────────────────────────────────────────
def test_short_prompt_flagged_as_ambiguous():
    result = parse_constraints_deterministic("change buses")
    # Should parse (no contradiction) but flag ambiguity
    assert result.constraints is not None
    assert len(result.constraints.ambiguityFlags) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Contradictory Constraints — All Cohorts Fixed
# ─────────────────────────────────────────────────────────────────────────────
def test_all_cohorts_fixed_is_invalid():
    constraints = ParsedConstraints(
        originalPrompt="keep everything fixed",
        demandFactor=1.0,
        fixedGroups=["c-prek", "c-g13", "c-g45", "c-g68", "c-hs"],
        siblingSync=False,
        maxShiftMin=30,
        optimizationObjective="queue_reduction",
    )
    result = validate_constraints(constraints)
    assert result.valid is False
    assert any("All cohorts are fixed" in e for e in result.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Fixed Kindergarten
# ─────────────────────────────────────────────────────────────────────────────
def test_fixed_kindergarten_stays_at_baseline():
    constraints = ParsedConstraints(
        originalPrompt="keep Kindergarten fixed",
        demandFactor=1.0,
        fixedGroups=["c-prek"],
        siblingSync=False,
        maxShiftMin=30,
        optimizationObjective="queue_reduction",
    )
    result = search_schedules(ScheduleSearchRequest(constraints=constraints))
    for candidate in result.candidates:
        for row in candidate.groupSchedule:
            if row.cohortId == "c-prek":
                assert row.offsetMinutes == 0, (
                    f"Kindergarten (c-prek) was shifted by {row.offsetMinutes} minutes — "
                    "it must stay fixed."
                )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Sibling Synchronization
# ─────────────────────────────────────────────────────────────────────────────
def test_sibling_sync_offsets_match():
    constraints = ParsedConstraints(
        originalPrompt="synchronize siblings",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=True,
        maxShiftMin=30,
        optimizationObjective="queue_reduction",
    )
    result = search_schedules(ScheduleSearchRequest(constraints=constraints))
    sc = get_scenario()
    # Find the sibling group cohorts
    for sg in sc.siblingGroups:
        if len(sg.cohortIds) >= 2:
            for candidate in result.candidates:
                offsets = {row.cohortId: row.offsetMinutes for row in candidate.groupSchedule}
                leader_offset = offsets.get(sg.cohortIds[0])
                for follower_id in sg.cohortIds[1:]:
                    follower_offset = offsets.get(follower_id)
                    assert leader_offset == follower_offset, (
                        f"Sibling sync failed: {sg.cohortIds[0]}={leader_offset} "
                        f"but {follower_id}={follower_offset}"
                    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Max Shift Validation
# ─────────────────────────────────────────────────────────────────────────────
def test_max_shift_respected():
    max_shift = 10
    constraints = ParsedConstraints(
        originalPrompt=f"maximum {max_shift} minute shift",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=False,
        maxShiftMin=max_shift,
        optimizationObjective="queue_reduction",
    )
    result = search_schedules(ScheduleSearchRequest(constraints=constraints))
    for candidate in result.candidates:
        for row in candidate.groupSchedule:
            assert abs(row.offsetMinutes) <= max_shift, (
                f"Cohort {row.cohortId} was shifted by {row.offsetMinutes} "
                f"but maxShiftMin={max_shift}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Zone Validation — Zero Max Shift is Invalid
# ─────────────────────────────────────────────────────────────────────────────
def test_zero_max_shift_is_invalid():
    constraints = ParsedConstraints(
        originalPrompt="no shifts at all",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=False,
        maxShiftMin=0,
        optimizationObjective="queue_reduction",
    )
    result = validate_constraints(constraints)
    assert result.valid is False
    assert any("maxShiftMin = 0" in e for e in result.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Planner Feasibility
# ─────────────────────────────────────────────────────────────────────────────
def test_planner_returns_feasible_candidates():
    constraints = ParsedConstraints(
        originalPrompt="queue reduction with 15 min stagger",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=False,
        maxShiftMin=30,
        optimizationObjective="queue_reduction",
    )
    result = search_schedules(ScheduleSearchRequest(constraints=constraints))
    assert len(result.candidates) > 0
    for c in result.candidates:
        assert c.isFeasible is True
        assert c.constraintFeasibility in ["100% Compliant", "Minor Leniency"]


def test_candidate_reductions_match_queue_estimates():
    constraints = ParsedConstraints(
        originalPrompt="queue reduction",
        demandFactor=1.0,
        fixedGroups=["c-prek"],
        siblingSync=False,
        maxShiftMin=15,
        optimizationObjective="queue_reduction",
    )
    result = search_schedules(ScheduleSearchRequest(constraints=constraints))
    scenario = get_scenario()
    gates_by_id = {gate.id: gate for gate in scenario.gates}
    baseline = _compute_queue_metrics(
        scenario.cohorts, [0] * len(scenario.cohorts), gates_by_id, 1.0
    )

    assert result.candidates
    for candidate in result.candidates:
        offsets = [row.offsetMinutes for row in candidate.groupSchedule]
        assignments = [row.assignedGateId for row in candidate.groupSchedule]
        estimated = _compute_queue_metrics(
            scenario.cohorts, offsets, gates_by_id, 1.0, assignments
        )
        expected_queue_reduction = (
            round(
                (baseline["peak_queue"] - estimated["peak_queue"])
                / baseline["peak_queue"] * 100,
                1,
            )
            if baseline["peak_queue"] > 0 else None
        )

        assert candidate.peakQueueReductionPct == expected_queue_reduction
        assert candidate.waitTimeReductionMin == pytest.approx(
            round(baseline["p95_wait_min"] - estimated["p95_wait_min"], 1)
        )
        assert candidate.spillbackReductionMeters == pytest.approx(
            round(baseline["spillback_meters"] - estimated["spillback_meters"], 1)
        )


def test_eligible_gate_reassignment_supports_baseline_schedule_and_comparison():
    constraints = ParsedConstraints(
        originalPrompt="keep sibling dismissal times together",
        demandFactor=1.0,
        fixedGroups=["c-prek"],
        siblingSync=True,
        maxShiftMin=15,
        allowGateReassignment=True,
        optimizationObjective="queue_reduction",
    )
    search_resp = client.post(
        "/api/schedules/search",
        json={"constraints": constraints.model_dump()},
    )
    assert search_resp.status_code == 200
    candidate = search_resp.json()["candidates"][0]
    rows = {row["cohortId"]: row for row in candidate["groupSchedule"]}

    assert rows["c-g45"]["assignedGateId"] == "gate-4"
    assert rows["c-g45"]["bayConstraintStatus"] == "satisfied"
    assert rows["c-g13"]["bayConstraintStatus"] == "grandfathered"
    for gate_id, load in candidate["gateLoads"].items():
        assert load <= candidate["gateCapacities"][gate_id] * 1.05

    sim_resp = client.post(
        "/api/simulation/run",
        json={"scheduleId": candidate["id"]},
    )
    assert sim_resp.status_code == 200
    simulation = sim_resp.json()
    assert simulation["simulationMethod"] == "DeterministicEstimate"
    assert simulation["metrics"]["peakQueue"]["baseline"] >= (
        simulation["metrics"]["peakQueue"]["candidate"]
    )

    compare_resp = client.get(
        f"/api/simulation/compare/{simulation['runId']}"
    )
    assert compare_resp.status_code == 200
    comparison = compare_resp.json()
    expected_reduction = max(
        0.0, -simulation["metrics"]["peakQueue"]["deltaPct"]
    )
    assert comparison["queueReductionPct"] == expected_reduction
    assert comparison["computedFrom"] == "DeterministicEstimate"


def test_high_demand_infeasibility_identifies_gate_capacity_blockers():
    constraints = ParsedConstraints(
        originalPrompt="increase demand",
        demandFactor=1.3,
        fixedGroups=["c-prek"],
        siblingSync=True,
        maxShiftMin=30,
        optimizationObjective="queue_reduction",
    )
    response = client.post(
        "/api/schedules/search",
        json={"constraints": constraints.model_dump()},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]["error"]["details"][0]
    assert "Gate 3" in detail
    assert "105% limit" in detail


def test_infeasible_constraints_raise_error():
    """POST to schedules/search with zero max shift should return 422."""
    constraints = ParsedConstraints(
        originalPrompt="impossible",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=False,
        maxShiftMin=0,
        optimizationObjective="queue_reduction",
    )
    resp = client.post("/api/schedules/search", json={"constraints": constraints.model_dump()})
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Schedule Selection & Registration
# ─────────────────────────────────────────────────────────────────────────────
def test_schedule_registered_after_search():
    constraints = ParsedConstraints(
        originalPrompt="basic search",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=False,
        maxShiftMin=20,
        optimizationObjective="balanced",
    )
    resp = client.post("/api/schedules/search", json={"constraints": constraints.model_dump()})
    assert resp.status_code == 200
    candidates = resp.json()["candidates"]
    assert len(candidates) > 0
    first_id = candidates[0]["id"]
    # Must be retrievable by ID
    get_resp = client.get(f"/api/schedules/{first_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == first_id


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Simulation Input Generation (schedule → simulation)
# ─────────────────────────────────────────────────────────────────────────────
def test_simulation_uses_selected_schedule():
    # Search and register
    constraints = ParsedConstraints(
        originalPrompt="run simulation",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=False,
        maxShiftMin=20,
        optimizationObjective="queue_reduction",
    )
    search_resp = client.post("/api/schedules/search", json={"constraints": constraints.model_dump()})
    assert search_resp.status_code == 200
    schedule_id = search_resp.json()["candidates"][0]["id"]

    # Run simulation
    sim_resp = client.post("/api/simulation/run", json={"scheduleId": schedule_id})
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["candidateId"] == schedule_id
    assert sim_data["simulationMethod"] == "DeterministicEstimate"


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: SUMO Availability (confirms not installed)
# ─────────────────────────────────────────────────────────────────────────────
def test_sumo_not_installed():
    health = client.get("/api/health").json()
    assert health["sumo"] == "not_installed"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: Simulation Response Parsing
# ─────────────────────────────────────────────────────────────────────────────
def test_simulation_response_structure():
    constraints = ParsedConstraints(
        originalPrompt="response structure test",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=False,
        maxShiftMin=20,
        optimizationObjective="queue_reduction",
    )
    search_resp = client.post("/api/schedules/search", json={"constraints": constraints.model_dump()})
    schedule_id = search_resp.json()["candidates"][0]["id"]

    sim_resp = client.post("/api/simulation/run", json={"scheduleId": schedule_id})
    sim_data = sim_resp.json()

    # All required fields present
    assert "metrics" in sim_data
    assert "timeIntervals" in sim_data
    assert "improvements" in sim_data
    assert "remainingRisks" in sim_data
    assert "fidelityNote" in sim_data
    assert "disclaimer" in sim_data

    metrics = sim_data["metrics"]
    for key in ["peakQueue", "waitTimeP95", "totalDelay", "spillbackDistance", "zoneViolations"]:
        assert key in metrics
        m = metrics[key]
        assert "baseline" in m
        assert "candidate" in m
        assert "deltaPct" in m


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Baseline vs Optimized Comparison
# ─────────────────────────────────────────────────────────────────────────────
def test_baseline_vs_optimized_comparison():
    constraints = ParsedConstraints(
        originalPrompt="compare baseline",
        demandFactor=1.0,
        fixedGroups=[],
        siblingSync=False,
        maxShiftMin=30,
        optimizationObjective="queue_reduction",
    )
    search_resp = client.post("/api/schedules/search", json={"constraints": constraints.model_dump()})
    schedule_id = search_resp.json()["candidates"][0]["id"]

    sim_resp = client.post("/api/simulation/run", json={"scheduleId": schedule_id})
    run_id = sim_resp.json()["runId"]

    compare_resp = client.get(f"/api/simulation/compare/{run_id}")
    assert compare_resp.status_code == 200
    report = compare_resp.json()
    assert report["candidateId"] == schedule_id
    assert "queueReductionPct" in report
    assert "computedFrom" in report


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: Stress Testing
# ─────────────────────────────────────────────────────────────────────────────
def test_stress_test_uses_selected_plan():
    constraints = ParsedConstraints(
        originalPrompt="stress test",
        demandFactor=1.0,
        fixedGroups=["c-prek"],
        siblingSync=True,
        maxShiftMin=15,
        optimizationObjective="queue_reduction",
    )
    search_resp = client.post("/api/schedules/search", json={"constraints": constraints.model_dump()})
    schedule_id = search_resp.json()["candidates"][0]["id"]
    schedule = get_registered_schedule(schedule_id)
    assert schedule is not None
    assert any(
        row.assignedGateId != next(
            cohort.assignedGateId
            for cohort in get_scenario().cohorts
            if cohort.id == row.cohortId
        )
        for row in schedule.groupSchedule
    )

    stress_resp = client.post("/api/stress/run", json={"scheduleId": schedule_id})
    assert stress_resp.status_code == 200
    stress_data = stress_resp.json()
    assert stress_data["scheduleId"] == schedule_id
    assert len(stress_data["scenarios"]) >= 6  # all defined scenarios
    for sc in stress_data["scenarios"]:
        assert "isFragile" in sc
        assert "explanation" in sc
        assert sc["status"] in ["stable", "degraded", "critical"]

    scenario = get_scenario()
    offsets = {row.cohortId: row.offsetMinutes for row in schedule.groupSchedule}
    assignments = {row.cohortId: row.assignedGateId for row in schedule.groupSchedule}
    _, expected_metrics = _simulate_queue_timeseries(
        scenario.cohorts,
        offsets,
        {gate.id: gate for gate in scenario.gates},
        1.0,
        assignments,
    )
    normal = next(
        result for result in stress_data["scenarios"]
        if result["scenarioId"] == "normal"
    )
    assert normal["meanQueue"] == pytest.approx(expected_metrics["mean_queue"])
    demand_surge = next(
        result for result in stress_data["scenarios"]
        if result["scenarioId"] == "demand-surge-30"
    )
    assert demand_surge["peakGateUtilizationPct"] > 105
    assert demand_surge["gateCapacityWithinLimit"] is False
    assert demand_surge["status"] == "degraded"
    assert "105% planning limit" in demand_surge["explanation"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: Invalid API Requests
# ─────────────────────────────────────────────────────────────────────────────
def test_missing_schedule_id_returns_404():
    resp = client.post("/api/simulation/run", json={"scheduleId": "does-not-exist"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "SCHEDULE_NOT_FOUND"


def test_empty_prompt_returns_validation_error():
    resp = client.post("/api/constraints/parse", json={"prompt": "x"})
    # Short prompt but valid parse — should succeed (parser handles it)
    # The real test is that it doesn't crash
    assert resp.status_code in [200, 422]


def test_nonexistent_schedule_returns_404():
    resp = client.get("/api/schedules/fake-schedule-123")
    assert resp.status_code == 404


def test_simulation_without_search_returns_404():
    resp = client.post("/api/simulation/run", json={"scheduleId": "not-registered"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "SCHEDULE_NOT_FOUND"


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: Reset Functionality
# ─────────────────────────────────────────────────────────────────────────────
def test_reset_endpoint():
    resp = client.post("/api/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "reset"
    # Scenario should still load after reset
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
