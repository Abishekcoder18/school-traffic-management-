/**
 * GateFlow AI — API Client
 *
 * Typed API layer that replaces all direct mockData imports.
 * All calls go through the Vite proxy → FastAPI backend.
 * No GEMINI_API_KEY or server secrets are used client-side.
 */

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => null);
    const message =
      body?.error?.message ||
      body?.detail?.error?.message ||
      body?.detail ||
      `API error ${resp.status}`;
    const error: any = new Error(message);
    error.status = resp.status;
    error.body = body;
    throw error;
  }
  return resp.json();
}

// ─── Health ─────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  scenario: string;
  gates: number;
  cohorts: number;
  dataSource: string;
  sumo: string;
  simulationMethod: string;
}

export function getHealth(): Promise<HealthResponse> {
  return request('/health');
}

// ─── Scenario ───────────────────────────────────────────────────────────────

export interface School {
  id: string;
  name: string;
  code: string;
  activeSession: string;
  timeWindowStart: string;
  timeWindowEnd: string;
  totalStudents: number;
  totalVehicles: number;
  totalGates: number;
  pickupBays: number;
  schoolContactPhone: string;
  trafficCoordinator: string;
  vehicleCapacityThreshold: number;
}

export interface GateInfo {
  id: string;
  name: string;
  bays: number;
  hourlyCapacity: number;
  peakDemand: number;
  utilizationRate: number;
  status: 'optimal' | 'moderate' | 'bottleneck';
  assignedGrades: string[];
  locationNote: string;
}

export interface DemandCohort {
  id: string;
  cohort: string;
  gradeSpan: string;
  studentCount: number;
  vehicleDemand: number;
  currentDismissalTime: string;
  assignedGateId: string;
  bayRequirement: number;
}

export interface TrafficMetric {
  id: string;
  label: string;
  value: string;
  numericValue: number;
  unit?: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  status: 'normal' | 'warning' | 'alert';
  description: string;
}

export interface ScenarioResponse {
  school: School;
  gates: GateInfo[];
  cohorts: DemandCohort[];
  trafficMetrics: TrafficMetric[];
  dataSource: string;
  dataNote: string;
}

export function getScenario(): Promise<ScenarioResponse> {
  return request('/scenario');
}

// ─── Diagnosis ──────────────────────────────────────────────────────────────

export interface DiagnosisEvidence {
  title: string;
  detail: string;
  metric: string;
}

export interface BottleneckDiagnosis {
  gateId: string;
  gateName: string;
  overloadRatio: number;
  peakDemandRate: number;
  maxThroughputCapacity: number;
  primaryCause: string;
  explanation: string;
  evidence: DiagnosisEvidence[];
}

export interface DiagnosisResponse {
  diagnosis: BottleneckDiagnosis;
  dataQuality: { source: string; validationStatus: string; limitations: string[] };
}

export function getDiagnosis(): Promise<DiagnosisResponse> {
  return request('/diagnosis');
}

// ─── Constraints ────────────────────────────────────────────────────────────

export interface ParsedConstraints {
  originalPrompt: string;
  demandFactor: number;
  fixedGroups: string[];
  siblingSync: boolean;
  maxShiftMin: number;
  optimizationObjective: string;
  ambiguityFlags: string[];
  contradictionFlags: string[];
  parserMethod: string;
}

export interface ConstraintValidationResult {
  valid: boolean;
  constraints: ParsedConstraints | null;
  errors: string[];
  warnings: string[];
  clarificationRequired: string | null;
}

export function parseConstraints(prompt: string): Promise<ConstraintValidationResult> {
  return request('/constraints/parse', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  });
}

// ─── Schedules ──────────────────────────────────────────────────────────────

export interface GroupScheduleRow {
  cohort: string;
  cohortId: string;
  baselineTime: string;
  proposedTime: string;
  timeDelta: string;
  offsetMinutes: number;
  assignedGate: string;
  assignedGateId: string;
  zoneBay: string;
  vehicles: number;
}

export interface ScheduleCandidate {
  id: string;
  name: string;
  badge: string;
  description: string;
  staggerIntervalMin: number;
  peakQueueReductionPct: number;
  waitTimeReductionMin: number;
  totalDelayHours: number;
  spillbackReductionMeters: number;
  constraintFeasibility: '100% Compliant' | 'Minor Leniency' | 'Boundary Risk';
  riskProfile: 'Low' | 'Medium' | 'High';
  groupSchedule: GroupScheduleRow[];
  objectiveScore?: number;
  disruptionScore?: number;
  isFeasible?: boolean;
  feasibilityReason?: string;
}

export interface ScheduleSearchResponse {
  candidates: ScheduleCandidate[];
  totalEvaluated: number;
  feasibleCount: number;
  infeasibleCount: number;
  searchExplanation: string;
}

export function searchSchedules(
  constraints: ParsedConstraints
): Promise<ScheduleSearchResponse> {
  return request('/schedules/search', {
    method: 'POST',
    body: JSON.stringify({ constraints }),
  });
}

export function getSchedule(id: string): Promise<ScheduleCandidate> {
  return request(`/schedules/${id}`);
}

// ─── Simulation ─────────────────────────────────────────────────────────────

export interface MetricComparison {
  baseline: number;
  candidate: number;
  unit: string;
  deltaPct: number;
}

export interface SimulationMetrics {
  peakQueue: MetricComparison;
  waitTimeP95: MetricComparison;
  totalDelay: MetricComparison;
  spillbackDistance: MetricComparison;
  zoneViolations: MetricComparison;
}

export interface TimeInterval {
  time: string;
  baselineQueue: number;
  candidateQueue: number;
  gateCapacity: number;
}

export interface SimulationResult {
  runId: string;
  candidateId: string;
  candidateName: string;
  simulatedAt: string;
  fidelityNote: string;
  status: string;
  simulationMethod: string;
  metrics: SimulationMetrics;
  timeIntervals: TimeInterval[];
  improvements: string[];
  remainingRisks: string[];
  disclaimer: string;
}

export function runSimulation(
  scheduleId: string,
  demandFactor: number = 1.0
): Promise<SimulationResult> {
  return request('/simulation/run', {
    method: 'POST',
    body: JSON.stringify({ scheduleId, demandFactor }),
  });
}

export function getSimulationResult(runId: string): Promise<SimulationResult> {
  return request(`/simulation/${runId}`);
}

// ─── Stress Testing ─────────────────────────────────────────────────────────

export interface StressScenarioResult {
  scenarioId: string;
  scenarioName: string;
  demandFactor: number;
  dwellFactor: number;
  complianceRate: number;
  meanQueue: number;
  p95Wait: number;
  worstCaseQueue: number;
  isFragile: boolean;
  explanation: string;
  status: 'stable' | 'degraded' | 'critical';
}

export interface StressTestResponse {
  scheduleId: string;
  scheduleName: string;
  scenarios: StressScenarioResult[];
  overallAssessment: string;
}

export function runStressTests(scheduleId: string): Promise<StressTestResponse> {
  return request('/stress/run', {
    method: 'POST',
    body: JSON.stringify({ scheduleId }),
  });
}

// ─── Driver ─────────────────────────────────────────────────────────────────

export interface DriverNotice {
  title: string;
  message: string;
  type: 'notice' | 'advisory' | 'success';
}

export interface DriverAssignment {
  driverName: string;
  driverId: string;
  studentName: string;
  grade: string;
  vehiclePlate: string;
  scheduleTitle: string;
  date: string;
  arrivalWindow: string;
  officialSlot: string;
  gateName: string;
  gateNumber: string;
  pickupZone: string;
  bayNumber: string;
  laneColor: string;
  routeInstructions: string;
  approachStreet: string;
  queueStatus: string;
  assignmentStatus: 'Confirmed' | 'Pending' | 'Checked-In';
  hasCheckedIn: boolean;
  checkedInTimestamp?: string;
  instructions: string[];
  notices: DriverNotice[];
}

export function getDriverAssignment(): Promise<DriverAssignment> {
  return request('/scenario/driver');
}

// ─── Reset ──────────────────────────────────────────────────────────────────

export function resetDemo(): Promise<{ status: string; message: string }> {
  return request('/reset', { method: 'POST' });
}
