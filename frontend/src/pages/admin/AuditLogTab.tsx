import React from 'react';
import { Download, ChevronDown, ShieldCheck } from 'lucide-react';
import { Button } from '../../components/Button';
import { mockAuditLogs } from '../../mocks';

interface AuditLogTabProps {
  isSupervisor?: boolean; // When true: read-only, NO export button
}

export const AuditLogTab: React.FC<AuditLogTabProps> = ({ isSupervisor = false }) => {
  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-black text-[#0F172A] tracking-tight">Audit log</h1>
          <p className="text-[13px] text-[#64748B] mt-0.5">
            Append-only record of every action. Integrity is checked nightly and at report time.
          </p>
        </div>

        {/* Rule: Supervisor sees only the Audit tab, read-only, no Export */}
        {!isSupervisor && (
          <Button
            variant="primary"
            leftIcon={<Download className="w-4 h-4" />}
            onClick={() => alert('Exporting audit log as CSV / JSON (action audited)...')}
          >
            Export CSV / JSON
          </Button>
        )}
      </div>

      {/* Filters Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <button className="h-10 px-3.5 bg-white rounded-[10px] border border-[#E2E8F0] text-[13px] text-[#0F172A] flex items-center gap-2 hover:border-[#CBD5E1]">
            <span>Any lot</span>
            <ChevronDown className="w-3.5 h-3.5 text-[#94A3B8]" />
          </button>

          <button className="h-10 px-3.5 bg-white rounded-[10px] border border-[#E2E8F0] text-[13px] text-[#0F172A] flex items-center gap-2 hover:border-[#CBD5E1]">
            <span>Any user</span>
            <ChevronDown className="w-3.5 h-3.5 text-[#94A3B8]" />
          </button>

          <button className="h-10 px-3.5 bg-white rounded-[10px] border border-[#E2E8F0] text-[13px] text-[#0F172A] flex items-center gap-2 hover:border-[#CBD5E1]">
            <span>Any action</span>
            <ChevronDown className="w-3.5 h-3.5 text-[#94A3B8]" />
          </button>

          <button className="h-10 px-3.5 bg-white rounded-[10px] border border-[#E2E8F0] text-[13px] text-[#0F172A] flex items-center gap-2 hover:border-[#CBD5E1]">
            <span>Last 7 days</span>
            <ChevronDown className="w-3.5 h-3.5 text-[#94A3B8]" />
          </button>
        </div>

        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#DCFCE7] text-[#15803D] text-[12px] font-bold border border-[#BBF7D0]">
          <ShieldCheck className="w-4 h-4" />
          <span>Chain verified 02:00</span>
        </div>
      </div>

      {/* Audit Table Card */}
      <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC]/50 text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
                <th className="py-3 px-4">TIME</th>
                <th className="py-3 px-4">USER</th>
                <th className="py-3 px-4">ACTION</th>
                <th className="py-3 px-4">LOT</th>
                <th className="py-3 px-4 text-right">RESULT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {mockAuditLogs.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="py-3.5 px-4 text-[#64748B] font-mono text-[12.5px] whitespace-nowrap">
                    {row.time}
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-[#0F172A] whitespace-nowrap">
                    {row.user}
                  </td>
                  <td className="py-3.5 px-4 text-[#0F172A] font-medium">{row.action}</td>
                  <td className="py-3.5 px-4 font-mono text-[12.5px] text-[#475569] whitespace-nowrap">
                    {row.lot}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                        row.result === 'OK'
                          ? 'bg-[#DCFCE7] text-[#15803D]'
                          : row.result === 'ESCALATE'
                          ? 'bg-[#EDE9FE] text-[#6D28D9]'
                          : row.result === 'Rejected'
                          ? 'bg-[#FEF3C7] text-[#B45309]'
                          : 'bg-[#FEE2E2] text-[#B91C1C]'
                      }`}
                    >
                      {row.result}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="text-[12px] text-[#64748B] pt-1">
        Rows cannot be edited or deleted. Text is escaped. Export is itself audited.
      </div>
    </div>
  );
};
