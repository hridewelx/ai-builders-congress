import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft, Lock, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Button } from '../components/Button';
import { Banner } from '../components/Banner';
import { useRole } from '../context';
import { mockLots } from '../mocks';

export const SamplingPlanScreen: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { currentRole } = useRole();

  // Find lot from mock data
  const lot = mockLots.find((l) => l.code === id || l.id === id) || mockLots[0];

  // Supervisor only can edit
  const canEdit = currentRole === 'Supervisor';

  // Form State initialized to exact mockup values in 06-sampling-plan.png
  const [criticalN, setCriticalN] = useState('80');
  const [criticalAc, setCriticalAc] = useState('0');
  const [criticalRe, setCriticalRe] = useState('1');

  const [majorN, setMajorN] = useState('80');
  const [majorAc, setMajorAc] = useState('5');
  const [majorRe, setMajorRe] = useState('6');

  const [minorN, setMinorN] = useState('80');
  const [minorAc, setMinorAc] = useState('7');
  const [minorRe, setMinorRe] = useState('9');

  const [planSource, setPlanSource] = useState('Buyer PO #4471, page 3');

  // Warnings, not blocks (Section 4.6):
  // 1. Re is not Ac + 1
  const isMinorReGap = parseInt(minorRe, 10) !== parseInt(minorAc, 10) + 1;
  const isMajorReGap = parseInt(majorRe, 10) !== parseInt(majorAc, 10) + 1;
  const isCriticalReGap = parseInt(criticalRe, 10) !== parseInt(criticalAc, 10) + 1;
  // 2. n differs across classes
  const isNDiffers = criticalN !== majorN || majorN !== minorN;
  // 3. n is at least the lot size (whole lot)
  const lotSize = lot?.pieces || 800;
  const isWholeLot =
    parseInt(criticalN, 10) >= lotSize ||
    parseInt(majorN, 10) >= lotSize ||
    parseInt(minorN, 10) >= lotSize;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canEdit) {
      alert('Read-only: Only a Supervisor can save sampling plans.');
      return;
    }
    alert('Sampling plan confirmed and saved!');
    navigate(`/lots/${lot.code}`);
  };

  return (
    <div className="space-y-6 text-[#0F172A] select-none">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/lots/${lot.code}`)}
            className="p-2 rounded-xl border border-[#E2E8F0] hover:bg-slate-100 text-[#0F172A] transition-colors"
            title="Back to lot details"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-black text-[#0F172A] tracking-tight">
                Sampling plan
              </h1>
              <span className="font-mono text-sm font-bold bg-[#EAF0FF] text-[#1F4FD8] px-2.5 py-0.5 rounded-full">
                {lot.code}
              </span>
            </div>
            <p className="text-sm text-[#64748B] mt-0.5">
              ANSI/ASQ Z1.4 Single Sampling Normal II Configuration
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {canEdit ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Supervisor
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
              <Lock className="w-3.5 h-3.5 text-amber-600" />
              Read-Only (Supervisor Required)
            </span>
          )}
        </div>
      </div>

      {/* Role notice if not Supervisor */}
      {!canEdit && (
        <Banner
          variant="warn"
          title="Read-Only Mode Enforced"
          description="Only a Supervisor can modify lot sampling plans. Switch role to Supervisor in the Dev Switcher to unlock editing."
        />
      )}

      {/* Assumption Banner matching 06-sampling-plan.png */}
      <div className="bg-[#EAF0FF] border border-[#CBD5E1] rounded-[16px] p-4 flex items-start gap-3">
        <div className="p-1 rounded-full bg-[#1F4FD8]/10 text-[#1F4FD8] shrink-0 mt-0.5">
          <ShieldCheck className="w-4 h-4" />
        </div>
        <div className="text-[13px] text-[#0B1F5C] leading-relaxed">
          <strong className="font-bold">Assumption:</strong> single sampling, normal inspection, General Inspection Level II. Entered by S. Karim.
        </div>
      </div>

      {/* Global Warnings if active */}
      {isNDiffers && (
        <div className="bg-[#FEF3C7] border border-[#FDE68A] rounded-[16px] p-3.5 flex items-center gap-2.5 text-amber-800 text-xs font-medium">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>Warning: Sample size (n) differs across defect classes. Standard inspection recommends uniform sample size.</span>
        </div>
      )}

      {isWholeLot && (
        <div className="bg-[#FEF3C7] border border-[#FDE68A] rounded-[16px] p-3.5 flex items-center gap-2.5 text-amber-800 text-xs font-medium">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>Warning: Sample size (n) equals or exceeds lot batch size ({lotSize} pcs), requiring 100% whole-lot inspection.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Three Class Cards in One Row on Desktop (grid grid-cols-1 md:grid-cols-3 gap-6) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Critical Class */}
          <div className="bg-white rounded-[20px] border border-[#E2E8F0] shadow-xs p-5 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#F1F5F9]">
              <h2 className="text-[16px] font-bold text-[#0F172A]">Critical</h2>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-[#FEE2E2] text-[#B91C1C]">
                AQL 0
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">n</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={criticalN}
                  onChange={(e) => setCriticalN(e.target.value)}
                  className="w-full h-11 px-2 rounded-[10px] border border-[#E2E8F0] text-[15px] font-bold text-[#0F172A] bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">Ac</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={criticalAc}
                  onChange={(e) => setCriticalAc(e.target.value)}
                  className="w-full h-11 px-2 rounded-[10px] border border-[#E2E8F0] text-[15px] font-bold text-[#15803D] bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">Re</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={criticalRe}
                  onChange={(e) => setCriticalRe(e.target.value)}
                  className={`w-full h-11 px-2 rounded-[10px] text-[15px] font-bold bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none ${
                    isCriticalReGap
                      ? 'border border-[#F59E0B] text-[#B45309]'
                      : 'border border-[#E2E8F0] text-[#B91C1C]'
                  }`}
                />
              </div>
            </div>

            <p className="text-[11.5px] text-[#64748B]">
              Any critical defect immediately triggers lot escalation.
            </p>
          </div>

          {/* Card 2: Major Class */}
          <div className="bg-white rounded-[20px] border border-[#E2E8F0] shadow-xs p-5 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#F1F5F9]">
              <h2 className="text-[16px] font-bold text-[#0F172A]">Major</h2>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-[#FEF3C7] text-[#B45309]">
                AQL 2.5
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">n</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={majorN}
                  onChange={(e) => setMajorN(e.target.value)}
                  className="w-full h-11 px-2 rounded-[10px] border border-[#E2E8F0] text-[15px] font-bold text-[#0F172A] bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">Ac</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={majorAc}
                  onChange={(e) => setMajorAc(e.target.value)}
                  className="w-full h-11 px-2 rounded-[10px] border border-[#E2E8F0] text-[15px] font-bold text-[#15803D] bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">Re</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={majorRe}
                  onChange={(e) => setMajorRe(e.target.value)}
                  className={`w-full h-11 px-2 rounded-[10px] text-[15px] font-bold bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none ${
                    isMajorReGap
                      ? 'border border-[#F59E0B] text-[#B45309]'
                      : 'border border-[#E2E8F0] text-[#B91C1C]'
                  }`}
                />
              </div>
            </div>

            <p className="text-[11.5px] text-[#64748B]">
              Standard ANSI limits: Ac 5, Re 6 for batch size 800 pcs.
            </p>
          </div>

          {/* Card 3: Minor Class */}
          <div className="bg-white rounded-[20px] border border-[#E2E8F0] shadow-xs p-5 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#F1F5F9]">
              <h2 className="text-[16px] font-bold text-[#0F172A]">Minor</h2>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-[#E0F2FE] text-[#0369A1]">
                AQL 4.0
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">n</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={minorN}
                  onChange={(e) => setMinorN(e.target.value)}
                  className="w-full h-11 px-2 rounded-[10px] border border-[#E2E8F0] text-[15px] font-bold text-[#0F172A] bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">Ac</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={minorAc}
                  onChange={(e) => setMinorAc(e.target.value)}
                  className="w-full h-11 px-2 rounded-[10px] border border-[#E2E8F0] text-[15px] font-bold text-[#15803D] bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#64748B]">Re</label>
                <input
                  type="number"
                  disabled={!canEdit}
                  value={minorRe}
                  onChange={(e) => setMinorRe(e.target.value)}
                  className={`w-full h-11 px-2 rounded-[10px] text-[15px] font-bold bg-white font-mono text-center disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none ${
                    isMinorReGap
                      ? 'border-2 border-[#EF4444] text-[#B91C1C]'
                      : 'border border-[#E2E8F0] text-[#B91C1C]'
                  }`}
                />
              </div>
            </div>

            {isMinorReGap && (
              <p className="text-[11.5px] font-semibold text-[#B45309] leading-snug">
                Warning: Re is not Ac + 1. Saving is allowed; a gap will HOLD the lot.
              </p>
            )}
          </div>
        </div>

        {/* Plan Source Card (from 06-sampling-plan.png) */}
        <div className="bg-white rounded-[20px] border border-[#E2E8F0] shadow-xs p-5 space-y-2">
          <label className="text-[13px] font-semibold text-[#0F172A] block">
            Plan source
          </label>
          <input
            type="text"
            disabled={!canEdit}
            value={planSource}
            onChange={(e) => setPlanSource(e.target.value)}
            placeholder="e.g. Buyer PO #4471, page 3"
            className="w-full h-11 px-3.5 rounded-[12px] border border-[#CBD5E1] text-[14px] text-[#0F172A] bg-white placeholder-[#94A3B8] disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8]"
          />
        </div>

        {/* Read-Back Confirmation Card below the three class cards */}
        <div className="bg-[#EAF0FF] rounded-[20px] border border-[#CBD5E1] p-6 space-y-2">
          <h2 className="text-[15px] font-bold text-[#0B1F5C]">
            Read-back
          </h2>
          <p className="text-sm font-medium text-[#1E3A8A]">
            Sample {criticalN} of {lot.pieces || 800} pieces. Reject on {criticalRe} critical, {majorRe} major or {minorRe} minor defective units.
          </p>
        </div>

        {/* Bottom Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate(`/lots/${lot.code}`)}
          >
            Back
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={!canEdit}
          >
            {canEdit ? 'Confirm and save' : 'Locked (Supervisor only)'}
          </Button>
        </div>
      </form>
    </div>
  );
};