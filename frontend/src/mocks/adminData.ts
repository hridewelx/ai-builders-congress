export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: 'Admin' | 'Supervisor' | 'Inspector';
  status: 'Active' | 'Locked' | 'Disabled';
  lastLogin: string;
  isSelf?: boolean;
}

export interface AuditLogRow {
  id: string;
  time: string;
  user: string;
  action: string;
  lot: string;
  result: 'ESCALATE' | 'OK' | 'Rejected' | 'High risk' | 'Denied';
}

export interface ProductItem {
  name: string;
  family: string;
}

export interface BuyerItem {
  name: string;
  clausesSummary: string;
}

export interface BuyerClause {
  defectType: string;
  severity: 'Critical' | 'Major' | 'Minor';
  clause: string;
}

export interface ModelVersionItem {
  version: string;
  sha256: string;
  classes: string;
  evaluatedOn: string;
  status: 'Active' | 'Inactive';
}

export interface HealthCardItem {
  id: string;
  name: string;
  status: 'Up' | 'Down' | 'OK';
  description: string;
  checkedAt: string;
}

export interface BackupHistoryItem {
  run: string;
  size: string;
  auditChainHead: string;
  status: 'Success' | 'Failed';
}

export const mockAdminUsers: AdminUser[] = [
  {
    id: 'u-1',
    name: 'Admin Root',
    email: 'admin@acme.com',
    role: 'Admin',
    status: 'Active',
    lastLogin: 'Today 09:12',
    isSelf: true,
  },
  {
    id: 'u-2',
    name: 'S. Karim',
    email: 'karim@acme.com',
    role: 'Supervisor',
    status: 'Active',
    lastLogin: 'Today 08:40',
  },
  {
    id: 'u-3',
    name: 'A. Rahman',
    email: 'rahman@acme.com',
    role: 'Inspector',
    status: 'Active',
    lastLogin: 'Today 10:02',
  },
  {
    id: 'u-4',
    name: 'N. Akter',
    email: 'akter@acme.com',
    role: 'Inspector',
    status: 'Locked',
    lastLogin: 'Yesterday',
  },
  {
    id: 'u-5',
    name: 'T. Hasan',
    email: 'hasan@acme.com',
    role: 'Inspector',
    status: 'Disabled',
    lastLogin: '12 Nov',
  },
];

export const mockAuditLogs: AuditLogRow[] = [
  {
    id: 'aud-1',
    time: '18 Nov 10:42',
    user: 'A. Rahman',
    action: 'Decision computed',
    lot: 'LT-2411-018',
    result: 'ESCALATE',
  },
  {
    id: 'aud-2',
    time: '18 Nov 10:31',
    user: 'A. Rahman',
    action: 'Defect confirmed (hole)',
    lot: 'LT-2411-018',
    result: 'OK',
  },
  {
    id: 'aud-3',
    time: '18 Nov 09:58',
    user: 'N. Akter',
    action: 'Upload rejected: corrupt file',
    lot: 'LT-2411-017',
    result: 'Rejected',
  },
  {
    id: 'aud-4',
    time: '18 Nov 09:12',
    user: 'Admin Root',
    action: 'User unlock',
    lot: '—',
    result: 'OK',
  },
  {
    id: 'aud-5',
    time: '17 Nov 16:20',
    user: 'S. Karim',
    action: 'Override ACCEPT → REJECT',
    lot: 'LT-2411-012',
    result: 'High risk',
  },
  {
    id: 'aud-6',
    time: '17 Nov 15:03',
    user: 'N. Akter',
    action: 'Open report (not owner)',
    lot: 'LT-2411-010',
    result: 'Denied',
  },
];

export const mockProductsList: ProductItem[] = [
  { name: 'Single-jersey tee', family: 'Knit' },
  { name: 'Pique polo', family: 'Knit' },
];

export const mockBuyersList: BuyerItem[] = [
  { name: 'Northwind Apparel', clausesSummary: '7 defect types' },
  { name: 'Brightway Retail', clausesSummary: '6 defect types' },
];

export const mockNorthwindClauses: BuyerClause[] = [
  { defectType: 'Hole', severity: 'Critical', clause: '4.2' },
  { defectType: 'Dropped stitch', severity: 'Major', clause: '4.5' },
  { defectType: 'Oil stain', severity: 'Major', clause: '4.7' },
  { defectType: 'Needle line', severity: 'Minor', clause: '5.1' },
];

export const mockModelVersionsList: ModelVersionItem[] = [
  {
    version: 'v1.3.0',
    sha256: '9f2c...a41e',
    classes: '7 defect types',
    evaluatedOn: 'Knit tees, 2 sites',
    status: 'Active',
  },
  {
    version: 'v1.2.1',
    sha256: '71bd...0c97',
    classes: '7 defect types',
    evaluatedOn: 'Knit tees, 1 site',
    status: 'Inactive',
  },
  {
    version: 'v1.1.0',
    sha256: 'c3a8...55d2',
    classes: '6 defect types',
    evaluatedOn: 'Knit tees, 1 site',
    status: 'Inactive',
  },
];

export const mockHealthCards: HealthCardItem[] = [
  {
    id: 'health-1',
    name: 'Inference service',
    status: 'Down',
    description: 'Detector is not responding. Circuit breaker open.',
    checkedAt: 'Checked 1 min ago',
  },
  {
    id: 'health-2',
    name: 'Database',
    status: 'Up',
    description: 'Healthy. 14 ms response.',
    checkedAt: 'Checked 1 min ago',
  },
  {
    id: 'health-3',
    name: 'Disk space',
    status: 'OK',
    description: '61% free. Alert below 15%.',
    checkedAt: 'Checked 1 min ago',
  },
  {
    id: 'health-4',
    name: 'Audit chain',
    status: 'OK',
    description: 'Verified nightly and at report time.',
    checkedAt: 'Checked 02:00 today',
  },
  {
    id: 'health-5',
    name: 'Backup',
    status: 'OK',
    description: 'Last success 02:30. Next 02:30.',
    checkedAt: 'Checked 02:31 today',
  },
  {
    id: 'health-6',
    name: 'Login failures',
    status: 'OK',
    description: '4 in the last hour. No spike.',
    checkedAt: 'Checked 1 min ago',
  },
];

export const mockBackupHistory: BackupHistoryItem[] = [
  {
    run: '18 Nov 02:30',
    size: '412 MB',
    auditChainHead: 'e41a...77f0',
    status: 'Success',
  },
  {
    run: '17 Nov 02:30',
    size: '409 MB',
    auditChainHead: 'b09d...12c3',
    status: 'Success',
  },
  {
    run: '16 Nov 02:30',
    size: '405 MB',
    auditChainHead: '5ac7...9e18',
    status: 'Success',
  },
];
