/**
 * GateFlow AI — API Client
 *
 * Typed API layer that replaces all direct mockData imports.
 * All calls go through the Vite proxy → FastAPI backend.
 * No GEMINI_API_KEY or server secrets are used client-side.
 */

const BASE = '/api';
const AUTH_TOKEN_KEY = 'gateflow_access_token';
const SCHOOL_CONTEXT_KEY = 'gateflow_school_context';

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: 'admin' | 'parent';
  is_active: boolean;
}

export interface ManagedSchool {
  id: string;
  name: string;
  code: string;
  address: string;
  city: string;
  contactPhone: string;
  activeSession: string;
  pickupStart: string;
  pickupEnd: string;
  totalGates: number;
  totalVehicles: number;
  pickupInstructions: string;
  mapPlaceId: string | null;
  parentAccessEnabled: boolean;
  trafficScenarioConfigured: boolean;
  canManage: boolean;
  canCreateSchools: boolean;
}

export interface SchoolStudent {
  id: string;
  studentName: string;
  grade: string;
  parentEmail: string;
  assignedGate: string;
  arrivalWindow: string;
  pickupInstructions: string[];
  notices: string[];
  verified: boolean;
}

export interface ParentDashboardEntry {
  school: { id: string; name: string; city: string };
  student: SchoolStudent;
  notices: string[];
}

let activeSchoolId: string | null = sessionStorage.getItem(SCHOOL_CONTEXT_KEY);

export function setSchoolContext(schoolId: string | null): void {
  activeSchoolId = schoolId;
  if (schoolId) sessionStorage.setItem(SCHOOL_CONTEXT_KEY, schoolId);
  else sessionStorage.removeItem(SCHOOL_CONTEXT_KEY);
}

export function getAuthToken(): string | null {
  return sessionStorage.getItem(AUTH_TOKEN_KEY) || localStorage.getItem(AUTH_TOKEN_KEY);
}

export function clearAuthToken(): void {
  sessionStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_TOKEN_KEY);
  setSchoolContext(null);
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const token = getAuthToken();
  if (activeSchoolId && !headers.has('X-School-ID')) {
    headers.set('X-School-ID', activeSchoolId);
  }
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
  const resp = await fetch(`${BASE}${url}`, {
    ...options,
    headers,
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

export async function login(
  username: string,
  password: string,
  rememberTerminal: boolean,
): Promise<AuthUser> {
  const form = new URLSearchParams({ username, password });
  const token = await request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  });
  clearAuthToken();
  if (rememberTerminal) {
    localStorage.setItem(AUTH_TOKEN_KEY, token.access_token);
  } else {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token.access_token);
  }
  try {
    return await request<AuthUser>('/auth/me');
  } catch (error) {
    clearAuthToken();
    throw error;
  }
}

export function getCurrentUser(): Promise<AuthUser> {
  return request('/auth/me');
}

export function getMySchools(): Promise<ManagedSchool[]> {
  return request('/schools/mine');
}

export function getSchool(schoolId: string): Promise<ManagedSchool> {
  return request(`/schools/${encodeURIComponent(schoolId)}`);
}

export type SchoolWrite = Omit<ManagedSchool, 'id' | 'canManage' | 'canCreateSchools' | 'trafficScenarioConfigured'>;

export function createSchool(input: SchoolWrite): Promise<ManagedSchool> {
  return request('/schools', { method: 'POST', body: JSON.stringify(input) });
}

export function updateSchool(schoolId: string, input: SchoolWrite): Promise<ManagedSchool> {
  return request(`/schools/${encodeURIComponent(schoolId)}`, {
    method: 'PUT',
    body: JSON.stringify(input),
  });
}

export function getStudents(schoolId: string): Promise<SchoolStudent[]> {
  return request(`/schools/${encodeURIComponent(schoolId)}/students`);
}

export function createStudent(
  schoolId: string,
  student: Omit<SchoolStudent, 'id' | 'verified'>,
): Promise<SchoolStudent> {
  return request(`/schools/${encodeURIComponent(schoolId)}/students`, {
    method: 'POST',
    body: JSON.stringify(student),
  });
}

export function inviteParent(schoolId: string, studentId: string): Promise<{
  invitationUrl: string;
  expiresAt: string;
  email: string;
  studentName: string;
}> {
  return request(`/schools/${encodeURIComponent(schoolId)}/invitations`, {
    method: 'POST',
    body: JSON.stringify({ studentId }),
  });
}

export function acceptParentInvitation(input: {
  token: string;
  fullName: string;
  password: string;
}): Promise<{ status: string; message: string }> {
  return request('/schools/invitations/accept', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getParentDashboard(schoolId: string): Promise<ParentDashboardEntry[]> {
  return request(`/schools/${encodeURIComponent(schoolId)}/parent-dashboard`);
}

export function getSchoolMap(schoolId: string): Promise<{
  schoolId: string;
  placeId: string | null;
  annotations: MapAnnotations | null;
}> {
  return request(`/schools/${encodeURIComponent(schoolId)}/map`);
}

export function saveSchoolMap(
  schoolId: string,
  annotations: MapAnnotations,
): Promise<{ schoolId: string; placeId: string; annotations: MapAnnotations }> {
  return request(`/schools/${encodeURIComponent(schoolId)}/map`, {
    method: 'PUT',
    body: JSON.stringify(annotations),
  });
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

// ─── Optional integrations and shared school map ────────────────────────────

export interface IntegrationStatus {
  openRouter: { configured: boolean; model: string | null };
}

export interface MapPoint {
  latitude: number;
  longitude: number;
}

export interface GateMarker {
  id: string;
  name: string;
  position: MapPoint;
}

export interface PickupArea {
  id: string;
  name: string;
  vehicleType: 'bus' | 'car' | 'two_wheeler' | 'general';
  points: MapPoint[];
}

export interface MapAnnotations {
  placeId: string;
  gates: GateMarker[];
  pickupAreas: PickupArea[];
  source?: string;
}

export interface ExplanationResponse {
  explanation: string;
  sources: string[];
  model: string;
  provider: string;
  generated: true;
  disclaimer: string;
}

export function getIntegrationStatus(): Promise<IntegrationStatus> {
  return request('/integrations/status');
}

export function requestExplanation(
  question: string,
  source: 'diagnosis' | 'schedule' | 'simulation' | 'stress',
  referenceId?: string,
): Promise<ExplanationResponse> {
  return request('/explanations', {
    method: 'POST',
    body: JSON.stringify({ question, source, referenceId }),
  });
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
  zoneRestrictions: string[];
  allowGateReassignment: boolean;
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
  requiredBays: number;
  availableBays: number;
  bayConstraintStatus: 'satisfied' | 'grandfathered';
}

export interface ScheduleCandidate {
  id: string;
  name: string;
  badge: string;
  description: string;
  staggerIntervalMin: number;
  peakQueueReductionPct: number | null;
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
  gateLoads?: Record<string, number>;
  gateCapacities?: Record<string, number>;
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
  deltaPct: number | null;
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

export interface ComparisonReport {
  baselineRunId: string;
  optimizedRunId: string;
  candidateId: string;
  candidateName: string;
  queueReductionPct: number;
  waitReductionPct: number;
  delayReductionPct: number;
  spillbackEliminated: boolean;
  overallImprovement: string;
  computedFrom: string;
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

export function getComparison(runId: string): Promise<ComparisonReport> {
  return request(`/simulation/compare/${runId}`);
}

// ─── Stress Testing ─────────────────────────────────────────────────────────

export interface StressScenarioResult {
  scenarioId: string;
  scenarioName: string;
  demandFactor: number;
  dwellFactor: number;
  complianceRate: number;
  peakGateUtilizationPct: number;
  gateCapacityWithinLimit: boolean;
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
