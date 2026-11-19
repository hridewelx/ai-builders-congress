import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useSession } from "../lib/session";
import { num } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { LotTabs } from "../components/LotTabs";
import { ReasonList } from "../components/ReasonList";
import {
  Button, DecisionBadge, ErrorState, Field, Icon, Note, Pipeline, Spinner, Toast,
} from "../components/ui";

interface DecisionData {
  lot: { id: number; lot_code: string; buyer_name: string; lot_size: number; status: string; critical_nonvisual_status: string; nonvisual_note: string | null };
  plan: { n: number; counting_mode: string } | null;
  decision: {
    id: number; sequence: number; outcome: string; primary_reason: string; reasons: string[];
    counts: Record<string, number>; class_limits: Record<string, { ac: number; re: number }>;
    completeness: { units_present: number; required_units: number; views_pending: number; evidence_bad: number };
    plan_snapshot: { counting_mode?: string } | null; snapshot_hash: string; engine_version: string;
    created_at: string; manual_inspection?: number; decided_by?: string;
  } | null;
  override: {
    id: number; status: string; final_disposition: string; reason: string; supervisor: string; supervisor_id: number;
    created_at: string; effective?: boolean;
    approval?: { decision: string; approver: string; created_at: string } | null;
  } | null;
  final: string | null;
  history: Array<{ id: number; sequence: number; outcome: string; decided_by: string; created_at: string; counts: Record<string, number> }>;
  progress: { units: number; required_units: number; views: number; reviewed: number };
  is_supervisor: boolean;
  can_write: boolean;
  user: { id: number };
}

const ERROR_TEXT: Record<string, string> = {
  self_approval: "You cannot approve your own override. A different active Supervisor must approve.",
  reason_short: "An override reason must be at least 20 characters of substantive explanation.",
  override_not_allowed: "Only ACCEPT or REJECT outcomes are overridable. HOLD, ESCALATE and failed critical non-visual checks cannot be overridden.",
  already_overridden: "This decision has already been overridden.",
  locked: "This lot is locked.",
};

export function DecisionPage() {
  const { lotId } = useParams();
  const id = Number(lotId);
  const { t, lang } = useSession();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["decision", id],
    queryFn: () => api.get<DecisionData>(`/api/lots/${id}/decision`),
  });
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [override, setOverride] = useState({ disposition: "OVERRIDE_REJECT", reason: "" });
  const [showError, setShowError] = useState("");

  if (isLoading) return <AppShell title={t("dec.title")} active="lots"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("dec.title")} active="lots"><ErrorState message={(error as Error)?.message || "Not found"} /></AppShell>;

  const { lot, decision, override: overrideRow, final, progress } = data;

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["decision", id] });
    await queryClient.invalidateQueries({ queryKey: ["lot", id] });
  };

  const compute = async () => {
    setBusy(true);
    setShowError("");
    try {
      await api.post(`/api/lots/${id}/decisions`, { note });
      setToast(t("flash.saved"));
      await refresh();
    } catch (caught) {
      const detail = caught instanceof ApiError ? String(caught.detail) : "";
      setShowError(ERROR_TEXT[detail] || t("err.failed"));
    } finally {
      setBusy(false);
    }
  };

  const submitOverride = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!decision) return;
    setBusy(true);
    setShowError("");
    try {
      await api.post(`/api/decisions/${decision.id}/override`, override);
      setToast(t("flash.saved"));
      await refresh();
    } catch (caught) {
      const detail = caught instanceof ApiError ? String(caught.detail) : "";
      setShowError(ERROR_TEXT[detail] || t("err.failed"));
    } finally {
      setBusy(false);
    }
  };

  const approve = async (approval: "approved" | "refused") => {
    if (!overrideRow) return;
    setBusy(true);
    try {
      await api.post(`/api/overrides/${overrideRow.id}/approval`, { decision: approval });
      setToast(t("flash.saved"));
      await refresh();
    } catch (caught) {
      const detail = caught instanceof ApiError ? String(caught.detail) : "";
      setShowError(ERROR_TEXT[detail] || t("err.failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell
      title={t("dec.title")}
      subtitle={`${lot.lot_code} · ${lot.buyer_name} · ${t("lots.size")} ${lot.lot_size}`}
      active="lots"
    >
      {toast ? <Toast message={toast} onClose={() => setToast("")} /> : null}
      <LotTabs lotId={id} isAdmin={false} />

      <Pipeline steps={[
        { label: lang === "en" ? "1. AI Detection" : "১. এআই শনাক্তকরণ", value: `${progress.views} ${lang === "en" ? "views" : "ভিউ"}`, state: progress.views ? "done" : "pending" },
        { label: lang === "en" ? "2. Human Review" : "২. মানুষ পর্যালোচনা", value: `${progress.reviewed} / ${progress.views} ${lang === "en" ? "reviewed" : "পর্যালোচিত"}`, state: progress.views && progress.reviewed === progress.views ? "done" : "active" },
        { label: lang === "en" ? "3. Decision Engine" : "৩. নির্ধারক ইঞ্জিন", value: decision ? t(`out.${final || decision.outcome}`) : (lang === "en" ? "Awaiting compute" : "গণনা বাকি"), state: decision ? "done" : "pending" },
      ]} />

      {showError ? (
        <div className="error-state" role="alert" style={{ marginBottom: 14 }}>
          <span className="error-icon"><Icon name="shield-alert" size={24} /></span>
          <div><b>{lang === "en" ? "Action refused" : "কাজ প্রত্যাখ্যাত"}</b><p>{showError}</p></div>
        </div>
      ) : null}

      {!decision ? (
        <div className="card">
          <div className="card-h">
            <h2>{t("dec.none")}</h2>
            <div className="right"><span className="badge badge-warning">{lang === "en" ? "Decision needed" : "সিদ্ধান্ত দরকার"}</span></div>
          </div>
          <div className="pad">
            <div className="grid cols-3" style={{ marginBottom: 16 }}>
              <div className="kpi"><div className="lbl">{t("lot.plan")}</div><div className="n" style={{ fontSize: 18 }}>{data.plan ? `${lang === "en" ? "Set" : "সেট"} (n=${data.plan.n})` : (lang === "en" ? "Missing" : "নেই")}</div></div>
              <div className="kpi"><div className="lbl">{t("common.units")}</div><div className="n" style={{ fontSize: 20 }}>{progress.units} / {progress.required_units || "—"}</div></div>
              <div className="kpi"><div className="lbl">{t("lot.views_reviewed")}</div><div className="n" style={{ fontSize: 20 }}>{progress.reviewed} / {progress.views}</div></div>
            </div>
            {data.can_write ? (
              <div>
                <Field label={t("common.notes")} hint={t("common.optional")}>
                  <input value={note} onChange={(event) => setNote(event.target.value)} placeholder={lang === "en" ? "e.g. Initial lot acceptance computation" : "নোট লিখুন"} />
                </Field>
                <Button variant="primary" icon="cpu" disabled={busy} onClick={compute}>{t("dec.compute")}</Button>
              </div>
            ) : (
              <Note tone="info"><Icon name="shield" size={15} /> {lang === "en" ? "A Supervisor or Inspector with write permissions can compute the decision." : "সুপারভাইজার বা ক্ষমতাপ্রাপ্ত ইন্সপেক্টর সিদ্ধান্ত গণনা করতে পারেন।"}</Note>
            )}
          </div>
        </div>
      ) : (
        <div className="stack">
          <div className="card" style={{ borderLeft: `5px solid ${decision.outcome === "ACCEPT" ? "var(--green)" : decision.outcome === "REJECT" ? "var(--red)" : decision.outcome === "HOLD" ? "var(--amber)" : "var(--blue)"}`, padding: 18 }}>
            <div className="between" style={{ flexWrap: "wrap", gap: 14 }}>
              <div style={{ minWidth: 240 }}>
                <div className="row" style={{ gap: 8, alignItems: "center", marginBottom: 4 }}>
                  <span className="small dim" style={{ letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700 }}>
                    {lang === "en" ? "System recommendation" : "সিস্টেমের সুপারিশ"} · #{num(decision.sequence, lang)}
                  </span>
                </div>
                <div className="row" style={{ gap: 10, alignItems: "center", marginTop: 6 }}>
                  <DecisionBadge outcome={decision.outcome} label={t(`out.${decision.outcome}`)} />
                  {decision.manual_inspection ? <span className="badge badge-warning">{t("dec.manual")}</span> : null}
                </div>
                <p className="small dim" style={{ margin: "8px 0 0" }}>
                  <b>{lang === "en" ? "Primary reason" : "প্রধান কারণ"}:</b>{" "}
                  <span className="mono">{decision.primary_reason}</span> — {t(`out.${decision.outcome}`)}
                </p>
              </div>
              <div style={{ textAlign: "right", minWidth: 200 }}>
                <div className="small dim" style={{ letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, marginBottom: 4 }}>{lang === "en" ? "Final disposition" : "চূড়ান্ত সিদ্ধান্ত"}</div>
                <div style={{ marginTop: 4 }}><DecisionBadge outcome={final!} label={t(`out.${final}`)} /></div>
                {overrideRow ? overrideRow.status === "pending_approval" ? <div className="small bold" style={{ color: "var(--amber-ink)", marginTop: 6 }}><Icon name="clock" size={12} /> {lang === "en" ? "Pending supervisor approval" : "সুপারভাইজার অনুমোদন বাকি"}</div> : <div className="small dim" style={{ marginTop: 6 }}><Icon name="check" size={12} /> {t("dec.overridden")} ({lang === "en" ? "effective" : "কার্যকর"})</div> : null}
              </div>
            </div>
            {data.can_write ? (
              <div style={{ borderTop: "1px dashed var(--line)", marginTop: 14, paddingTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
                <Button size="sm" variant="subtle" icon="refresh-cw" disabled={busy} onClick={compute}>{lang === "en" ? "Recompute decision" : "পুনরায় গণনা"}</Button>
                <span className="small dim">{lang === "en" ? "Appends a new immutable decision row. Earlier rows are preserved in audit." : "নতুন অপরিবর্তনীয় সারি যোগ হয়। আগের সব সারি অডিটে সংরক্ষিত থাকে।"}</span>
              </div>
            ) : null}
          </div>

          {overrideRow ? (
            <div className="card" style={{ border: `1.5px solid ${overrideRow.status === "pending_approval" ? "var(--amber-line)" : "var(--green-line)"}` }}>
              <div className="card-h">
                <h2>{t("dec.override")}</h2>
                <div className="right">{overrideRow.status === "pending_approval" ? <span className="badge badge-warning"><span className="dot" />{lang === "en" ? "HIGH RISK · PENDING APPROVAL" : "উচ্চ ঝুঁকি · অনুমোদন বাকি"}</span> : <span className="badge badge-success"><span className="dot" />{lang === "en" ? "EFFECTIVE" : "কার্যকর"}</span>}</div>
              </div>
              <div className="pad-sm">
                <div className="row" style={{ gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 8 }}>
                  <span className="small"><b>{lang === "en" ? "Overriding Supervisor" : "ওভাররাইডকারী সুপারভাইজার"}:</b> {overrideRow.supervisor}</span>
                  <span className="small dim">· {overrideRow.created_at}</span>
                  <span className="badge badge-neutral">Target: {overrideRow.final_disposition.replace("OVERRIDE_", "")}</span>
                </div>
                <Note tone="info"><b>{lang === "en" ? "Reason for human judgment" : "মানব বিচারের কারণ"}:</b><p style={{ margin: "4px 0 0", fontStyle: "italic" }}>"{overrideRow.reason}"</p></Note>
                {overrideRow.status === "pending_approval" ? (
                  data.is_supervisor && overrideRow.supervisor_id !== data.user.id ? (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 6, padding: 12, marginTop: 8 }}>
                      <div className="small bold" style={{ marginBottom: 8 }}>{lang === "en" ? "Second Supervisor Action" : "দ্বিতীয় সুপারভাইজারের সিদ্ধান্ত"}:</div>
                      <div className="row" style={{ gap: 8 }}>
                        <Button size="sm" variant="primary" icon="check" disabled={busy} onClick={() => approve("approved")}>{lang === "en" ? "Approve override" : "ওভাররাইড অনুমোদন"}</Button>
                        <Button size="sm" variant="danger" icon="x" disabled={busy} onClick={() => approve("refused")}>{lang === "en" ? "Refuse override" : "ওভাররাইড প্রত্যাখ্যান"}</Button>
                      </div>
                    </div>
                  ) : data.is_supervisor ? (
                    <Note tone="info"><Icon name="lock" size={14} /> {lang === "en" ? "Self-approval forbidden: you initiated this override. A different active Supervisor must approve it." : "স্ব-অনুমোদন নিষিদ্ধ: আপনি এই ওভাররাইড শুরু করেছেন।"}</Note>
                  ) : <div className="small dim">{lang === "en" ? "Awaiting review and approval by a Supervisor." : "সুপারভাইজারের অনুমোদনের অপেক্ষায়।"}</div>
                ) : overrideRow.approval ? (
                  <Note tone={overrideRow.approval.decision === "approved" ? "ok" : "bad"}>
                    <Icon name={overrideRow.approval.decision === "approved" ? "check-circle" : "x-circle"} size={15} /> {overrideRow.approval.decision === "approved" ? (lang === "en" ? "Approved" : "অনুমোদিত") : (lang === "en" ? "Refused" : "প্রত্যাখ্যাত")} {lang === "en" ? "by" : "দ্বারা"} {overrideRow.approval.approver} · {overrideRow.approval.created_at}
                  </Note>
                ) : null}
              </div>
            </div>
          ) : null}

          <div className="split">
            <div className="stack">
              <div className="card">
                <div className="card-h"><h2>{t("dec.counts")}</h2><div className="right"><span className="chip">{decision.plan_snapshot?.counting_mode || "—"}</span></div></div>
                <div className="tblwrap">
                  <table className="table">
                    <thead><tr><th>{lang === "en" ? "Defect Class" : "ত্রুটি শ্রেণি"}</th><th className="num">{t("dec.count")}</th><th className="num">Ac</th><th className="num">Re</th><th className="right">{t("dec.result")}</th></tr></thead>
                    <tbody>
                      {(["critical", "major", "minor"] as const).map((key) => {
                        const limit = decision.class_limits[key];
                        return (
                          <tr key={key}>
                            <td><span className={`badge ${key}`}>{t(`plan.${key}`)}</span></td>
                            <td className="num bold mono">{decision.counts[key] ?? 0}</td>
                            <td className="num dim mono">{limit?.ac ?? "—"}</td>
                            <td className="num dim mono">{limit?.re ?? "—"}</td>
                            <td className="right">{limit ? (decision.counts[key] ?? 0) < limit.re ? <span className="badge badge-success">PASS</span> : <span className="badge badge-danger">FAIL</span> : <span className="dim">—</span>}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="pad-sm"><Note tone="info">{lang === "en" ? "Deterministic rule: only human-confirmed defects count. AI proposals never count." : "নির্ধারক নিয়ম: শুধুমাত্র মানুষ-নিশ্চিত ত্রুটি গণনা হয়। এআই প্রস্তাব কখনো গণনা হয় না।"}</Note></div>
              </div>

              <div className="card">
                <div className="card-h"><h2>{t("common.reasons")}</h2><div className="right"><span className="mono small dim">{decision.engine_version}</span></div></div>
                <div className="pad-sm"><ReasonList codes={decision.reasons} /></div>
              </div>

              <div className="card">
                <div className="card-h"><h2>{t("dec.completeness")}</h2></div>
                <div className="pad-sm">
                  <div className="grid cols-3" style={{ gap: 10, marginBottom: 12 }}>
                    <div className="kpi" style={{ padding: 10 }}><div className="lbl">{t("common.units")}</div><div className="n" style={{ fontSize: 18 }}>{decision.completeness.units_present} / {decision.completeness.required_units}</div></div>
                    <div className="kpi" style={{ padding: 10 }}><div className="lbl">{lang === "en" ? "Pending views" : "বাকি ভিউ"}</div><div className="n" style={{ fontSize: 18 }}>{decision.completeness.views_pending}</div></div>
                    <div className="kpi" style={{ padding: 10 }}><div className="lbl">{lang === "en" ? "Evidence errors" : "প্রমাণ ত্রুটি"}</div><div className="n" style={{ fontSize: 18 }}>{decision.completeness.evidence_bad}</div></div>
                  </div>
                  <div className="small dim"><div><b>{lang === "en" ? "Snapshot SHA-256" : "স্ন্যাপশট SHA-256"}:</b> <span className="mono">{decision.snapshot_hash}</span></div></div>
                </div>
              </div>
            </div>

            <div className="stack">
              <div className="card">
                <div className="card-h"><h2>{t("lot.nonvisual")}</h2><div className="right"><span className={`badge ${["done", "not_required"].includes(lot.critical_nonvisual_status) ? "ACCEPT" : lot.critical_nonvisual_status === "failed" ? "REJECT" : "HOLD"}`}><span className="dot" />{lot.critical_nonvisual_status}</span></div></div>
                <div className="pad-sm">
                  <p className="small dim" style={{ margin: "0 0 10px" }}>{t("lot.nonvisual_hint")}</p>
                  {lot.nonvisual_note ? <Note tone="info">{lot.nonvisual_note}</Note> : null}
                </div>
              </div>

              <div className="card">
                <div className="card-h"><h2>{lang === "en" ? "Supervisor Override" : "সুপারভাইজার ওভাররাইড"}</h2></div>
                <div className="pad-sm">
                  {!data.is_supervisor ? <Note tone="info"><Icon name="shield" size={15} /> {lang === "en" ? "Only a Supervisor can override a decision." : "শুধুমাত্র সুপারভাইজার সিদ্ধান্ত ওভাররাইড করতে পারেন।"}</Note>
                    : ["HOLD", "ESCALATE"].includes(decision.outcome) ? <Note tone="warn"><Icon name="triangle-alert" size={15} /> {lang === "en" ? "HOLD and ESCALATE decisions cannot be overridden. Complete the sample first." : "HOLD এবং ESCALATE সিদ্ধান্ত ওভাররাইড করা যায় না।"}</Note>
                      : decision.primary_reason === "REJECT_CRITICAL_NONVISUAL_FAILED" ? <Note tone="bad"><Icon name="shield-alert" size={15} /> {lang === "en" ? "Decisions caused by a failed critical non-visual check cannot be overridden." : "ব্যর্থ ক্রিটিক্যাল নন-ভিজ্যুয়াল চেকের সিদ্ধান্ত ওভাররাইড করা যায় না।"}</Note>
                        : overrideRow ? <Note tone="info"><Icon name="info" size={15} /> {lang === "en" ? "An override is already registered for this decision." : "এই সিদ্ধান্তের জন্য একটি ওভাররাইড ইতিমধ্যে বিদ্যমান।"}</Note>
                          : (
                            <form onSubmit={submitOverride} className="stack" style={{ gap: 12 }}>
                              <Field label={lang === "en" ? "Target Disposition" : "কাঙ্ক্ষিত সিদ্ধান্ত"} required>
                                <select value={override.disposition} onChange={(event) => setOverride((previous) => ({ ...previous, disposition: event.target.value }))}>
                                  {decision.outcome === "REJECT" ? <option value="OVERRIDE_ACCEPT">{t("dec.override_accept")} ({lang === "en" ? "High-Risk — requires 2nd Supervisor" : "উচ্চ ঝুঁকি"})</option> : null}
                                  <option value="OVERRIDE_REJECT">{t("dec.override_reject")} ({lang === "en" ? "Stricter — effective immediately" : "অবিলম্বে কার্যকর"})</option>
                                </select>
                              </Field>
                              <Field label={t("dec.override_reason")} required hint={lang === "en" ? "20 characters minimum" : "কমপক্ষে ২০ অক্ষর"}>
                                <textarea rows={3} minLength={20} required value={override.reason} onChange={(event) => setOverride((previous) => ({ ...previous, reason: event.target.value }))} placeholder={lang === "en" ? "Explain why human judgment differs from the deterministic engine rule." : "কেন মানবিক বিবেচনা ইঞ্জিনের নিয়মের চেয়ে ভিন্ন তা লিখুন।"} />
                              </Field>
                              <Button type="submit" size="sm" variant="primary" icon="check" disabled={busy || override.reason.trim().length < 20}>{lang === "en" ? "Submit Override" : "ওভাররাইড দাখিল"}</Button>
                            </form>
                          )}
                </div>
              </div>

              <div className="card">
                <div className="card-h"><h2>{t("dec.history")}</h2><div className="right"><span className="small dim">{data.history.length} {lang === "en" ? "records" : "রেকর্ড"}</span></div></div>
                <div className="pad-sm">
                  {data.history.length ? (
                    <div className="list" style={{ margin: 0 }}>
                      {data.history.map((entry) => (
                        <li key={entry.id}>
                          <span className={`badge ${entry.outcome}`}>{t(`out.${entry.outcome}`)}</span>
                          <div className="grow">
                            <div className="small bold">#{entry.sequence} · {entry.decided_by}</div>
                            <div className="small dim">{entry.created_at} · {entry.counts.critical}C / {entry.counts.major}M / {entry.counts.minor}m</div>
                          </div>
                        </li>
                      ))}
                    </div>
                  ) : <div className="small dim">{lang === "en" ? "No earlier decisions." : "পূর্ববর্তী সিদ্ধান্ত নেই।"}</div>}
                  <div style={{ marginTop: 12, borderTop: "1px dashed var(--line)", paddingTop: 10 }}>
                    <Link className="btn sm ghost" to={`/lots/${id}/report`}><Icon name="file-text" size={14} /><span>{t("lot.report")} →</span></Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
