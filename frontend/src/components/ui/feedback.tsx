import type { ReactNode } from "react";
import { useSession } from "../../lib/session";
import { Icon } from "./icons";
import { IconButton } from "./buttons";

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
