import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useSession } from "../lib/session";
import { num, numGrouped, pct } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { LotTabs } from "../components/LotTabs";
import {
  Button, ErrorState, Field, Icon, Note, Pipeline, Spinner, Toast,
} from "../components/ui";

interface PlanData {
  lot: { id: number; lot_code: string; buyer_name: string; lot_size: number; status: string; critical_nonvisual_status: string };
  plan: { version: number; n: number; counting_mode: string; is_demo: boolean; source_edition: string; source_reference: string;
    critical: { ac: number; re: number }; major: { ac: number; re: number }; minor: { ac: number; re: number };
    critical_aql: number | null; major_aql: number | null; minor_aql: number | null } | null;
  progress: { units: number; required_units: number; views: number; reviewed: number; pending: number };
  units: Array<{ id: number; views: Array<{ image: unknown; inference_status: string }> }>;
  decision: { outcome: string; primary_reason: string } | null;
  evidence_summary: { units_present: number; required_units: number; counts: { critical: number; major: number; minor: number }; nonvisual_status: string };
  is_supervisor: boolean;
  locked: boolean;
}

type Limits = { critical_ac: string; critical_re: string; major_ac: string; major_re: string; minor_ac: string; minor_re: string };

const emptyLimits: Limits = { critical_ac: "", critical_re: "", major_ac: "", major_re: "", minor_ac: "", minor_re: "" };

export function PlanPage() {
  const { lotId } = useParams();
  const id = Number(lotId);
  const { t, lang, reason } = useSession();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["plan", id],
    queryFn: () => api.get<PlanData>(`/api/lots/${id}/plan`),
  });

  const [form, setForm] = useState({
    n: "",
    counting_mode: "highest_class_only",
    critical_aql: "",
    major_aql: "",
    minor_aql: "",
    source_edition: "",
    source_reference: "",
    confirmed: false,
    is_demo: false,
    ...emptyLimits,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!data) return;
    const plan = data.plan;
    setForm({
      n: plan ? String(plan.n) : "",
      counting_mode: plan?.counting_mode || "highest_class_only",
      critical_aql: plan?.critical_aql != null ? String(plan.critical_aql) : "",
      major_aql: plan?.major_aql != null ? String(plan.major_aql) : "",
      minor_aql: plan?.minor_aql != null ? String(plan.minor_aql) : "",
      source_edition: plan?.source_edition || "",
      source_reference: plan?.source_reference || "",
      confirmed: false,
      is_demo: Boolean(plan?.is_demo),
      critical_ac: plan ? String(plan.critical.ac) : "",
      critical_re: plan ? String(plan.critical.re) : "",
      major_ac: plan ? String(plan.major.ac) : "",
      major_re: plan ? String(plan.major.re) : "",
      minor_ac: plan ? String(plan.minor.ac) : "",
      minor_re: plan ? String(plan.minor.re) : "",
    });
  }, [data]);

  const set = (key: keyof typeof form, value: string | boolean) =>
    setForm((previous) => ({ ...previous, [key]: value }));

  const reMatches = (ac: string, re: string) => re !== "" && ac !== "" && Number(re) === Number(ac) + 1;

  const preview = useMemo(() => {
    if (!data) return null;
    const n = Number(form.n) || 0;
    const limits = {
      critical: { ac: Number(form.critical_ac), re: Number(form.critical_re) },
      major: { ac: Number(form.major_ac), re: Number(form.major_re) },
      minor: { ac: Number(form.minor_ac), re: Number(form.minor_re) },
    };
    return {
      coverage: data.lot.lot_size ? pct(n, data.lot.lot_size) : 0,
      limits,
      valid: ["critical", "major", "minor"].every((key) => {
        const item = limits[key as keyof typeof limits];
        return Number.isFinite(item.ac) && item.ac >= 0 && item.re === item.ac + 1;
      }),
    };
  }, [data, form]);

  if (isLoading) return <AppShell title={t("plan.title")} active="lots"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("plan.title")} active="lots"><ErrorState message={(error as Error)?.message || "Not found"} /></AppShell>;

  const { lot, progress, decision, plan } = data;
  const allViews = data.units.flatMap((unit) => unit.views);
  const images = allViews.filter((view) => view.image);
  const manual = images.filter((view) => ["failed", "not_inferred"].includes(view.inference_status));
  const pending = images.filter((view) => view.inference_status === "pending");
  const ok = images.filter((view) => view.inference_status === "ok");

  const gateState = plan ? "done" : "blocked";
  const capState = !images.length ? "not-started" : images.length >= progress.views ? "done" : "in-progress";
  const aiState = !images.length ? "not-started" : pending.length ? "in-progress" : "done";
  const revState = !images.length || !progress.views ? "not-started" : progress.reviewed === progress.views ? "done" : "in-progress";
  const decState = !plan ? "blocked" : lot.status === "decided" || decision ? "done" : revState === "done" ? "in-progress" : "not-started";

  const applyPreset = () => {
    setForm((previous) => ({
      ...previous,
      n: String(Math.min(8, lot.lot_size)),
      counting_mode: "highest_class_only",
      critical_ac: "0", critical_re: "1",
      major_ac: "1", major_re: "2",
      minor_ac: "2", minor_re: "3",
      critical_aql: "0", major_aql: "1.0", minor_aql: "2.5",
      source_edition: "ISO 2859-1:2026 (demo assumption)",
      source_reference: "LT-2026 demo",
      is_demo: true,
    }));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      await api.post(`/api/lots/${id}/plan`, {
        ...form,
        n: Number(form.n),
        critical_ac: Number(form.critical_ac),
        critical_re: Number(form.critical_re),
        major_ac: Number(form.major_ac),
        major_re: Number(form.major_re),
        minor_ac: Number(form.minor_ac),
        minor_re: Number(form.minor_re),
        is_demo: form.is_demo ? 1 : 0,
        confirmed: form.confirmed ? "1" : "",
      });
      setToast(lang === "en" ? "Sampling plan saved successfully." : "স্যাম্পলিং প্ল্যান সফলভাবে সংরক্ষিত হয়েছে।");
      await queryClient.invalidateQueries({ queryKey: ["plan", id] });
      await queryClient.invalidateQueries({ queryKey: ["lot", id] });
    } catch (caught) {
      if (caught instanceof ApiError && typeof caught.detail === "object" && caught.detail) {
        setErrors(((caught.detail as { errors?: Record<string, string> }).errors) || {});
      } else {
        setErrors({ form: t("err.failed") });
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell title={t("plan.title")} subtitle={`${lot.lot_code} · ${lot.buyer_name} · ${t("lots.size")} ${numGrouped(lot.lot_size, lang)}`} active="lots">
      {toast ? <Toast message={toast} onClose={() => setToast("")} /> : null}
      <LotTabs lotId={id} isAdmin={false} />

      <Pipeline steps={[
        { label: lang === "en" ? "Gate: Sampling Plan" : "গেট: স্যাম্পলিং প্ল্যান", value: plan ? `v${plan.version} · n=${plan.n}` : lang === "en" ? "No sampling plan" : "স্যাম্পলিং প্ল্যান নেই", state: gateState, title: plan ? "" : "HOLD_PLAN_MISSING" },
        { label: lang === "en" ? "1. Photo Capture" : "১. ছবি ধারণ", value: `${num(images.length, lang)} / ${num(progress.views || lot.lot_size * 2, lang)}`, state: capState },
        { label: lang === "en" ? "2. AI Proposals" : "২. এআই প্রস্তাব", value: !images.length ? t("pipe.awaiting_photos") : pending.length ? `${num(pending.length, lang)} queued` : `${num(ok.length, lang)} ok · ${num(manual.length, lang)} manual`, state: aiState },
        { label: lang === "en" ? "3. Human Review" : "৩. মানুষ নিশ্চিত করে", value: `${num(progress.reviewed, lang)} / ${num(progress.views, lang)} ${lang === "en" ? "reviewed" : "পর্যালোচিত"}`, state: revState },
        { label: lang === "en" ? "4. Decision Engine" : "৪. ইঞ্জিনের সিদ্ধান্ত", value: !plan ? (lang === "en" ? "No sampling plan" : "স্যাম্পলিং প্ল্যান নেই") : decision ? t(`out.${decision.outcome}`) : t("pipe.ready_to_compute"), state: decState, title: decision?.primary_reason },
      ]} />

      {Object.keys(errors).length ? (
        <div className="error-state plan-error-summary mb-3" role="alert">
          <span className="error-icon"><Icon name="alert-octagon" size={24} /></span>
          <div>
            <b>{lang === "en" ? "Validation Error: Please correct the following issues" : "যাচাইকরণ ত্রুটি: অনুগ্রহ করে নিচের বিষয়গুলো সংশোধন করুন"}</b>
            <ul className="error-list">{Object.entries(errors).map(([key, message]) => <li key={key}>{message}</li>)}</ul>
          </div>
        </div>
      ) : null}

      <div className="split">
        <div className="card">
          <div className="card-h">
            <h2>{t("plan.title")}</h2>
            <div className="right d-flex gap-2 align-items-center">
              {plan ? <span className="badge badge-neutral">v{plan.version}</span> : <span className="badge badge-danger">{lang === "en" ? "Not set" : "সেট করা হয়নি"}</span>}
              {plan?.is_demo ? <span className="badge badge-warning">{lang === "en" ? "Unauthorized demo assumption" : "অননুমোদিত ডেমো অনুমান"}</span> : null}
              {data.is_supervisor && !data.locked ? <Button size="sm" icon="sparkles" onClick={applyPreset}>{lang === "en" ? "Use demo preset" : "ডেমো প্রিসেট ব্যবহার করুন"}</Button> : null}
            </div>
          </div>
          <div className="pad">
            <p className="small dim mb-3">{t("plan.subtitle")}</p>
            <div className="note warn mb-3">
              <b>{t("lot.plan_assumption")}</b>
              <div className="small dim mt-1">
                {lang === "en"
                  ? "Single sampling, normal inspection, General Inspection Level II (ISO 2859-1 / ANSI ASQ Z1.4). Default parameters are an assumption, not a standard lookup. Lotline never reconstructs tables or looks up plans automatically."
                  : "সিঙ্গেল স্যাম্পলিং, নরমাল ইন্সপেকশন, জেনারেল ইন্সপেকশন লেভেল II (ISO 2859-1 / ANSI ASQ Z1.4)। ডিফল্ট প্যারামিটার একটি অনুমান। Lotline কখনো টেবিল থেকে প্ল্যান খোঁজে না।"}
              </div>
            </div>

            {data.locked ? (
              <div className="locked-pill badge badge-warning mb-3">
                <Icon name="lock" size={14} />
                <span>{lang === "en" ? "Locked" : "লক হয়েছে"} · {lang === "en" ? "Supervisor" : "সুপারভাইজার"}</span>
              </div>
            ) : !data.is_supervisor ? (
              <Note tone="info">
                <Icon name="shield" size={15} /> {lang === "en" ? "Inspector view (read-only): Awaiting supervisor configuration. Only an active Supervisor can configure or modify the sampling plan." : "ইন্সপেক্টর ভিউ (শুধু পড়া যায়): সুপারভাইজারের অপেক্ষায় — শুধুমাত্র সুপারভাইজার স্যাম্পলিং প্ল্যান কনফিগার করতে পারেন।"}
              </Note>
            ) : null}

            {data.is_supervisor && !data.locked ? (
              <form onSubmit={submit}>
                <div className="grid cols-2 mb-3">
                  <Field label={t("plan.n")} required error={errors.n} hint={`${lang === "en" ? "Lot size" : "লট সাইজ"}: ${numGrouped(lot.lot_size, lang)}`}>
                    <input type="number" min={1} max={lot.lot_size} required value={form.n} onChange={(event) => set("n", event.target.value)} />
                  </Field>
                  <Field label={t("plan.mode")} required error={errors.counting_mode}>
                    <select value={form.counting_mode} onChange={(event) => set("counting_mode", event.target.value)}>
                      <option value="highest_class_only">{t("plan.mode_highest")}</option>
                      <option value="every_class">{t("plan.mode_every")}</option>
                    </select>
                  </Field>
                </div>

                <div className="mb-3">
                  <div className="table-header-lbl">
                    <span className="small bold">{lang === "en" ? "Acceptance & Rejection Limits per Class (Single Sampling)" : "প্রতি শ্রেণির গ্রহণযোগ্যতা ও বাতিলের সীমা (সিঙ্গেল স্যাম্পলিং)"}</span>
                  </div>
                  <div className="tblwrap">
                    <table className="table plan-form-table">
                      <thead>
                        <tr>
                          <th>{lang === "en" ? "Class" : "শ্রেণি"}</th>
                          <th>{t("plan.aql")} <span className="dim small">({lang === "en" ? "Not used by decision engine" : "ইঞ্জিন এটি ব্যবহার করে না"})</span></th>
                          <th className="num">{t("plan.ac")} <span className="req">*</span></th>
                          <th className="num">{t("plan.re")} <span className="req">*</span></th>
                        </tr>
                      </thead>
                      <tbody>
                        {(["critical", "major", "minor"] as const).map((key) => {
                          const ac = form[`${key}_ac` as keyof typeof form] as string;
                          const re = form[`${key}_re` as keyof typeof form] as string;
                          const aql = form[`${key}_aql` as keyof typeof form] as string;
                          return (
                            <tr key={key}>
                              <th scope="row" className="plan-class-cell"><span className={`badge ${key}`}>{t(`plan.${key}`)}</span></th>
                              <td><input value={aql} placeholder="e.g. 1.0" onChange={(event) => set(`${key}_aql` as keyof typeof form, event.target.value)} /></td>
                              <td className="num"><input type="number" min={0} required value={ac} className={errors[`${key}_ac`] ? "is-invalid" : ""} onChange={(event) => set(`${key}_ac` as keyof typeof form, event.target.value)} /></td>
                              <td className="num">
                                <input type="number" min={1} required value={re} className={errors[`${key}_re`] || (re && ac && !reMatches(ac, re)) ? "is-invalid" : ""} onChange={(event) => set(`${key}_re` as keyof typeof form, event.target.value)} />
                                {re && ac && !reMatches(ac, re) ? <div className="row-warning text-danger small mt-1">Re must equal Ac + 1</div> : null}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="grid cols-2 mb-3">
                  <Field label={t("plan.source_edition")}><input value={form.source_edition} placeholder={lang === "en" ? "Standard name & edition year" : "স্ট্যান্ডার্ডের নাম ও সংস্করণ বছর"} onChange={(event) => set("source_edition", event.target.value)} /></Field>
                  <Field label={t("plan.source_ref")}><input value={form.source_reference} placeholder={lang === "en" ? "Buyer PO number" : "ক্রেতার PO নম্বর"} onChange={(event) => set("source_reference", event.target.value)} /></Field>
                </div>

                {!form.source_edition && !form.source_reference ? (
                  <div className="note warn mb-3">
                    <Icon name="triangle-alert" size={15} /> {lang === "en" ? "Unreferenced plan — decisions and reports will be permanently labeled \"Unauthorized assumption\"." : "সূত্রহীন প্ল্যান — সিদ্ধান্ত ও রিপোর্টে 'অননুমোদিত অনুমান' লেবেল থাকবে"}
                  </div>
                ) : null}

                <div className="note info mb-3">
                  <Icon name="shield-alert" size={15} /> {lang === "en" ? "Single-sampling invariant: Re must equal Ac + 1 for each class. Any mismatch is invalid and causes decisions to result in HOLD_PLAN_INVALID." : "সিঙ্গেল স্যাম্পলিং নিয়ম: প্রতিটি শ্রেণিতে Re = Ac + 1 হতে হবে। অমিল থাকলে HOLD_PLAN_INVALID হবে।"}
                </div>

                <div className={`plan-confirm-card mb-3 ${errors.confirmed ? "is-invalid-box" : ""}`}>
                  <label className="check-label d-flex gap-2 align-items-flex-start cursor-pointer">
                    <input type="checkbox" checked={form.confirmed} onChange={(event) => set("confirmed", event.target.checked)} className="mt-1" required />
                    <div className="check-body">
                      <div className="bold">{lang === "en" ? "I have verified the values against the source standard / buyer specification." : "আমি উৎস থেকে মান মিলিয়ে যাচাই করেছি"} <span className="req">*</span></div>
                      <div className="small dim mt-1">{lang === "en" ? "Audit log will record your identity, timestamp, and plan confirmation. The decision engine will not treat unconfirmed plans as valid." : "অডিট লগে আপনার পরিচয়, সময় ও যাচাইয়ের সত্যতা সংরক্ষিত হবে। নিশ্চিত না করা প্ল্যানকে নির্ধারক ইঞ্জিন বৈধ বিবেচনা করবে না।"}</div>
                    </div>
                  </label>
                  {errors.confirmed ? <div className="field-error mt-2">{errors.confirmed}</div> : null}
                </div>

                <Button type="submit" variant="primary" icon="check" disabled={busy}>{t("common.save")}</Button>
              </form>
            ) : plan ? (
              <div className="tblwrap">
                <table className="table">
                  <thead><tr><th>{lang === "en" ? "Class" : "শ্রেণি"}</th><th>{t("plan.aql")}</th><th className="num">Ac</th><th className="num">Re</th></tr></thead>
                  <tbody>
                    {(["critical", "major", "minor"] as const).map((key) => (
                      <tr key={key}>
                        <th className="plan-class-cell"><span className={`badge ${key}`}>{t(`plan.${key}`)}</span></th>
                        <td>{plan[`${key}_aql`] != null ? num(plan[`${key}_aql`], lang) : "—"}</td>
                        <td className="num mono bold">{num(plan[key].ac, lang)}</td>
                        <td className="num mono bold">{num(plan[key].re, lang)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty p-3"><b>{lang === "en" ? "Plan not set. Decisions will HOLD." : "প্ল্যান সেট করা হয়নি। সিদ্ধান্ত হোল্ড থাকবে।"}</b></div>
            )}
          </div>
        </div>

        <div className="stack">
          <div className="card plan-preview-card">
            <div className="card-h">
              <h2>{lang === "en" ? "Live Plan & Evidence Preview" : "লাইভ প্ল্যান ও প্রমাণের পূর্বরূপ"}</h2>
              <div className="right">
                {preview?.valid ? <span className="badge badge-success">{lang === "en" ? "Valid single sampling" : "বৈধ সিঙ্গেল-স্যাম্পলিং"}</span> : <span className="badge badge-danger">{lang === "en" ? "Not set" : "সেট করা হয়নি"}</span>}
              </div>
            </div>
            <div className="pad-sm">
              <div className="plan-preview-metric mb-3">
                <div className="d-flex justify-content-between align-items-baseline">
                  <span className="dim small">{lang === "en" ? "Sample Coverage" : "নমুনা কভারেজ"}</span>
                  <span className="metric-val mono bold">{form.n ? `${num(form.n, lang)} / ${numGrouped(lot.lot_size, lang)} (${num(preview?.coverage ?? 0, lang)}%)` : "--"}</span>
                </div>
                <div className="progress-bar-track mt-1"><div className="progress-bar-fill" style={{ width: `${preview?.coverage ?? 0}%` }} /></div>
              </div>

              <div className="preview-limits-box mb-3">
                <div className="dim small bold mb-1">{lang === "en" ? "Configured Class Limits" : "শ্রেণিভিত্তিক সীমা"}</div>
                <table className="table sm m-0">
                  <tbody>
                    {(["critical", "major", "minor"] as const).map((key) => (
                      <tr key={key}>
                        <td className="dim">{t(`plan.${key}`)}</td>
                        <td className="right mono bold">
                          {form[`${key}_ac` as keyof typeof form] !== "" ? `Ac: ${num(form[`${key}_ac` as keyof typeof form], lang)} / Re: ${num(form[`${key}_re` as keyof typeof form], lang)}` : "--"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="preview-info-list small mb-3">
                <div className="preview-info-item"><span className="dim">{t("plan.mode")}:</span> <span className="bold">{t(form.counting_mode === "highest_class_only" ? "plan.mode_highest" : "plan.mode_every")}</span></div>
                <div className="preview-info-item mt-1">
                  <span className="dim">{lang === "en" ? "Decision label" : "সিদ্ধান্তের লেবেল"}:</span>{" "}
                  {form.is_demo ? <span className="badge badge-warning ms-1">{lang === "en" ? "Unauthorized demo assumption" : "অননুমোদিত ডেমো অনুমান"}</span>
                    : form.source_edition ? <span className="badge badge-neutral ms-1">{form.source_edition}</span>
                      : <span className="badge badge-neutral ms-1">{lang === "en" ? "Unauthorized assumption" : "অননুমোদিত অনুমান"}</span>}
                </div>
              </div>

              <div className={`preview-forecast-box p-3 rounded ${!plan ? "forecast-hold" : decision?.outcome === "ACCEPT" ? "forecast-accept" : decision?.outcome === "REJECT" ? "forecast-reject" : "forecast-hold"}`}>
                <div className="d-flex align-items-center gap-2 mb-1">
                  <Icon name="shield-alert" size={16} />
                  <strong>{!plan ? (lang === "en" ? "HOLD Forecast (Plan Not Set)" : "HOLD পূর্বাভাস (প্ল্যান সেট করা হয়নি)") : decision ? `${lang === "en" ? "Predicted Decision: " : "অনুমিত সিদ্ধান্ত: "}${t(`out.${decision.outcome}`)}` : lang === "en" ? "HOLD Forecast (No Evidence)" : "HOLD পূর্বাভাস (প্রমাণ নেই)"}</strong>
                </div>
                <p className="small mb-0">{!plan ? (lang === "en" ? "No sampling plan is configured — decision engine will return HOLD_PLAN_MISSING." : "কোনো স্যাম্পলিং প্ল্যান সেট করা হয়নি — সিদ্ধান্ত গণনা HOLD_PLAN_MISSING রিটার্ন করবে।") : decision ? reason(decision.primary_reason).text : (lang === "en" ? "0 garments registered — will remain HOLD after saving: no evidence." : "০ গার্মেন্ট নিবন্ধিত — সংরক্ষণের পরও HOLD থাকবে: প্রমাণ নেই।")}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-h"><h2>{lang === "en" ? "Audit & Report Compliance" : "অডিট ও রিপোর্ট নীতি"}</h2></div>
            <div className="pad-sm small dim">
              <ul className="plan-compliance-list">
                <li>{lang === "en" ? "Plans are entered explicitly by a Supervisor; Lotline never suggests or guesses a plan." : "সুপারভাইজার সরাসরি প্ল্যান লিখবেন; Lotline কখনো অনুমান করে না।"}</li>
                <li>{lang === "en" ? "Sampling plan assumption label is embedded permanently in the decision snapshot and PDF certificate." : "স্যাম্পলিং প্ল্যানের অনুমানের লেবেল সিদ্ধান্তে ও সার্টিফিকেটে স্থায়ীভাবে যুক্ত হয়।"}</li>
                <li>{lang === "en" ? "Counting mode strictly determines how multi-defect garments count toward limits." : "গণনার পদ্ধতি নির্ধারণ করে একাধিক ত্রুটিযুক্ত গার্মেন্ট কীভাবে সীমা প্রভাবিত করে।"}</li>
                <li>{lang === "en" ? "Once a decision is computed, the lot plan is locked to preserve evidence integrity." : "সিদ্ধান্ত নেওয়া হলে প্রমাণের নির্ভরযোগ্যতা রক্ষায় প্ল্যান লক হয়ে যায়।"}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
