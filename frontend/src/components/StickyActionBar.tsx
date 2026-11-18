import React from 'react';

export interface StickyActionBarProps {
  children?: React.ReactNode;
  row1?: React.ReactNode;
  row2?: React.ReactNode;
  helperText?: React.ReactNode;
  className?: string;
}

export const StickyActionBar: React.FC<StickyActionBarProps> = ({
  children,
  row1,
  row2,
  helperText,
  className = '',
}) => {
  return (
    <div
      className={`sticky bottom-0 left-0 right-0 z-30 w-full bg-white border-t border-[#E2E8F0] shadow-[0_-4px_20px_rgba(15,23,42,0.08)] px-4 py-3 select-none ${className}`}
    >
      <div className="max-w-md mx-auto flex flex-col gap-2.5">
        {helperText && (
          <div className="text-center text-[12px] text-[#64748B]">{helperText}</div>
        )}

        {row1 && <div className="grid grid-cols-2 gap-2.5">{row1}</div>}
        {row2 && <div className="grid grid-cols-2 gap-2.5">{row2}</div>}
        {children && !row1 && !row2 && <div className="flex gap-2.5 items-center">{children}</div>}
      </div>
    </div>
  );
};
