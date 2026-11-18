import React from 'react';
import { AlertTriangle, Clock } from 'lucide-react';
import { mockHealthCards } from '../../mocks';

interface SystemHealthTabProps {
  onGoToAudit?: () => void;
}

export const SystemHealthTab: React.FC<SystemHealthTabProps> = ({ onGoToAudit }) => {
  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-black text-[#0F172A] tracking-tight">System health</h1>
        <p className="text-[13px] text-[#64748B] mt-0.5">
          Live status. Alerts also appear on the Dashboard.
        </p>
      </div>

      {/* 6 Health Status Cards (3 cols x 2 rows) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {mockHealthCards.map((card) => {
          const isDown = card.status === 'Down';
          const isUp = card.status === 'Up' || card.status === 'OK';

          return (
            <div
              key={card.id}
              className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs p-4 flex flex-col justify-between min-h-[120px]"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <h2 className="font-bold text-[14.5px] text-[#0F172A]">{card.name}</h2>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                      isDown
                        ? 'bg-[#FEE2E2] text-[#B91C1C]'
                        : isUp
                        ? 'bg-[#DCFCE7] text-[#15803D]'
                        : 'bg-[#FEF3C7] text-[#B45309]'
                    }`}
                  >
                    {card.status}
                  </span>
                </div>
                <p className="text-[12.5px] text-[#475569] leading-relaxed">{card.description}</p>
              </div>

              <div className="flex items-center gap-1.5 text-[11.5px] text-[#94A3B8] pt-3">
                <Clock className="w-3.5 h-3.5" />
                <span>{card.checkedAt}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Alert Banner linking to Audit Tab */}
      <div className="bg-[#FEE2E2] border border-[#FECACA] rounded-[14px] p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-[#B91C1C] shrink-0 mt-0.5" />
        <div className="text-[13px] text-[#991B1B] leading-relaxed">
          <strong className="font-bold text-[#B91C1C]">Detector unavailable.</strong> New photos
          show &ldquo;not inferred&rdquo;. Lots HOLD until reviewed by a person.{' '}
          <button
            type="button"
            onClick={onGoToAudit}
            className="font-bold underline underline-offset-2 hover:opacity-80 ml-1 inline-flex items-center"
          >
            Investigate in Audit log →
          </button>
        </div>
      </div>
    </div>
  );
};
