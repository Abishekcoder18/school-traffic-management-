"""GateFlow AI — Pydantic Models: Simulation & Stress"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


# ─── Simulation ───────────────────────────────────────────────────────────────

class MetricComparison(BaseModel):
    baseline: float
    candidate: float
    unit: str
    deltaPct: Optional[float]


class SimulationMetrics(BaseModel):
    peakQueue: MetricComparison
    waitTimeP95: MetricComparison
    totalDelay: MetricComparison
    spillbackDistance: MetricComparison
    zoneViolations: MetricComparison


class TimeInterval(BaseModel):
    time: str
    baselineQueue: float
    candidateQueue: float
    gateCapacity: float


SimulationStatus = Literal["success", "failed", "sumo_unavailable", "deterministic"]


class SimulationResult(BaseModel):
    runId: str
    candidateId: str
    candidateName: str
    simulatedAt: str
    fidelityNote: str
    status: SimulationStatus
    simulationMethod: Literal["SUMO", "DeterministicEstimate"]
    metrics: SimulationMetrics
    timeIntervals: list[TimeInterval]
    improvements: list[str]
    remainingRisks: list[str]
    dataSource: str = "Synthetic"
    disclaimer: str = (
        "Results are deterministic planning estimates based on queuing theory "
        "and synthetic data. They do not represent field-measured observations."
    )


class SimulationRunRequest(BaseModel):
    scheduleId: str
    demandFactor: float = 1.0


# ─── Baseline Comparison ──────────────────────────────────────────────────────

class ComparisonReport(BaseModel):
    baselineRunId: str
    optimizedRunId: str
    candidateId: str
    candidateName: str
    queueReductionPct: float
    waitReductionPct: float
    delayReductionPct: float
    spillbackEliminated: bool
    overallImprovement: str
    computedFrom: str = "DeterministicEstimate"


# ─── Stress Testing ───────────────────────────────────────────────────────────

class StressScenarioResult(BaseModel):
    scenarioId: str
    scenarioName: str
    demandFactor: float
    dwellFactor: float
    complianceRate: float  # 0.0 to 1.0
    peakGateUtilizationPct: float
    gateCapacityWithinLimit: bool
    meanQueue: float
    p95Wait: float
    worstCaseQueue: float
    isFragile: bool
    explanation: str
    status: Literal["stable", "degraded", "critical"]


class StressTestRequest(BaseModel):
    scheduleId: str


class StressTestResponse(BaseModel):
    scheduleId: str
    scheduleName: str
    scenarios: list[StressScenarioResult]
    overallAssessment: str
    computedFrom: str = "DeterministicEstimate"
    dataSource: str = "Synthetic"
