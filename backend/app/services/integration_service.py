"""Read-only provider readiness information; never return credential values."""
from app.config import settings
from app.models.integrations import IntegrationStatusResponse, ProviderStatus


def get_integration_status() -> IntegrationStatusResponse:
    return IntegrationStatusResponse(
        openRouter=ProviderStatus(
            configured=bool(settings.openrouter_api_key.strip()),
            model=settings.openrouter_model,
        )
    )
