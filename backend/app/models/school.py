"""GateFlow AI — Pydantic Models: School / Gate / Cohort"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ─── School ──────────────────────────────────────────────────────────────────

class School(BaseModel):
    id: str
    name: str
    code: str
    activeSession: str
    timeWindowStart: str
    timeWindowEnd: str
    totalStudents: int
    totalVehicles: int
    totalGates: int
    pickupBays: int
    schoolContactPhone: str
    trafficCoordinator: str
    randomSeed: int
    vehicleCapacityThreshold: int
    averageDwellTimeSeconds: float
    designDwellTimeSeconds: float


# ─── Gates ───────────────────────────────────────────────────────────────────

GateStatus = Literal["optimal", "moderate", "bottleneck"]


class GateInfo(BaseModel):
    id: str
    name: str
    bays: int
    hourlyCapacity: int
    peakDemand: int
    utilizationRate: float
    status: GateStatus
    assignedGrades: list[str]
    locationNote: str
    approachStreet: str


# ─── Demand Cohorts ───────────────────────────────────────────────────────────

class DemandCohort(BaseModel):
    id: str
    cohort: str
    gradeSpan: str
    studentCount: int
    vehicleDemand: int
    currentDismissalTime: str  # "HH:MM" 24-hour
    assignedGateId: str
    bayRequirement: int
    isKindergarten: bool
    hasSiblingGroup: bool


class SiblingGroup(BaseModel):
    id: str
    name: str
    cohortIds: list[str]
    description: str


# ─── Traffic Metrics ─────────────────────────────────────────────────────────

MetricTrend = Literal["up", "down", "neutral"]
MetricStatus = Literal["normal", "warning", "alert"]


class TrafficMetric(BaseModel):
    id: str
    label: str
    value: str
    numericValue: float
    unit: Optional[str] = None
    change: str
    trend: MetricTrend
    status: MetricStatus
    description: str


# ─── Notices (for driver dashboard) ──────────────────────────────────────────

class DriverNotice(BaseModel):
    title: str
    message: str
    type: Literal["notice", "advisory", "success"]


# ─── Driver Assignment ────────────────────────────────────────────────────────

class DriverAssignment(BaseModel):
    driverName: str
    driverId: str
    studentName: str
    grade: str
    vehiclePlate: str
    scheduleTitle: str
    date: str
    arrivalWindow: str
    officialSlot: str
    gateName: str
    gateNumber: str
    pickupZone: str
    bayNumber: str
    laneColor: str
    routeInstructions: str
    approachStreet: str
    queueStatus: str
    assignmentStatus: Literal["Confirmed", "Pending", "Checked-In"]
    hasCheckedIn: bool
    checkedInTimestamp: Optional[str] = None
    instructions: list[str]
    notices: list[DriverNotice]


# ─── Full Scenario ────────────────────────────────────────────────────────────

class ScenarioResponse(BaseModel):
    school: School
    gates: list[GateInfo]
    cohorts: list[DemandCohort]
    siblingGroups: list[SiblingGroup]
    trafficMetrics: list[TrafficMetric]
    dataSource: str = "Synthetic"
    dataNote: str = (
        "All values are assumed/synthetic for demonstration purposes. "
        "They do not represent real-world school traffic observations."
    )
