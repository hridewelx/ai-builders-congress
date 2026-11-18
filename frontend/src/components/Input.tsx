import React, { useId } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helpText?: string;
  mono?: boolean;
  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helpText,
      mono = false,
      leftAddon,
      rightAddon,
      id,
      className = '',
      disabled,
      required,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const helpId = `${inputId}-help`;

    return (
      <div className="w-full flex flex-col gap-1.5 text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="text-[13px] font-semibold text-[#0F172A] flex items-center justify-between"
          >
            <span>
              {label}
              {required && <span className="text-[#B91C1C] ml-1">*</span>}
            </span>
          </label>
        )}

        <div className="relative flex items-center">
          {leftAddon && (
            <div className="absolute left-3.5 z-10 flex items-center pointer-events-none text-[#64748B]">
              {leftAddon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            disabled={disabled}
            required={required}
            aria-invalid={!!error}
            aria-describedby={error ? errorId : helpText ? helpId : undefined}
            className={`
              w-full h-11 min-h-[44px] px-3.5
              bg-white text-[#0F172A] text-[14px]
              rounded-[10px] border transition-colors
              placeholder:text-[#94A3B8]
              focus:outline-none focus:ring-2 focus:ring-offset-1
              disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] disabled:cursor-not-allowed
              ${mono ? 'font-mono tracking-tight text-[13px]' : 'font-sans'}
              ${leftAddon ? 'pl-10' : ''}
              ${rightAddon ? 'pr-10' : ''}
              ${
                error
                  ? 'border-[#B91C1C] focus:border-[#B91C1C] focus:ring-[#FEE2E2] bg-[#FFFBFB]'
                  : 'border-[#E2E8F0] focus:border-[#1F4FD8] focus:ring-[#EAF0FF] hover:border-[#CBD5E1]'
              }
              ${className}
            `}
            {...props}
          />

          {rightAddon && (
            <div className="absolute right-3.5 z-10 flex items-center pointer-events-none text-[#64748B]">
              {rightAddon}
            </div>
          )}
        </div>

        {error ? (
          <p id={errorId} className="text-[12px] font-medium text-[#B91C1C] flex items-center gap-1">
            <span>{error}</span>
          </p>
        ) : helpText ? (
          <p id={helpId} className="text-[12px] text-[#64748B]">
            {helpText}
          </p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = 'Input';
