"""Optional AI explanations grounded in server-selected GateFlow evidence."""
from fastapi import APIRouter, Depends, HTTPException

from app.routers.schools import require_traffic_admin
from app.models.integrations import ExplanationRequest, ExplanationResponse
from app.services.openrouter_service import (
    ExplanationUnavailable,
    explain_with_openrouter,
)

router = APIRouter(prefix="/api/explanations", tags=["explanations"], dependencies=[Depends(require_traffic_admin)])


@router.post("", response_model=ExplanationResponse)
def create_explanation(body: ExplanationRequest):
    try:
        explanation, sources = explain_with_openrouter(body)
    except ExplanationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    from app.config import settings

    return ExplanationResponse(
        explanation=explanation,
        sources=sources,
        model=settings.openrouter_model,
    )
