import type { ReactNode } from "react";
import { useSession } from "../../lib/session";
import { Icon } from "./icons";

const STATUS_TONES: Record<string, string> = {
  open: "info",
  decided: "success",
  reopened: "warning",
  archived: "neutral",
  pending: "warning",
  pending_approval: "warning",
  ok: "success",
  failed: "danger",
  not_inferred: "neutral",
  needs_retake: "warning",
  reviewed_clean: "success",
  confirmed_defects: "danger",
  active: "success",
  disabled: "neutral",
  proposed: "ai",
  confirmed: "confirmed",
  rejected: "rejected",
  done: "success",
  not_required: "neutral",
  in_progress: "info",
};

export function Badge({
  children,
  tone = "neutral",
  dot = false,
  icon,
  title,
}: {
  children: ReactNode;
  tone?: string;
  dot?: boolean;
  icon?: string;
  title?: string;
}) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {dot ? <span className="dot" aria-hidden="true" /> : null}
      {icon ? <Icon name={icon} size={13} /> : null}
      {children}
    </span>
  );
}

export function DecisionBadge({ outcome, label }: { outcome: string; label?: string }) {
  return (
    <span className={`badge decision-badge decision-${outcome.toLowerCase()}`}>
      <span className="dot" aria-hidden="true" />
      {label ?? outcome}
    </span>
  );
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const { t } = useSession();
  const tone = STATUS_TONES[status] || "neutral";
  const text = label || (STATUS_TONES[status] ? t(`status.${status}`) : status);
  return <Badge tone={tone} dot>{text}</Badge>;
}
