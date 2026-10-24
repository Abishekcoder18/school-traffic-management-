"""GateFlow AI — Pydantic Models: Schedule / Constraints"""
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ─── Constraints ──────────────────────────────────────────────────────────────

class ParsedConstraints(BaseModel):
    originalPrompt: str
    demandFactor: float = 1.0          # e.g. 1.30 for +30%
    fixedGroups: list[str] = []        # cohort IDs that must not shift
    siblingSync: bool = False          # synchronize sibling groups
    maxShiftMin: int = 30              # maximum time shift per cohort
    zoneRestrictions: list[str] = []   # e.g. ["gate-2-only"]
    optimizationObjective: Literal[
        "queue_reduction", "minimal_disruption", "balanced"
    ] = "queue_reduction"
    ambiguityFlags: list[str] = []     # user input was unclear in these areas
    contradictionFlags: list[str] = [] # detected logical contradictions
    parserMethod: Literal["deterministic", "ai"] = "deterministic"


class ConstraintParseRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)


class ConstraintValidationResult(BaseModel):
    valid: bool
    constraints: Optional[ParsedConstraints] = None
    errors: list[str] = []
    warnings: list[str] = []
    clarificationRequired: Optional[str] = None


# ─── Schedule ─────────────────────────────────────────────────────────────────

class GroupScheduleRow(BaseModel):
    cohort: str
    cohortId: str
    baselineTime: str    # human-readable "HH:MM AM/PM"
    proposedTime: str
    timeDelta: str       # human-readable "+15 min" etc.
    offsetMinutes: int   # actual numeric offset applied
    assignedGate: str
    assignedGateId: str
    zoneBay: str
    vehicles: int


class ScheduleCandidate(BaseModel):
    id: str
    name: str
    badge: str
    description: str
    staggerIntervalMin: int
    peakQueueReductionPct: float
    waitTimeReductionMin: float
    totalDelayHours: float
    spillbackReductionMeters: float
    constraintFeasibility: Literal["100% Compliant", "Minor Leniency", "Boundary Risk"]
    riskProfile: Literal["Low", "Medium", "High"]
    groupSchedule: list[GroupScheduleRow]
    # Planner metadata
    objectiveScore: float = 0.0
    disruptionScore: float = 0.0
    gateLoads: dict[str, float] = {}
    isFeasible: bool = True
    feasibilityReason: str = "All gate capacity constraints satisfied"
    computedFrom: str = "DeterministicPlanning"


class ScheduleSearchRequest(BaseModel):
    constraints: ParsedConstraints


class ScheduleSearchResponse(BaseModel):
    candidates: list[ScheduleCandidate]
    totalEvaluated: int
    feasibleCount: int
    infeasibleCount: int
    dominatedCount: int
    searchExplanation: str
    dataSource: str = "Synthetic"
    computedFrom: str = "DeterministicPlanning"
