import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import { AppShell } from "../components/AppShell";
import { Button, ErrorState, Icon, Note, Spinner } from "../components/ui";

interface AuditRow {
  id: number; at: string; actor_label: string; actor: number | null;
  action: string; entity: string; entity_id: string | null;
  before: unknown; after: unknown;
}

export function AuditPage() {
  const { t, lang } = useSession();
  const [query, setQuery] = useState("");
  const [applied, setApplied] = useState("");
  const [showAll, setShowAll] = useState(false);
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit", applied],
    queryFn: () => api.get<{ rows: AuditRow[]; q: string; can_export: boolean }>(`/api/audit?q=${encodeURIComponent(applied)}`),
  });

  if (isLoading) return <AppShell title={t("audit.title")} active="audit"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("audit.title")} active="audit"><ErrorState message={(error as Error)?.message || "Forbidden"} /></AppShell>;

  return (
    <AppShell title={t("audit.title")} subtitle={t("audit.immutable")} active="audit">
      <div className="card" style={{ marginBottom: 18 }}>
        <div className="pad-sm">
          <form
            className="row"
            style={{ flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}
            onSubmit={(event) => { event.preventDefault(); setApplied(query.trim()); }}
          >
            <div className="field" style={{ flex: "3 1 260px", margin: 0 }}>
              <label htmlFor="audit-q">{t("common.search")}</label>
              <input
                id="audit-q"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={lang === "en" ? "Search by action (e.g. decision.computed, override.created) or actor…" : "অ্যাকশন বা ব্যবহারকারীর নাম দিয়ে খুঁজুন…"}
              />
            </div>
            <div className="btnrow" style={{ margin: 0, gap: 8 }}>
              <button className="btn primary" type="submit">{t("common.filter")}</button>
              {applied ? <button className="btn ghost" type="button" onClick={() => { setQuery(""); setApplied(""); }}>{lang === "en" ? "Reset" : "রিসেট"}</button> : null}
            </div>
            {data.can_export ? (
              <div style={{ marginLeft: "auto" }}>
                <a className="btn primary" href="/api/audit.csv"><Icon name="download" size={14} /><span>{lang === "en" ? "Export Immutable CSV" : "অপরিবর্তনীয় সিএসভি ডাউনলোড"}</span></a>
              </div>
            ) : null}
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-h" style={{ justifyContent: "space-between" }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
            <span>{t("audit.title")}</span>
            <span className="badge badge-neutral" style={{ fontSize: 11 }}>{data.rows.length} {lang === "en" ? "events recorded" : "টি ইভেন্ট সংরক্ষিত"}</span>
          </div>
          <div className="right">
            <button className="btn sm ghost" type="button" onClick={() => setShowAll((value) => !value)}>
              <Icon name="code" size={13} /><span>{lang === "en" ? "Toggle All Payloads" : "সব পেলোড টগল করুন"}</span>
            </button>
          </div>
        </div>

        {data.rows.length ? (
          <div className="tblwrap">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 50 }}>#</th>
                  <th style={{ width: 170 }}>{t("common.time")}</th>
                  <th style={{ width: 160 }}>{t("audit.actor")}</th>
                  <th style={{ width: 180 }}>{t("audit.action")}</th>
                  <th style={{ width: 130 }}>{t("audit.entity")}</th>
                  <th>{lang === "en" ? "Audit Payload (Before → After)" : "অডিট পেলোড (আগে → পরে)"}</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => <AuditRowView key={row.id} row={row} showAll={showAll} />)}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="pad">
            <Note tone="info"><b>{lang === "en" ? "No matching events" : "কোনো ইভেন্ট মেলেনি"}</b>{applied ? ` — ${lang === "en" ? "query" : "কোয়েরি"}: “${applied}”` : null}</Note>
          </div>
        )}
      </div>

      <div className="note info" style={{ marginTop: 16 }}>
        <Icon name="lock" size={14} /> <b>{t("audit.immutable")}</b> — {lang === "en"
          ? "Events are append-only. No update or delete path exists in the application, and the audit chain is exportable only by an Admin."
          : "ইভেন্টগুলো কেবল সংযোজিত হয়। অ্যাপ্লিকেশনে আপডেট বা ডিলিটের কোনো পথ নেই।"}
      </div>
    </AppShell>
  );
}

function AuditRowView({ row, showAll }: { row: AuditRow; showAll: boolean }) {
  const [open, setOpen] = useState(false);
  const expanded = showAll || open;
  const hasPayload = row.before != null || row.after != null;

  return (
    <>
      <tr>
        <td className="mono dim">{row.id}</td>
        <td className="small mono dim" style={{ whiteSpace: "nowrap" }}>{row.at}</td>
        <td className="small"><span className="badge badge-neutral">{row.actor_label}</span></td>
        <td className="small mono" style={{ fontWeight: 600 }}>{row.action}</td>
        <td className="small"><span className="mono dim">{row.entity}</span>{row.entity_id ? <span className="dim">#{row.entity_id}</span> : null}</td>
        <td>
          {hasPayload ? (
            <button className="btn sm ghost" type="button" onClick={() => setOpen((value) => !value)} style={{ fontSize: 11 }}>
              <Icon name="code" size={12} /><span>{expanded ? "Hide" : "Show"} payload</span>
            </button>
          ) : <span className="dim small">—</span>}
          {expanded && hasPayload ? (
            <pre className="mono" style={{ fontSize: 10.5, margin: "6px 0 0", background: "var(--subtle)", padding: 8, borderRadius: 4, maxWidth: 520, overflow: "auto", maxHeight: 260 }}>
              {JSON.stringify({ before: row.before, after: row.after }, null, 2)}
            </pre>
          ) : null}
        </td>
      </tr>
    </>
  );
}
