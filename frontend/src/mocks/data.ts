import type {
  DashboardMetrics,
  AttentionItem,
  RecentDecision,
  LotItem,
  SamplingPlan,
  DefectProposal,
  UploadQueueItem,
  DecisionSummaryData,
  ReportData,
} from './types';

export const mockDashboardMetrics: DashboardMetrics = {
  openLotsCount: 7,
  onHoldCount: 2,
  escalateCount: 1,
  detectorAvailable: false,
  detectorMessage: {
    title: 'Not inferred, detector unavailable.',
    description: 'New photos need full manual review.',
  },
};

export const mockAttentionItems: AttentionItem[] = [
  {
    code: 'LT-2411-018',
    product: 'Navy polo',
    buyer: 'Northwind',
    status: 'ESCALATE',
  },
  {
    code: 'LT-2411-016',
    product: 'Grey tee',
    buyer: 'Northwind',
    status: 'HOLD',
  },
  {
    code: 'LT-2411-015',
    product: 'White tee',
    buyer: 'Brightway',
    status: 'HOLD',
  },
];

export const mockRecentDecisions: RecentDecision[] = [
  {
    code: 'LT-2411-014',
    dateStr: 'Today 10:42',
    reviewer: 'A. Rahman',
    outcome: 'ACCEPT',
  },
  {
    code: 'LT-2411-012',
    dateStr: 'Yesterday',
    reviewer: 'S. Karim',
    outcome: 'REJECT',
  },
];

export const mockLots: LotItem[] = [
  {
    id: 'LT-2411-018',
    code: 'LT-2411-018',
    product: 'Navy polo',
    buyer: 'Northwind Apparel',
    pieces: 800,
    status: 'ESCALATE',
    progressPercent: 75,
    registeredUnits: 74,
    requiredUnits: 80,
    reviewedUnits: 62,
    color: 'Navy',
    planSummary: 'n 80 · Ac 5 / Re 6 (major)',
    createdBy: 'A. Rahman',
    notInferredCount: 3,
    retakeCount: 2,
    escalateCount: 1,
    engineRecommendation: 'ESCALATE',
    finalDisposition: 'Not decided',
    escalationNote: 'Possible critical defect not yet confirmed. A person must decide this case.',
    history: [
      { title: 'Decision computed', timestamp: 'Today 10:42 · ESCALATE' },
      { title: 'Plan saved (rev 1)', timestamp: 'Yesterday · S. Karim' },
      { title: 'Lot created', timestamp: 'Yesterday · A. Rahman' },
    ],
  },
  {
    id: 'LT-2411-017',
    code: 'LT-2411-017',
    product: 'Black tee',
    buyer: 'Brightway',
    pieces: 1200,
    status: 'IN_PROGRESS',
    progressPercent: 35,
    registeredUnits: 32,
    requiredUnits: 80,
    color: 'Black',
    planSummary: 'n 80 · Ac 5 / Re 6 (major)',
    createdBy: 'S. Karim',
  },
  {
    id: 'LT-2411-016',
    code: 'LT-2411-016',
    product: 'Grey tee',
    buyer: 'Northwind',
    pieces: 500,
    status: 'HOLD',
    progressPercent: 75,
    registeredUnits: 64,
    requiredUnits: 80,
    color: 'Grey',
    planSummary: 'n 50 · Ac 3 / Re 4 (major)',
    createdBy: 'A. Rahman',
  },
  {
    id: 'LT-2411-014',
    code: 'LT-2411-014',
    product: 'Olive polo',
    buyer: 'Brightway',
    pieces: 650,
    status: 'ACCEPT',
    progressPercent: 85,
    registeredUnits: 80,
    requiredUnits: 80,
    color: 'Olive',
    reviewer: 'A. Rahman',
    planSummary: 'n 80 · Ac 5 / Re 6 (major)',
    createdBy: 'A. Rahman',
  },
  {
    id: 'LT-2411-012',
    code: 'LT-2411-012',
    product: 'Red tee',
    buyer: 'Northwind',
    pieces: 300,
    status: 'REJECT',
    progressPercent: 85,
    registeredUnits: 50,
    requiredUnits: 50,
    color: 'Red',
    reviewer: 'S. Karim',
    planSummary: 'n 50 · Ac 3 / Re 4 (major)',
    createdBy: 'S. Karim',
  },
];

export const mockDefaultSamplingPlan: SamplingPlan = {
  assumption:
    'Assumption: single sampling, normal inspection, General Inspection Level II. Entered by S. Karim.',
  enteredBy: 'S. Karim',
  classes: [
    {
      classType: 'critical',
      label: 'Critical',
      aql: 'AQL 0',
      n: 80,
      ac: 0,
      re: 1,
    },
    {
      classType: 'major',
      label: 'Major',
      aql: 'AQL 2.5',
      n: 80,
      ac: 5,
      re: 6,
    },
    {
      classType: 'minor',
      label: 'Minor',
      aql: 'AQL 4.0',
      n: 80,
      ac: 7,
      re: 9,
      warning: 'Warning: Re is not Ac + 1. Saving is allowed; a gap will HOLD the lot.',
    },
  ],
  source: 'e.g. Buyer PO #4471, page 3',
  readBack:
    'Sample 80 of 800 pieces. Reject on 1 critical, 6 major or 9 minor defective units.',
};

export const mockUploadQueue: UploadQueueItem[] = [
  {
    id: 'up-1',
    title: 'U-074 · Front',
    subtitle: '2.4 MB',
    status: 'Accepted',
  },
  {
    id: 'up-2',
    title: 'U-074 · Back',
    subtitle: 'Duplicate of earlier photo',
    status: 'Not counted',
  },
  {
    id: 'up-3',
    title: 'U-073 · Detail',
    subtitle: 'Uploading 62%',
    status: 'Uploading',
    progressPercent: 62,
  },
];

export const mockDefectProposals: DefectProposal[] = [
  {
    id: 'prop-1',
    type: 'Hole',
    score: 0.86,
    severity: 'CRITICAL',
    clause: 'Clause 4.2 · Northwind. You cannot edit severity.',
    flag: 'Possible critical',
    box: { x: 34, y: 26, width: 17, height: 14 },
    resolved: false,
  },
  {
    id: 'prop-2',
    type: 'Oil stain',
    score: 0.41,
    severity: 'MAJOR',
    clause: 'Clause 3.1 · Northwind. You cannot edit severity.',
    flag: 'Low score',
    box: { x: 57, y: 43, width: 20, height: 16 },
    resolved: false,
  },
];

export const defectTypeOptions = [
  'Hole',
  'Dropped stitch',
  'Skipped stitch',
  'Needle line',
  'Oil stain',
  'Shade band',
  'Other',
];

export const mockDecisionSummary: DecisionSummaryData = {
  lotCode: 'LT-2411-018',
  recommendation: 'REJECT',
  recommendationDetail: 'Major: 6 defective units ≥ Re 6 · sample complete',
  highRisk: true,
  classes: [
    { classType: 'Critical', n: 80, ac: 0, re: 1, count: 0, status: 'PASS' },
    { classType: 'Major', n: 80, ac: 5, re: 6, count: 6, status: 'FAIL' },
    { classType: 'Minor', n: 80, ac: 7, re: 8, count: 3, status: 'PASS' },
  ],
  reasonCode: 'CLASS_FAIL_MAJOR',
  planAssumption: 'Plan assumption: single sampling, normal, Level II.',
  modelVersion: 'Model v1.3.0.',
};

export const mockReportData: ReportData = {
  lotCode: 'LT-2411-018',
  product: 'Navy polo',
  buyer: 'Northwind',
  outcome: 'REJECT',
  sample: '80 / 800',
  defectsSummary: '0 / 6 / 3',
  reviewer: 'A. Rahman',
  modelVersion: 'v1.3.0 (uncalibrated)',
  auditVerified: true,
};
