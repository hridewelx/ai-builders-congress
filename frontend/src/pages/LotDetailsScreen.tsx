import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ChevronLeft,
  Camera,
  Eye,
  FileSpreadsheet,
  PlayCircle,
  Building2,
  Layers,
  History,
} from 'lucide-react';
import { Button } from '../components/Button';
import { OutcomeChip } from '../components/OutcomeChip';
import { StatusChip } from '../components/StatusChip';
import { ProgressBar } from '../components/ProgressBar';
import { Banner } from '../components/Banner';
import { mockLots } from '../mocks';

export const LotDetailsScreen: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  // Find lot from mock data or fallback to LT-2411-018
  const lot = mockLots.find((l) => l.code === id || l.id === id) || mockLots[0];

  const handleComputeDecision = () => {
    navigate(`/lots/${lot.code}/decision`);
  };

  // Fallback history events if none defined
  const historyEvents = lot.history || [
    { title: 'Decision computed', timestamp: 'Today 10:42 · ESCALATE' },
    { title: 'Plan saved (rev 1)', timestamp: 'Yesterday · S. Karim' },
    { title: 'Lot created', timestamp: 'Yesterday · A. Rahman' },
  ];

  return (
    <div className="space-y-6 text-[#0F172A] select-none">
      {/* Top Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-[#64748B]">
        <button
          type="button"
          onClick={() => navigate('/lots')}
          className="hover:text-[#1F4FD8] font-medium flex items-center gap-1"
        >
          <ChevronLeft className="w-3.5 h-3.5" /> Lots
        </button>
        <span>/</span>
        <span className="font-mono font-bold text-[#0F172A]">{lot.code}</span>
      </div>

      {/* Detector Warning Alert if needed */}
      <Banner
        variant="warn"
        title="Not inferred, detector unavailable."
        description="New photos need full manual review. Inspector must inspect every garment surface manually."
      />

      {/* ========================================================= */}
      {/* TWO COLUMNS LAYOUT FOR DESKTOP                            */}
      {/* Left: header, plan, sample progress, history              */}
      {/* Right: recommendation vs final, status chips, actions card*/}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ======================================================= */}
        {/* LEFT COLUMN: Header, Plan, Sample Progress, History     */}
        {/* ======================================================= */}
        <div className="lg:col-span-7 space-y-6">
          {/* 1. Header Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-4">
            <div className="flex items-start justify-between gap-4 pb-3 border-b border-[#F1F5F9]">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-3xl font-black text-[#0F172A] tracking-tight font-mono">
                    {lot.code}
                  </h1>
                  <span className="inline-block px-3 py-0.5 bg-[#E0F2FE] text-[#0369A1] font-bold text-[11.5px] rounded-full uppercase tracking-wider">
                    OPEN
                  </span>
                </div>
                <p className="text-base font-semibold text-[#0F172A] mt-1">
                  {lot.product}
                </p>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Batch: <strong>{lot.pieces.toLocaleString()} pcs</strong> · Shade: {lot.color || 'Navy'}
                </p>
              </div>

              <div className="text-right">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] block">
                  Buyer
                </span>
                <span className="font-bold text-sm text-[#0F172A] flex items-center justify-end gap-1.5 mt-0.5">
                  <Building2 className="w-4 h-4 text-[#1F4FD8]" /> {lot.buyer}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs text-[#64748B]">
              <div>
                <span>Created by: </span>
                <strong className="text-[#0F172A]">{lot.createdBy || 'A. Rahman'}</strong>
              </div>
              <div className="text-right">
                <span>Inspection line: </span>
                <strong className="text-[#0F172A]">Floor Line 2</strong>
              </div>
            </div>
          </div>

          {/* 2. Plan Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#1F4FD8]" />
                <h2 className="text-[16px] font-bold text-[#0F172A]">Sampling Plan</h2>
              </div>
              <button
                type="button"
                onClick={() => navigate(`/lots/${lot.code}/plan`)}
                className="text-xs font-semibold text-[#1F4FD8] hover:underline"
              >
                View plan details →
              </button>
            </div>

            <div className="bg-[#F8FAFC] p-3.5 rounded-[14px] border border-[#E2E8F0] space-y-1.5">
              <div className="flex justify-between items-center text-sm">
                <span className="text-[#64748B]">Plan Summary:</span>
                <span className="font-mono font-bold text-[#0F172A]">
                  {lot.planSummary || 'n 80 · Ac 5 / Re 6 (major)'}
                </span>
              </div>
              <div className="text-xs text-[#64748B] leading-relaxed">
                ANSI/ASQ Z1.4 Normal II single sampling plan approved by Supervisor Karim.
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2.5 text-center text-xs">
              <div className="p-2 rounded-lg bg-slate-50 border border-slate-200/80">
                <span className="text-[#64748B] block text-[10.5px]">Critical</span>
                <strong className="font-mono text-[#0F172A]">Ac 0 / Re 1</strong>
              </div>
              <div className="p-2 rounded-lg bg-slate-50 border border-slate-200/80">
                <span className="text-[#64748B] block text-[10.5px]">Major</span>
                <strong className="font-mono text-[#0F172A]">Ac 5 / Re 6</strong>
              </div>
              <div className="p-2 rounded-lg bg-slate-50 border border-slate-200/80">
                <span className="text-[#64748B] block text-[10.5px]">Minor</span>
                <strong className="font-mono text-[#0F172A]">Ac 7 / Re 9</strong>
              </div>
            </div>
          </div>

          {/* 3. Sample Progress Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#F1F5F9]">
              <div>
                <h2 className="text-[16px] font-bold text-[#0F172A]">Sample Progress</h2>
                <p className="text-xs text-[#64748B]">
                  Required units registered against lot size
                </p>
              </div>
              <span className="text-[#1F4FD8] font-bold font-mono text-sm bg-[#EAF0FF] px-3 py-1 rounded-full">
                {lot.registeredUnits || 74} / {lot.requiredUnits || 80}
              </span>
            </div>

            {/* Blue Progress Bar */}
            <ProgressBar
              value={lot.registeredUnits || 74}
              max={lot.requiredUnits || 80}
              variant="blue"
              height="default"
            />

            {/* 3 Metrics: Required, Registered, Reviewed */}
            <div className="grid grid-cols-3 gap-3 text-center pt-1">
              <div className="bg-[#F8FAFC] p-3 rounded-[14px] border border-[#E2E8F0]">
                <div className="text-[26px] font-black text-[#0F172A] leading-none mb-1">
                  {lot.requiredUnits || 80}
                </div>
                <div className="text-[12px] font-medium text-[#64748B]">Required</div>
              </div>
              <div className="bg-[#F8FAFC] p-3 rounded-[14px] border border-[#E2E8F0]">
                <div className="text-[26px] font-black text-[#0F172A] leading-none mb-1">
                  {lot.registeredUnits || 74}
                </div>
                <div className="text-[12px] font-medium text-[#64748B]">Registered</div>
              </div>
              <div className="bg-[#F8FAFC] p-3 rounded-[14px] border border-[#E2E8F0]">
                <div className="text-[26px] font-black text-[#0F172A] leading-none mb-1">
                  {lot.reviewedUnits || 62}
                </div>
                <div className="text-[12px] font-medium text-[#64748B]">Reviewed</div>
              </div>
            </div>
          </div>

          {/* 4. History Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-[#F1F5F9]">
              <History className="w-4 h-4 text-[#1F4FD8]" />
              <h2 className="text-[16px] font-bold text-[#0F172A]">Lot History Log</h2>
            </div>

            <div className="space-y-4 pl-2">
              {historyEvents.map((event, idx) => (
                <div key={idx} className="relative flex items-start gap-3 text-left">
                  {/* Timeline connecting line */}
                  {idx < historyEvents.length - 1 && (
                    <div className="absolute top-4 left-[9px] w-0.5 h-10 bg-[#E2E8F0]" />
                  )}

                  {/* Milestone dot */}
                  <div className="w-5 h-5 rounded-full bg-[#EAF0FF] border-2 border-[#1F4FD8] flex items-center justify-center shrink-0 z-10">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#1F4FD8]" />
                  </div>

                  <div className="space-y-0.5 text-xs">
                    <div className="font-bold text-[13.5px] text-[#0F172A]">
                      {event.title}
                    </div>
                    <div className="text-[#64748B]">{event.timestamp}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ======================================================= */}
        {/* RIGHT COLUMN: Recommendation vs Final, Status Chips,    */}
        {/*               Action Buttons as a Card (Not Bottom Bar) */}
        {/* ======================================================= */}
        <div className="lg:col-span-5 space-y-6">
          {/* 1. Recommendation vs Final Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-4">
            <h2 className="text-[16px] font-bold text-[#0F172A] pb-2 border-b border-[#F1F5F9]">
              Recommendation vs Final Disposition
            </h2>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#F8FAFC] p-3.5 rounded-[14px] border border-[#E2E8F0] space-y-1.5">
                <span className="text-[11.5px] font-semibold uppercase tracking-wider text-[#64748B] block">
                  Sampling Engine
                </span>
                <OutcomeChip outcome={lot.engineRecommendation || 'ESCALATE'} size="default" showDot />
              </div>

              <div className="bg-[#F8FAFC] p-3.5 rounded-[14px] border border-[#E2E8F0] space-y-1.5">
                <span className="text-[11.5px] font-semibold uppercase tracking-wider text-[#64748B] block">
                  Final Disposition
                </span>
                <span className="inline-block text-[12px] font-semibold text-[#475569] bg-[#E2E8F0] px-3 py-1 rounded-full">
                  {lot.finalDisposition || 'Not decided'}
                </span>
              </div>
            </div>

            <Banner
              variant="escalate"
              description={lot.escalationNote || 'Possible critical defect not yet confirmed. A person must decide this case.'}
            />
          </div>

          {/* 2. Status Chips Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
              <h2 className="text-[16px] font-bold text-[#0F172A]">Sample Status Chips</h2>
              <span className="text-xs text-[#64748B]">Unit Proposal Flags</span>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              <StatusChip
                label="not inferred"
                count={lot.notInferredCount ?? 3}
                variant="neutral"
              />
              <StatusChip
                label="retake"
                count={lot.retakeCount ?? 2}
                variant="warning"
              />
              <StatusChip
                label="escalate"
                count={lot.escalateCount ?? 1}
                variant="escalate"
              />
              <StatusChip
                label="uncalibrated"
                variant="uncalibrated"
              />
            </div>

            <p className="text-xs text-[#64748B] pt-1 leading-relaxed">
              Model detection scores are uncalibrated. Flags indicate units requiring manual inspector verification or image recapture.
            </p>
          </div>

          {/* 3. ACTION BUTTONS AS A CARD (NOT A BOTTOM BAR!) */}
          <div className="bg-white rounded-[22px] border-2 border-[#1F4FD8]/20 shadow-md p-6 space-y-4">
            <div>
              <h2 className="text-[17px] font-black text-[#0B1F5C] tracking-tight">
                Lot Actions
              </h2>
              <p className="text-xs text-[#64748B] mt-0.5">
                Primary inspection and decision evaluation workflows
              </p>
            </div>

            <div className="space-y-3 pt-1">
              {/* Action 1: Add Unit */}
              <Button
                variant="primary"
                fullWidth
                size="default"
                leftIcon={<Camera className="w-4 h-4" />}
                onClick={() => navigate(`/lots/${lot.code}/capture`)}
              >
                Add unit (Capture photo)
              </Button>

              {/* Action 2: Review */}
              <Button
                variant="secondary"
                fullWidth
                size="default"
                leftIcon={<Eye className="w-4 h-4" />}
                onClick={() => navigate(`/lots/${lot.code}/review`)}
              >
                Review ({lot.reviewedUnits || 62}/{lot.registeredUnits || 74})
              </Button>

              {/* Action 3: Sampling Plan */}
              <Button
                variant="outline"
                fullWidth
                size="default"
                leftIcon={<FileSpreadsheet className="w-4 h-4" />}
                onClick={() => navigate(`/lots/${lot.code}/plan`)}
              >
                Sampling plan
              </Button>

              {/* Action 4: Compute Decision */}
              <Button
                variant="compute"
                fullWidth
                size="default"
                leftIcon={<PlayCircle className="w-4 h-4" />}
                onClick={handleComputeDecision}
              >
                Compute decision
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
