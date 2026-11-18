import React from 'react';

export type StatusChipVariant =
  | 'uncalibrated'
  | 'critical'
  | 'warning'
  | 'escalate'
  | 'info'
  | 'neutral'
  | 'open';

export interface StatusChipProps {
  label: string;
  variant?: StatusChipVariant;
  count?: number | string;
  size?: 'sm' | 'default';
  className?: string;
}

export const StatusChip: React.FC<StatusChipProps> = ({
  label,
  variant = 'neutral',
  count,
  size = 'default',
  className = '',
}) => {
  const variantStyles: Record<StatusChipVariant, { bg: string; text: string; border?: string }> = {
    uncalibrated: {
      bg: 'bg-[#E0F2FE]',
      text: 'text-[#0369A1]',
    },
    critical: {
      bg: 'bg-[#FEE2E2]',
      text: 'text-[#B91C1C]',
    },
    warning: {
      bg: 'bg-[#FEF3C7]',
      text: 'text-[#B45309]',
    },
    escalate: {
      bg: 'bg-[#EDE9FE]',
      text: 'text-[#6D28D9]',
    },
    info: {
      bg: 'bg-[#E0F2FE]',
      text: 'text-[#0369A1]',
    },
    neutral: {
      bg: 'bg-[#F1F5F9]',
      text: 'text-[#475569]',
    },
    open: {
      bg: 'bg-[#E0F2FE]',
      text: 'text-[#0369A1]',
    },
  };

  const sizeClasses =
    size === 'sm'
      ? 'text-[11px] px-2 py-0.5'
      : 'text-[12px] px-2.5 py-1';

  const style = variantStyles[variant];

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium rounded-full select-none ${style.bg} ${style.text} ${sizeClasses} ${className}`}
    >
      {count !== undefined && <span className="font-bold">{count}</span>}
      <span>{label}</span>
    </span>
  );
};
