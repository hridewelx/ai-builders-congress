import * as Lucide from "lucide-react";
import type { ComponentType, ReactNode } from "react";
import { useSession } from "../lib/session";
import { num } from "../lib/format";

const ALIASES: Record<string, string> = {
  "circle-check": "CircleCheck",
  "circle-x": "CircleX",
  "circle-alert": "CircleAlert",
  "check-circle": "CircleCheck",
  "x-circle": "CircleX",
  "alert-circle": "CircleAlert",
  "alert-octagon": "OctagonAlert",
  "triangle-alert": "TriangleAlert",
  "plus-circle": "CirclePlus",
  "git-commit": "GitCommit",
  "git-branch": "GitBranch",
  "git-pull-request": "GitPullRequest",
  "panel-left-close": "PanelLeftClose",
  "panel-left-open": "PanelLeftOpen",
  "maximize-2": "Maximize2",
  "mouse-pointer-2": "MousePointer2",
  "refresh-cw": "RefreshCw",
  "rotate-ccw": "RotateCcw",
  "list-filter": "ListFilter",
  "circle-dot": "CircleDot",
  "square-check": "SquareCheck",
  "square-x": "SquareX",
  "badge-check": "BadgeCheck",
  "arrow-up-right": "ArrowUpRight",
  "arrow-up-down": "ArrowUpDown",
  "user-plus": "UserPlus",
  "book-open": "BookOpen",
  "sliders": "SlidersHorizontal",
  "list": "List",
  "grid": "Grid2x2",
  "check": "Check",
  "loader-circle": "LoaderCircle",
  "scan-line": "ScanLine",
  "file-text": "FileText",
  "clipboard-check": "ClipboardCheck",
  "external-link": "ExternalLink",
  "hard-drive": "HardDrive",
  "user-check": "UserCheck",
  "package-check": "PackageCheck",
  "panel-top": "PanelTop",
  "zoom-in": "ZoomIn",
  "zoom-out": "ZoomOut",
};

function componentFor(name: string): ComponentType<{ size?: number; strokeWidth?: number; className?: string }> {
  const key = ALIASES[name] || name.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join("");
  const found = (Lucide as unknown as Record<string, ComponentType<never>>)[key];
  return (found || Lucide.Circle) as ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
}

export function Icon({
  name,
  size = 18,
  stroke = 1.8,
  className = "icon",
}: {
  name: string;
  size?: number;
  stroke?: number;
  className?: string;
}) {
  const Component = componentFor(name);
  return <Component size={size} strokeWidth={stroke} className={className} />;
}

type ButtonProps = {
  children: ReactNode;
  icon?: string;
  iconAfter?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "subtle";
  size?: "sm" | "md" | "lg";
  href?: string;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  title?: string;
  className?: string;
};

export function Button({
  children,
  icon,
  iconAfter,
  variant = "secondary",
  size,
  href,
  onClick,
  type = "button",
  disabled,
  title,
  className = "",
}: ButtonProps) {
  const classes = ["btn", variant !== "secondary" ? variant : "", size || "", disabled ? "is-disabled" : "", className]
    .filter(Boolean)
    .join(" ");
  const body = (
    <>
      {icon ? <Icon name={icon} size={16} /> : null}
      <span>{children}</span>
      {iconAfter ? <Icon name={iconAfter} size={16} /> : null}
    </>
  );
  if (href && !disabled) {
    return (
      <a className={classes} href={href} title={title}>
        {body}
      </a>
    );
  }
  return (
    <button className={classes} type={type} onClick={onClick} disabled={disabled} title={title}>
      {body}
    </button>
  );
}

export function IconButton({
  name,
  label,
  onClick,
  size = 18,
}: {
  name: string;
  label: string;
  onClick?: () => void;
  size?: number;
}) {
  return (
    <button className="icon-btn" type="button" onClick={onClick} aria-label={label} title={label}>
      <Icon name={name} size={size} />
    </button>
  );
}

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

export function MetricCard({
  label,
  value,
  unit,
  hint,
  tone,
  href,
  icon,
  badge,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: ReactNode;
  tone?: string;
  href?: string;
  icon?: string;
  badge?: ReactNode;
}) {
  const { lang } = useSession();
  const inner = (
    <>
      <div className="kpi-head">
        <div className="lbl">
          {icon ? <Icon name={icon} size={14} /> : null}
          <span>{label}</span>
        </div>
        {badge ? <span className="kpi-badge">{badge}</span> : null}
      </div>
      <div className="n">
        {num(value, lang)}
        {unit ? <small> {unit}</small> : null}
      </div>
      {hint ? (
        <div className="meta">
          <span className="kpi-hint">{hint}</span>
        </div>
      ) : null}
    </>
  );
  const classes = `kpi${tone ? ` is-${tone}` : ""}${href ? " kpi-link" : ""}`;
  if (href) {
    return (
      <a className={classes} href={href}>
        {inner}
      </a>
    );
  }
  return <div className={classes}>{inner}</div>;
}

export type PipelineStep = {
  label: string;
  value?: ReactNode;
  state?: string;
  title?: string;
};

export function Pipeline({ steps, compact = false }: { steps: PipelineStep[]; compact?: boolean }) {
  return (
    <ol className={`pipeline${compact ? " is-compact" : ""}`} aria-label="Pipeline">
      {steps.map((step, index) => {
        const state = step.state || "not-started";
        return (
          <li className={`pipeline-step is-${state}`} key={`${step.label}-${index}`}>
            <span className="pipeline-dot" aria-hidden="true">
              {state === "done" ? (
                <Icon name="check" size={12} stroke={2.4} />
              ) : state === "failed" ? (
                <Icon name="x" size={12} stroke={2.4} />
              ) : state === "blocked" || state === "stale" ? (
                <Icon name="triangle-alert" size={12} stroke={2.2} />
              ) : (
                <span>{index + 1}</span>
              )}
            </span>
            <span className="pipeline-copy">
              <span className="pipeline-label">{step.label}</span>
              {step.value ? (
                <span className="pipeline-value" title={step.title}>
                  {step.value}
                </span>
              ) : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function EmptyState({
  title,
  body,
  icon = "search",
  actionLabel,
  actionHref,
}: {
  title: string;
  body?: string;
  icon?: string;
  actionLabel?: string;
  actionHref?: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon" aria-hidden="true">
        <Icon name={icon} size={22} />
      </span>
      <b>{title}</b>
      {body ? <p>{body}</p> : null}
      {actionLabel && actionHref ? (
        <a className="btn sm" href={actionHref}>
          {actionLabel}
        </a>
      ) : null}
    </div>
  );
}

export function Timeline({
  items,
}: {
  items: Array<{ title: string; actor?: string; datetime?: string; meta?: string }>;
}) {
  const { lang } = useSession();
  if (!items.length) {
    return (
      <ul className="timeline">
        <li className="timeline-item">
          <div className="m">No events yet.</div>
        </li>
      </ul>
    );
  }
  return (
    <ul className="timeline">
      {items.map((item, index) => (
        <li className="timeline-item" key={`${item.title}-${index}`}>
          <span className="timeline-dot" aria-hidden="true" />
          <div className="timeline-body">
            <div className="a">{item.title}</div>
            <div className="m">
              {item.actor ? <span className="timeline-actor">{item.actor}</span> : null}
              {item.datetime ? (
                <>
                  {item.actor ? <span aria-hidden="true"> · </span> : null}
                  <time dateTime={item.datetime}>{dtLocalSafe(item.datetime, lang)}</time>
                </>
              ) : null}
              {item.meta ? <span> · {item.meta}</span> : null}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

function dtLocalSafe(value: string, lang: "en" | "bn") {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(lang === "bn" ? "bn-BD" : "en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Asia/Dhaka",
  }).format(date);
}

export function Field({
  label,
  children,
  hint,
  error,
  required,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
  error?: string;
  required?: boolean;
}) {
  return (
    <div className={`field${error ? " has-error" : ""}`}>
      <label>
        {label} {required ? <span className="req" aria-hidden="true">*</span> : null}
      </label>
      {children}
      {error ? <div className="field-error">{error}</div> : null}
      {hint ? <div className="hint">{hint}</div> : null}
    </div>
  );
}

export function Note({
  children,
  tone = "info",
  role,
}: {
  children: ReactNode;
  tone?: "info" | "ok" | "bad" | "warn";
  role?: "alert" | "status";
}) {
  return (
    <div className={`note ${tone}`} role={role}>
      {children}
    </div>
  );
}

export function AiTag() {
  const { t } = useSession();
  return (
    <span className="demo-tag demo-tag-ai" title={t("dash.illustrative")}>
      <Icon name="info" size={12} />
      {t("dash.illustrative")}
    </span>
  );
}

export function DemoTag({ label }: { label?: string }) {
  const { t } = useSession();
  return (
    <span className="demo-tag demo-tag-demo">
      <span className="demo-dot" aria-hidden="true" />
      {label || t("lot.demo_data")}
    </span>
  );
}

export function Dialog({
  id,
  title,
  open,
  onClose,
  children,
  actions,
  small = false,
}: {
  id?: string;
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  actions?: ReactNode;
  small?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="dialog-backdrop" role="presentation" onClick={onClose}>
      <div
        className={`dialog${small ? " dialog-sm" : ""} is-open`}
        id={id}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="dialog-head">
          <h2>{title}</h2>
          <IconButton name="x" label="Close" onClick={onClose} />
        </div>
        <div className="dialog-body">{children}</div>
        {actions ? <div className="dialog-actions">{actions}</div> : null}
      </div>
    </div>
  );
}

export function Toast({
  message,
  tone = "success",
  onClose,
}: {
  message: string;
  tone?: "success" | "danger" | "warning" | "info";
  onClose?: () => void;
}) {
  return (
    <div className={`toast is-${tone} is-visible`} role="status">
      <span className="toast-icon">
        <Icon name={tone === "success" ? "circle-check" : tone === "danger" ? "circle-x" : "info"} size={18} />
      </span>
      <span>{message}</span>
      {onClose ? <IconButton name="x" label="Dismiss" size={15} onClick={onClose} /> : null}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <Icon name="loader-circle" size={18} className="icon spin" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="error-state" role="alert">
      <span className="error-icon" aria-hidden="true">
        <Icon name="alert-octagon" size={24} />
      </span>
      <div>
        <b>Something went wrong</b>
        <p>{message}</p>
      </div>
    </div>
  );
}

export function ProgressBar({ value, tone }: { value: number; tone?: string }) {
  return (
    <div className={`bar${tone ? ` bar-${tone}` : ""}`}>
      <i style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}
