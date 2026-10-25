from __future__ import annotations

import pytest
import httpx
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import settings
from app.models.integrations import ExplanationRequest
from app.models.map_annotations import GeoPoint, MapAnnotations, PickupArea
from app.services.integration_service import get_integration_status
from app.services.map_state_service import MapStateStore
from app.services.openrouter_service import (
    ExplanationUnavailable,
    build_project_evidence,
    explain_with_openrouter,
)
from app.main import app


def test_map_state_persists_active_place_and_annotations(tmp_path):
    path = tmp_path / "map-state.json"
    store = MapStateStore(path)
    annotations = MapAnnotations(
        placeId="ChIJschool",
        gates=[
            {
                "id": "gate-main",
                "name": "Main Gate",
                "position": {"latitude": 13.0827, "longitude": 80.2707},
            }
        ],
        pickupAreas=[
            {
                "id": "pickup-main",
                "name": "Main Gate pickup",
                "points": [
                    {"latitude": 13.0826, "longitude": 80.2706},
                    {"latitude": 13.0827, "longitude": 80.2708},
                    {"latitude": 13.0825, "longitude": 80.2709},
                ],
            }
        ],
    )

    store.set_active_place("ChIJschool")
    store.save_annotations(annotations)

    reloaded = MapStateStore(path)
    assert reloaded.get_active_place() == "ChIJschool"
    assert reloaded.get_annotations("ChIJschool") == annotations
    other_school = MapAnnotations(
        placeId="ChIJschool",
        pickupAreas=[],
    )
    reloaded.save_annotations(annotations, storage_key="school-a")
    reloaded.save_annotations(other_school, storage_key="school-b")
    assert reloaded.get_annotations("ChIJschool", storage_key="school-a") == annotations
    assert reloaded.get_annotations("ChIJschool", storage_key="school-b") == other_school


def test_legacy_global_map_api_is_not_mounted():
    client = TestClient(app)

    assert client.get("/api/maps/active").status_code == 404


def test_map_coordinates_and_polygon_are_validated():
    with pytest.raises(ValidationError):
        GeoPoint(latitude=91, longitude=0)
    with pytest.raises(ValidationError):
        PickupArea(
            id="pickup",
            name="Pickup",
            points=[
                {"latitude": 13.0, "longitude": 80.0},
                {"latitude": 13.1, "longitude": 80.1},
            ],
        )


def test_integration_status_never_returns_provider_key(monkeypatch):
    secret = "not-a-real-provider-secret"
    monkeypatch.setattr(settings, "openrouter_api_key", secret)
    monkeypatch.setattr(settings, "openrouter_model", "moonshotai/kimi-k2:free")

    status = get_integration_status()
    serialized = status.model_dump_json()

    assert status.openRouter.configured is True
    assert status.openRouter.model == "moonshotai/kimi-k2:free"
    assert secret not in serialized


def test_integration_status_reports_missing_provider_without_failing(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")

    status = get_integration_status()

    assert status.openRouter.configured is False
    assert status.openRouter.model == "moonshotai/kimi-k2:free"


def test_explanation_evidence_is_selected_server_side(monkeypatch):
    class Diagnosis:
        def model_dump(self, mode):
            return {"diagnosis": {"primaryCause": "Gate 2 overload"}}

    monkeypatch.setattr(
        "app.services.openrouter_service.compute_diagnosis",
        lambda: Diagnosis(),
    )

    evidence, sources = build_project_evidence(
        ExplanationRequest(question="Explain the bottleneck.", source="diagnosis")
    )

    assert evidence == {"diagnosis": {"primaryCause": "Gate 2 overload"}}
    assert sources == ["GateFlow diagnosis"]


def test_explanation_requires_configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")

    with pytest.raises(ExplanationUnavailable, match="not configured"):
        explain_with_openrouter(
            ExplanationRequest(question="Explain the bottleneck.", source="diagnosis")
        )


def test_explanation_sends_project_evidence_to_openrouter_and_returns_sources(monkeypatch):
    class Diagnosis:
        def model_dump(self, mode):
            return {"diagnosis": {"primaryCause": "Gate 2 overload"}}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Gate 2 is the bottleneck."}}]}

    class Client:
        def __init__(self, timeout):
            assert timeout == 20.0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers, json):
            assert url.endswith("/chat/completions")
            assert headers["Authorization"] == "Bearer test-secret"
            assert json["model"] == "test-model"
            prompt = json["messages"][1]["content"]
            assert "Gate 2 overload" in prompt
            assert "vehicle_demand_all_runs.csv" not in prompt
            return Response()

    monkeypatch.setattr(settings, "openrouter_api_key", "test-secret")
    monkeypatch.setattr(settings, "openrouter_model", "test-model")
    monkeypatch.setattr(
        "app.services.openrouter_service.compute_diagnosis",
        lambda: Diagnosis(),
    )
    monkeypatch.setattr("app.services.openrouter_service.httpx.Client", Client)

    explanation, sources = explain_with_openrouter(
        ExplanationRequest(question="Explain the bottleneck.", source="diagnosis")
    )

    assert explanation == "Gate 2 is the bottleneck."
    assert sources == ["GateFlow diagnosis"]


def test_explanation_provider_failure_is_explicit_and_does_not_leak_secret(monkeypatch):
    class Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ConnectError("provider failure")

    monkeypatch.setattr(settings, "openrouter_api_key", "do-not-leak")
    monkeypatch.setattr(
        "app.services.openrouter_service.httpx.Client",
        Client,
    )

    with pytest.raises(ExplanationUnavailable) as error:
        explain_with_openrouter(
            ExplanationRequest(question="Explain the bottleneck.", source="diagnosis")
        )

    assert "do-not-leak" not in str(error.value)
