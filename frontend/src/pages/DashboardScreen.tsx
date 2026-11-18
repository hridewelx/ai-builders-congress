import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Clock, AlertCircle, ShieldAlert, Plus, ArrowUpRight } from 'lucide-react';
import { Banner } from '../components/Banner';
import { OutcomeChip } from '../components/OutcomeChip';
import { Button } from '../components/Button';
import { useRole } from '../context';
import {
  mockDashboardMetrics,
  mockAttentionItems,
  mockRecentDecisions,
} from '../mocks';

export const DashboardScreen: React.FC = () => {
  const navigate = useNavigate();
  const { currentRole } = useRole();

  return (
    <div className="space-y-6 text-[#0F172A] select-none">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#E2E8F0]">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-[#0F172A] tracking-tight">
            Dashboard
          </h1>
          <p className="text-sm text-[#64748B] mt-0.5">
            Acme Knitwear Ltd. · Floor 2 Inspection Control Center
          </p>
        </div>

        {currentRole !== 'Admin' && (
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => navigate('/lots/new')}
          >
            New lot
          </Button>
        )}
      </div>

      {/* Detector Warning Banner */}
      <Banner
        variant="warn"
        title={mockDashboardMetrics.detectorMessage.title}
        description={mockDashboardMetrics.detectorMessage.description}
        actionLabel="Review fallback protocol"
        onAction={() => alert('Fallback: inspectors must examine every garment surface manually.')}
      />

      {/* ========================================================= */}
      {/* 3 KPI CARDS IN ONE ROW (Grid 3 cols on desktop)           */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* KPI 1: Open Lots */}
        <div
          onClick={() => navigate('/lots')}
          className="group bg-white p-6 rounded-[20px] border border-[#E2E8F0] shadow-xs hover:border-[#1F4FD8]/40 hover:shadow-md transition-all cursor-pointer relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#1F4FD8]" />
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-bold uppercase tracking-wider text-[#64748B]">
              Open Lots
            </span>
            <div className="w-9 h-9 rounded-xl bg-[#EAF0FF] flex items-center justify-center text-[#1F4FD8] group-hover:scale-110 transition-transform">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="text-[38px] font-black leading-tight text-[#0F172A] mt-3">
            {mockDashboardMetrics.openLotsCount}
          </div>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#F1F5F9] text-[12px] text-[#64748B]">
            <span>Active on floor lines</span>
            <span className="text-[#1F4FD8] font-semibold flex items-center gap-0.5">
              View lots <ArrowUpRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </div>

        {/* KPI 2: On HOLD */}
        <div
          onClick={() => navigate('/lots')}
          className="group bg-white p-6 rounded-[20px] border border-[#E2E8F0] shadow-xs hover:border-[#B45309]/40 hover:shadow-md transition-all cursor-pointer relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#B45309]" />
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-bold uppercase tracking-wider text-[#64748B]">
              On HOLD
            </span>
            <div className="w-9 h-9 rounded-xl bg-[#FEF3C7] flex items-center justify-center text-[#B45309] group-hover:scale-110 transition-transform">
              <AlertCircle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-[38px] font-black leading-tight text-[#B45309] mt-3">
            {mockDashboardMetrics.onHoldCount}
          </div>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#F1F5F9] text-[12px] text-[#64748B]">
            <span>Awaiting plan configuration</span>
            <span className="text-[#B45309] font-semibold flex items-center gap-0.5">
              Resolve hold <ArrowUpRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </div>

        {/* KPI 3: ESCALATE */}
        <div
          onClick={() => navigate('/lots')}
          className="group bg-white p-6 rounded-[20px] border border-[#E2E8F0] shadow-xs hover:border-[#6D28D9]/40 hover:shadow-md transition-all cursor-pointer relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#6D28D9]" />
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-bold uppercase tracking-wider text-[#64748B]">
              ESCALATE
            </span>
            <div className="w-9 h-9 rounded-xl bg-[#EDE9FE] flex items-center justify-center text-[#6D28D9] group-hover:scale-110 transition-transform">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="text-[38px] font-black leading-tight text-[#6D28D9] mt-3">
            {mockDashboardMetrics.escalateCount}
          </div>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#F1F5F9] text-[12px] text-[#64748B]">
            <span>A person must decide</span>
            <span className="text-[#6D28D9] font-semibold flex items-center gap-0.5">
              Review queue <ArrowUpRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* NEEDS ATTENTION & RECENT DECISIONS SIDE BY SIDE (2 COLS)  */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Column 1: Needs Attention Card */}
        <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 text-left flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center pb-4 mb-3 border-b border-[#F1F5F9]">
              <div>
                <h2 className="text-[18px] font-bold text-[#0F172A] tracking-tight">
                  Needs attention
                </h2>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Lots requiring sampling, inspection, or decision
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/lots')}
                className="text-[13px] font-semibold text-[#1F4FD8] hover:underline"
              >
                See all lots
              </button>
            </div>

            <div className="divide-y divide-[#F1F5F9]">
              {mockAttentionItems.map((item) => (
                <div
                  key={item.code}
                  onClick={() => navigate(`/lots/${item.code}`)}
                  className="py-3.5 first:pt-0 last:pb-0 flex items-center justify-between cursor-pointer hover:bg-slate-50/80 -mx-2 px-3 rounded-xl transition-all group"
                >
                  <div className="space-y-0.5">
                    <div className="font-bold text-[15px] text-[#0F172A] group-hover:text-[#1F4FD8] transition-colors leading-tight flex items-center gap-2">
                      <span className="font-mono">{item.code}</span>
                      <span className="text-xs text-[#CBD5E1]">·</span>
                      <span className="text-xs font-semibold text-[#475569]">{item.product}</span>
                    </div>
                    <div className="text-[12px] text-[#64748B]">
                      {item.buyer} · Line 2 Inspection Station
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <OutcomeChip outcome={item.status} size="sm" showDot />
                    <ChevronRight className="w-4 h-4 text-[#94A3B8] group-hover:text-[#1F4FD8] group-hover:translate-x-0.5 transition-all" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-[#F1F5F9] flex items-center justify-between text-xs text-[#64748B]">
            <span>Showing {mockAttentionItems.length} priority items</span>
            <button
              type="button"
              onClick={() => navigate('/lots')}
              className="font-semibold text-[#1F4FD8] hover:underline"
            >
              Open lot queue →
            </button>
          </div>
        </div>

        {/* Column 2: Recent Decisions Card */}
        <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 text-left flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center pb-4 mb-3 border-b border-[#F1F5F9]">
              <div>
                <h2 className="text-[18px] font-bold text-[#0F172A] tracking-tight">
                  Recent decisions
                </h2>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Evaluated by deterministic sampling engine
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/lots')}
                className="text-[13px] font-semibold text-[#1F4FD8] hover:underline"
              >
                Lot list
              </button>
            </div>

            <div className="divide-y divide-[#F1F5F9]">
              {mockRecentDecisions.map((decision) => (
                <div
                  key={decision.code}
                  onClick={() => navigate(`/lots/${decision.code}/decision`)}
                  className="py-3.5 first:pt-0 last:pb-0 flex items-center justify-between cursor-pointer hover:bg-slate-50/80 -mx-2 px-3 rounded-xl transition-all group"
                >
                  <div className="space-y-0.5">
                    <div className="font-bold text-[15px] text-[#0F172A] group-hover:text-[#1F4FD8] transition-colors leading-tight font-mono">
                      {decision.code}
                    </div>
                    <div className="text-[12px] text-[#64748B]">
                      {decision.dateStr} · Evaluator: <strong>{decision.reviewer}</strong>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <OutcomeChip outcome={decision.outcome} size="sm" showDot />
                    <ChevronRight className="w-4 h-4 text-[#94A3B8] group-hover:text-[#1F4FD8] group-hover:translate-x-0.5 transition-all" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-[#F1F5F9] flex items-center justify-between text-xs text-[#64748B]">
            <span>Deterministic engine v1.3</span>
            <button
              type="button"
              onClick={() => navigate('/lots')}
              className="font-semibold text-[#1F4FD8] hover:underline"
            >
              Browse decision register →
            </button>
          </div>
        </div>
      </div>

      {/* Mandatory Floor Footnote */}
      <div className="pt-2 text-center text-[12px] text-[#64748B] leading-relaxed max-w-xl mx-auto">
        Governing principle: AI proposes defects. Humans confirm defects. Deterministic sampling engine decides.
      </div>
    </div>
  );
};
