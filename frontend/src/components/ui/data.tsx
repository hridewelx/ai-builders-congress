import type { ReactNode } from "react";
import { num } from "../../lib/format";
import { useSession } from "../../lib/session";
import { Icon } from "./icons";

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
