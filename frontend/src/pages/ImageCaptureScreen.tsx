import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  Camera,
  Upload,
  ArrowRight,
} from 'lucide-react';
import { Button } from '../components/Button';
import { Banner } from '../components/Banner';
import { mockUploadQueue } from '../mocks';

export const ImageCaptureScreen: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const lotId = id || 'LT-2411-018';

  const [garmentUnit, setGarmentUnit] = useState('U-075');
  const [selectedSide, setSelectedSide] = useState<'Front' | 'Back' | 'Detail'>('Front');

  const handleTakePhoto = () => {
    navigate(`/lots/${lotId}/review`);
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
                Capture & Upload Photo
              </h1>
              <span className="font-mono text-sm font-bold bg-[#EAF0FF] text-[#1F4FD8] px-2.5 py-0.5 rounded-full">
                {lotId}
              </span>
            </div>
            <p className="text-sm text-[#64748B] mt-0.5">
              Capture garment surface images for AI proposed defect inference
            </p>
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          rightIcon={<ArrowRight className="w-4 h-4" />}
          onClick={handleTakePhoto}
        >
          Go to Review
        </Button>
      </div>

      {/* ========================================================= */}
      {/* 2-COLUMN LAYOUT:                                          */}
      {/* Left: Upload area                                         */}
      {/* Right: "No faces, no badges." banner + Result list        */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ======================================================= */}
        {/* LEFT COLUMN: Upload Area                                */}
        {/* ======================================================= */}
        <div className="lg:col-span-7 space-y-5">
          {/* Unit & Side Selection Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-5 grid grid-cols-1 sm:grid-cols-12 gap-4 items-center text-left">
            {/* Garment unit picker */}
            <div className="sm:col-span-5 space-y-1.5">
              <label className="text-[12.5px] text-[#64748B] font-bold uppercase tracking-wider block">
                Garment Unit
              </label>
              <div
                onClick={() => {
                  const units = ['U-075', 'U-076', 'U-077', 'U-078'];
                  const next = units[(units.indexOf(garmentUnit) + 1) % units.length];
                  setGarmentUnit(next);
                }}
                className="w-full h-11 px-3.5 rounded-[12px] border border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between cursor-pointer hover:border-[#CBD5E1] transition-colors"
              >
                <span className="text-[14.5px] font-bold text-[#0F172A] font-mono">
                  {garmentUnit}
                </span>
                <ChevronRight className="w-4 h-4 text-[#94A3B8]" />
              </div>
            </div>

            {/* Side segmented control */}
            <div className="sm:col-span-7 space-y-1.5">
              <label className="text-[12.5px] text-[#64748B] font-bold uppercase tracking-wider block">
                Surface Side
              </label>
              <div className="h-11 bg-[#F1F5F9] p-1 rounded-[12px] flex items-center gap-1 border border-[#E2E8F0]">
                {(['Front', 'Back', 'Detail'] as const).map((side) => {
                  const isActive = selectedSide === side;
                  return (
                    <button
                      key={side}
                      type="button"
                      onClick={() => setSelectedSide(side)}
                      className={`flex-1 h-full rounded-[9px] text-[13px] font-medium transition-all ${
                        isActive
                          ? 'bg-white text-[#1F4FD8] font-bold shadow-xs'
                          : 'text-[#64748B] hover:text-[#0F172A]'
                      }`}
                    >
                      {side}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Interactive Upload Area / Camera Viewfinder */}
          <div
            onClick={handleTakePhoto}
            className="group relative bg-[#0B1F5C] rounded-[24px] p-8 sm:p-12 flex flex-col items-center justify-center border-2 border-dashed border-white/20 hover:border-[#60A5FA] transition-all cursor-pointer shadow-lg overflow-hidden text-center min-h-[360px]"
          >
            <div className="w-20 h-20 rounded-2xl bg-white/10 flex items-center justify-center text-white mb-4 group-hover:scale-110 group-hover:bg-[#1F4FD8] transition-all border border-white/15">
              <Camera className="w-10 h-10 text-[#60A5FA]" />
            </div>

            <h2 className="text-[20px] font-bold text-white tracking-tight leading-tight">
              Lay garment flat & capture
            </h2>
            <p className="text-[14px] text-white/70 mt-2 max-w-md leading-relaxed">
              Fill the frame under even floor illumination. Click anywhere in this area to capture unit{' '}
              <strong className="text-white font-mono">{garmentUnit}</strong> ({selectedSide} side).
            </p>

            <div className="mt-6 flex flex-wrap gap-3 justify-center">
              <Button
                variant="primary"
                leftIcon={<Camera className="w-4 h-4" />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleTakePhoto();
                }}
              >
                Take Photo
              </Button>
              <Button
                variant="secondary"
                className="bg-white/10 text-white hover:bg-white/20 border-white/30"
                leftIcon={<Upload className="w-4 h-4" />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleTakePhoto();
                }}
              >
                Pick File From Computer
              </Button>
            </div>
          </div>
        </div>

        {/* ======================================================= */}
        {/* RIGHT COLUMN: "No faces, no badges" Banner & Result List*/}
        {/* ======================================================= */}
        <div className="lg:col-span-5 space-y-6">
          {/* Mandatory Privacy Rule: Keep "No faces, no badges." */}
          <Banner
            variant="warn"
            title="No faces, no badges."
            description="Do not photograph people, factory worker faces, or ID security badges. Fill the viewfinder frame with the garment fabric only."
          />

          {/* Result List Card */}
          <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs p-6 space-y-4 text-left">
            <div className="flex justify-between items-center pb-2 border-b border-[#F1F5F9]">
              <div>
                <h3 className="text-[17px] font-bold text-[#0F172A]">
                  Upload Results
                </h3>
                <p className="text-xs text-[#64748B]">Batch queue for lot {lotId}</p>
              </div>
              <span className="font-mono text-xs font-bold bg-[#EAF0FF] text-[#1F4FD8] px-2.5 py-0.5 rounded-full">
                74 / 80 Registered
              </span>
            </div>

            <div className="divide-y divide-[#F1F5F9]">
              {mockUploadQueue.map((item) => (
                <div key={item.id} className="py-3.5 first:pt-0 last:pb-0 space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold text-[14px] text-[#0F172A] leading-tight">
                        {item.title}
                      </div>
                      <div className="text-[12px] text-[#64748B] mt-0.5">
                        {item.subtitle}
                      </div>
                    </div>

                    <div>
                      {item.status === 'Accepted' && (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#DCFCE7] text-[#15803D]">
                          Accepted
                        </span>
                      )}
                      {item.status === 'Not counted' && (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#FEF3C7] text-[#B45309]">
                          Duplicate (not counted)
                        </span>
                      )}
                    </div>
                  </div>

                  {item.status === 'Uploading' && (
                    <div className="w-full h-1.5 bg-[#E2E8F0] rounded-full overflow-hidden mt-1">
                      <div
                        className="h-full bg-[#1F4FD8] rounded-full transition-all duration-300"
                        style={{ width: `${item.progressPercent || 62}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-[#F1F5F9]">
              <Button
                variant="primary"
                fullWidth
                rightIcon={<ArrowRight className="w-4 h-4" />}
                onClick={handleTakePhoto}
              >
                Proceed to Review Unit U-075
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
