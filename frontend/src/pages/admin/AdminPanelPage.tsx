import React, { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Users,
  ClipboardList,
  Box,
  Cpu,
  Activity,
  HardDrive,
} from 'lucide-react';
import { useRole } from '../../context';
import { UsersTab } from './UsersTab';
import { AuditLogTab } from './AuditLogTab';
import { ProductsBuyersTab } from './ProductsBuyersTab';
import { ModelVersionsTab } from './ModelVersionsTab';
import { SystemHealthTab } from './SystemHealthTab';
import { BackupTab } from './BackupTab';
import { Forbidden403 } from './Forbidden403';

export type AdminTabId =
  | 'users'
  | 'audit'
  | 'products-buyers'
  | 'models'
  | 'health'
  | 'backup';

export const AdminPanelPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentRole } = useRole();

  // Role Checks
  const isInspector = currentRole === 'Inspector';
  const isSupervisor = currentRole === 'Supervisor';
  const isAdmin = currentRole === 'Admin';

  // Active Tab from URL search param (?tab=...)
  const rawTab = searchParams.get('tab') as AdminTabId | null;
  const activeTab: AdminTabId = isSupervisor
    ? 'audit'
    : rawTab && ['users', 'audit', 'products-buyers', 'models', 'health', 'backup'].includes(rawTab)
    ? rawTab
    : 'users';

  // Ensure Supervisor is locked to audit tab in URL
  useEffect(() => {
    if (isSupervisor && rawTab !== 'audit') {
      setSearchParams({ tab: 'audit' }, { replace: true });
    }
  }, [isSupervisor, rawTab, setSearchParams]);

  const handleTabChange = (tabId: AdminTabId) => {
    setSearchParams({ tab: tabId });
  };

  // Nav tab definitions matching 12-17
  const allNavItems = [
    { id: 'users' as AdminTabId, label: 'Users', icon: Users },
    { id: 'audit' as AdminTabId, label: 'Audit log', icon: ClipboardList },
    { id: 'products-buyers' as AdminTabId, label: 'Products & Buyers', icon: Box },
    { id: 'models' as AdminTabId, label: 'Model versions', icon: Cpu },
    { id: 'health' as AdminTabId, label: 'System health', icon: Activity },
    { id: 'backup' as AdminTabId, label: 'Backup', icon: HardDrive },
  ];

  // Rule: Supervisor sees only the Audit tab
  const visibleNavItems = isSupervisor
    ? allNavItems.filter((item) => item.id === 'audit')
    : allNavItems;

  if (isInspector) {
    /* Rule: Inspector opening this route sees a 403 page */
    return (
      <div className="py-12 flex items-center justify-center">
        <Forbidden403 />
      </div>
    );
  }

  return (
    <div className="space-y-6 text-[#0F172A] select-none">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-black text-[#0F172A] tracking-tight">
              Administration & Audit Center
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-purple-100 text-purple-800">
              {isAdmin ? 'System Admin' : 'Supervisor Audit Access'}
            </span>
          </div>
          <p className="text-sm text-[#64748B] mt-0.5">
            Manage factory floor accounts, inspect tamper-evident audit logs, and monitor infrastructure
          </p>
        </div>
      </div>

      {/* Main Admin Card with Sub-Navigation Rail / Tabs */}
      <div className="bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm overflow-hidden flex flex-col md:flex-row min-h-[640px]">
        {/* Left Sub-Rail */}
        <aside className="w-full md:w-60 bg-white border-b md:border-b-0 md:border-r border-[#E2E8F0] p-4 flex flex-col justify-between shrink-0 select-none">
          <div className="space-y-4">
            <div className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] px-3">
              Admin Sections
            </div>

            <nav className="space-y-1">
              {visibleNavItems.map((item) => {
                const isActive = activeTab === item.id;
                const Icon = item.icon;

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleTabChange(item.id)}
                    className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-[12px] text-[13.5px] font-medium transition-all text-left ${
                      isActive
                        ? 'bg-[#EAF0FF] text-[#1F4FD8] font-bold shadow-xs'
                        : 'text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-[#1F4FD8]' : 'text-[#64748B]'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Quick Notice */}
          <div className="pt-4 border-t border-[#F1F5F9] mt-6 text-xs text-[#64748B] px-3 space-y-1">
            <div className="font-semibold text-[#0F172A]">Access Mode</div>
            <p>
              {isAdmin
                ? 'Full admin privileges. Actions are permanently signed into the audit log.'
                : 'Read-only audit view. Export and user management locked.'}
            </p>
          </div>
        </aside>

        {/* Tab Content Panel */}
        <main className="flex-1 p-6 md:p-8 bg-[#F8FAFC] overflow-y-auto min-w-0">
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'audit' && (
            /* Rule: Supervisor sees only Audit tab, read-only, no Export */
            <AuditLogTab isSupervisor={isSupervisor} />
          )}
          {activeTab === 'products-buyers' && <ProductsBuyersTab />}
          {activeTab === 'models' && <ModelVersionsTab />}
          {activeTab === 'health' && <SystemHealthTab />}
          {activeTab === 'backup' && <BackupTab />}
        </main>
      </div>
    </div>
  );
};
