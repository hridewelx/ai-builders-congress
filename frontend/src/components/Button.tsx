import React from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'compute' | 'destructive' | 'outline';
export type ButtonSize = 'sm' | 'default' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'default',
  fullWidth = false,
  leftIcon,
  rightIcon,
  loading = false,
  disabled,
  className = '',
  ...props
}) => {
  // Base classes: 44px min touch target on default/lg, rounded 12px (radius tokens)
  const baseClasses =
    'inline-flex items-center justify-center font-medium transition-colors select-none focus:outline-none focus:ring-2 focus:ring-offset-2 active:scale-[0.98] disabled:active:scale-100 disabled:cursor-not-allowed rounded-[12px]';

  const sizeClasses: Record<ButtonSize, string> = {
    sm: 'h-9 min-h-[36px] px-3 text-[13px] gap-1.5',
    default: 'h-11 min-h-[44px] px-4 text-[14px] font-semibold gap-2', // Meets 44px touch target
    lg: 'h-12 min-h-[48px] px-5 text-[15px] font-semibold gap-2.5',
  };

  const variantClasses: Record<ButtonVariant, string> = {
    primary:
      'bg-[#1F4FD8] text-white hover:bg-[#183FB0] active:bg-[#13328D] focus:ring-[#1F4FD8] shadow-sm disabled:bg-[#CBD5E1] disabled:text-[#94A3B8]',
    secondary:
      'bg-white text-[#1F4FD8] border-[1.5px] border-[#1F4FD8] hover:bg-[#EAF0FF] active:bg-[#D5E3FF] focus:ring-[#1F4FD8] disabled:border-[#CBD5E1] disabled:text-[#94A3B8] disabled:bg-white',
    ghost:
      'bg-transparent text-[#0F172A] hover:bg-[#F1F5F9] active:bg-[#E2E8F0] focus:ring-[#64748B] disabled:text-[#94A3B8]',
    compute:
      'bg-[#15803D] text-white hover:bg-[#166534] active:bg-[#14532D] focus:ring-[#15803D] shadow-sm disabled:bg-[#CBD5E1] disabled:text-[#94A3B8]',
    destructive:
      'bg-[#B91C1C] text-white hover:bg-[#991B1B] active:bg-[#7F1D1D] focus:ring-[#B91C1C] shadow-sm disabled:bg-[#CBD5E1] disabled:text-[#94A3B8]',
    outline:
      'bg-white text-[#0F172A] border border-[#E2E8F0] hover:bg-[#F8FAFC] active:bg-[#F1F5F9] focus:ring-[#1F4FD8] disabled:border-[#E2E8F0] disabled:text-[#94A3B8]',
  };

  const widthClass = fullWidth ? 'w-full' : '';

  return (
    <button
      disabled={disabled || loading}
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${widthClass} ${className}`}
      {...props}
    >
      {loading ? (
        <svg
          className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : (
        leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>
      )}
      <span>{children}</span>
      {!loading && rightIcon && <span className="inline-flex shrink-0">{rightIcon}</span>}
    </button>
  );
};
