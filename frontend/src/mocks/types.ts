export type UserRole = 'Inspector' | 'Supervisor' | 'Admin';

export type OutcomeType = 'ACCEPT' | 'REJECT' | 'HOLD' | 'ESCALATE';

export interface LotItem {
  id: string;
  code: string;
  product: string;
  buyer: string;
  pieces: number;
  status: OutcomeType | 'IN_PROGRESS';
  progressPercent: number;
  registeredUnits?: number;
  requiredUnits?: number;
  reviewedUnits?: number;
  color?: string;
  updatedAt?: string;
  reviewer?: string;
  planSummary?: string;
  createdBy?: string;
  notInferredCount?: number;
  retakeCount?: number;
  escalateCount?: number;
  engineRecommendation?: OutcomeType;
  finalDisposition?: string;
  escalationNote?: string;
  history?: LotHistoryEvent[];
}

export interface DashboardMetrics {
  openLotsCount: number;
  onHoldCount: number;
  escalateCount: number;
  detectorAvailable: boolean;
  detectorMessage: {
    title: string;
    description: string;
  };
}

export interface AttentionItem {
  code: string;
  product: string;
  buyer: string;
  status: 'ESCALATE' | 'HOLD';
}

export interface RecentDecision {
  code: string;
  dateStr: string;
  reviewer: string;
  outcome: 'ACCEPT' | 'REJECT';
}

export interface PlanClass {
  classType: 'critical' | 'major' | 'minor';
  label: string;
  aql: string;
  n: number;
  ac: number;
  re: number;
  warning?: string;
}

export interface SamplingPlan {
  assumption: string;
  enteredBy: string;
  classes: PlanClass[];
  source: string;
  readBack: string;
}

export interface LotHistoryEvent {
  title: string;
  timestamp: string;
}

export interface DefectProposal {
  id: string;
  type: string;
  score: number;
  severity: 'CRITICAL' | 'MAJOR' | 'MINOR';
  clause: string;
  flag?: string;
  box: { x: number; y: number; width: number; height: number };
  resolved?: boolean;
  resolution?: 'CONFIRMED' | 'REJECTED';
}

export interface UploadQueueItem {
  id: string;
  title: string;
  subtitle: string;
  status: 'Accepted' | 'Not counted' | 'Uploading';
  progressPercent?: number;
}

export interface DecisionClassRow {
  classType: string;
  n: number;
  ac: number;
  re: number;
  count: number;
  status: 'PASS' | 'FAIL' | 'GAP';
}

export interface DecisionSummaryData {
  lotCode: string;
  recommendation: OutcomeType;
  recommendationDetail: string;
  highRisk: boolean;
  classes: DecisionClassRow[];
  reasonCode: string;
  planAssumption: string;
  modelVersion: string;
}

export interface ReportData {
  lotCode: string;
  product: string;
  buyer: string;
  outcome: OutcomeType;
  sample: string;
  defectsSummary: string;
  reviewer: string;
  modelVersion: string;
  auditVerified: boolean;
}
