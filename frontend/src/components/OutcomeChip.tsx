import React from 'react';

export type OutcomeType = 'ACCEPT' | 'REJECT' | 'HOLD' | 'ESCALATE';
export type OutcomeChipSize = 'sm' | 'default' | 'lg';

export interface OutcomeChipProps {
  outcome: OutcomeType;
  label?: string; // Optional custom text, defaults to outcome name
  size?: OutcomeChipSize;
  showDot?: boolean;
  className?: string;
}

export const OutcomeChip: React.FC<OutcomeChipProps> = ({
  outcome,
  label,
  size = 'default',
  showDot = false,
  className = '',
}) => {
  // Styles based strictly on Section 2 design tokens
  const outcomeConfig: Record<
    OutcomeType,
    { bg: string; text: string; dot: string; defaultLabel: string }
  > = {
    ACCEPT: {
      bg: 'bg-[#DCFCE7]',
      text: 'text-[#15803D]',
      dot: 'bg-[#15803D]',
      defaultLabel: 'ACCEPT',
    },
    REJECT: {
      bg: 'bg-[#FEE2E2]',
      text: 'text-[#B91C1C]',
      dot: 'bg-[#B91C1C]',
      defaultLabel: 'REJECT',
    },
    HOLD: {
      bg: 'bg-[#FEF3C7]',
      text: 'text-[#B45309]',
      dot: 'bg-[#B45309]',
      defaultLabel: 'HOLD',
    },
    ESCALATE: {
      bg: 'bg-[#EDE9FE]',
      text: 'text-[#6D28D9]',
      dot: 'bg-[#6D28D9]',
      defaultLabel: 'ESCALATE',
    },
  };

  const sizeClasses: Record<OutcomeChipSize, string> = {
    sm: 'text-[10.5px] px-2 py-0.5 tracking-wider gap-1',
    default: 'text-[12px] px-2.5 py-1 tracking-wider gap-1.5',
    lg: 'text-[14px] px-3.5 py-1.5 tracking-wider font-bold gap-2',
  };

  const config = outcomeConfig[outcome];
  const displayText = label || config.defaultLabel;

  return (
    <span
      className={`inline-flex items-center justify-center font-bold uppercase rounded-full select-none ${config.bg} ${config.text} ${sizeClasses[size]} ${className}`}
      role="status"
      aria-label={`Outcome: ${displayText}`}
    >
      {showDot && (
        <span
          className={`w-1.5 h-1.5 rounded-full shrink-0 ${config.dot}`}
          aria-hidden="true"
        />
      )}
      <span>{displayText}</span>
    </span>
  );
};
