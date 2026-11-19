import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import { num, numGrouped } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { LotTabs } from "../components/LotTabs";
import { ReasonList } from "../components/ReasonList";
import {
  Button, DecisionBadge, EmptyState, ErrorState, Icon, Note, Pipeline, ProgressBar,
  Spinner, StatusBadge, Timeline, Toast,
} from "../components/ui";

export interface LotDetail {
  lot: {
    id: number; lot_code: string; buyer_name: string; product_name: string; color: string;
    lot_size: number; status: string; version: number; critical_nonvisual_status: string;
    nonvisual_note: string | null; created_by: number;
  };
  plan: {
    n: number; counting_mode: string; is_demo: boolean;
    critical: { ac: number; re: number }; major: { ac: number; re: number }; minor: { ac: number; re: number };
  } | null;
  progress: { units: number; required_units: number; views: number; reviewed: number; pending: number; pct_units: number; pct_views: number };
  units: Array<{ id: number; garment_code: string; views: Array<{
    id: number; side: string; required: boolean; image: { id: number; width: number; height: number; bytes: number } | null;
    review_state: string; inference_status: string; predictions: Array<{ id: number; review_state: string; second_review?: string; provisional_critical?: number }>;
    open_proposals?: number;
  }> }>;
  decision: { id: number; outcome: string; primary_reason: string; reasons: string[]; sequence: number; created_at: string; manual_inspection?: number } | null;
  override: { effective?: boolean; status?: string; final_disposition?: string } | null;
  final: string | null;
  audit: Array<{ id: number; action: string; actor_label: string; at: string }>;
  is_admin: boolean;
  is_supervisor: boolean;
  can_write: boolean;
}

export function LotPage() {
  const { lotId } = useParams();
  const id = Number(lotId);
  const { t, lang, reason } = useSession();
  const queryClient = useQueryClient();
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);
  const [nvStatus, setNvStatus] = useState("");
  const [nvNote, setNvNote] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["lot", id],
    queryFn: () => api.get<LotDetail>(`/api/lots/${id}`),
  });

  if (isLoading) {
    return <AppShell title="Lot" active="lots"><Spinner /></AppShell>;
  }
  if (error || !data) {
    return <AppShell title="Lot" active="lots"><ErrorState message={(error as Error)?.message || "Not found"} /></AppShell>;
  }

  const { lot, plan, progress, units, decision, override, final } = data;
  const allViews = units.flatMap((unit) => unit.views);
  const images = allViews.filter((view) => view.image);
  const manual = images.filter((view) => ["failed", "not_inferred"].includes(view.inference_status));
  const pending = images.filter((view) => view.inference_status === "pending");
  const ok = images.filter((view) => view.inference_status === "ok");
  const retakes = allViews.filter((view) => view.review_state === "needs_retake");
  const second = allViews.flatMap((view) => view.predictions).filter((prediction) => prediction.second_review === "requested");

  const aiState = !images.length ? "not-started" : pending.length ? "in-progress" : "done";
  const aiValue = !images.length
    ? `${num(0, lang)} ${lang === "en" ? "photos" : "ছবি"}`
    : pending.length
      ? `${num(pending.length, lang)} ${lang === "en" ? "queued" : "প্রক্রিয়াধীন"}`
      : `${num(ok.length, lang)} ${lang === "en" ? "ok" : "সফল"} · ${num(manual.length, lang)} ${lang === "en" ? "manual" : "ম্যানুয়াল"}`;

  const revState = !images.length || progress.views === 0
    ? "not-started" : progress.reviewed === progress.views ? "done" : "in-progress";
  const revValue = !images.length || progress.views === 0
    ? t("pipe.awaiting_photos")
    : `${num(progress.reviewed, lang)} / ${num(progress.views, lang)} ${lang === "en" ? "reviewed" : "পর্যালোচিত"}`;

  const missingPlan = !plan || (decision && decision.reasons.includes("HOLD_PLAN_MISSING"));
  let decState: string;
  let decValue: React.ReactNode;
  if (missingPlan) {
    decState = "blocked";
    decValue = t("pipe.blocked_no_plan");
  } else if (aiState !== "done" || revState !== "done") {
    decState = decision ? "in-progress" : "not-started";
    decValue = decision ? `${lang === "en" ? "In progress: " : "চলমান: "}${t(`out.${decision.outcome}`)}` : t("pipe.awaiting_review");
  } else if (lot.status === "decided" || decision) {
    decState = "done";
    decValue = t(`out.${final || decision?.outcome}`);
  } else {
    decState = "in-progress";
    decValue = t("pipe.ready_to_compute");
  }

  const compute = async () => {
    setBusy(true);
    try {
      const result = await api.post<{ unchanged: boolean }>(`/api/lots/${id}/decisions`, {});
      setToast(result.unchanged ? t("lot.no_changes") : t("flash.saved"));
      await queryClient.invalidateQueries({ queryKey: ["lot", id] });
    } catch {
      setToast(t("err.failed"));
    } finally {
      setBusy(false);
    }
  };

  const saveNonvisual = async () => {
    setBusy(true);
    try {
      await api.post(`/api/lots/${id}/nonvisual`, { status: nvStatus || lot.critical_nonvisual_status, note: nvNote });
      setToast(t("flash.saved"));
      await queryClient.invalidateQueries({ queryKey: ["lot", id] });
    } catch {
      setToast(t("err.failed"));
    } finally {
      setBusy(false);
    }
  };

  const nvTone = ["done", "not_required"].includes(lot.critical_nonvisual_status) ? "ACCEPT" : lot.critical_nonvisual_status === "failed" ? "REJECT" : "HOLD";

  return (
    <AppShell
      title={lot.lot_code}
      subtitle={`${lot.buyer_name} · ${lot.product_name} · ${lot.color} · ${t("lots.size")} ${numGrouped(lot.lot_size, lang)}`}
      active="lots"
    >
      {toast ? <Toast message={toast} onClose={() => setToast("")} /> : null}
      <LotTabs lotId={id} isAdmin={data.is_admin} />

      <Pipeline steps={[
        { label: t("pipe.ai_detection"), value: aiValue, state: aiState },
        { label: t("pipe.human_review"), value: revValue, state: revState },
        { label: t("pipe.decision_engine"), value: decValue, state: decState },
      ]} />

      <div className="card lot-action-card">
        <div className="pad-sm lot-action-bar">
          <div className="lot-chips-row">
            {lot.status === "decided" ? <span className="badge badge-neutral">v{lot.version}</span> : null}
            {manual.length ? <span className="badge badge-warning"><span className="dot" />{num(manual.length, lang)} {lang === "en" ? "manual review" : "ম্যানুয়াল পর্যালোচনা"}</span> : null}
            {retakes.length ? <span className="badge badge-danger"><span className="dot" />{num(retakes.length, lang)} {lang === "en" ? "retake needed" : "পুনরায় ছবি দরকার"}</span> : null}
            {second.length ? <span className="badge badge-info"><span className="dot" />{num(second.length, lang)} {lang === "en" ? "second opinion pending" : "দ্বিতীয় মত বাকি"}</span> : null}
            {allViews.some((view) => view.predictions.length) ? (
              <span className="demo-tag demo-tag-ai"><Icon name="info" size={12} />{t("dash.illustrative")}</span>
            ) : null}
          </div>

          <div className="lot-cta-row">
            {data.can_write ? (
              <>
                <Button href={`/lots/${id}/capture`} size="sm" icon="camera">{t("cap.upload")}</Button>
                {!units.length ? (
                  <>
                    <Button size="sm" variant="ghost" icon="eye" disabled>{t("lot.review")}</Button>
                    <Button size="sm" variant="subtle" icon="cpu" disabled>{t("dec.compute")}</Button>
                  </>
                ) : progress.reviewed < progress.views ? (
                  <>
                    <Link className="btn sm primary" to={`/lots/${id}/review`}><Icon name="eye" size={14} /><span>{t("lot.review")}</span></Link>
                    <Button size="sm" variant="subtle" icon="cpu" disabled={!plan || !images.length} onClick={compute}>
                      {t("dec.compute")}
                    </Button>
                  </>
                ) : (
                  <>
                    <Link className="btn sm" to={`/lots/${id}/review`}><Icon name="eye" size={14} /><span>{t("lot.review")}</span></Link>
                    <Button size="sm" variant="primary" icon="cpu" disabled={!plan} onClick={compute}>{t("dec.compute")}</Button>
                  </>
                )}
              </>
            ) : null}
            {!data.is_admin ? (
              <>
                <Button href={`/lots/${id}/plan`} size="sm" variant="ghost" icon="sliders">{t("lot.plan")}</Button>
                <Button href={`/lots/${id}/report`} size="sm" variant="ghost" icon="file-text">{t("lot.report")}</Button>
              </>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid cols-4 kpi-grid kpi-grid-lot">
        <div className={`kpi${lot.status === "open" ? " accent" : ""}`}>
          <div className="kpi-head">
            <div className="lbl">{t("common.status")}</div>
            {lot.status === "decided" ? <span className="kpi-badge">v{lot.version}</span> : null}
          </div>
          <div className="kpi-row-status"><StatusBadge status={lot.status} /></div>
          <div className="meta"><span className="kpi-hint">{lang === "en" ? "Lot size" : "লট সাইজ"}: <b>{numGrouped(lot.lot_size, lang)}</b> {t("common.pcs")}</span></div>
        </div>
        <div className="kpi is-info">
          <div className="kpi-head"><div className="lbl">{t("lot.units_registered")}</div><span className="kpi-badge">{num(progress.pct_units, lang)}%</span></div>
          <div className="n">{num(progress.units, lang)}<small> / {progress.required_units ? num(progress.required_units, lang) : "—"}</small></div>
          <ProgressBar value={progress.pct_units} tone="lime" />
        </div>
        <div className="kpi is-success">
          <div className="kpi-head"><div className="lbl">{t("lot.views_reviewed")}</div><span className="kpi-badge">{num(progress.pct_views, lang)}%</span></div>
          <div className="n">{num(progress.reviewed, lang)}<small> / {num(progress.views, lang)}</small></div>
          <ProgressBar value={progress.pct_views} tone="lime" />
        </div>
        <div className={`kpi${decision && ["HOLD", "ESCALATE"].includes(decision.outcome) ? " is-warning" : decision?.outcome === "ACCEPT" ? " is-success" : ""}`}>
          <div className="kpi-head">
            <div className="lbl">{t("common.outcome")}</div>
            <span className="kpi-badge">{decision ? t(`out.${final || decision.outcome}`) : t("status.pending")}</span>
          </div>
          {decision ? (
            <div className="disp-kpi-box">
              <div className="disp-kpi-row"><span className="dim">{lang === "en" ? "System recommendation" : "সিস্টেম সুপারিশ"}:</span><DecisionBadge outcome={decision.outcome} label={t(`out.${decision.outcome}`)} /></div>
              <div className="disp-kpi-row font-medium"><span className="dim font-bold">{t(lot.status === "decided" ? "dash.final_disposition" : "dash.current_decision")}</span><DecisionBadge outcome={final!} label={t(`out.${final}`)} /></div>
              {override ? (
                <div className="disp-kpi-sub">
                  {override.effective ? <span className="badge ghost">{t("dec.overridden")}</span> : <span className="badge HOLD"><span className="dot" />{lang === "en" ? "Pending supervisor approval" : "সুপারভাইজার অনুমোদন বাকি"}</span>}
                </div>
              ) : null}
            </div>
          ) : (
            <>
              <div className="n disp-empty-n">—</div>
              <div className="meta"><span className="kpi-hint">{t("dec.none")}</span></div>
            </>
          )}
        </div>
      </div>

      <div className="split">
        <div className="stack">
          <div className="card">
            <div className="card-h">
              <h2>{t("common.units")}</h2>
              <div className="right"><span className="small dim">{num(units.length, lang)} {t("common.units").toLowerCase()}</span></div>
            </div>
            <div className="pad-sm">
              {units.length ? (
                <div className="grid garment-units-grid">
                  {units.map((unit) => (
                    <div className="unit garment-unit-card" key={unit.id}>
                      <div className="garment-unit-head">
                        <b>{unit.garment_code}</b>
                        <span className="small dim">{num(unit.views.length, lang)} {lang === "en" ? (unit.views.length === 1 ? "view" : "views") : "ভিউ"}</span>
                      </div>
                      <div className="views garment-views-row">
                        {unit.views.map((view) => view.image ? (
                          <Link
                            key={view.id}
                            className={`vchip ${["confirmed_defects", "reviewed_clean"].includes(view.review_state) ? "done" : view.review_state === "needs_retake" ? "bad" : "pending"}`}
                            to={`/review/${view.image.id}`}
                            title={lang === "en" ? "Review photo" : "ছবি পর্যালোচনা"}
                          >
                            {t(`cap.${view.side}`)}
                            {view.review_state === "confirmed_defects" ? ` ● ${num(view.predictions.filter((prediction) => prediction.review_state === "confirmed").length, lang)}` : null}
                            {view.review_state === "reviewed_clean" ? " ✓" : null}
                            {view.review_state === "needs_retake" ? " !" : null}
                            {["failed", "not_inferred"].includes(view.inference_status) && !["confirmed_defects", "reviewed_clean", "needs_retake"].includes(view.review_state) ? " [M]" : null}
                          </Link>
                        ) : (
                          <Link key={view.id} className="vchip none" to={`/lots/${id}/capture`} title={lang === "en" ? "Upload photo" : "ছবি আপলোড"}>
                            {t(`cap.${view.side}`)} · —
                          </Link>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title={t("lot.no_units")} body={t("lot.no_units_body")} icon="camera" actionLabel={t("cap.upload")} actionHref={`/lots/${id}/capture`} />
              )}
            </div>
            {lot.status === "decided" ? <div className="pad-sm"><Note tone="info">{t("lot.locked")}</Note></div> : null}
          </div>

          <div className="card">
            <div className="card-h">
              <h2>{t("dec.title")}</h2>
              <div className="right">{!data.is_admin ? <Link className="link-quiet" to={`/lots/${id}/decision`}>{t("common.open")} →</Link> : null}</div>
            </div>
            <div className="pad-sm">
              {decision ? (
                <>
                  <div className="dec-summary-row">
                    <div><div className="small dim" style={{ marginBottom: 2 }}>{lang === "en" ? "Recommendation" : "সুপারিশ"}</div><DecisionBadge outcome={decision.outcome} label={t(`out.${decision.outcome}`)} /></div>
                    <div><div className="small dim" style={{ marginBottom: 2 }}>{t(lot.status === "decided" ? "dec.final_disposition" : "dec.current_decision")}</div><DecisionBadge outcome={final!} label={t(`out.${final}`)} /></div>
                    <span className="small dim" style={{ marginLeft: "auto" }}>#{num(decision.sequence, lang)} · {decision.created_at}</span>
                  </div>
                  <div className="mt-6"><ReasonList codes={decision.reasons} /></div>
                </>
              ) : (
                <div className="empty dec-empty-box">
                  <b>{t("dec.none")}</b>
                  <p className="small dim" style={{ margin: "6px 0 12px" }}>{t("dec.compute")}</p>
                  {data.can_write ? <Button size="sm" variant="primary" disabled={!plan || !images.length || busy} onClick={compute}>{t("dec.compute")}</Button> : null}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="stack">
          <div className="card">
            <div className="card-h">
              <h2>{t("lot.plan")}</h2>
              <div className="right">{data.is_supervisor && lot.status !== "decided" && plan ? <Button href={`/lots/${id}/plan`} size="sm">{t("common.open")}</Button> : null}</div>
            </div>
            <div className="pad-sm">
              {plan ? (
                <>
                  <div className="plan-chips-row">
                    <span className="chip">n = {num(plan.n, lang)}</span>
                    <span className="chip">{plan.counting_mode}</span>
                    {plan.is_demo ? <span className="badge badge-warning">TEST CONFIGURATION</span> : null}
                  </div>
                  <table className="table plan-table">
                    <thead><tr><th>{lang === "en" ? "Class" : "শ্রেণি"}</th><th className="num">Ac</th><th className="num">Re</th></tr></thead>
                    <tbody>
                      {(["critical", "major", "minor"] as const).map((key) => (
                        <tr key={key}>
                          <td><span className={`badge ${key}`}>{t(`plan.${key}`)}</span></td>
                          <td className="num">{num(plan[key].ac, lang)}</td>
                          <td className="num">{num(plan[key].re, lang)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="note warn plan-note-warn">
                    <b>{lang === "en" ? "Assumption" : "অনুমান"}:</b> {t("lot.plan_assumption")}
                    <div className="small dim" style={{ marginTop: 3 }}>Normal inspection · Single sampling · General Level II (ISO 2859-1 / ANSI ASQ Z1.4)</div>
                  </div>
                </>
              ) : data.is_supervisor ? (
                <div className="empty dec-empty-box">
                  <b>{t("lot.plan_missing")}</b>
                  <p className="small dim" style={{ margin: "6px 0 14px" }}>{lang === "en" ? "Configure an AQL sampling plan to enable deterministic lot decisions." : "ডিটারমিনিস্টিক সিদ্ধান্ত গণনার জন্য AQL স্যাম্পলিং প্ল্যান কনফিগার করুন।"}</p>
                  {lot.status !== "decided" ? <Button href={`/lots/${id}/plan`} size="sm" variant="primary" icon="plus">{t("lot.create_plan")}</Button> : null}
                </div>
              ) : (
                <Note tone="warn">
                  <b>{t("lot.awaiting_supervisor")}</b>
                  <div className="small dim" style={{ marginTop: 3 }}>{t("lot.awaiting_supervisor_desc")}</div>
                </Note>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-h">
              <h2>{t("lot.nonvisual")}</h2>
              <div className="right"><span className={`badge ${nvTone}`}><span className="dot" />{t(`nv.${lot.critical_nonvisual_status}`)}</span></div>
            </div>
            <div className="pad-sm">
              <div className="small dim" style={{ marginBottom: 9 }}>{t("lot.nonvisual_hint")}</div>
              {data.is_supervisor && lot.status !== "decided" ? (
                <div className="nv-form">
                  <div className="field">
                    <label>{t("common.status")}</label>
                    <select value={nvStatus || lot.critical_nonvisual_status} onChange={(event) => setNvStatus(event.target.value)}>
                      {["pending", "done", "not_required", "failed"].map((value) => (
                        <option key={value} value={value}>{t(`nv.${value}`)}</option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label>{t("common.notes")}</label>
                    <input value={nvNote || lot.nonvisual_note || ""} onChange={(event) => setNvNote(event.target.value)} placeholder={`${t("common.notes")} (${lang === "en" ? "required for failed" : "failed-এর জন্য আবশ্যক"})`} />
                  </div>
                  <Button size="sm" variant="primary" disabled={busy} onClick={saveNonvisual}>{t("common.save")}</Button>
                </div>
              ) : lot.nonvisual_note ? (
                <Note tone="info">{lot.nonvisual_note}</Note>
              ) : (
                <Note tone="info">
                  <b>{lang === "en" ? "Recorded check status" : "নথিভুক্ত চেকের অবস্থা"}:</b> {t(`nv.${lot.critical_nonvisual_status}`)}
                  <div className="small dim" style={{ marginTop: 3 }}>{t("lot.supervisor_only_nv")}</div>
                </Note>
              )}
            </div>
          </div>

          <div className="card" id="history">
            <div className="card-h">
              <h2>{t("lot.timeline")}</h2>
              <div className="right"><span className="small dim">{num(data.audit.length, lang)} {lang === "en" ? "events" : "টি ইভেন্ট"}</span></div>
            </div>
            <div className="pad-sm">
              <Timeline items={data.audit.slice(0, 12).map((entry) => ({
                title: t(`event.${entry.action}`) === `event.${entry.action}` ? entry.action : t(`event.${entry.action}`),
                actor: entry.actor_label || `User #${entry.id}`,
                datetime: entry.at,
              }))} />
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
