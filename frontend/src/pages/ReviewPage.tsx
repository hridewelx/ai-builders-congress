import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useSession } from "../lib/session";
import { AppShell } from "../components/AppShell";
import { LotTabs } from "../components/LotTabs";
import {
  Badge, Button, Dialog, ErrorState, Field, Icon, Note, Pipeline, Spinner, Toast,
} from "../components/ui";

interface Prediction {
  id: number;
  defect_type: string;
  confirmed_type: string | null;
  score: number;
  x1: number; y1: number; x2: number; y2: number;
  review_state: string;
  provisional_critical: number;
  severity: string | null;
  zone_code: string | null;
  size_band: string | null;
  clause_ref: string | null;
  second_review: string | null;
  note: string | null;
  reviewer: string | null;
  reviewed_by: number | null;
}

interface ReviewData {
  lot: { id: number; lot_code: string; buyer_name: string; status: string };
  image: { id: number; sha256_working: string; width: number; height: number; bytes: number };
  view: { garment_code: string; side: string };
  review: { state: string; note: string | null; reviewer: string | null } | null;
  job: { status: string; model_version: string; error?: string } | null;
  preds: Prediction[];
  status: string;
  next_item: { view: { image: { id: number } } } | null;
  can_write: boolean;
  is_supervisor: boolean;
  user: { id: number };
  zones: string[];
  human_classes: string[];
}

const ERROR_TEXT: Record<string, string> = {
  review_first: "Please confirm or reject every proposal before closing this view.",
  no_defects: "Cannot mark \"Confirmed defects\" with zero confirmed proposals. If clean, select \"Reviewed clean\".",
  has_defects: "Cannot mark \"Reviewed clean\" while defects are confirmed. Reject confirmed defects first.",
  different_reviewer: "A second review must come from a different supervisor.",
  not_allowed: "You do not have permission for this action.",
  locked: "This lot is locked.",
};

export function ReviewPage() {
  const { imageId } = useParams();
  const id = Number(imageId);
  const { t, lang } = useSession();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["review", id],
    queryFn: () => api.get<ReviewData>(`/api/review/${id}`),
  });
  const [toast, setToast] = useState("");
  const [heat, setHeat] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pending, setPending] = useState<{ x: number; y: number } | null>(null);
  const [manual, setManual] = useState({ defect_type: "hole", zone: "I", size_band: "", note: "", second_opinion: false });
  const [closeState, setCloseState] = useState("confirmed_defects");
  const [closeNote, setCloseNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [shortcuts, setShortcuts] = useState(false);

  if (isLoading) return <AppShell title={t("rev.title")} active="lots"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("rev.title")} active="lots"><ErrorState message={(error as Error)?.message || "Not found"} /></AppShell>;

  const { lot, image, view, review, preds, job } = data;
  const confirmed = preds.filter((prediction) => prediction.review_state === "confirmed");
  const open = preds.filter((prediction) => prediction.review_state === "proposed");

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["review", id] });
    await queryClient.invalidateQueries({ queryKey: ["review-queue", lot.id] });
    await queryClient.invalidateQueries({ queryKey: ["lot", lot.id] });
  };

  const call = async (path: string, body?: unknown) => {
    setBusy(true);
    try {
      await api.post(path, body || {});
      setToast(t("flash.saved"));
      await refresh();
    } catch (caught) {
      const detail = caught instanceof ApiError ? String(caught.detail) : "";
      setToast(ERROR_TEXT[detail] || t("err.failed"));
    } finally {
      setBusy(false);
    }
  };

  const confirm = (prediction: Prediction, values: { defect_type: string; zone: string; size_band: string; note: string }) =>
    call(`/api/review/${id}/confirm`, { prediction_id: prediction.id, ...values });

  const reject = (prediction: Prediction) =>
    call(`/api/review/${id}/reject`, { prediction_id: prediction.id });

  const secondReview = (prediction: Prediction, outcome: "confirm" | "overturn") =>
    call(`/api/review/${id}/second-review`, { prediction_id: prediction.id, outcome });

  const addManual = async (event: React.FormEvent) => {
    event.preventDefault();
    await call(`/api/review/${id}/add`, {
      ...manual,
      second_opinion: manual.second_opinion ? "1" : "",
      cx: pending?.x ?? 0.5,
      cy: pending?.y ?? 0.5,
    });
    setPending(null);
  };

  const finish = async () => {
    setBusy(true);
    try {
      const result = await api.post<{ retake: boolean }>(`/api/review/${id}/state`, { state: closeState, note: closeNote });
      if (result.retake) {
        navigate(`/lots/${lot.id}/capture`);
        return;
      }
      setToast(t("flash.saved"));
      await refresh();
    } catch (caught) {
      const detail = caught instanceof ApiError ? String(caught.detail) : "";
      setToast(ERROR_TEXT[detail] || t("err.failed"));
    } finally {
      setBusy(false);
    }
  };

  const placeBox = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!data.can_write) return;
    const rect = event.currentTarget.getBoundingClientRect();
    setPending({
      x: Math.min(0.95, Math.max(0.05, (event.clientX - rect.left) / rect.width)),
      y: Math.min(0.95, Math.max(0.05, (event.clientY - rect.top) / rect.height)),
    });
  };

  return (
    <AppShell
      title={t("rev.title")}
      subtitle={`${lot.lot_code} · ${view.garment_code} · ${t(`cap.${view.side}`)} · ${lot.buyer_name}`}
      active="lots"
    >
      {toast ? <Toast message={toast} onClose={() => setToast("")} /> : null}
      <LotTabs lotId={lot.id} isAdmin={false} />

      <Pipeline steps={[
        { label: lang === "en" ? "1. AI Detection" : "১. এআই শনাক্তকরণ", value: data.status === "ok" ? (lang === "en" ? `Inferred (${preds.length} proposals)` : `ইনফারেন্স হয়েছে (${preds.length} প্রস্তাব)`) : data.status === "pending" ? (lang === "en" ? "Queued" : "প্রক্রিয়াধীন") : (lang === "en" ? "Manual review" : "ম্যানুয়াল পর্যালোচনা"), state: data.status === "ok" ? "done" : "active" },
        { label: lang === "en" ? "2. Human Review" : "২. মানুষ পর্যালোচনা", value: review ? review.state.replace(/_/g, " ") : (lang === "en" ? "In review" : "পর্যালোচনাধীন"), state: review && ["confirmed_defects", "reviewed_clean"].includes(review.state) ? "done" : review?.state === "needs_retake" ? "failed" : "active" },
        { label: lang === "en" ? "3. Decision Engine" : "৩. নির্ধারক ইঞ্জিন", value: `${t("common.status")}: ${lot.status}`, state: lot.status === "decided" ? "done" : "pending" },
      ]} />

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="pad-sm" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <div className="row" style={{ gap: 10, alignItems: "center" }}>
            <span className="badge badge-neutral bold" style={{ fontSize: 13 }}>{view.garment_code}</span>
            <span className="badge badge-lime">{t(`cap.${view.side}`)}</span>
            {review ? review.state === "confirmed_defects" ? <span className="badge badge-danger"><span className="dot" />{lang === "en" ? "Defects confirmed" : "ত্রুটি নিশ্চিত"}</span>
              : review.state === "reviewed_clean" ? <span className="badge badge-success"><span className="dot" />{lang === "en" ? "Reviewed clean" : "পরিষ্কার পর্যালোচিত"}</span>
                : review.state === "needs_retake" ? <span className="badge badge-warning"><span className="dot" />{t("rev.retake")}</span> : null
              : <span className="badge badge-pending"><span className="dot" />{lang === "en" ? "Unreviewed" : "পর্যালোচনা হয়নি"}</span>}
          </div>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <Button size="sm" variant="ghost" icon="command" onClick={() => setShortcuts(true)}>{lang === "en" ? "Shortcuts" : "শর্টকাট"}</Button>
            <Button href={`/lots/${lot.id}/review`} size="sm" variant="ghost" icon="list">{t("rev.queue")}</Button>
            {data.next_item ? <Button href={`/review/${data.next_item.view.image.id}`} size="sm" variant="primary" iconAfter="chevron-right">{lang === "en" ? "Next photo" : "পরের ছবি"}</Button> : null}
          </div>
        </div>
      </div>

      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <div className="kpi">
          <div className="lbl">{lang === "en" ? "Detector" : "ডিটেক্টর"}</div>
          <div style={{ marginTop: 8 }}>
            {data.status === "ok" ? <span className="badge badge-success"><span className="dot" />{lang === "en" ? "Inferred" : "ইনফারেন্স সম্পন্ন"}</span>
              : ["failed", "not_inferred"].includes(data.status) ? <span className="badge badge-warning"><span className="dot" />{lang === "en" ? "Manual review" : "ম্যানুয়াল পর্যালোচনা"}</span>
                : <span className="badge badge-pending"><span className="dot" />{lang === "en" ? "Queued" : "প্রক্রিয়াধীন"}</span>}
          </div>
          {job?.model_version ? <div className="meta" style={{ marginTop: 4 }}>{job.model_version}</div> : null}
        </div>
        <div className="kpi"><div className="lbl">{lang === "en" ? "Proposals" : "প্রস্তাব"}</div><div className="n">{preds.length}</div><div className="meta" style={{ marginTop: 4 }}>{confirmed.length} {lang === "en" ? "confirmed" : "নিশ্চিত"} · {preds.filter((prediction) => prediction.review_state === "rejected").length} {lang === "en" ? "rejected" : "বাতিল"}</div></div>
        <div className="kpi">
          <div className="lbl">{lang === "en" ? "Review state" : "পর্যালোচনা অবস্থা"}</div>
          <div style={{ marginTop: 8 }}>{review ? <span className="badge badge-pending"><span className="dot" />{review.state.replace(/_/g, " ")}</span> : <span className="badge badge-pending"><span className="dot" />{lang === "en" ? "Pending review" : "পর্যালোচনা বাকি"}</span>}</div>
          {review?.reviewer ? <div className="meta" style={{ marginTop: 4 }}>{review.reviewer}</div> : null}
        </div>
        <div className="kpi"><div className="lbl">{lang === "en" ? "Evidence (working copy)" : "প্রমাণ (ওয়ার্কিং কপি)"}</div><div className="small mono dim" style={{ marginTop: 9 }}>{image.sha256_working.slice(0, 18)}…</div><div className="meta" style={{ marginTop: 4 }}>{image.width}×{image.height} px · {Math.round(image.bytes / 1024)} KB</div></div>
      </div>

      {job?.status === "failed" ? (
        <div className="error-state" style={{ marginBottom: 14 }} role="alert">
          <span className="error-icon"><Icon name="alert-octagon" size={24} /></span>
          <div>
            <b>{t("cap.not_inferred")}</b>
            <p>{lang === "en" ? "Zero proposals is not a pass. The detector was unavailable or failed; manual review is active and valid." : "শূন্য প্রস্তাব মানে পাস নয়। ডিটেক্টর অনুপলব্ধ ছিল; ম্যানুয়াল পর্যালোচনা সক্রিয়।"}</p>
            {data.can_write ? <Button size="sm" icon="refresh-cw" disabled={busy} onClick={() => call(`/api/images/${id}/infer`)}>{t("cap.infer")}</Button> : null}
          </div>
        </div>
      ) : !preds.length ? (
        <Note tone="warn">
          <b>{t("rev.no_proposals")}</b>
          <p className="small dim" style={{ margin: "3px 0 0" }}>{lang === "en" ? "Zero proposals is not a pass. Inspect the photo carefully. If you find defects, click the photo to place a box." : "শূন্য প্রস্তাব মানে পাস নয়। ছবিটি সতর্কভাবে দেখুন। ত্রুটি থাকলে ক্লিক করে বক্স বসান।"}</p>
        </Note>
      ) : null}

      <div className="workspace">
        <div className="stack">
          <div className="card">
            <div className="card-h">
              <h2>{lang === "en" ? "Working copy inspection" : "ওয়ার্কিং কপি পরিদর্শন"}</h2>
              <div className="right">
                <Button size="sm" variant="ghost" onClick={() => setHeat((value) => !value)}>
                  {heat ? (lang === "en" ? "Show photo" : "ছবি দেখান") : (lang === "en" ? "Attention map" : "অ্যাটেনশন ম্যাপ")}
                </Button>
              </div>
            </div>
            <div className="pad-sm">
              <div className="viewer">
                <div className="viewer-scroll" style={{ overflow: "auto" }}>
                  <div
                    style={{ position: "relative", transform: `scale(${zoom})`, transformOrigin: "top left", cursor: data.can_write ? "crosshair" : "default" }}
                    onClick={placeBox}
                  >
                    <img
                      src={heat ? `/api/images/${id}/heat` : `/api/images/${id}`}
                      alt={`${view.garment_code} ${view.side}`}
                      draggable={false}
                      style={{ display: "block", width: "100%", height: "auto" }}
                    />
                    <div className="boxlayer">
                      {preds.map((prediction) => (
                        <div
                          key={prediction.id}
                          className={`box ${prediction.provisional_critical ? "crit" : prediction.severity === "major" || prediction.severity === "critical" ? "major" : ""} ${prediction.review_state === "confirmed" ? "confirmed" : ""} ${prediction.review_state === "rejected" ? "rejected" : ""}`}
                          style={{
                            left: `${prediction.x1 * 100}%`, top: `${prediction.y1 * 100}%`,
                            width: `${(prediction.x2 - prediction.x1) * 100}%`, height: `${(prediction.y2 - prediction.y1) * 100}%`,
                          }}
                        >
                          <span className="tag">
                            {prediction.review_state === "confirmed" ? `✓ ${t(`type.${prediction.confirmed_type || prediction.defect_type}`)}${prediction.zone_code ? ` · ${prediction.zone_code}` : ""}`
                              : prediction.review_state === "rejected" ? t(`type.${prediction.confirmed_type || prediction.defect_type}`)
                                : `AI · ${t(`type.${prediction.defect_type}`)} · ${prediction.score}`}
                          </span>
                        </div>
                      ))}
                      {pending ? (
                        <div className="box" style={{ left: `${(pending.x - 0.08) * 100}%`, top: `${(pending.y - 0.08) * 100}%`, width: "16%", height: "16%", borderStyle: "dashed" }}>
                          <span className="tag">+ {t("rev.add")}</span>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>

              <div className="viewer-tools">
                <button className="icon-btn" type="button" onClick={() => setZoom((value) => Math.max(0.5, value - 0.25))} aria-label="Zoom out"><Icon name="zoom-out" size={18} /></button>
                <span className="zoom-level">{Math.round(zoom * 100)}%</span>
                <button className="icon-btn" type="button" onClick={() => setZoom((value) => Math.min(4, value + 0.25))} aria-label="Zoom in"><Icon name="zoom-in" size={18} /></button>
                <button className="btn sm ghost" type="button" onClick={() => setZoom(1)}>{lang === "en" ? "Reset" : "রিসেট"}</button>
                <span className="viewer-hint">{lang === "en" ? "Click image to place manual defect box" : "ম্যানুয়াল ত্রুটির জন্য ছবিতে ক্লিক করুন"}</span>
              </div>

              <div className="legend" style={{ marginTop: 10 }}>
                <span><i className="sw" style={{ background: "var(--lime)" }} />{lang === "en" ? "AI proposal (dashed)" : "এআই প্রস্তাব (ড্যাশ)"}</span>
                <span><i className="sw" style={{ background: "var(--green)" }} />{lang === "en" ? "Human-confirmed (solid)" : "মানুষ নিশ্চিত (সলিড)"}</span>
                <span><i className="sw" style={{ background: "var(--red)" }} />{lang === "en" ? "Critical routing" : "ক্রিটিক্যাল রুটিং"}</span>
                <span><i className="sw" style={{ background: "var(--dim)" }} />{lang === "en" ? "Rejected" : "বাতিল"}</span>
                <span className="dim">{t("rev.uncalibrated")}</span>
              </div>

              <div className="row" style={{ marginTop: 12, gap: 8, flexWrap: "wrap" }}>
                <a className="btn sm ghost" href={`/api/images/${id}`} target="_blank" rel="noopener"><Icon name="external-link" size={13} /><span>{lang === "en" ? "Full resolution" : "পূর্ণ রেজোলিউশন"}</span></a>
                <a className="btn sm ghost" href={`/api/images/${id}/heat`} target="_blank" rel="noopener"><Icon name="external-link" size={13} /><span>{lang === "en" ? "Attention map" : "অ্যাটেনশন ম্যাপ"}</span></a>
                <span className="demo-tag demo-tag-ai"><Icon name="info" size={12} />{t("dash.illustrative")}</span>
              </div>
            </div>
          </div>

          {data.can_write ? (
            <div className="card">
              <div className="card-h">
                <h2>{t("rev.add")}</h2>
                <div className="right"><span className="small dim">{pending ? `Box at ${Math.round(pending.x * 100)}%, ${Math.round(pending.y * 100)}%` : (lang === "en" ? "Click photo to position box" : "ছবিতে ক্লিক করে অবস্থান দিন")}</span></div>
              </div>
              <div className="pad-sm">
                <form onSubmit={addManual}>
                  <div className="grid cols-3" style={{ gap: 10, marginBottom: 10 }}>
                    <Field label={t("rev.type")}>
                      <select value={manual.defect_type} onChange={(event) => setManual((previous) => ({ ...previous, defect_type: event.target.value }))}>
                        {data.human_classes.map((value) => <option key={value} value={value}>{t(`type.${value}`)}</option>)}
                      </select>
                    </Field>
                    <Field label={t("rev.zone")}>
                      <select value={manual.zone} onChange={(event) => setManual((previous) => ({ ...previous, zone: event.target.value }))}>
                        {data.zones.map((value) => <option key={value} value={value}>{lang === "en" ? "Zone" : "জোন"} {value}</option>)}
                      </select>
                    </Field>
                    <Field label={t("rev.size_band")} hint={t("common.optional")}>
                      <input value={manual.size_band} onChange={(event) => setManual((previous) => ({ ...previous, size_band: event.target.value }))} placeholder="e.g. XL" />
                    </Field>
                  </div>
                  <div className="field" style={{ marginBottom: 10 }}>
                    <label className="check" style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 600 }}>
                      <input type="checkbox" checked={manual.second_opinion} onChange={(event) => setManual((previous) => ({ ...previous, second_opinion: event.target.checked }))} style={{ width: "auto", margin: 0 }} />
                      <span>{lang === "en" ? "Possible critical — request second opinion from Supervisor" : "সম্ভাব্য ক্রিটিক্যাল — দ্বিতীয় মত চাওয়া হচ্ছে"}</span>
                    </label>
                  </div>
                  <Field label={t("common.notes")} hint={t("common.optional")}>
                    <input value={manual.note} onChange={(event) => setManual((previous) => ({ ...previous, note: event.target.value }))} placeholder={lang === "en" ? "e.g. Discovered during visual pass near collar" : "নোট লিখুন"} />
                  </Field>
                  <div className="note info" style={{ marginBottom: 12 }}><Icon name="shield-alert" size={14} /> {t("rev.severity_server")}</div>
                  <Button type="submit" size="sm" variant="primary" icon="plus" disabled={busy}>{t("common.save")}</Button>
                </form>
              </div>
            </div>
          ) : null}
        </div>

        <div className="stack">
          <div className="card">
            <div className="card-h"><h2>{t("rev.proposals")}</h2><div className="right"><span className="chip">{preds.length}</span></div></div>
            <div className="pad-sm">
              {preds.map((prediction, index) => (
                <ProposalCard
                  key={prediction.id}
                  prediction={prediction}
                  first={index === 0}
                  canWrite={data.can_write}
                  isSupervisor={data.is_supervisor}
                  userId={data.user.id}
                  zones={data.zones}
                  busy={busy}
                  onConfirm={(values) => confirm(prediction, values)}
                  onReject={() => reject(prediction)}
                  onSecondReview={(outcome) => secondReview(prediction, outcome)}
                />
              ))}
              {!preds.length ? <div className="empty" style={{ padding: 18 }}><b>{t("rev.no_proposals")}</b><p className="small dim" style={{ margin: "4px 0 0" }}>{lang === "en" ? "Zero proposals is not a pass. Inspect photo and mark view below." : "শূন্য প্রস্তাব মানে পাস নয়। ছবিটি দেখে নিচে চিহ্নিত করুন।"}</p></div> : null}
            </div>
          </div>

          {data.can_write ? (
            <div className="card">
              <div className="card-h"><h2>{lang === "en" ? "Finish image review" : "ভিউ পর্যালোচনা শেষ করুন"}</h2></div>
              <div className="pad-sm">
                {open.length ? <Note tone="warn"><b>{open.length} {lang === "en" ? "proposal(s) still open" : "প্রস্তাব এখনও খোলা"}</b> — {lang === "en" ? "Answer each one (confirm or reject) before you close the view. The engine refuses to guess." : "ভিউ বন্ধ করার আগে প্রতিটি প্রস্তাব নিশ্চিত বা বাতিল করুন।"}</Note> : null}
                <div className="stack" style={{ gap: 10 }}>
                  <Field label={t("common.notes")} hint={t("common.optional")}>
                    <input value={closeNote} onChange={(event) => setCloseNote(event.target.value)} placeholder={lang === "en" ? "e.g. Inspected under standard light" : "নোট লিখুন"} />
                  </Field>
                  <div className="btnrow" style={{ gap: 8, flexWrap: "wrap" }}>
                    <button className="btn primary" type="button" disabled={!confirmed.length || busy} onClick={() => { setCloseState("confirmed_defects"); finish(); }}>
                      <Icon name="circle-check" size={16} /><span>{lang === "en" ? "Defects confirmed" : "ত্রুটি নিশ্চিত"} ({confirmed.length})</span>
                    </button>
                    <button className="btn ghost" type="button" disabled={!!confirmed.length || busy} onClick={() => { setCloseState("reviewed_clean"); finish(); }}>
                      <Icon name="check" size={16} /><span>{t("rev.clean")}</span>
                    </button>
                    <button className="btn danger" type="button" disabled={busy} onClick={() => { setCloseState("needs_retake"); finish(); }}>
                      <Icon name="camera" size={16} /><span>{t("rev.retake")}</span>
                    </button>
                  </div>
                </div>
                <div className="small dim" style={{ marginTop: 10 }}>{t("rev.severity_server")}</div>
              </div>
            </div>
          ) : null}

          <div className="card">
            <div className="card-h"><h2>{lang === "en" ? "Navigation" : "নেভিগেশন"}</h2></div>
            <div className="pad-sm btnrow" style={{ gap: 8, flexWrap: "wrap" }}>
              <Button href={`/lots/${lot.id}/review`} size="sm" variant="ghost" icon="chevron-left">{t("rev.queue")}</Button>
              {data.next_item ? <Button href={`/review/${data.next_item.view.image.id}`} size="sm" variant="primary" iconAfter="chevron-right">{lang === "en" ? "Next photo" : "পরের ছবি"}</Button> : null}
              <Button href={`/lots/${lot.id}`} size="sm" variant="ghost" icon="grid">{t("lot.overview")}</Button>
            </div>
          </div>
        </div>
      </div>

      <Dialog title={lang === "en" ? "Review Keyboard Shortcuts" : "কিবোর্ড শর্টকাট"} open={shortcuts} onClose={() => setShortcuts(false)} small
        actions={<button className="btn sm primary" type="button" onClick={() => setShortcuts(false)}>{lang === "en" ? "Got it" : "বুঝেছি"}</button>}>
        <div className="small dim">
          <p><kbd>+</kbd> / <kbd>=</kbd> — {lang === "en" ? "Zoom in" : "জুম ইন"}</p>
          <p><kbd>-</kbd> — {lang === "en" ? "Zoom out" : "জুম আউট"}</p>
          <p><kbd>0</kbd> — {lang === "en" ? "Reset zoom" : "জুম রিসেট"}</p>
          <p>{lang === "en" ? "Use the proposal cards to confirm or reject. Click the photo to place a manual box." : "প্রস্তাব কার্ড থেকে নিশ্চিত বা বাতিল করুন। ম্যানুয়াল বক্সের জন্য ছবিতে ক্লিক করুন।"}</p>
        </div>
      </Dialog>
    </AppShell>
  );
}

function ProposalCard({
  prediction,
  first,
  canWrite,
  isSupervisor,
  userId,
  zones,
  busy,
  onConfirm,
  onReject,
  onSecondReview,
}: {
  prediction: Prediction;
  first: boolean;
  canWrite: boolean;
  isSupervisor: boolean;
  userId: number;
  zones: string[];
  busy: boolean;
  onConfirm: (values: { defect_type: string; zone: string; size_band: string; note: string }) => void;
  onReject: () => void;
  onSecondReview: (outcome: "confirm" | "overturn") => void;
}) {
  const { t, lang } = useSession();
  const [values, setValues] = useState({
    defect_type: prediction.defect_type,
    zone: prediction.zone_code || "I",
    size_band: prediction.size_band || "",
    note: "",
  });
  const [openForm, setOpenForm] = useState(first);

  return (
    <div className={`prop ${first ? "sel" : ""} ${prediction.review_state === "confirmed" ? "is-confirmed" : prediction.review_state === "rejected" ? "is-rejected" : ""}`}>
      <div className="top">
        <div className="row" style={{ gap: 7, alignItems: "center", flexWrap: "wrap" }}>
          <b style={{ fontSize: 13.5 }}>{t(`type.${prediction.confirmed_type || prediction.defect_type}`)}</b>
          {prediction.provisional_critical ? <span className="badge badge-danger"><span className="dot" />{lang === "en" ? "Critical routing" : "ক্রিটিক্যাল"}</span> : null}
          {prediction.score < 0.35 && prediction.review_state === "proposed" ? <span className="badge badge-neutral" style={{ fontSize: 10.5 }}>LOW_SCORE</span> : null}
          {prediction.review_state === "confirmed" ? prediction.severity ? <Badge tone={prediction.severity}>{t(`severe.${prediction.severity}`)}</Badge> : <span className="badge badge-warning">{t("rev.unmapped")}</span>
            : prediction.review_state === "rejected" ? <Badge tone="neutral">{t("rev.reject")}</Badge>
              : <span className="badge badge-warning"><span className="dot" />{lang === "en" ? "Proposed" : "প্রস্তাবিত"}</span>}
        </div>
        <div className="score-label" title={t("rev.uncalibrated")}>
          <span className="small dim">{lang === "en" ? "Score (uncalibrated):" : "স্কোর (অপরিমাপিত):"}</span>
          <span className="mono bold">{prediction.review_state !== "confirmed" ? prediction.score : "—"}</span>
        </div>
      </div>

      <div className="small dim" style={{ marginTop: 6 }}>
        {lang === "en" ? "Box" : "বক্স"}: {(prediction.x1 * 100).toFixed(1)}%, {(prediction.y1 * 100).toFixed(1)}% → {(prediction.x2 * 100).toFixed(1)}%, {(prediction.y2 * 100).toFixed(1)}%
        {prediction.zone_code ? ` · ${lang === "en" ? "Zone" : "জোন"} ${prediction.zone_code}` : ""}
        {prediction.clause_ref ? ` · ${lang === "en" ? "Clause" : "ক্লজ"} ${prediction.clause_ref}` : ""}
        {prediction.confirmed_type && !prediction.severity ? <> · <span style={{ color: "var(--amber-ink)", fontWeight: 600 }}>{t("rev.unmapped")}</span></> : null}
        {prediction.second_review === "pending" ? <> · <span style={{ color: "var(--blue-ink)", fontWeight: 600 }}>{t("rev.second_review")}</span></> : null}
        {prediction.note ? <> · <span style={{ color: "var(--text-sec)" }}>{prediction.note}</span></> : null}
        {prediction.reviewer ? <> · <span className="dim">by {prediction.reviewer}</span></> : null}
      </div>

      {prediction.review_state === "proposed" && canWrite ? (
        <div style={{ marginTop: 10, borderTop: "1px dashed var(--line)", paddingTop: 8 }}>
          <button className="btn sm ghost" type="button" onClick={() => setOpenForm((value) => !value)} style={{ paddingLeft: 0 }}>
            <Icon name="chevron-down" size={14} /><span>{lang === "en" ? "Review proposal" : "প্রস্তাব পর্যালোচনা"}</span>
          </button>
          {openForm ? (
            <div style={{ marginTop: 8 }}>
              <div className="grid cols-3" style={{ gap: 8, marginBottom: 8 }}>
                <Field label={t("rev.type")}>
                  <select value={values.defect_type} onChange={(event) => setValues((previous) => ({ ...previous, defect_type: event.target.value }))}>
                    {["hole", "dropped_stitch", "skipped_stitch", "needle_line", "oil_stain", "shade_band", "other"].map((value) => <option key={value} value={value}>{t(`type.${value}`)}</option>)}
                  </select>
                </Field>
                <Field label={t("rev.zone")}>
                  <select value={values.zone} onChange={(event) => setValues((previous) => ({ ...previous, zone: event.target.value }))}>
                    {zones.map((value) => <option key={value} value={value}>{lang === "en" ? "Zone" : "জোন"} {value}</option>)}
                  </select>
                </Field>
                <Field label={t("rev.size_band")}>
                  <input value={values.size_band} onChange={(event) => setValues((previous) => ({ ...previous, size_band: event.target.value }))} placeholder="e.g. XL" />
                </Field>
              </div>
              <Field label={t("common.notes")} hint={t("common.optional")}>
                <input value={values.note} onChange={(event) => setValues((previous) => ({ ...previous, note: event.target.value }))} placeholder={lang === "en" ? "e.g. Verified by visual inspection" : "নোট লিখুন"} />
              </Field>
              <div className="small dim" style={{ margin: "8px 0" }}>{t("rev.severity_server")}</div>
              <div className="row" style={{ gap: 8 }}>
                <Button size="sm" variant="primary" icon="check" disabled={busy} onClick={() => onConfirm(values)}>{t("rev.confirm")}</Button>
                <Button size="sm" variant="danger" icon="x" disabled={busy} onClick={onReject}>{t("rev.reject")}</Button>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {prediction.review_state === "rejected" && prediction.second_review === "pending" && isSupervisor && prediction.reviewed_by !== userId ? (
        <div style={{ marginTop: 8, padding: 8, background: "var(--amber-bg)", border: "1px solid var(--amber-line)", borderRadius: 6 }}>
          <div className="small bold" style={{ color: "var(--amber-ink)", marginBottom: 6 }}>{lang === "en" ? "Second Supervisor Review Required (provisional critical rejection)" : "দ্বিতীয় সুপারভাইজার পর্যালোচনা আবশ্যক"}</div>
          <div className="row" style={{ gap: 8 }}>
            <Button size="sm" disabled={busy} onClick={() => onSecondReview("confirm")}>{lang === "en" ? "Confirm Rejection" : "বাতিল নিশ্চিত"}</Button>
            <Button size="sm" variant="danger" disabled={busy} onClick={() => onSecondReview("overturn")}>{lang === "en" ? "Overturn to Defect" : "ত্রুটিতে রূপান্তর"}</Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
