import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import { num, numGrouped } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { LotTabs } from "../components/LotTabs";
import { Button, ErrorState, Icon, Spinner } from "../components/ui";

interface ReportData {
  rc: {
    lot_code: string; product: string; buyer: string; sequence: number; created_at: string;
    engine_version: string; outcome: string;
    override: { final_disposition: string; reason: string; approved: boolean } | null;
    plan: {
      n: number; counting_mode: string; source_edition: string; source_reference: string;
      critical: { ac: number; re: number }; major: { ac: number; re: number }; minor: { ac: number; re: number };
    } | null;
    n_effective: number | null;
    counts: Record<string, number>;
    class_status: Record<string, { count: number; ac: number; re: number; status: string }>;
    reasons: Array<{ code: string; text: string }>;
    units_present: number; required_units: number; views_pending: number; evidence_bad: number;
    nonvisual: string; images: number; units: number; model: string; model_domains: string;
    manual: boolean; selection: string; snapshot_hash: string; lot: { id: number };
  };
}

export function ReportPage() {
  const { lotId } = useParams();
  const id = Number(lotId);
  const { t, lang, reason } = useSession();
  const { data, isLoading, error } = useQuery({
    queryKey: ["report", id],
    queryFn: () => api.get<ReportData>(`/api/lots/${id}/report`),
  });

  if (isLoading) return <AppShell title={t("rep.title")} active="lots"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("rep.title")} active="lots"><ErrorState message={(error as Error)?.message || "Not found"} /></AppShell>;

  const rc = data.rc;
  const outcome = rc.override?.approved ? rc.override.final_disposition.replace("OVERRIDE_", "") : rc.outcome;

  return (
    <AppShell title={t("rep.title")} subtitle={`${rc.lot_code} · ${t("rep.one_page")}`} active="lots">
      <LotTabs lotId={id} isAdmin={false} />

      <div className="btnrow no-print" style={{ marginBottom: 18, justifyContent: "space-between", alignItems: "center" }}>
        <div className="row" style={{ gap: 10 }}>
          <Button href={`/api/lots/${id}/report.pdf`} variant="primary" icon="download">{t("common.download_pdf")}</Button>
          <Button icon="printer" onClick={() => window.print()}>{t("common.print")}</Button>
        </div>
        <Link className="btn ghost" to={`/lots/${id}/decision`}>← {t("dec.title")}</Link>
      </div>

      <div className="card" id="reportSheet" style={{ maxWidth: 880, margin: "0 auto", boxShadow: "0 4px 18px rgba(0,0,0,0.04)" }}>
        <div className="pad" style={{ padding: "36px 42px" }}>
          <div className="between" style={{ alignItems: "flex-start", borderBottom: "2px solid var(--text)", paddingBottom: 16 }}>
            <div>
              <div style={{ fontWeight: 800, letterSpacing: ".2em", fontSize: 12, color: "var(--muted)" }}>LOTLINE · QUALITY CONTROL</div>
              <h1 style={{ fontSize: 24, fontWeight: 800, margin: "6px 0 2px", letterSpacing: "-0.02em", color: "var(--text)" }}>{t("rep.title")}</h1>
              <div className="small dim">{t("app.tagline")}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: "var(--text)" }}>{rc.lot_code}</div>
              <div className="small dim" style={{ marginTop: 2 }}>{lang === "en" ? "Decision Record" : "সিদ্ধান্ত রেকর্ড"} #{rc.sequence} · {rc.created_at.slice(0, 16)}</div>
              <div className="small dim mono" style={{ fontSize: 11 }}>Engine: {rc.engine_version} · Model: {rc.model}</div>
            </div>
          </div>

          <div style={{ margin: "20px 0 16px", padding: "16px 20px", background: "var(--subtle)", borderRadius: "var(--radius-sm)", border: "1px solid var(--line)" }}>
            <div className="between" style={{ alignItems: "center" }}>
              <div>
                <div className="small dim" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>{lang === "en" ? "System Recommendation" : "সিস্টেম সুপারিশ"}</div>
                <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 10 }}>
                  <span className={`badge ${rc.outcome}`} style={{ fontSize: 14, padding: "4px 12px", fontWeight: 700 }}><span className="dot" />{t(`out.${rc.outcome}`)}</span>
                  <span className="small dim">{rc.product} · {rc.buyer}</span>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="small dim" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>{lang === "en" ? "Final Disposition" : "চূড়ান্ত সিদ্ধান্ত"}</div>
                <div style={{ marginTop: 4 }}>
                  <span className={`badge ${outcome}`} style={{ fontSize: 14, padding: "4px 12px", fontWeight: 700 }}>
                    <span className="dot" />{t(`out.${outcome}`)}{rc.override?.approved ? " (OVERRIDE)" : ""}
                  </span>
                </div>
              </div>
            </div>

            {rc.override ? (
              <div className="note warn" style={{ marginTop: 14, marginBottom: 0 }}>
                <div className="small">
                  <b>OVERRIDE RECORD:</b> System recommended <b>{t(`out.${rc.outcome}`)}</b>, Supervisor requested <b>{t(`out.${rc.override.final_disposition.replace("OVERRIDE_", "")}`)}</b>.
                  <div style={{ marginTop: 3 }}><i>Reason:</i> {rc.override.reason}</div>
                  {!rc.override.approved ? <div style={{ marginTop: 4, fontWeight: 600, color: "var(--amber-ink)" }}>⚠️ {lang === "en" ? "Awaiting second-Supervisor approval. The system recommendation remains the legal disposition until approved." : "⚠️ দ্বিতীয় সুপারভাইজারের অনুমোদনের অপেক্ষায়।"}</div>
                    : <div style={{ marginTop: 4, color: "var(--success)" }}>✓ {lang === "en" ? "Approved by second supervisor. Final disposition is now effective." : "✓ দ্বিতীয় সুপারভাইজার কর্তৃক অনুমোদিত।"}</div>}
                </div>
              </div>
            ) : null}
          </div>

          <p className="small muted" style={{ margin: "12px 0 20px", lineHeight: 1.5 }}>
            {rc.outcome === "ACCEPT" ? t("rep.statistical")
              : rc.outcome === "REJECT" ? (lang === "en" ? "At least one defect class reached its rejection number (Re). The sample failed the acceptance sampling criteria." : "অন্তত একটি ডিফেক্ট শ্রেণি তার বাতিল সংখ্যায় (Re) পৌঁছেছে।")
                : rc.outcome === "HOLD" ? (lang === "en" ? "The sampling decision rule cannot be evaluated yet. Inspection prerequisites are incomplete." : "স্যাম্পলিং সিদ্ধান্ত নিয়ম এখনো প্রয়োগ করা যায় না।")
                  : (lang === "en" ? "A human authority must decide. This case involves conditions outside automated deterministic competence." : "কর্তৃপক্ষকে সিদ্ধান্ত নিতে হবে।")}
          </p>

          <div className="grid cols-2" style={{ gap: 24, marginTop: 20 }}>
            <div>
              <div className="lbl" style={{ marginBottom: 8, fontWeight: 700 }}>{t("lot.plan")}</div>
              {rc.plan ? (
                <>
                  <table className="table" style={{ fontSize: 12 }}>
                    <tbody>
                      <tr><td className="dim">Sample Size (n entered / effective)</td><td className="right mono" style={{ fontWeight: 600 }}>{rc.plan.n} / {rc.n_effective}</td></tr>
                      <tr><td className="dim">{t("plan.mode")}</td><td className="right mono">{rc.plan.counting_mode}</td></tr>
                      {(["critical", "major", "minor"] as const).map((key) => (
                        <tr key={key}><td className="dim">{t(`plan.${key}`)}</td><td className="right mono">Ac {rc.plan![key].ac} / Re {rc.plan![key].re}</td></tr>
                      ))}
                      <tr><td className="dim">{t("plan.source_edition")}</td><td className="right">{rc.plan.source_edition || "—"}</td></tr>
                      <tr><td className="dim">{t("plan.source_ref")}</td><td className="right">{rc.plan.source_reference || "—"}</td></tr>
                    </tbody>
                  </table>
                  <div className="small dim" style={{ marginTop: 8, fontSize: 11 }}>
                    <b>{t("lot.plan_assumption")}:</b> {lang === "en" ? "Single sampling, normal inspection, General Inspection Level II (ISO 2859-1 / ANSI ASQ Z1.4)." : "সিঙ্গেল স্যাম্পলিং, নরমাল ইন্সপেকশন, জেনারেল ইন্সপেকশন লেভেল II।"}
                  </div>
                </>
              ) : <div className="note bad">{lang === "en" ? "No sampling plan is configured." : "কোনো স্যাম্পলিং প্ল্যান নেই।"}</div>}
            </div>

            <div>
              <div className="lbl" style={{ marginBottom: 8, fontWeight: 700 }}>{t("dec.counts")}</div>
              <table className="table" style={{ fontSize: 12 }}>
                <thead><tr><th>Class</th><th className="num">{t("dec.count")}</th><th className="num">Ac</th><th className="num">Re</th><th className="right">Status</th></tr></thead>
                <tbody>
                  {(["critical", "major", "minor"] as const).map((key) => {
                    const status = rc.class_status[key];
                    return (
                      <tr key={key}>
                        <td><span className={`badge ${key}`} style={{ fontSize: 11 }}>{t(`plan.${key}`)}</span></td>
                        <td className="num mono" style={{ fontWeight: 700 }}>{rc.counts[key] ?? 0}</td>
                        <td className="num dim mono">{status?.ac ?? "—"}</td>
                        <td className="num dim mono">{status?.re ?? "—"}</td>
                        <td className="right">{status ? status.status === "FAIL" ? <span className="badge REJECT" style={{ fontSize: 10.5 }}>FAIL</span> : <span className="badge ACCEPT" style={{ fontSize: 10.5 }}>PASS</span> : <span className="dim">—</span>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="small dim" style={{ marginTop: 8, fontSize: 11 }}>{t("common.units")}: <b>{rc.units_present}/{rc.required_units}</b> · {lang === "en" ? "Views pending" : "বাকি ভিউ"}: <b>{rc.views_pending}</b></div>
            </div>
          </div>

          <div style={{ marginTop: 22 }}>
            <div className="lbl" style={{ marginBottom: 8, fontWeight: 700 }}>{t("common.reasons")}</div>
            <ul className="small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.6 }}>
              {rc.reasons.map((entry) => (
                <li key={entry.code}><span className="mono" style={{ fontWeight: 600 }}>{entry.code}</span> — <span>{reason(entry.code).text}</span></li>
              ))}
            </ul>
          </div>

          <div style={{ marginTop: 22, paddingTop: 16, borderTop: "1px solid var(--line)" }}>
            <div className="lbl" style={{ marginBottom: 8, fontWeight: 700 }}>{lang === "en" ? "Evidence Integrity & Gates" : "প্রমাণ ইন্টিগ্রিটি ও গেইটস"}</div>
            <div className="grid cols-2" style={{ gap: 16, fontSize: 11.5 }}>
              <ul className="list" style={{ margin: 0 }}>
                <li><div className="grow"><span className="dim">{lang === "en" ? "Critical non-visual check:" : "ক্রিটিক্যাল নন-ভিজ্যুয়াল চেক:"}</span> <b>{rc.nonvisual.toUpperCase()}</b></div></li>
                <li><div className="grow"><span className="dim">{lang === "en" ? "Working images:" : "কাজের ছবি:"}</span> <span>{rc.images} photos across {rc.units} sample units</span></div></li>
                <li><div className="grow"><span className="dim">{lang === "en" ? "Detector model:" : "ডিটেক্টর মডেল:"}</span> <span className="mono">{rc.model}</span></div></li>
              </ul>
              <ul className="list" style={{ margin: 0 }}>
                <li><div className="grow"><span className="dim">{lang === "en" ? "Manual review fallback:" : "ম্যানুয়াল রিভিউ বিকল্প:"}</span> <span>{rc.manual ? (lang === "en" ? "Yes" : "হ্যাঁ") : (lang === "en" ? "No" : "না")}</span></div></li>
                <li><div className="grow"><span className="dim">{lang === "en" ? "Selection method:" : "স্যাম্পলিং পদ্ধতি:"}</span> <span>{rc.selection}</span></div></li>
                <li><div className="grow"><span className="dim">SHA-256:</span> <span className="mono" style={{ fontSize: 10 }}>{rc.snapshot_hash.slice(0, 28)}…</span></div></li>
              </ul>
            </div>
            <div className="small dim" style={{ marginTop: 10, fontSize: 11 }}>
              <i>* {lang === "en" ? "The critical class covers visible defects only. Photo evidence cannot prove needle or metal absence." : "ক্রিটিক্যাল শ্রেণি শুধু দৃশ্যমান ত্রুটি কভার করে।"}</i>
            </div>
          </div>

          <div className="grid cols-2" style={{ marginTop: 34, gap: 40, paddingTop: 20, borderTop: "1px solid var(--line)" }}>
            <div><div className="small dim" style={{ marginBottom: 28 }}>Inspector Signature / Date:</div><div style={{ borderBottom: "1px solid var(--text)", width: "90%" }} /></div>
            <div><div className="small dim" style={{ marginBottom: 28 }}>Supervisor Signature / Date:</div><div style={{ borderBottom: "1px solid var(--text)", width: "90%" }} /></div>
          </div>

          <div className="small dim" style={{ marginTop: 22, borderTop: "1px solid var(--line)", paddingTop: 12, fontSize: 10, lineHeight: 1.4 }}>
            {lang === "en"
              ? "This report renders one stored decision row. It contains no reconstructed sampling table, no percentage allowance, and no claim of calibration or certification. AQL schemes were designed for a continuing series of lots. Generated by the Lotline demo build for the International AI Builders Congress 2026."
              : "এই রিপোর্ট একটি সংরক্ষিত সিদ্ধান্ত রেকর্ড দেখায়। এতে কোনো পুনর্গঠিত স্যাম্পলিং টেবিল, শতাংশ অনুমতি বা ক্যালিব্রেশন/সার্টিফিকেশনের দাবি নেই।"}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
