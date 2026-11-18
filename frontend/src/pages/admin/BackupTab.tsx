import React from 'react';
import { Clock } from 'lucide-react';
import { mockBackupHistory } from '../../mocks';

export const BackupTab: React.FC = () => {
  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-black text-[#0F172A] tracking-tight">Backup</h1>
        <p className="text-[13px] text-[#64748B] mt-0.5">
          Nightly encrypted backup. Restore is done by the host operator, outside the app.
        </p>
      </div>

      {/* 3 Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs p-5">
          <div className="text-[12.5px] text-[#64748B] font-medium mb-1">Last backup</div>
          <div className="text-[22px] font-black text-[#0F172A] leading-tight mb-2">
            Today 02:30
          </div>
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#DCFCE7] text-[#15803D]">
            Success
          </span>
        </div>

        <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs p-5">
          <div className="text-[12.5px] text-[#64748B] font-medium mb-1">Retention</div>
          <div className="text-[22px] font-black text-[#0F172A] leading-tight mb-1">
            7 daily + 4 weekly
          </div>
          <div className="text-[12px] text-[#64748B]">1 off-machine copy</div>
        </div>

        <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs p-5">
          <div className="text-[12.5px] text-[#64748B] font-medium mb-1">Last restore drill</div>
          <div className="text-[22px] font-black text-[#0F172A] leading-tight mb-2">
            3 Nov 2026
          </div>
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#DCFCE7] text-[#15803D]">
            Passed
          </span>
        </div>
      </div>

      {/* Backups Table Card */}
      <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC]/50 text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
                <th className="py-3 px-4">RUN</th>
                <th className="py-3 px-4">SIZE</th>
                <th className="py-3 px-4">AUDIT-CHAIN HEAD</th>
                <th className="py-3 px-4 text-right">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {mockBackupHistory.map((item) => (
                <tr key={item.run} className="hover:bg-slate-50/60 transition-colors">
                  <td className="py-3.5 px-4 font-mono text-[12.5px] text-[#0F172A] whitespace-nowrap">
                    {item.run}
                  </td>
                  <td className="py-3.5 px-4 text-[#475569] whitespace-nowrap">{item.size}</td>
                  <td className="py-3.5 px-4 font-mono text-[12.5px] text-[#64748B] whitespace-nowrap">
                    {item.auditChainHead}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <span className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-[#DCFCE7] text-[#15803D]">
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Warning Banner */}
      <div className="bg-[#FEF3C7] border border-[#FDE68A] rounded-[14px] p-3.5 flex items-start gap-2.5 text-left">
        <Clock className="w-4 h-4 text-[#B45309] shrink-0 mt-0.5" />
        <div className="text-[12.5px] text-[#92400E] leading-relaxed">
          Monthly restore drill is due 3 Dec. There is no restore button in the app by design.
        </div>
      </div>
    </div>
  );
};
