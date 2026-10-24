export type UserRole = 'admin' | 'driver';

export type AdminTab = 'overview' | 'cause' | 'schedule' | 'test';

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

export interface GateInfo {
  id: string;
  name: string;
  bays: number;
  hourlyCapacity: number;
  peakDemand: number;
  utilizationRate: number; // percentage
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

export interface BottleneckDiagnosis {
  gateId: string;
  gateName: string;
  overloadRatio: number; // e.g. 1.50
  peakDemandRate: number;
  maxThroughputCapacity: number;
  primaryCause: string;
  explanation: string;
  evidence: {
    title: string;
    detail: string;
    metric: string;
  }[];
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
  groupSchedule: {
    cohort: string;
    baselineTime: string;
    proposedTime: string;
    timeDelta: string;
    assignedGate: string;
    zoneBay: string;
    vehicles: number;
  }[];
}

export interface SimulationResult {
  candidateId: string;
  candidateName: string;
  simulatedAt: string;
  fidelityNote: string;
  metrics: {
    peakQueue: { baseline: number; candidate: number; unit: string; deltaPct: number };
    waitTimeP95: { baseline: number; candidate: number; unit: string; deltaPct: number };
    totalDelay: { baseline: number; candidate: number; unit: string; deltaPct: number };
    spillbackDistance: { baseline: number; candidate: number; unit: string; deltaPct: number };
    zoneViolations: { baseline: number; candidate: number; unit: string; deltaPct: number };
  };
  timeIntervals: {
    time: string;
    baselineQueue: number;
    candidateQueue: number;
    gateCapacity: number;
  }[];
  improvements: string[];
  remainingRisks: string[];
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
  notices: {
    title: string;
    message: string;
    type: 'notice' | 'advisory' | 'success';
  }[];
}
