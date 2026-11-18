import React from 'react';

export type ProgressVariant = 'blue' | 'green' | 'red';

export interface ProgressBarProps {
  value: number; // Current value
  max?: number; // Total / max value, default 100
  variant?: ProgressVariant;
  label?: string;
  showPercent?: boolean;
  height?: 'sm' | 'default' | 'lg';
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  variant = 'blue',
  label,
  showPercent = false,
  height = 'default',
  className = '',
}) => {
  const percentage = Math.min(100, Math.max(0, (value / (max || 1)) * 100));

  const variantColors: Record<ProgressVariant, string> = {
    blue: 'bg-[#1F4FD8]', // In progress
    green: 'bg-[#15803D]', // Accepted
    red: 'bg-[#B91C1C]', // Rejected
  };

  const heightClasses: Record<'sm' | 'default' | 'lg', string> = {
    sm: 'h-1.5',
    default: 'h-2.5',
    lg: 'h-3.5',
  };

  return (
    <div className={`w-full flex flex-col gap-1.5 ${className}`}>
      {(label || showPercent) && (
        <div className="flex justify-between items-center text-[12.5px] font-medium text-[#64748B]">
          {label && <span>{label}</span>}
          {showPercent && (
            <span className="font-mono text-[12px] text-[#0F172A] font-semibold">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}

      <div
        className={`w-full ${heightClasses[height]} bg-[#E2E8F0] rounded-full overflow-hidden`}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <div
          className={`h-full ${variantColors[variant]} rounded-full transition-all duration-300 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
