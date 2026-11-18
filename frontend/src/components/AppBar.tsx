import React from 'react';
import { ChevronLeft } from 'lucide-react';

export interface AppBarProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  role?: 'Inspector' | 'Supervisor' | 'Admin' | string;
  onBack?: () => void;
  backLabel?: string;
  actions?: React.ReactNode;
  variant?: 'navy' | 'light';
  showStatusBarMock?: boolean;
  className?: string;
}

export const AppBar: React.FC<AppBarProps> = ({
  title,
  subtitle,
  role,
  onBack,
  backLabel,
  actions,
  variant = 'navy',
  showStatusBarMock = false,
  className = '',
}) => {
  const isNavy = variant === 'navy';

  return (
    <header
      className={`w-full select-none transition-colors ${
        isNavy
          ? 'bg-[#0B1F5C] text-white'
          : 'bg-white text-[#0B1F5C] border-b border-[#E2E8F0]'
      } ${className}`}
    >
      {/* Optional phone status bar mock for fidelity with 02-dashboard.png */}
      {showStatusBarMock && (
        <div
          className={`flex justify-between items-center px-5 pt-2 text-[12px] font-semibold tracking-tight ${
            isNavy ? 'text-white/80' : 'text-[#64748B]'
          }`}
        >
          <span>9:41</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
            <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
            <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between px-4 py-3 min-h-[56px] gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              aria-label={backLabel || 'Go back'}
              className={`p-1.5 -ml-1.5 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 ${
                isNavy
                  ? 'hover:bg-white/10 active:bg-white/20 text-white focus:ring-white/40'
                  : 'hover:bg-slate-100 active:bg-slate-200 text-[#0B1F5C] focus:ring-[#0B1F5C]/20'
              }`}
            >
              <ChevronLeft className="w-6 h-6 stroke-[2.2]" />
            </button>
          )}

          <div className="min-w-0">
            <h1
              className={`text-[19px] font-bold leading-tight truncate tracking-tight ${
                isNavy ? 'text-white' : 'text-[#0B1F5C]'
              }`}
            >
              {title}
            </h1>
            {subtitle && (
              <p
                className={`text-[12px] leading-tight truncate mt-0.5 ${
                  isNavy ? 'text-white/70' : 'text-[#64748B]'
                }`}
              >
                {subtitle}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {actions}

          {role && (
            <span
              className={`text-[12px] font-semibold px-2.5 py-1 rounded-full ${
                isNavy
                  ? 'bg-white/15 text-white backdrop-blur-sm'
                  : 'bg-[#EAF0FF] text-[#1F4FD8]'
              }`}
            >
              {role}
            </span>
          )}
        </div>
      </div>
    </header>
  );
};
