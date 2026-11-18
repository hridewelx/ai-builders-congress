import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ChevronLeft,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  X,
} from 'lucide-react';
import { Button } from '../components/Button';
import { Banner } from '../components/Banner';
import { GarmentCanvas } from '../components/GarmentCanvas';
import {
  mockDefectProposals,
  defectTypeOptions,
  type DefectProposal,
} from '../mocks';

export const ImageReviewScreen: React.FC = () => {
  const navigate = useNavigate();
  const { id, proposalId: urlProposalId } = useParams<{ id: string; proposalId?: string }>();
  const lotId = id || 'LT-2411-018';

  // Proposal state
  const [proposals, setProposals] = useState<DefectProposal[]>(mockDefectProposals);
  const [activeProposalId, setActiveProposalId] = useState<string | undefined>(
    urlProposalId || 'prop-1'
  );

  // Zoom state for image on the left
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  // Initial proposal to confirm if passed in URL
  const initialConfirmProposal = urlProposalId
    ? mockDefectProposals.find((p) => p.id === urlProposalId) || mockDefectProposals[0]
    : null;

  // Defect confirmation side panel state
  const [confirmingProposal, setConfirmingProposal] = useState<DefectProposal | null>(
    initialConfirmProposal
  );
  const [selectedType, setSelectedType] = useState<string>(
    initialConfirmProposal ? initialConfirmProposal.type : 'Hole'
  );
  const [rejectNote, setRejectNote] = useState<string>('');

  // Open side panel for a proposal
  const openConfirmPanel = (prop: DefectProposal) => {
    setConfirmingProposal(prop);
    setSelectedType(prop.type);
    setRejectNote('');
    setActiveProposalId(prop.id);
  };

  // Close side panel
  const closeConfirmPanel = () => {
    setConfirmingProposal(null);
  };

  // Confirm defect from side panel
  const handleConfirmDefect = () => {
    if (!confirmingProposal) return;
    setProposals((prev) =>
      prev.map((p) =>
        p.id === confirmingProposal.id
          ? {
              ...p,
              type: selectedType,
              resolved: true,
              resolution: 'CONFIRMED',
            }
          : p
      )
    );
    closeConfirmPanel();
  };

  // Reject proposal from side panel
  const handleRejectProposal = () => {
    if (!confirmingProposal) return;
    if (confirmingProposal.severity === 'CRITICAL') {
      alert('Rejecting a critical-mapped proposal escalates the lot to a Supervisor.');
    }
    setProposals((prev) =>
      prev.map((p) =>
        p.id === confirmingProposal.id
          ? {
              ...p,
              resolved: true,
              resolution: 'REJECTED',
            }
          : p
      )
    );
    closeConfirmPanel();
  };

  // Zoom handlers
  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 25, 200));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 25, 75));
  const handleZoomReset = () => setZoomLevel(100);

  // Check if all proposals are resolved (or if list is empty)
  const allResolved = proposals.length === 0 || proposals.every((p) => p.resolved);

  const handleToggleEmptyState = () => {
    if (proposals.length > 0) {
      setProposals([]);
    } else {
      setProposals(mockDefectProposals);
    }
    closeConfirmPanel();
  };

  const handleMarkReviewed = () => {
    if (!allResolved) {
      alert('Every defect proposal must be reviewed and resolved before marking unit reviewed.');
      return;
    }
    alert('Unit U-075 marked reviewed. Proceeding to lot decision evaluation.');
    navigate(`/lots/${lotId}/decision`);
  };

  return (
    <div className="space-y-6 text-[#0F172A] select-none relative">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/lots/${lotId}/capture`)}
            className="p-2 rounded-xl border border-[#E2E8F0] hover:bg-slate-100 text-[#0F172A] transition-colors"
            title="Back to image capture"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-black text-[#0F172A] tracking-tight">
                Review Unit Image
              </h1>
              <span className="font-mono text-sm font-bold bg-[#EAF0FF] text-[#1F4FD8] px-2.5 py-0.5 rounded-full">
                Unit 75 of 80 · Front side
              </span>
            </div>
            <p className="text-sm text-[#64748B] mt-0.5">
              AI proposes defects. Humans confirm. Every score is uncalibrated.
            </p>
          </div>
        </div>

        {/* Dev test empty state button */}
        <button
          type="button"
          onClick={handleToggleEmptyState}
          className="text-xs font-semibold text-[#1F4FD8] bg-[#EAF0FF] px-3.5 py-1.5 rounded-xl hover:bg-[#D5E3FF] transition-colors self-start sm:self-auto"
        >
          {proposals.length > 0 ? 'Test 0 Proposals Rule' : 'Restore Proposals'}
        </button>
      </div>

      {/* Mandatory Uncalibrated Rule Banner */}
      <Banner
        variant="info"
        title="Protocol: AI scores are uncalibrated"
        description="Inspect proposed boxes individually. You confirm every defect before lot conformance computation. No bulk confirm."
      />

      {/* ========================================================= */}
      {/* 2-COLUMN DESKTOP LAYOUT                                   */}
      {/* Left: Large Image with box overlay and zoom               */}
      {/* Right: Proposals list and actions                         */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ======================================================= */}
        {/* LEFT COLUMN: Large Image, Box Overlay, and Zoom Controls */}
        {/* ======================================================= */}
        <div className="lg:col-span-7 space-y-3">
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-5 space-y-3">
            {/* Zoom Toolbar */}
            <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
              <div className="flex items-center gap-2 text-xs font-bold text-[#64748B] uppercase tracking-wider">
                <span>Viewfinder Zoom:</span>
                <span className="font-mono text-[#0F172A] bg-[#F1F5F9] px-2 py-0.5 rounded">
                  {zoomLevel}%
                </span>
              </div>

              <div className="flex items-center gap-1.5 bg-[#F8FAFC] p-1 rounded-xl border border-[#E2E8F0]">
                <button
                  type="button"
                  onClick={handleZoomOut}
                  disabled={zoomLevel <= 75}
                  className="p-1.5 rounded-lg text-[#475569] hover:bg-white hover:text-[#0F172A] disabled:opacity-40 transition-colors"
                  title="Zoom Out (-25%)"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={handleZoomIn}
                  disabled={zoomLevel >= 200}
                  className="p-1.5 rounded-lg text-[#475569] hover:bg-white hover:text-[#0F172A] disabled:opacity-40 transition-colors"
                  title="Zoom In (+25%)"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={handleZoomReset}
                  className="p-1.5 rounded-lg text-[#475569] hover:bg-white hover:text-[#0F172A] transition-colors"
                  title="Reset Zoom (100%)"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Scrollable / Scalable Image Container */}
            <div className="relative w-full overflow-hidden rounded-[16px] bg-[#1B2436] min-h-[380px] sm:min-h-[440px] flex items-center justify-center">
              <div
                className="w-full transition-transform duration-200 origin-center flex items-center justify-center p-2"
                style={{ transform: `scale(${zoomLevel / 100})` }}
              >
                <GarmentCanvas
                  proposals={proposals}
                  activeProposalId={activeProposalId}
                  onSelectProposal={(propId) => {
                    const target = proposals.find((p) => p.id === propId);
                    if (target) openConfirmPanel(target);
                  }}
                  editorMode={false}
                />
              </div>
            </div>

            {/* Visual Indicators & Flags Under Canvas */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#F1F5F9]">
              <div className="flex flex-wrap items-center gap-1.5">
                {proposals.length > 0 && (
                  <>
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#FEE2E2] text-[#B91C1C]">
                      Possible critical
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#FEF3C7] text-[#B45309]">
                      LOW_SCORE
                    </span>
                  </>
                )}
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#EAF0FF] text-[#0B1F5C]">
                  Unit U-075 · Front
                </span>
              </div>

              <span className="text-[11.5px] text-[#64748B]">
                Click any box to inspect & confirm
              </span>
            </div>
          </div>
        </div>

        {/* ======================================================= */}
        {/* RIGHT COLUMN: Proposals List & Unit Actions             */}
        {/* ======================================================= */}
        <div className="lg:col-span-5 space-y-6">
          {/* Proposals List Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#F1F5F9]">
              <div>
                <h2 className="text-[17px] font-bold text-[#0F172A]">
                  Proposals ({proposals.length})
                </h2>
                <p className="text-xs text-[#64748B]">
                  Confirm each proposal individually. No bulk approval.
                </p>
              </div>
              {/* Note: NO "Confirm all" button per governing principles */}
            </div>

            {proposals.length === 0 ? (
              /* Rule: Empty detections say "No proposals. This is not a pass." */
              <div className="py-10 px-4 text-center bg-[#F8FAFC] rounded-[16px] border-2 border-dashed border-[#CBD5E1] space-y-2">
                <AlertTriangle className="w-8 h-8 text-[#B45309] mx-auto" />
                <p className="text-[16px] font-bold text-[#0F172A]">
                  No proposals. This is not a pass.
                </p>
                <p className="text-[12.5px] text-[#64748B] max-w-xs mx-auto leading-relaxed">
                  Inspect all surfaces manually. Every garment must be visually verified by an inspector.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-[#F1F5F9]">
                {proposals.map((prop, idx) => {
                  const isPrimary = idx === 0;
                  const isSelected = activeProposalId === prop.id;

                  return (
                    <div
                      key={prop.id}
                      onClick={() => openConfirmPanel(prop)}
                      className={`py-3.5 first:pt-0 last:pb-0 flex items-center justify-between gap-3 p-2 rounded-xl transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-[#EAF0FF]/50 border border-[#1F4FD8]/20'
                          : 'hover:bg-slate-50'
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="font-bold text-[15px] text-[#0F172A] leading-tight flex items-center gap-2">
                          <span>{prop.type}</span>
                          {prop.resolved && (
                            <span
                              className={`text-[10px] font-bold px-2 py-0.2 rounded-full uppercase ${
                                prop.resolution === 'CONFIRMED'
                                  ? 'bg-[#DCFCE7] text-[#15803D]'
                                  : 'bg-[#FEE2E2] text-[#B91C1C]'
                              }`}
                            >
                              {prop.resolution}
                            </span>
                          )}
                        </div>

                        {/* Mandatory Rule: show "uncalibrated" next to every score */}
                        <div className="flex flex-wrap items-center gap-1.5 text-[11.5px] text-[#64748B]">
                          <span className="font-mono text-[#0F172A] font-semibold">
                            Score: {prop.score}
                          </span>
                          <span className="bg-[#F1F5F9] text-[#475569] font-semibold px-2 py-0.5 rounded text-[10.5px]">
                            uncalibrated
                          </span>
                          <span>·</span>
                          <span
                            className={
                              prop.severity === 'CRITICAL'
                                ? 'text-[#B91C1C] font-semibold'
                                : 'text-[#475569]'
                            }
                          >
                            {prop.severity}
                          </span>
                        </div>
                      </div>

                      <Button
                        variant={prop.resolved ? 'secondary' : isPrimary ? 'primary' : 'outline'}
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          openConfirmPanel(prop);
                        }}
                      >
                        {prop.resolved ? 'Edit' : 'Review'}
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Unit Completion Action Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-3.5">
            <h3 className="text-sm font-bold text-[#0F172A]">Unit Disposition</h3>
            {!allResolved && (
              <p className="text-xs text-[#B45309] font-medium leading-relaxed">
                Every proposed defect must be confirmed or rejected before unit review can be completed.
              </p>
            )}
            <Button
              variant="primary"
              fullWidth
              size="default"
              disabled={!allResolved}
              onClick={handleMarkReviewed}
            >
              {allResolved
                ? 'Mark unit reviewed & proceed'
                : 'Mark unit reviewed (resolve all proposals first)'}
            </Button>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* DEFECT CONFIRMATION SIDE PANEL / MODAL OVER REVIEW SCREEN */}
      {/* ========================================================= */}
      {confirmingProposal && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg h-full bg-white shadow-2xl flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200 border-l border-[#CBD5E1]">
            <div>
              {/* Side Panel Header */}
              <div className="bg-[#0B1F5C] text-white p-6 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold">Confirm Defect</h2>
                    <span className="font-mono text-xs font-bold bg-[#1F4FD8] px-2 py-0.5 rounded">
                      {confirmingProposal.id}
                    </span>
                  </div>
                  <p className="text-xs text-white/70 mt-1">
                    Side panel editor over review screen
                  </p>
                </div>

                <button
                  type="button"
                  onClick={closeConfirmPanel}
                  className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
                  title="Close panel"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Side Panel Body */}
              <div className="p-6 space-y-6 text-left">
                {/* 1. Defect Type Classification */}
                <div className="space-y-3">
                  <label className="text-[13.5px] font-bold text-[#0F172A] block">
                    Defect Type
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {defectTypeOptions.map((type) => {
                      const isSelected = selectedType.toLowerCase() === type.toLowerCase();
                      return (
                        <button
                          key={type}
                          type="button"
                          onClick={() => setSelectedType(type)}
                          className={`px-3.5 py-1.5 rounded-full text-[13px] font-medium transition-all ${
                            isSelected
                              ? 'bg-[#EAF0FF] text-[#1F4FD8] border-2 border-[#1F4FD8] font-bold shadow-xs'
                              : 'bg-[#F1F5F9] text-[#475569] border-2 border-transparent hover:bg-[#E2E8F0]'
                          }`}
                        >
                          {type}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 2. Severity: Rule - Severity is shown but not editable */}
                <div className="bg-[#F8FAFC] rounded-[16px] border border-[#E2E8F0] p-4 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[13px] font-bold text-[#0F172A]">
                      Severity (Set by Buyer Clause)
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                        confirmingProposal.severity === 'CRITICAL'
                          ? 'bg-[#FEE2E2] text-[#B91C1C]'
                          : 'bg-[#FEF3C7] text-[#B45309]'
                      }`}
                    >
                      {confirmingProposal.severity}
                    </span>
                  </div>
                  <p className="text-[12px] text-[#64748B] leading-relaxed">
                    Clause 4.2 · Northwind Apparel tech-pack. <strong className="text-[#0F172A]">You cannot edit severity.</strong>
                  </p>
                </div>

                {/* 3. Rejection Reason Note */}
                <div className="space-y-2">
                  <label className="text-[13px] font-bold text-[#0F172A] block">
                    Note (Optional, for reject)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. False proposal caused by fabric shadow"
                    value={rejectNote}
                    onChange={(e) => setRejectNote(e.target.value)}
                    className="w-full h-11 px-3.5 rounded-[12px] border border-[#E2E8F0] text-[13.5px] text-[#0F172A] bg-white placeholder:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8] focus:ring-2 focus:ring-[#EAF0FF] transition-all"
                  />
                </div>
              </div>
            </div>

            {/* Side Panel Footer Actions */}
            <div className="p-6 border-t border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                className="text-[#B91C1C] border-[#CBD5E1] hover:bg-[#FEE2E2]/50 font-bold"
                onClick={handleRejectProposal}
              >
                Reject
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={handleConfirmDefect}
              >
                Confirm Defect
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
