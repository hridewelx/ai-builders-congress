import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, ChevronLeft, AlertTriangle } from 'lucide-react';
import { Button } from '../components/Button';
import { Banner } from '../components/Banner';
import { mockLots } from '../mocks';

export const CreateLotScreen: React.FC = () => {
  const navigate = useNavigate();

  // Form State initialized to match 04-create-lot.png
  const [lotCode, setLotCode] = useState('LT-2411-017');
  const [product, setProduct] = useState('Single-jersey knit tee');
  const [colour, setColour] = useState('Navy');
  const [lotSize, setLotSize] = useState('800');
  const [buyer, setBuyer] = useState('Northwind Apparel');

  // Validation logic: LT-2411-017 already exists in mockLots
  const isDuplicateCode = mockLots.some(
    (l) => l.code.toUpperCase() === lotCode.trim().toUpperCase()
  );
  const lotSizeNum = parseInt(lotSize, 10);
  const isLotSizeInvalid = isNaN(lotSizeNum) || lotSizeNum < 1;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (isDuplicateCode) {
      alert('Cannot save: This lot code already exists. Please choose a unique code.');
      return;
    }
    if (isLotSizeInvalid) {
      alert('Lot size must be a whole number of 1 or more.');
      return;
    }
    alert(`Lot ${lotCode} created! Decisions will HOLD until a Supervisor configures the plan.`);
    navigate('/lots');
  };

  return (
    <div className="space-y-6 text-[#0F172A] select-none py-2">
      {/* Top Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-[#64748B] max-w-[560px] mx-auto">
        <button
          type="button"
          onClick={() => navigate('/lots')}
          className="hover:text-[#1F4FD8] font-medium flex items-center gap-1"
        >
          <ChevronLeft className="w-3.5 h-3.5" /> Lots
        </button>
        <span>/</span>
        <span className="font-bold text-[#0F172A]">New Lot</span>
      </div>

      {/* ========================================================= */}
      {/* CENTERED FORM CARD (MAX 560px)                            */}
      {/* ========================================================= */}
      <div className="w-full max-w-[560px] mx-auto bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm p-6 sm:p-8 space-y-6 text-left">
        {/* Card Header */}
        <div className="pb-4 border-b border-[#F1F5F9] space-y-1">
          <h1 className="text-2xl font-black text-[#0F172A] tracking-tight">
            Create new lot
          </h1>
          <p className="text-xs sm:text-sm text-[#64748B]">
            Step 1 of 1 · Register garment batch for inspection
          </p>
        </div>

        {/* Main Form Fields */}
        <form onSubmit={handleSave} className="space-y-4">
          {/* Field 1: Lot code */}
          <div className="space-y-1.5">
            <label className="text-[13px] font-bold text-[#0F172A]">Lot code</label>
            <input
              type="text"
              value={lotCode}
              onChange={(e) => setLotCode(e.target.value)}
              className={`w-full h-11 px-3.5 rounded-[12px] text-[14px] bg-white text-[#0F172A] font-mono tracking-tight focus:outline-none ${
                isDuplicateCode
                  ? 'border border-[#EF4444] focus:border-[#B91C1C] focus:ring-2 focus:ring-[#FEE2E2]'
                  : 'border border-[#E2E8F0] focus:border-[#1F4FD8] focus:ring-2 focus:ring-[#EAF0FF]'
              }`}
            />
            {isDuplicateCode && (
              <p className="text-[12px] font-semibold text-[#B91C1C] pt-0.5 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                This lot code already exists. Use a different code.
              </p>
            )}
          </div>

          {/* Field 2: Product selector */}
          <div className="space-y-1.5">
            <label className="text-[13px] font-bold text-[#0F172A]">Product</label>
            <div
              onClick={() => {
                const options = ['Single-jersey knit tee', 'Navy polo', 'Ribbed sweater'];
                const next = options[(options.indexOf(product) + 1) % options.length];
                setProduct(next);
              }}
              className="w-full h-11 px-3.5 rounded-[12px] border border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between cursor-pointer hover:border-[#CBD5E1] transition-colors"
            >
              <span className="text-[13.5px] text-[#0F172A] font-medium">{product}</span>
              <ChevronRight className="w-4 h-4 text-[#94A3B8]" />
            </div>
          </div>

          {/* Field 3: Colour */}
          <div className="space-y-1.5">
            <label className="text-[13px] font-bold text-[#0F172A]">Colour</label>
            <input
              type="text"
              value={colour}
              onChange={(e) => setColour(e.target.value)}
              className="w-full h-11 px-3.5 rounded-[12px] border border-[#E2E8F0] text-[13.5px] text-[#0F172A] bg-white focus:outline-none focus:border-[#1F4FD8] focus:ring-2 focus:ring-[#EAF0FF]"
            />
          </div>

          {/* Field 4: Lot size (pieces) */}
          <div className="space-y-1.5">
            <label className="text-[13px] font-bold text-[#0F172A]">Lot size (pieces)</label>
            <input
              type="number"
              value={lotSize}
              onChange={(e) => setLotSize(e.target.value)}
              className="w-full h-11 px-3.5 rounded-[12px] border border-[#E2E8F0] text-[13.5px] text-[#0F172A] bg-white font-mono focus:outline-none focus:border-[#1F4FD8] focus:ring-2 focus:ring-[#EAF0FF]"
            />
            <p className="text-[11.5px] text-[#64748B]">
              {isLotSizeInvalid ? (
                <span className="text-[#B91C1C] font-semibold">Must be a whole number of 1 or more.</span>
              ) : (
                'Whole number, 1 or more pieces.'
              )}
            </p>
          </div>

          {/* Field 5: Buyer selector */}
          <div className="space-y-1.5">
            <label className="text-[13px] font-bold text-[#0F172A]">Buyer</label>
            <div
              onClick={() => {
                const buyers = ['Northwind Apparel', 'Brightway', 'Acme Global'];
                const next = buyers[(buyers.indexOf(buyer) + 1) % buyers.length];
                setBuyer(next);
              }}
              className="w-full h-11 px-3.5 rounded-[12px] border border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between cursor-pointer hover:border-[#CBD5E1] transition-colors"
            >
              <span className="text-[13.5px] text-[#0F172A] font-medium">{buyer}</span>
              <ChevronRight className="w-4 h-4 text-[#94A3B8]" />
            </div>
            <p className="text-[11.5px] text-[#64748B] leading-tight">
              Buyer decides which defects are critical, major or minor based on contract clause.
            </p>
          </div>

          {/* Info Banner */}
          <div className="pt-1">
            <Banner
              variant="info"
              title="Supervisor Plan Required"
              description="After saving, a Supervisor sets the sampling plan. Until then, decisions will remain on HOLD."
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#F1F5F9]">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/lots')}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isDuplicateCode || isLotSizeInvalid}
            >
              Save lot
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
