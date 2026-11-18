import React from 'react';

interface PhoneFrameProps {
  children: React.ReactNode;
  className?: string;
}

export const PhoneFrame: React.FC<PhoneFrameProps> = ({ children, className = '' }) => {
  return (
    <div className="min-h-screen bg-slate-100/90 py-4 sm:py-8 px-2 flex flex-col items-center justify-start pb-8 sm:pb-12 font-sans">
      {/* 360 CSS px Reference Chassis */}
      <div
        className={`w-full max-w-[360px] bg-white rounded-[28px] overflow-hidden shadow-2xl border border-slate-300/80 flex flex-col min-h-[760px] relative transition-all ${className}`}
        style={{ width: '360px', maxWidth: '100%' }}
      >
        {children}
      </div>
    </div>
  );
};
