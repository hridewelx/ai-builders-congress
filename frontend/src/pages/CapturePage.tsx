import { useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useSession } from "../lib/session";
import { num, pct } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { LotTabs } from "../components/LotTabs";
import { Button, ErrorState, Icon, Note, Pipeline, Spinner, Toast } from "../components/ui";
import { MobileCameraModal } from "../components/MobileCameraModal";

interface CaptureData {
  lot: { id: number; lot_code: string; buyer_name: string; lot_size: number; status: string };
  units: Array<{ id: number; garment_code: string; views: Array<{
    id: number; side: string; image: { id: number; width: number; height: number; bytes: number } | null;
    review_state: string; inference_status: string;
    predictions: Array<{ id: number; review_state: string }>;
    open_proposals?: number;
  }> }>;
  progress: { units: number; required_units: number; views: number; reviewed: number; pending: number; pct_units: number };
  can_write: boolean;
  cloudinary_configured?: boolean;
  lan_ip?: string;
  public_base_url?: string;
  is_tunnel?: boolean;
  session_token?: string;
}

export function CapturePage() {
  const { lotId } = useParams();
  const id = Number(lotId);
  const { t, lang } = useSession();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["capture", id],
    queryFn: () => api.get<CaptureData>(`/api/lots/${id}/capture`),
  });
  const [garment, setGarment] = useState("");
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);
  const [side, setSide] = useState<"all" | "front" | "back">("all");
  const [jump, setJump] = useState("all");
  const [cameraModalOpen, setCameraModalOpen] = useState(false);
  const [cameraModalMode, setCameraModalMode] = useState<"camera" | "qr">("camera");
  const formRefs = useRef<Record<number, HTMLFormElement | null>>({});

  if (isLoading) return <AppShell title={t("cap.title")} active="lots"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("cap.title")} active="lots"><ErrorState message={(error as Error)?.message || "Not found"} /></AppShell>;

  const { lot, progress, units } = data;
  const allViews = units.flatMap((unit) => unit.views);
  const images = allViews.filter((view) => view.image);
  const manual = images.filter((view) => ["failed", "not_inferred"].includes(view.inference_status));
  const pending = images.filter((view) => view.inference_status === "pending");
  const ok = images.filter((view) => view.inference_status === "ok");
  const target = progress.required_units || lot.lot_size;

  const addUnit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      await api.post(`/api/lots/${id}/units`, { garment_code: garment });
      setGarment("");
      setToast(t("flash.saved"));
      await queryClient.invalidateQueries({ queryKey: ["capture", id] });
    } catch (caught) {
      const detail = caught instanceof ApiError ? caught.detail : "";
      setToast(detail === "units_full" ? t("err.units_full") : detail === "exists" ? t("err.exists") : t("err.failed"));
    } finally {
      setBusy(false);
    }
  };

  const upload = async (event: React.FormEvent, viewId: number) => {
    event.preventDefault();
    const form = formRefs.current[viewId];
    const input = form?.querySelector<HTMLInputElement>("input[type=file]");
    if (!input?.files?.length) return;
    setBusy(true);
    const body = new FormData();
    body.append("file", input.files[0]);
    try {
      const result = await api.postForm<{ image_id: number }>(`/api/lots/${id}/views/${viewId}/upload`, body);
      navigate(`/review/${result.image_id}`);
    } catch (caught) {
      const detail = caught instanceof ApiError ? caught.detail : "";
      setToast(detail === "duplicate" ? t("cap.duplicate") : detail === "too_big" ? t("cap.too_big") : detail === "bad_type" ? t("cap.bad_type") : t("err.failed"));
      await queryClient.invalidateQueries({ queryKey: ["capture", id] });
    } finally {
      setBusy(false);
    }
  };

  const visibleUnits = units.filter((unit) => jump === "all" || `unit-${unit.id}` === jump);

  return (
    <AppShell title={t("cap.title")} subtitle={`${lot.lot_code} · ${t("cap.guidance")}`} active="lots">
      {toast ? <Toast message={toast} onClose={() => setToast("")} /> : null}
      <LotTabs lotId={id} isAdmin={false} />

      <Pipeline steps={[
        { label: lang === "en" ? "1. AI Detection" : "১. এআই শনাক্তকরণ", value: !images.length ? (lang === "en" ? "0 photos" : "০ ছবি") : pending.length ? `${pending.length} queued` : `${ok.length} ok · ${manual.length} manual`, state: !images.length ? "pending" : pending.length ? "active" : "done" },
        { label: lang === "en" ? "2. Human Review" : "২. মানুষ পর্যালোচনা", value: `${progress.reviewed} / ${progress.views} ${lang === "en" ? "reviewed" : "পর্যালোচিত"}`, state: progress.views > 0 && progress.reviewed === progress.views ? "done" : progress.reviewed > 0 ? "active" : "pending" },
        { label: lang === "en" ? "3. Decision Engine" : "৩. নির্ধারক ইঞ্জিন", value: `${t("common.status")}: ${lot.status}`, state: lot.status === "decided" ? "done" : "pending" },
      ]} />

      {!data.can_write ? (
        <Note tone="warn">
          {lang === "en" ? "This lot is read-only for your role or already decided. Ask a Supervisor to reopen it." : "আপনার ভূমিকা বা সিদ্ধান্তের কারণে লটটি শুধু পড়া যায়। সুপারভাইজারকে খুলতে বলুন।"}
        </Note>
      ) : null}

      <div className="grid cols-3" style={{ marginBottom: 16 }}>
        <div className="kpi">
          <div className="lbl">{lang === "en" ? "Sample Units" : "স্যাম্পল ইউনিট"}</div>
          <div className="n">{num(progress.units, lang)}<small> / {progress.required_units ? num(progress.required_units, lang) : `${lang === "en" ? "Max" : "সর্বোচ্চ"} ${num(lot.lot_size, lang)}`}</small></div>
          <div className="bar" style={{ marginTop: 8 }}><i style={{ width: `${progress.pct_units}%` }} /></div>
        </div>
        <div className="kpi">
          <div className="lbl">{lang === "en" ? "Photos Uploaded" : "আপলোড করা ছবি"}</div>
          <div className="n">{num(images.length, lang)}<small> / {num(progress.views, lang)}</small></div>
          <div className="bar" style={{ marginTop: 8 }}><i style={{ width: `${pct(images.length, progress.views)}%` }} /></div>
        </div>
        <div className="kpi">
          <div className="lbl">{lang === "en" ? "Inference & Review" : "ইনফারেন্স ও পর্যালোচনা"}</div>
          <div className="row" style={{ marginTop: 6, gap: 6, flexWrap: "wrap" }}>
            {manual.length ? <span className="badge badge-warning"><span className="dot" />{manual.length} {lang === "en" ? "manual" : "ম্যানুয়াল"}</span> : null}
            <span className="badge badge-info">{progress.reviewed} {lang === "en" ? "reviewed" : "পর্যালোচিত"}</span>
            <span className="badge badge-neutral">{progress.pending} {lang === "en" ? "remaining" : "বাকি"}</span>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="pad-sm" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <div className="row" style={{ gap: 10, alignItems: "flex-start" }}>
            <span style={{ color: "var(--navy)", background: "var(--lime)", padding: 7, borderRadius: 8, display: "inline-flex" }}><Icon name="camera" size={18} /></span>
            <div>
              <b>{lang === "en" ? "Factory Capture Rules" : "ফ্যাক্টরি ক্যাপচার নিয়ম"}</b>
              <p className="small dim" style={{ margin: "2px 0 0" }}>
                {lang === "en" ? "JPEG or PNG only, up to 15 MB. No client-side compression (server creates canonical working copy). Fill frame with garment panel; no faces, no badges." : "শুধুমাত্র JPEG বা PNG, সর্বোচ্চ ১৫ মেগাবাইট। ক্লায়েন্ট-সাইডে কম্প্রেশন হবে না। পুরো ফ্রেমে গার্মেন্টস রাখুন; মুখ বা ব্যাজ নয়।"}
              </p>
            </div>
          </div>
          <div className="small" style={{ background: "var(--amber-bg)", color: "var(--amber-ink)", border: "1px solid var(--amber-line)", padding: "6px 10px", borderRadius: 6 }}>
            {lang === "en" ? 'iPhone HEIC not supported → Camera: "Most Compatible"' : 'আইফোন HEIC সমর্থিত নয় → ক্যামেরা: "Most Compatible"'}
          </div>
        </div>
      </div>

      {/* Automated Mobile Camera & Cloud Sync Banner */}
      <div className="card" style={{ marginBottom: 16, borderLeft: "4px solid #10b981" }}>
        <div className="pad-sm" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div className="row" style={{ gap: 12, alignItems: "center" }}>
            <span style={{ color: "var(--navy)", background: "var(--lime)", padding: 8, borderRadius: 8, display: "inline-flex" }}>
              <Icon name="camera" size={20} />
            </span>
            <div>
              <div style={{ fontWeight: 700, fontSize: "14.5px", display: "flex", alignItems: "center", gap: 8 }}>
                <span>{lang === "en" ? "Automated Mobile Camera & Cloud Sync" : "স্বয়ংক্রিয় মোবাইল ক্যামেরা ও ক্লাউড সিঙ্ক"}</span>
                {data.cloudinary_configured ? (
                  <span className="badge badge-success" style={{ fontSize: 11 }}>Cloudinary Active</span>
                ) : (
                  <span className="badge badge-neutral" style={{ fontSize: 11 }}>Local Storage</span>
                )}
                <span className="badge badge-info" style={{ fontSize: 11 }}>● Zero Browsing</span>
              </div>
              <p className="small dim" style={{ margin: "2px 0 0" }}>
                {lang === "en"
                  ? "No manual file browsing needed. Open mobile camera to snap and auto-upload directly into this lot."
                  : "ম্যানুয়ালি ফাইল ব্রাউজ করার প্রয়োজন নেই। মোবাইল ক্যামেরা খুলে ছবি তুললেই স্বয়ংক্রিয়ভাবে আপলোড হবে।"}
              </p>
            </div>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <Button variant="primary" size="sm" onClick={() => { setCameraModalMode("camera"); setCameraModalOpen(true); }}>
              <Icon name="camera" size={15} />
              <span>{lang === "en" ? "Launch Mobile Camera" : "মোবাইল ক্যামেরা চালু করুন"}</span>
            </Button>
            <Button variant="subtle" size="sm" onClick={() => { setCameraModalMode("qr"); setCameraModalOpen(true); }}>
              <Icon name="external-link" size={14} />
              <span>{lang === "en" ? "Scan Phone QR" : "ফোন কিউআর কোড"}</span>
            </Button>
          </div>
        </div>
      </div>

      {data.can_write ? (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-h">
            <h2>{lang === "en" ? "Register Garment" : "গার্মেন্ট নিবন্ধন"}</h2>
            <div className="right"><span className="chip">{progress.units} / {progress.required_units || `${lang === "en" ? "Max" : "সর্বোচ্চ"} ${lot.lot_size}`}</span></div>
          </div>
          <div className="pad-sm">
            {progress.units < target ? (
              <form onSubmit={addUnit} className="inline">
                <div className="field" style={{ flex: 1, minWidth: 200 }}>
                  <label htmlFor="garment_code">{lang === "en" ? "Garment code (unique in lot)" : "গার্মেন্ট কোড (লটে অনন্য)"}</label>
                  <input id="garment_code" value={garment} onChange={(event) => setGarment(event.target.value)} placeholder={`G-${String(progress.units + 1).padStart(2, "0")}`} pattern="[A-Za-z0-9_-]+" />
                </div>
                <button className="btn primary" type="submit" disabled={busy}><Icon name="plus" size={16} /><span>{lang === "en" ? "Register garment & open photo upload" : "গার্মেন্ট যোগ করুন ও ছবি আপলোড শুরু করুন"}</span></button>
              </form>
            ) : (
              <Note tone="info">
                <Icon name="check" size={15} /> {progress.required_units ? (lang === "en" ? `The required sample size (n=${progress.required_units}) is complete. All garment slots are registered.` : `প্রয়োজনীয় স্যাম্পল সাইজ (n=${progress.required_units}) সম্পূর্ণ।`) : (lang === "en" ? `All garment slots up to lot size (${lot.lot_size}) are registered.` : `লটের সর্বোচ্চ সাইজ (${lot.lot_size} টি) পর্যন্ত সকল গার্মেন্ট নিবন্ধিত হয়েছে।`)}
              </Note>
            )}
          </div>
        </div>
      ) : null}

      {units.length ? (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="pad-sm" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
            <div className="row" style={{ gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <label htmlFor="unitPicker" className="small bold" style={{ margin: 0 }}>{lang === "en" ? "Jump to garment:" : "গার্মেন্টে যান:"}</label>
              <select id="unitPicker" value={jump} onChange={(event) => setJump(event.target.value)} style={{ fontSize: 13, padding: "5px 9px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--surface)" }}>
                <option value="all">{lang === "en" ? "All garments" : "সব গার্মেন্টস"} ({units.length})</option>
                {units.map((unit) => <option key={unit.id} value={`unit-${unit.id}`}>{unit.garment_code}</option>)}
              </select>
            </div>
            <div className="row" style={{ gap: 6 }}>
              {(["all", "front", "back"] as const).map((value) => (
                <button key={value} className={`btn sm ${side === value ? "subtle active" : "ghost"}`} type="button" onClick={() => setSide(value)}>
                  {value === "all" ? (lang === "en" ? "All views" : "সব ভিউ") : t(`cap.${value}`)}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(330px,1fr))", gap: 14 }}>
        {visibleUnits.map((unit) => (
          <div className="card unit-garment-card" id={`unit-${unit.id}`} key={unit.id}>
            <div className="card-h">
              <h2>{unit.garment_code}</h2>
              <div className="right"><span className="small dim">{unit.views.length} {lang === "en" ? (unit.views.length === 1 ? "view" : "views") : "ভিউ"}</span></div>
            </div>
            <div className="pad-sm">
              {unit.views.filter((view) => side === "all" || view.side === side).map((view) => (
                <div className="upload-view" key={view.id}>
                  <div className="between" style={{ marginBottom: 8 }}>
                    <div className="row" style={{ gap: 6 }}>
                      <span className="badge badge-neutral bold">{t(`cap.${view.side}`)}</span>
                      {view.review_state === "confirmed_defects" ? <span className="badge badge-danger"><span className="dot" />{view.predictions.filter((prediction) => prediction.review_state === "confirmed").length} {lang === "en" ? "defect(s)" : "ত্রুটি"}</span>
                        : view.review_state === "reviewed_clean" ? <span className="badge badge-success"><span className="dot" />{lang === "en" ? "reviewed clean" : "পরিষ্কার"}</span>
                          : view.review_state === "needs_retake" ? <span className="badge badge-warning"><span className="dot" />{t("rev.retake")}</span>
                            : view.image ? <span className="badge badge-pending"><span className="dot" />{lang === "en" ? "pending review" : "পর্যালোচনা বাকি"}</span>
                              : <span className="badge badge-neutral">—</span>}
                    </div>
                    {view.image ? (
                      <div className="small dim">
                        {view.inference_status === "ok" ? <span className="badge badge-success" style={{ fontSize: 10.5 }}>inferred</span>
                          : ["failed", "not_inferred"].includes(view.inference_status) ? <span className="badge badge-warning" style={{ fontSize: 10.5 }}>{lang === "en" ? "manual" : "ম্যানুয়াল"}</span>
                            : <span className="badge badge-pending" style={{ fontSize: 10.5 }}>queued</span>}
                      </div>
                    ) : null}
                  </div>

                  <div className="row" style={{ gap: 10, alignItems: "flex-start" }}>
                    {view.image ? (
                      <>
                        <a href={`/review/${view.image.id}`} style={{ display: "block", flexShrink: 0 }}>
                          <img className="thumb" src={`/api/images/${view.image.id}`} alt={`${unit.garment_code} ${view.side}`} style={{ width: 72, height: 72, objectFit: "cover", borderRadius: 6, border: "1px solid var(--line)" }} />
                        </a>
                        <div className="small dim" style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 600, color: "var(--text)" }}>
                            {view.open_proposals ? `${view.open_proposals} ${lang === "en" ? "open proposal(s)" : "খোলা প্রস্তাব"}` : view.predictions.length ? `${view.predictions.length} ${lang === "en" ? "proposals reviewed" : "প্রস্তাব পর্যালোচিত"}` : (lang === "en" ? "No proposals" : "কোনো প্রস্তাব নেই")}
                          </div>
                          <div style={{ marginTop: 2 }}>{Math.round(view.image.bytes / 1024)} KB · {view.image.width}×{view.image.height}</div>
                          <div style={{ marginTop: 6 }}>
                            <a className="btn sm subtle" href={`/review/${view.image.id}`} style={{ padding: "3px 8px", fontSize: 11.5 }}><Icon name="eye" size={13} /><span>{t("rev.title")} →</span></a>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="small dim" style={{ padding: "16px 8px", background: "var(--bg)", borderRadius: 6, width: "100%", textAlign: "center" }}>
                        <Icon name="camera" size={18} />
                        <div style={{ marginTop: 4 }}>{lang === "en" ? "No photo yet. Capture or upload photo below." : "এখনো ছবি নেই। নিচে ক্যামেরা বা ফাইল ব্যবহার করুন।"}</div>
                      </div>
                    )}
                  </div>

                  {data.can_write ? (
                    <form
                      ref={(element) => { formRefs.current[view.id] = element; }}
                      onSubmit={(event) => upload(event, view.id)}
                      style={{ marginTop: 10 }}
                    >
                      <div className="inline" style={{ gap: 6 }}>
                        <div className="field" style={{ flex: 2, margin: 0 }}>
                          <label className="sr-only" htmlFor={`file-${view.id}`}>{t("cap.upload")}</label>
                          <input className="upload-input" id={`file-${view.id}`} type="file" name="file" accept="image/jpeg,image/png" capture="environment" required style={{ fontSize: 12, padding: "6px 8px" }} />
                        </div>
                        <button className={`btn sm ${view.image ? "subtle" : "primary"}`} type="submit" style={{ minHeight: 36 }} disabled={busy}>
                          <Icon name="upload" size={14} /><span>{view.image ? t("cap.replace") : t("cap.upload")}</span>
                        </button>
                      </div>
                    </form>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        ))}

        {!visibleUnits.length ? (
          <div className="card" style={{ gridColumn: "1/-1", padding: "36px 24px", textAlign: "center" }}>
            <span className="empty-icon" style={{ display: "inline-flex", padding: 14, background: "var(--subtle)", borderRadius: "50%", marginBottom: 12, color: "var(--navy)" }}><Icon name="camera" size={30} /></span>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>{lang === "en" ? "Step 1: Register Sample Garments" : "ধাপ ১: স্যাম্পল গার্মেন্ট নিবন্ধন করুন"}</h3>
            <p className="small dim" style={{ maxWidth: 540, margin: "0 auto 18px", lineHeight: 1.5 }}>
              {lang === "en" ? "Photos are attached per garment (Front and Back views). Register a garment to reveal its upload controls." : "ছবি প্রতিটি গার্মেন্টের ফ্রন্ট ও ব্যাক ভিউ অনুযায়ী আপলোড হয়। ছবি আপলোড করতে একটি গার্মেন্ট নিবন্ধন করুন।"}
            </p>
          </div>
        ) : null}
      </div>

      {cameraModalOpen && (
        <MobileCameraModal
          lotId={id}
          lotCode={lot.lot_code}
          units={units}
          cloudinaryConfigured={data.cloudinary_configured}
          lanIp={data.lan_ip}
          publicBaseUrl={data.public_base_url}
          isTunnel={data.is_tunnel}
          sessionToken={data.session_token}
          initialMode={cameraModalMode}
          onClose={() => setCameraModalOpen(false)}
          onUploadSuccess={async () => {
            await queryClient.invalidateQueries({ queryKey: ["capture", id] });
          }}
        />
      )}
    </AppShell>
  );
}
