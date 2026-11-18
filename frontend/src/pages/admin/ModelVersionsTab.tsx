import React from 'react';
import { Info } from 'lucide-react';
import { mockModelVersionsList } from '../../mocks';

export const ModelVersionsTab: React.FC = () => {
  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-black text-[#0F172A] tracking-tight">Model versions</h1>
        <p className="text-[13px] text-[#64748B] mt-0.5">
          Detector models are activated on the host. Old decisions keep their original version.
        </p>
      </div>

      {/* Model Versions Table Card */}
      <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC]/50 text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
                <th className="py-3 px-4">VERSION</th>
                <th className="py-3 px-4">SHA-256</th>
                <th className="py-3 px-4">CLASSES</th>
                <th className="py-3 px-4">EVALUATED ON</th>
                <th className="py-3 px-4 text-right">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {mockModelVersionsList.map((m) => (
                <tr key={m.version} className="hover:bg-slate-50/60 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-[#0F172A] whitespace-nowrap">
                    {m.version}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-[12.5px] text-[#475569] whitespace-nowrap">
                    {m.sha256}
                  </td>
                  <td className="py-3.5 px-4 text-[#0F172A] whitespace-nowrap">{m.classes}</td>
                  <td className="py-3.5 px-4 text-[#64748B] whitespace-nowrap">{m.evaluatedOn}</td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                        m.status === 'Active'
                          ? 'bg-[#DCFCE7] text-[#15803D]'
                          : 'bg-[#F1F5F9] text-[#64748B]'
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Details Card */}
      <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs p-5 space-y-3">
        <h2 className="text-[15px] font-bold text-[#0F172A]">v1.3.0 details</h2>
        <div className="space-y-2 text-[13px]">
          <div className="flex justify-between items-center">
            <span className="text-[#64748B]">Training data</span>
            <span className="font-bold text-[#0F172A]">4,200 labelled photos, Oct 2026</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#64748B]">Evaluation report</span>
            <span className="font-bold text-[#0F172A] font-mono">EVAL-2026-11</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#64748B]">Score meaning</span>
            <span className="font-bold text-[#0F172A]">Uncalibrated</span>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-[#E0F2FE] border border-[#BAE6FD]/80 rounded-[14px] p-3.5 flex items-start gap-2.5 text-left">
        <Info className="w-4 h-4 text-[#0369A1] shrink-0 mt-0.5" />
        <div className="text-[12.5px] text-[#075985] leading-relaxed">
          No model upload or download in the app. Activation happens on the host and is audited.
        </div>
      </div>
    </div>
  );
};
