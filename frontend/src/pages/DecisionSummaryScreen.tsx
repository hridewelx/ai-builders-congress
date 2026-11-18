import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ChevronLeft,
  FileText,
} from 'lucide-react';
import { Button } from '../components/Button';
import { OutcomeChip } from '../components/OutcomeChip';
import { mockDecisionSummary } from '../mocks';

export const DecisionSummaryScreen: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const lotId = id || 'LT-2411-018';

  // Supervisor override state
  const [overrideOutcome, setOverrideOutcome] = useState<'ACCEPT' | 'REJECT'>('REJECT');
  const [overrideReason, setOverrideReason] = useState('Reject due to clause non-compliance');

  // Rule: Supervisor override needs a reason of at least 20 characters
  const reasonLen = overrideReason.trim().length;
  const isReasonValid = reasonLen >= 20;

  const handleOverride = () => {
    if (!isReasonValid) {
      alert('Supervisor override requires a reason of at least 20 characters.');
      return;
    }
    alert(`Supervisor override saved with disposition: ${overrideOutcome}`);
    navigate(`/lots/${lotId}/report`);
  };

  return (
    <div className="space-y-6 text-[#0F172A] select-none">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/lots/${lotId}`)}
            className="p-2 rounded-xl border border-[#E2E8F0] hover:bg-slate-100 text-[#0F172A] transition-colors"
            title="Back to lot details"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-black text-[#0F172A] tracking-tight">
                Lot Decision Summary
              </h1>
              <span className="font-mono text-sm font-bold bg-[#EAF0FF] text-[#1F4FD8] px-2.5 py-0.5 rounded-full">
                {lotId}
              </span>
            </div>
            <p className="text-sm text-[#64748B] mt-0.5">
              Deterministic sampling engine recommendation and supervisory audit
            </p>
          </div>
        </div>

        <Button
          variant="primary"
          size="sm"
          leftIcon={<FileText className="w-4 h-4" />}
          onClick={() => navigate(`/lots/${lotId}/report`)}
        >
          View Full Report
        </Button>
      </div>

      {/* ========================================================= */}
      {/* 2-COLUMN LAYOUT:                                          */}
      {/* Left: outcome card and per-class table                    */}
      {/* Right: reason codes and Supervisor override               */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ======================================================= */}
        {/* LEFT COLUMN: Outcome Card and Per-Class Table           */}
        {/* ======================================================= */}
        <div className="lg:col-span-7 space-y-6">
          {/* 1. Outcome Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-7 text-center relative overflow-hidden space-y-3.5">
            <div className="absolute top-0 left-0 right-0 h-1.5 bg-[#B91C1C]" />

            <div className="text-[13px] font-bold uppercase tracking-wider text-[#64748B]">
              Engine Recommendation
            </div>

            <h2 className="text-[44px] font-black text-[#B91C1C] tracking-tight leading-none">
              {mockDecisionSummary.recommendation}
            </h2>

            <p className="text-[15px] text-[#0F172A] font-semibold max-w-md mx-auto">
              {mockDecisionSummary.recommendationDetail}
            </p>

            <div className="flex flex-wrap items-center justify-center gap-2.5 pt-2">
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#EAF0FF] text-[#0B1F5C]">
                uncalibrated model v1.3.0
              </span>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#FEE2E2] text-[#B91C1C]">
                High-risk if overridden
              </span>
            </div>
          </div>

          {/* 2. Per-Class Table */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
              <h3 className="text-[17px] font-bold text-[#0F172A]">
                Defect Conformance by Class
              </h3>
              <span className="text-xs text-[#64748B]">
                Sample n=80 per class
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[500px]">
                <thead>
                  <tr className="border-b border-[#E2E8F0] text-[11.5px] font-bold text-[#64748B] uppercase tracking-wider bg-[#F8FAFC]">
                    <th className="py-3 px-4">Class</th>
                    <th className="py-3 px-3 text-center">n</th>
                    <th className="py-3 px-3 text-center">Ac</th>
                    <th className="py-3 px-3 text-center">Re</th>
                    <th className="py-3 px-4 text-center">Defect Count</th>
                    <th className="py-3 px-4 text-right">Result</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F1F5F9] text-sm">
                  {mockDecisionSummary.classes.map((cls) => {
                    const isPass = cls.status === 'PASS';
                    return (
                      <tr key={cls.classType} className="hover:bg-slate-50/60">
                        <td className="py-3.5 px-4 font-bold text-[#0F172A]">
                          {cls.classType}
                        </td>
                        <td className="py-3.5 px-3 text-center font-mono text-[#64748B]">
                          {cls.n}
                        </td>
                        <td className="py-3.5 px-3 text-center font-mono text-[#15803D] font-bold">
                          {cls.ac}
                        </td>
                        <td className="py-3.5 px-3 text-center font-mono text-[#B91C1C] font-bold">
                          {cls.re}
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono font-bold text-[#0F172A]">
                          {cls.count}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <OutcomeChip outcome={isPass ? 'ACCEPT' : 'REJECT'} size="sm" showDot />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="pt-2 text-xs text-[#64748B] leading-relaxed border-t border-[#F1F5F9]">
              Re limits exceeded in Major Defect class (6 defects found $\ge$ Re limit 6).
            </div>
          </div>
        </div>

        {/* ======================================================= */}
        {/* RIGHT COLUMN: Reason Codes and Supervisor Override      */}
        {/* ======================================================= */}
        <div className="lg:col-span-5 space-y-6">
          {/* 1. Reason Codes Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-3.5 text-left">
            <h3 className="text-[16px] font-bold text-[#0F172A] pb-2 border-b border-[#F1F5F9]">
              Reason Codes & Precedence
            </h3>

            <div className="space-y-1.5">
              <span className="text-xs font-bold text-[#64748B] uppercase tracking-wider block">
                Applicable Reason Code
              </span>
              <span className="inline-block px-3 py-1 rounded-lg text-xs font-mono font-bold bg-[#EAF0FF] text-[#0B1F5C] border border-[#1F4FD8]/20">
                {mockDecisionSummary.reasonCode}
              </span>
            </div>

            <div className="space-y-1 text-xs text-[#64748B] leading-relaxed pt-1">
              <p>
                <strong>Assumption:</strong> {mockDecisionSummary.planAssumption}
              </p>
              <p>
                <strong>Model Version:</strong> {mockDecisionSummary.modelVersion} (uncalibrated)
              </p>
              <p className="text-[11.5px] text-[#475569] pt-1">
                <strong>Precedence rule:</strong> ESCALATE over HOLD over ACCEPT/REJECT.
              </p>
            </div>
          </div>

          {/* 2. Supervisor Override Card */}
          <div className="bg-white rounded-[22px] border-2 border-amber-300 shadow-sm p-6 space-y-4 text-left">
            <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
              <div>
                <h3 className="text-[17px] font-black text-[#0F172A]">Supervisor Override</h3>
                <p className="text-xs text-[#64748B]">Audited supervisory action</p>
              </div>
              <span className="text-[11px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800 px-2.5 py-0.5 rounded-full border border-amber-300/60">
                Audited
              </span>
            </div>

            {/* Disposition Choice */}
            <div className="space-y-2">
              <label className="text-[13px] font-bold text-[#0F172A] block">
                Override Disposition
              </label>
              <div className="grid grid-cols-2 gap-3">
                {(['ACCEPT', 'REJECT'] as const).map((outcome) => {
                  const isSelected = overrideOutcome === outcome;
                  return (
                    <button
                      key={outcome}
                      type="button"
                      onClick={() => setOverrideOutcome(outcome)}
                      className={`py-2 px-3 rounded-[12px] text-sm font-bold border-2 transition-all ${
                        isSelected
                          ? outcome === 'ACCEPT'
                            ? 'bg-[#DCFCE7] text-[#15803D] border-[#15803D]'
                            : 'bg-[#FEE2E2] text-[#B91C1C] border-[#B91C1C]'
                          : 'bg-white text-[#64748B] border-[#E2E8F0] hover:bg-slate-50'
                      }`}
                    >
                      {outcome}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Override Reason with min 20 chars validation */}
            <div className="space-y-2">
              <div className="flex justify-between items-baseline">
                <label className="text-[13px] font-bold text-[#0F172A]">
                  Mandatory Reason Explanation
                </label>
                <span
                  className={`text-[11px] font-mono font-bold ${
                    isReasonValid ? 'text-emerald-600' : 'text-[#B91C1C]'
                  }`}
                >
                  {reasonLen.toString().padStart(2, '0')}/20 chars min
                </span>
              </div>
              <textarea
                rows={3}
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Give a factual rationale for overriding engine recommendation (minimum 20 characters)..."
                className="w-full p-3 rounded-[12px] border border-[#E2E8F0] text-sm text-[#0F172A] bg-[#F8FAFC] placeholder:text-[#94A3B8] focus:bg-white focus:outline-none focus:border-[#1F4FD8] focus:ring-2 focus:ring-[#EAF0FF] transition-all"
              />
              {!isReasonValid && (
                <p className="text-xs font-semibold text-[#B91C1C]">
                  Please enter at least 20 characters before confirming override.
                </p>
              )}
            </div>

            <Button
              variant="destructive"
              fullWidth
              disabled={!isReasonValid}
              onClick={handleOverride}
            >
              Confirm Supervisor Override
            </Button>
          </div>

          {/* 3. Next Steps Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-3 text-left">
            <h4 className="text-sm font-bold text-[#0F172A]">Next Action</h4>
            <p className="text-xs text-[#64748B] leading-relaxed">
              Generate the immutable, tamper-evident one-page inspection certificate PDF for lot register archival.
            </p>
            <Button
              variant="primary"
              fullWidth
              leftIcon={<FileText className="w-4 h-4" />}
              onClick={() => navigate(`/lots/${lotId}/report`)}
            >
              Generate Inspection Report PDF
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
