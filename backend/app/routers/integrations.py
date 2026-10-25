"""Safe status for optional external integrations."""
from fastapi import APIRouter

from app.models.integrations import IntegrationStatusResponse
from app.services.integration_service import get_integration_status

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationStatusResponse)
def integration_status():
    return get_integration_status()
