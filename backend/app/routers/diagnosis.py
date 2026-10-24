"""GateFlow AI — Diagnosis Router
GET /api/diagnosis — compute and return bottleneck diagnosis
"""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter

from app.models.diagnosis import DiagnosisResponse
from app.services.diagnosis_service import compute_diagnosis

router = APIRouter(prefix="/api", tags=["diagnosis"])
logger = logging.getLogger(__name__)


@router.get("/diagnosis", response_model=DiagnosisResponse)
def get_diagnosis():
    """
    Compute the bottleneck diagnosis from scenario data.
    Every field is backed by a calculated value — no AI-generated paragraphs.
    Data is labeled Synthetic.
    """
    return compute_diagnosis()
