import React from 'react';
import { AlertTriangle, Info, AlertCircle, CheckCircle2, X } from 'lucide-react';

export type BannerVariant = 'warn' | 'info' | 'error' | 'ok' | 'escalate';

export interface BannerProps {
  variant?: BannerVariant;
  title?: string;
  description?: React.ReactNode;
  children?: React.ReactNode;
  requestId?: string;
  actionLabel?: string;
  onAction?: () => void;
  onClose?: () => void;
  className?: string;
}

export const Banner: React.FC<BannerProps> = ({
  variant = 'info',
  title,
  description,
  children,
  requestId,
  actionLabel,
  onAction,
  onClose,
  className = '',
}) => {
  const variantConfig: Record<
    BannerVariant,
    { bg: string; border: string; text: string; iconColor: string; Icon: React.ElementType }
  > = {
    warn: {
      bg: 'bg-[#FEF3C7]',
      border: 'border-[#FDE68A]',
      text: 'text-[#92400E]',
      iconColor: 'text-[#B45309]',
      Icon: AlertTriangle,
    },
    info: {
      bg: 'bg-[#E0F2FE]',
      border: 'border-[#BAE6FD]',
      text: 'text-[#075985]',
      iconColor: 'text-[#0369A1]',
      Icon: Info,
    },
    error: {
      bg: 'bg-[#FEE2E2]',
      border: 'border-[#FECACA]',
      text: 'text-[#991B1B]',
      iconColor: 'text-[#B91C1C]',
      Icon: AlertCircle,
    },
    ok: {
      bg: 'bg-[#DCFCE7]',
      border: 'border-[#BBF7D0]',
      text: 'text-[#166534]',
      iconColor: 'text-[#15803D]',
      Icon: CheckCircle2,
    },
    escalate: {
      bg: 'bg-[#EDE9FE]',
      border: 'border-[#DDD6FE]',
      text: 'text-[#5B21B6]',
      iconColor: 'text-[#6D28D9]',
      Icon: AlertTriangle,
    },
  };

  const config = variantConfig[variant];
  const { Icon } = config;

  return (
    <div
      role="alert"
      className={`relative flex items-start gap-3 p-3.5 rounded-[14px] border ${config.bg} ${config.border} ${config.text} text-[13.5px] leading-relaxed ${className}`}
    >
      <div className={`shrink-0 mt-0.5 ${config.iconColor}`}>
        <Icon className="w-5 h-5" aria-hidden="true" />
      </div>

      <div className="flex-1 min-w-0">
        {title && <div className="font-semibold mb-0.5">{title}</div>}
        {description && <div className="text-[13px] opacity-95">{description}</div>}
        {children}

        {requestId && (
          <div className="mt-1.5 flex items-center gap-1.5 font-mono text-[11px] opacity-80">
            <span className="font-sans font-medium">Request ID:</span>
            <code className="bg-white/60 px-1.5 py-0.5 rounded text-[11px] select-all">
              {requestId}
            </code>
          </div>
        )}

        {actionLabel && onAction && (
          <div className="mt-2">
            <button
              type="button"
              onClick={onAction}
              className="text-[12.5px] font-semibold underline underline-offset-2 hover:opacity-80 focus:outline-none"
            >
              {actionLabel}
            </button>
          </div>
        )}
      </div>

      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Dismiss banner"
          className="shrink-0 p-1 -mr-1 -mt-1 text-current opacity-70 hover:opacity-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-current"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
