from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.main import app
from app.routers.auth import get_current_user
from app.routers.schools import require_traffic_admin


@pytest.fixture(autouse=True)
def authorize_existing_api_tests():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    app.dependency_overrides[require_traffic_admin] = lambda: SimpleNamespace(
        id="test-school", traffic_scenario_configured=True
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_traffic_admin, None)
