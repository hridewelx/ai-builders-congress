import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft, ShieldCheck, AlertTriangle, Download, RefreshCw, FileText, CheckCircle2 } from 'lucide-react';
import { Button } from '../components/Button';
import { OutcomeChip } from '../components/OutcomeChip';
import { mockReportData } from '../mocks';
import { useRole } from '../context';

export const ReportViewScreen: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { currentRole } = useRole();
  const lotId = id || mockReportData.lotCode;

  const [auditVerified, setAuditVerified] = useState(true);

  const sha256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
  const reportDate = '18 Nov 2026, 14:32';

  const handleDownload = () => {
    alert(`Downloading one-page PDF certificate for lot ${lotId}...`);
  };

  const handleRegenerate = () => {
    alert('Regenerating report snapshot from current audit log entries...');
  };

  return (
    <div className="space-y-6 text-[#0F172A] select-none">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/lots/${lotId}/decision`)}
            className="p-2 rounded-xl border border-[#E2E8F0] hover:bg-slate-100 text-[#0F172A] transition-colors"
            title="Back to decision summary"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-black text-[#0F172A] tracking-tight">
                Report
              </h1>
              <span className="font-mono text-sm font-bold bg-[#EAF0FF] text-[#1F4FD8] px-2.5 py-0.5 rounded-full">
                {lotId}
              </span>
            </div>
            <p className="text-sm text-[#64748B] mt-0.5">
              One-page PDF
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#EAF0FF] text-[#1F4FD8]">
            <FileText className="w-3.5 h-3.5" />
            {currentRole}
          </span>
        </div>
      </div>

      {/* Main Two-Column Desktop Layout: PDF Preview on the Left, Details & Download on the Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (lg:col-span-7): PDF Preview Sheet */}
        <div className="lg:col-span-7 space-y-4">
          <div className="text-xs font-bold uppercase tracking-wider text-[#64748B] flex items-center justify-between">
            <span>One-Page PDF Preview</span>
            <span className="font-mono text-[11px] text-[#94A3B8]">A4 Printable Form</span>
          </div>

          <div className="bg-white rounded-[24px] border border-[#CBD5E1] shadow-lg p-6 sm:p-10 text-left space-y-6">
            {/* Certificate Header */}
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-5 border-b border-[#E2E8F0]">
              <div>
                <h2 className="text-xl sm:text-2xl font-black text-[#0B1F5C] tracking-tight">
                  Lotline inspection report
                </h2>
                <p className="text-xs sm:text-sm font-semibold text-[#64748B] mt-1">
                  {lotId} · Navy polo · Northwind
                </p>
              </div>

              <div className="self-start sm:self-auto">
                <OutcomeChip outcome="REJECT" size="lg" showDot />
              </div>
            </div>

            {/* Metrics List (exact match with 11-report-view.png) */}
            <div className="divide-y divide-[#F1F5F9] text-sm">
              <div className="flex justify-between py-2.5">
                <span className="text-[#64748B] font-medium">Sample</span>
                <span className="font-mono font-bold text-[#0F172A]">80 / 800</span>
              </div>
              <div className="flex justify-between py-2.5">
                <span className="text-[#64748B] font-medium">Critical / Major / Minor</span>
                <span className="font-mono font-bold text-[#0F172A]">0 / 6 / 3</span>
              </div>
              <div className="flex justify-between py-2.5">
                <span className="text-[#64748B] font-medium">Reviewer</span>
                <span className="font-semibold text-[#0F172A]">A. Rahman</span>
              </div>
              <div className="flex justify-between py-2.5">
                <span className="text-[#64748B] font-medium">Model</span>
                <span className="font-mono font-bold text-[#0F172A]">
                  v1.3.0 <span className="text-amber-600 font-semibold">(uncalibrated)</span>
                </span>
              </div>
            </div>

            {/* Visual Thumbnail Cards / Defect Previews (from 11-report-view.png) */}
            <div className="space-y-2 pt-2">
              <div className="grid grid-cols-3 gap-2 sm:gap-3">
                <div className="aspect-4/3 bg-[#E2E8F0] rounded-[14px] flex items-center justify-center border border-[#CBD5E1] p-1">
                  <span className="text-[10px] sm:text-xs font-mono font-medium text-[#64748B] text-center">Unit #01 Front</span>
                </div>
                <div className="aspect-4/3 bg-[#E2E8F0] rounded-[14px] flex items-center justify-center border border-[#CBD5E1] p-1">
                  <span className="text-[10px] sm:text-xs font-mono font-medium text-[#64748B] text-center">Unit #02 Back</span>
                </div>
                <div className="aspect-4/3 bg-[#E2E8F0] rounded-[14px] flex items-center justify-center border border-[#CBD5E1] p-1">
                  <span className="text-[10px] sm:text-xs font-mono font-medium text-[#64748B] text-center">Unit #03 Detail</span>
                </div>
              </div>
              <p className="text-[12px] text-[#64748B] pt-1">
                Engine recommendation and final disposition shown together. PDF is a rendering of the decision rows.
              </p>
            </div>

            {/* Defect Conformance Evaluation Table */}
            <div className="space-y-2 pt-2">
              <h3 className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
                Defect Conformance Evaluation
              </h3>
              <div className="border border-[#E2E8F0] rounded-[14px] overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs sm:text-sm min-w-[340px]">
                    <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[11px] font-bold text-[#64748B] uppercase">
                      <tr>
                        <th className="py-2 px-3 sm:px-4">Defect Class</th>
                        <th className="py-2 px-2 sm:px-4 text-center">n</th>
                        <th className="py-2 px-2 sm:px-4 text-center">Ac / Re</th>
                        <th className="py-2 px-2 sm:px-4 text-center">Found</th>
                        <th className="py-2 px-3 sm:px-4 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#F1F5F9]">
                      <tr>
                        <td className="py-2.5 px-3 sm:px-4 font-semibold text-[#0F172A]">Critical</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono">80</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono">0 / 1</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono font-bold text-[#15803D]">0</td>
                        <td className="py-2.5 px-3 sm:px-4 text-right">
                          <span className="px-2 py-0.5 rounded-full text-[10px] sm:text-[11px] font-bold bg-[#DCFCE7] text-[#15803D]">
                            PASS
                          </span>
                        </td>
                      </tr>
                      <tr>
                        <td className="py-2.5 px-3 sm:px-4 font-semibold text-[#0F172A]">Major</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono">80</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono">5 / 6</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono font-bold text-[#B91C1C]">6</td>
                        <td className="py-2.5 px-3 sm:px-4 text-right">
                          <span className="px-2 py-0.5 rounded-full text-[10px] sm:text-[11px] font-bold bg-[#FEE2E2] text-[#B91C1C]">
                            REJECT
                          </span>
                        </td>
                      </tr>
                      <tr>
                        <td className="py-2.5 px-3 sm:px-4 font-semibold text-[#0F172A]">Minor</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono">80</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono">7 / 9</td>
                        <td className="py-2.5 px-2 sm:px-4 text-center font-mono font-bold text-[#15803D]">3</td>
                        <td className="py-2.5 px-3 sm:px-4 text-right">
                          <span className="px-2 py-0.5 rounded-full text-[10px] sm:text-[11px] font-bold bg-[#DCFCE7] text-[#15803D]">
                            PASS
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Certified Signatures & Digest */}
            <div className="pt-4 border-t border-[#E2E8F0] space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs text-[#64748B] gap-2">
                <div>
                  <span className="font-bold text-[#0F172A]">Inspector:</span> A. Rahman (Rahim Khan)
                </div>
                <div>
                  <span className="font-bold text-[#0F172A]">Supervisor:</span> S. Karim (Karim Rahman)
                </div>
              </div>

              <div className="bg-[#F8FAFC] rounded-[12px] p-2.5 border border-[#E2E8F0] text-center font-mono text-[10.5px] text-[#64748B] break-all">
                SHA-256 Digest: {sha256}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column (lg:col-span-5): Audit Integrity, Details & Download Action */}
        <div className="lg:col-span-5 space-y-6 lg:sticky lg:top-6">
          {/* Audit Integrity Banner (from 11-report-view.png) */}
          <div className="space-y-2">
            {auditVerified ? (
              <div className="bg-[#DCFCE7] border border-[#BBF7D0] rounded-[18px] p-4 flex items-center justify-between text-left">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-5 h-5 text-[#15803D] shrink-0" />
                  <div className="text-[13px] text-[#166534] font-semibold">
                    Audit integrity verified at report time.
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setAuditVerified(false)}
                  className="text-[11px] text-[#15803D] underline font-semibold opacity-75 hover:opacity-100 shrink-0 ml-2"
                  title="Simulate chain failure"
                >
                  Simulate Fail
                </button>
              </div>
            ) : (
              <div className="bg-[#FEE2E2] border border-[#FECACA] rounded-[18px] p-4 flex items-center justify-between text-left">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-[#B91C1C] shrink-0" />
                  <div className="text-[13px] text-[#991B1B] font-bold">
                    Audit integrity failed and an alert is raised.
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setAuditVerified(true)}
                  className="text-[11px] text-[#B91C1C] underline font-bold shrink-0 ml-2"
                >
                  Restore
                </button>
              </div>
            )}

            <div className="bg-[#FFF1F2] border border-[#FECDD3] rounded-[14px] p-3 text-left flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-[#E11D48] shrink-0 mt-0.5" />
              <p className="text-[11.5px] text-[#9F1239] leading-snug">
                If the chain fails, this banner reads <strong className="font-bold">Audit integrity failed</strong> and an alert is raised.
              </p>
            </div>
          </div>

          {/* Details Card */}
          <div className="bg-white rounded-[20px] border border-[#E2E8F0] shadow-xs p-6 space-y-4 text-left">
            <h2 className="text-[16px] font-bold text-[#0F172A] border-b border-[#F1F5F9] pb-3">
              Inspection Details
            </h2>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Lot Code</span>
                <span className="font-mono font-bold text-[#0F172A] bg-[#F1F5F9] px-2 py-0.5 rounded">
                  {lotId}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Product & Buyer</span>
                <span className="font-semibold text-[#0F172A]">Navy polo · Northwind</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Batch Size</span>
                <span className="font-mono font-semibold text-[#0F172A]">800 pieces</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Inspection Standard</span>
                <span className="font-semibold text-[#0F172A]">ANSI/ASQ Z1.4 Normal II</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Report Timestamp</span>
                <span className="font-mono text-xs text-[#0F172A]">{reportDate}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Ledger Status</span>
                <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Sealed & Tamper-Evident
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons Card */}
          <div className="bg-white rounded-[20px] border border-[#E2E8F0] shadow-xs p-6 space-y-3">
            <Button
              variant="primary"
              size="lg"
              className="w-full h-12 shadow-md shadow-blue-500/20"
              leftIcon={<Download className="w-5 h-5" />}
              onClick={handleDownload}
            >
              Download PDF
            </Button>

            <Button
              variant="outline"
              size="lg"
              className="w-full h-12"
              leftIcon={<RefreshCw className="w-5 h-5" />}
              onClick={handleRegenerate}
            >
              Regenerate
            </Button>

            <p className="text-[11.5px] text-[#64748B] text-center pt-1">
              Inspector generates for own lots; Supervisor for any. Admin can view and download only.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};