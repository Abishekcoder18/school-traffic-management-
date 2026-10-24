import {
  TrafficMetric,
  GateInfo,
  DemandCohort,
  BottleneckDiagnosis,
  ScheduleCandidate,
  SimulationResult,
  DriverAssignment
} from '../types';

export const SCHOOL_PROFILE = {
  name: 'Oakridge Academy & Secondary Campus',
  code: 'OAK-2026-DISTRICT-7',
  activeSession: 'Afternoon Dismissal (Peak Period)',
  timeWindow: '2:30 PM – 3:45 PM',
  totalVehicles: 540,
  totalGates: 4,
  pickupBays: 21,
  schoolContactPhone: '(555) 839-2041',
  trafficCoordinator: 'Officer Marcus Vance (Traffic Safety Lead)'
};

export const INITIAL_TRAFFIC_METRICS: TrafficMetric[] = [
  {
    id: 'peak-queue',
    label: 'Peak Queue Length',
    value: '48 vehicles',
    numericValue: 48,
    unit: 'veh',
    change: '+14% vs limit',
    trend: 'up',
    status: 'alert',
    description: 'Design limit is 35 vehicles before campus perimeter spillback'
  },
  {
    id: 'avg-wait-time',
    label: '95th% Pickup Wait Time',
    value: '16.4 min',
    numericValue: 16.4,
    unit: 'min',
    change: '+4.2 min vs baseline',
    trend: 'up',
    status: 'warning',
    description: 'Calculated from gate entry check-in to vehicle departure'
  },
  {
    id: 'gate-utilization',
    label: 'Bottleneck Gate Utilization',
    value: '150%',
    numericValue: 150,
    unit: '%',
    change: 'Severe load imbalance',
    trend: 'up',
    status: 'alert',
    description: 'East Wing Loop (Gate 2) is 50% over throughput capacity'
  },
  {
    id: 'total-delay',
    label: 'Total Vehicle Delay',
    value: '138 veh-hrs',
    numericValue: 138,
    unit: 'hrs',
    change: '+26% weekly average',
    trend: 'up',
    status: 'warning',
    description: 'Cumulative idle time across all 4 gate staging zones'
  }
];

export const GATES_DATA: GateInfo[] = [
  {
    id: 'gate-1',
    name: 'Gate 1 — Main Campus Loop',
    bays: 6,
    hourlyCapacity: 140,
    peakDemand: 110,
    utilizationRate: 78,
    status: 'optimal',
    assignedGrades: ['Kindergarten', 'Pre-K', 'Early Care'],
    locationNote: 'Direct access via South Boulevard with dual bypass lane'
  },
  {
    id: 'gate-2',
    name: 'Gate 2 — East Wing Loop',
    bays: 4,
    hourlyCapacity: 90,
    peakDemand: 135,
    utilizationRate: 150,
    status: 'bottleneck',
    assignedGrades: ['Grades 1–3', 'Grades 4–5'],
    locationNote: 'Single-lane entry off Municipal Parkway; severe spillback'
  },
  {
    id: 'gate-3',
    name: 'Gate 3 — North Bus & Van Bay',
    bays: 5,
    hourlyCapacity: 100,
    peakDemand: 82,
    utilizationRate: 82,
    status: 'moderate',
    assignedGrades: ['District Transit Buses', 'Special Care Vans', 'Grades 6–8'],
    locationNote: 'Controlled security barrier with dedicated staff signal'
  },
  {
    id: 'gate-4',
    name: 'Gate 4 — Athletics & South Overflow',
    bays: 6,
    hourlyCapacity: 130,
    peakDemand: 45,
    utilizationRate: 35,
    status: 'optimal',
    assignedGrades: ['High School Grades 9–12', 'Carpool Volunteers'],
    locationNote: 'High capacity staging area, currently underutilized by 65%'
  }
];

export const DEMAND_COHORTS: DemandCohort[] = [
  {
    id: 'c-prek',
    cohort: 'Kindergarten & Early Care',
    gradeSpan: 'Pre-K – K',
    studentCount: 95,
    vehicleDemand: 75,
    currentDismissalTime: '2:30 PM',
    assignedGateId: 'gate-1',
    bayRequirement: 4
  },
  {
    id: 'c-g13',
    cohort: 'Elementary Lower Cohort',
    gradeSpan: 'Grades 1–3',
    studentCount: 190,
    vehicleDemand: 140,
    currentDismissalTime: '3:00 PM',
    assignedGateId: 'gate-2',
    bayRequirement: 5
  },
  {
    id: 'c-g45',
    cohort: 'Elementary Upper Cohort',
    gradeSpan: 'Grades 4–5',
    studentCount: 180,
    vehicleDemand: 130,
    currentDismissalTime: '3:00 PM',
    assignedGateId: 'gate-2',
    bayRequirement: 5
  },
  {
    id: 'c-g68',
    cohort: 'Middle School Cadre',
    gradeSpan: 'Grades 6–8',
    studentCount: 160,
    vehicleDemand: 115,
    currentDismissalTime: '3:15 PM',
    assignedGateId: 'gate-3',
    bayRequirement: 4
  },
  {
    id: 'c-hs',
    cohort: 'High School & Secondary',
    gradeSpan: 'Grades 9–12',
    studentCount: 150,
    vehicleDemand: 80,
    currentDismissalTime: '3:30 PM',
    assignedGateId: 'gate-4',
    bayRequirement: 3
  }
];

export const BOTTLENECK_DIAGNOSIS: BottleneckDiagnosis = {
  gateId: 'gate-2',
  gateName: 'Gate 2 — East Wing Loop',
  overloadRatio: 1.5,
  peakDemandRate: 135,
  maxThroughputCapacity: 90,
  primaryCause: 'Simultaneous 3:00 PM Dismissal Collision on Single-Lane Infrastructure',
  explanation:
    'Both Grades 1–3 (140 vehicles) and Grades 4–5 (130 vehicles) share the exact same dismissal bell at 3:00 PM and are routed to the 4-bay East Wing Gate. With a processing capability of 90 vehicles per hour, the peak surge of 270 arriving vehicles overwhelms the loop within 20 minutes, generating an unmitigated 48-vehicle queue that spills 180 meters onto Municipal Parkway.',
  evidence: [
    {
      title: 'Arrival Surge vs Bay Capacity Mismatch',
      detail:
        '270 vehicles funneling through 4 loading bays gives 26.6 seconds per boarding operation, while measured student boarding averages 48 seconds.',
      metric: '150% Capacity Overload'
    },
    {
      title: 'Spillback onto Public Arterial Road',
      detail:
        'Queue reaches past campus turn-lane threshold into the westbound lane of Municipal Parkway, impeding local transit buses.',
      metric: '180m Spillback Beyond Perimeter'
    },
    {
      title: 'Underutilized Adjacent Infrastructure',
      detail:
        'Gate 4 (Athletics Complex) operates at only 35% capacity during the 3:00 PM peak with 6 vacant bays and a dedicated 40-car staging driveway.',
      metric: '65% Idle Capacity at Gate 4'
    }
  ]
};

export const CANDIDATE_SCHEDULES: ScheduleCandidate[] = [
  {
    id: 'candidate-a',
    name: 'Plan Alpha: 15-Min Stagger & East Wing Decongestion',
    badge: 'Recommended',
    description:
      'Staggers Lower Elementary (Grades 1–3) to 2:45 PM, retains Upper Elementary at 3:00 PM, and reroutes Grade 5 carpools to Gate 4.',
    staggerIntervalMin: 15,
    peakQueueReductionPct: 54,
    waitTimeReductionMin: 8.8,
    totalDelayHours: 61,
    spillbackReductionMeters: 180,
    constraintFeasibility: '100% Compliant',
    riskProfile: 'Low',
    groupSchedule: [
      {
        cohort: 'Kindergarten & Pre-K',
        baselineTime: '2:30 PM',
        proposedTime: '2:30 PM',
        timeDelta: '0 min (Unchanged)',
        assignedGate: 'Gate 1 (Main Loop)',
        zoneBay: 'Bays 1–4',
        vehicles: 75
      },
      {
        cohort: 'Grades 1–3 (Lower)',
        baselineTime: '3:00 PM',
        proposedTime: '2:45 PM',
        timeDelta: '-15 min (Earlier)',
        assignedGate: 'Gate 2 (East Wing)',
        zoneBay: 'Bays 1–4',
        vehicles: 140
      },
      {
        cohort: 'Grades 4–5 (Upper)',
        baselineTime: '3:00 PM',
        proposedTime: '3:05 PM',
        timeDelta: '+5 min (Shift)',
        assignedGate: 'Gate 2 (East Wing)',
        zoneBay: 'Bays 1–4',
        vehicles: 85
      },
      {
        cohort: 'Grade 5 Carpools & High School',
        baselineTime: '3:00 PM / 3:30 PM',
        proposedTime: '3:10 PM',
        timeDelta: 'Rerouted to Gate 4',
        assignedGate: 'Gate 4 (Athletics)',
        zoneBay: 'Bays 1–6',
        vehicles: 125
      },
      {
        cohort: 'Grades 6–8 & District Transit',
        baselineTime: '3:15 PM',
        proposedTime: '3:20 PM',
        timeDelta: '+5 min',
        assignedGate: 'Gate 3 (North Bay)',
        zoneBay: 'Bays 1–5',
        vehicles: 115
      }
    ]
  },
  {
    id: 'candidate-b',
    name: 'Plan Beta: Infrastructure Balancing (Shift Upper to Gate 4)',
    badge: 'Alternative',
    description:
      'Keeps 3:00 PM dismissal synchronous but reallocates all Upper Elementary (Grades 4–5) vehicles to the spacious Gate 4 Athletics loop.',
    staggerIntervalMin: 10,
    peakQueueReductionPct: 42,
    waitTimeReductionMin: 6.5,
    totalDelayHours: 79,
    spillbackReductionMeters: 145,
    constraintFeasibility: 'Minor Leniency',
    riskProfile: 'Medium',
    groupSchedule: [
      {
        cohort: 'Kindergarten & Pre-K',
        baselineTime: '2:30 PM',
        proposedTime: '2:30 PM',
        timeDelta: '0 min',
        assignedGate: 'Gate 1 (Main Loop)',
        zoneBay: 'Bays 1–4',
        vehicles: 75
      },
      {
        cohort: 'Grades 1–3 (Lower)',
        baselineTime: '3:00 PM',
        proposedTime: '3:00 PM',
        timeDelta: '0 min',
        assignedGate: 'Gate 2 (East Wing)',
        zoneBay: 'Bays 1–4',
        vehicles: 140
      },
      {
        cohort: 'Grades 4–5 (Upper)',
        baselineTime: '3:00 PM',
        proposedTime: '3:00 PM',
        timeDelta: 'Gate Change Only',
        assignedGate: 'Gate 4 (Athletics)',
        zoneBay: 'Bays 1–6',
        vehicles: 130
      },
      {
        cohort: 'Grades 6–8',
        baselineTime: '3:15 PM',
        proposedTime: '3:15 PM',
        timeDelta: '0 min',
        assignedGate: 'Gate 3 (North Bay)',
        zoneBay: 'Bays 1–5',
        vehicles: 115
      },
      {
        cohort: 'Grades 9–12',
        baselineTime: '3:30 PM',
        proposedTime: '3:30 PM',
        timeDelta: '0 min',
        assignedGate: 'Gate 4 (Athletics)',
        zoneBay: 'Bays 1–6',
        vehicles: 80
      }
    ]
  },
  {
    id: 'candidate-c',
    name: 'Plan Gamma: Sibling-Clustered Cohort Priority',
    badge: 'Family Sync',
    description:
      'Permits multi-child families to dismiss simultaneously at 2:50 PM through Gate 1 Main Loop, smoothing individual grade traffic.',
    staggerIntervalMin: 12,
    peakQueueReductionPct: 35,
    waitTimeReductionMin: 4.9,
    totalDelayHours: 92,
    spillbackReductionMeters: 120,
    constraintFeasibility: '100% Compliant',
    riskProfile: 'Low',
    groupSchedule: [
      {
        cohort: 'Multi-Child Sibling Families',
        baselineTime: '3:00 PM',
        proposedTime: '2:50 PM',
        timeDelta: '-10 min Priority',
        assignedGate: 'Gate 1 (Main Loop)',
        zoneBay: 'Bays 1–6',
        vehicles: 110
      },
      {
        cohort: 'Grades 1–3 (Single Student)',
        baselineTime: '3:00 PM',
        proposedTime: '3:02 PM',
        timeDelta: '+2 min',
        assignedGate: 'Gate 2 (East Wing)',
        zoneBay: 'Bays 1–4',
        vehicles: 95
      },
      {
        cohort: 'Grades 4–5 (Single Student)',
        baselineTime: '3:00 PM',
        proposedTime: '3:14 PM',
        timeDelta: '+14 min',
        assignedGate: 'Gate 2 (East Wing)',
        zoneBay: 'Bays 1–4',
        vehicles: 80
      },
      {
        cohort: 'Grades 6–8 & High School',
        baselineTime: '3:15 PM / 3:30 PM',
        proposedTime: '3:25 PM',
        timeDelta: 'Consolidated',
        assignedGate: 'Gate 3 & Gate 4',
        zoneBay: 'Bays 1–6',
        vehicles: 180
      }
    ]
  }
];

export const SIMULATION_RESULT_DATA: SimulationResult = {
  candidateId: 'candidate-a',
  candidateName: 'Plan Alpha: 15-Min Stagger & East Wing Decongestion',
  simulatedAt: 'Today at 02:14 PM',
  fidelityNote:
    'Calibrated using GateFlow Poisson arrival distribution and campus geometric loop throughput benchmarks.',
  metrics: {
    peakQueue: {
      baseline: 48,
      candidate: 22,
      unit: 'vehicles',
      deltaPct: -54.2
    },
    waitTimeP95: {
      baseline: 16.4,
      candidate: 7.6,
      unit: 'minutes',
      deltaPct: -53.7
    },
    totalDelay: {
      baseline: 138,
      candidate: 61,
      unit: 'veh-hrs',
      deltaPct: -55.8
    },
    spillbackDistance: {
      baseline: 180,
      candidate: 0,
      unit: 'meters',
      deltaPct: -100
    },
    zoneViolations: {
      baseline: 14,
      candidate: 1,
      unit: 'incidents',
      deltaPct: -92.9
    }
  },
  timeIntervals: [
    { time: '2:30 PM', baselineQueue: 12, candidateQueue: 10, gateCapacity: 35 },
    { time: '2:45 PM', baselineQueue: 24, candidateQueue: 18, gateCapacity: 35 },
    { time: '3:00 PM', baselineQueue: 48, candidateQueue: 22, gateCapacity: 35 }, // Critical Peak
    { time: '3:15 PM', baselineQueue: 44, candidateQueue: 19, gateCapacity: 35 },
    { time: '3:30 PM', baselineQueue: 31, candidateQueue: 14, gateCapacity: 35 },
    { time: '3:45 PM', baselineQueue: 9, candidateQueue: 4, gateCapacity: 35 }
  ],
  improvements: [
    'Zero spillback onto Municipal Parkway: 100% of queuing vehicles stay within campus internal access road.',
    '48 to 22 vehicle reduction in peak queue length — well beneath the 35-vehicle critical threshold.',
    'Elimination of double-parking and pedestrian crosswalk occlusion at East Wing elementary crossing.',
    'Gate 4 capacity utilization increased from 35% to 78%, balancing infrastructure load across campus.'
  ],
  remainingRisks: [
    'Parent Compliance Sensitivity: If more than 15% of Grade 1–3 drivers arrive late past 2:55 PM, peak queue may increase by 4–6 vehicles.',
    'Early Arrival Staging: Requires clear communication so 2:45 PM drivers do not arrive before 2:35 PM and obstruct Kindergarten departure.',
    'Staff Reassignment: East Wing requires 1 additional escort monitor shifted from Gate 4 between 2:40 PM and 3:05 PM.'
  ]
};

export const INITIAL_DRIVER_ASSIGNMENT: DriverAssignment = {
  driverName: 'Sarah Jenkins',
  driverId: 'DRV-84920',
  studentName: 'Leo Jenkins',
  grade: 'Grade 2 — Mrs. Henderson',
  vehiclePlate: '7XYZ892 (Silver Honda Odyssey)',
  scheduleTitle: 'Afternoon Dismissal — Elementary Stagger',
  date: 'Today, Oct 24, 2026',
  arrivalWindow: '2:40 PM – 2:50 PM',
  officialSlot: '2:45 PM',
  gateName: 'Gate 2 — East Wing Loop',
  gateNumber: 'Gate 2',
  pickupZone: 'East Elementary Wing',
  bayNumber: 'Bay #3',
  laneColor: 'Blue Lane',
  routeInstructions:
    'Approach northbound via Municipal Parkway. Signal right into Gate 2 Queue Lane B. Follow Blue Lane markings to Bay #3.',
  approachStreet: 'Municipal Parkway (Northbound)',
  queueStatus: 'Flowing smoothly · 3 vehicles ahead',
  assignmentStatus: 'Confirmed',
  hasCheckedIn: false,
  instructions: [
    'Display your digital dashboard or physical green parking pass on passenger visor.',
    'Remain inside your vehicle. Oakridge staff escorts will bring Leo directly to your vehicle door.',
    'Do not block the pedestrian crosswalk before Bay #1.',
    'If arriving past 2:55 PM, proceed directly to Gate 4 Overflow Bay to avoid blocking upper grades.'
  ],
  notices: [
    {
      title: 'Rain Protocol Active',
      message: 'Covered awning bays are activated. Vehicle boarding takes place strictly in marked numbered slots.',
      type: 'notice'
    },
    {
      title: 'Pedestrian Safety Zone',
      message: 'Speed limit on East Loop approach is reduced to 10 MPH. Watch for crossing guards at Crosswalk B.',
      type: 'advisory'
    }
  ]
};

export const SYSTEM_NOTIFICATIONS = [
  {
    id: 'notif-1',
    time: '2 mins ago',
    title: 'Spillback Alert Resolved',
    detail: 'Municipal Parkway turn-lane clearance restored at Gate 2 approach.',
    type: 'success'
  },
  {
    id: 'notif-2',
    time: '18 mins ago',
    title: 'High Congestion Warning',
    detail: 'Gate 2 peak demand exceeded capacity by 50% during 3:00 PM dismissal.',
    type: 'alert'
  },
  {
    id: 'notif-3',
    time: '1 hour ago',
    title: 'Driver Pass Broadcast',
    detail: '348 driver instructions and QR passes dispatched for afternoon schedule.',
    type: 'info'
  }
];
