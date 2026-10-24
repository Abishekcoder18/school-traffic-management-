"""GateFlow AI — Pydantic Models: Diagnosis"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class DiagnosisEvidence(BaseModel):
    title: str
    detail: str
    metric: str


class DataQuality(BaseModel):
    source: Literal["Synthetic"] = "Synthetic"
    validationStatus: str
    limitations: list[str]


class BottleneckDiagnosis(BaseModel):
    gateId: str
    gateName: str
    overloadRatio: float
    peakDemandRate: float
    maxThroughputCapacity: float
    primaryCause: str
    explanation: str
    evidence: list[DiagnosisEvidence]


class DiagnosisResponse(BaseModel):
    diagnosis: BottleneckDiagnosis
    dataQuality: DataQuality
    computedFrom: str = "DeterministicAnalysis"
