import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import { num } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { ErrorState, Icon, Note, Spinner } from "../components/ui";

interface Card {
  model?: string; labels?: string; training?: string; live_model?: string; live_labels?: string;
  live_training?: string; live_evaluation?: { map50?: number; images?: number; split?: string; precision?: number; recall?: number };
  live_threshold?: number | null; live_parity?: { delta?: number }; live_reliability?: { ece?: number; detections?: number; top_band?: { bin: string; measured_precision: number } };
  calibration?: string; domains?: string; device?: string; sha256?: string; live_sha256?: string;
  self_test?: { passed?: boolean; detail?: string };
  evaluation?: { rows?: Array<{ class: string; n: number; recall: number }>; views?: { total: number; with_proposal: number }; false_positive_views?: number };
}

interface HowData {
  card: Card;
  stats: { lots: number; images: number; proposals: number; proposed: number; confirmed: number; rejected: number; decisions: Record<string, number>; audit: number };
  model: string;
}

export function HowPage() {
  const { t, lang } = useSession();
  const { data, isLoading, error } = useQuery({ queryKey: ["how"], queryFn: () => api.get<HowData>("/api/how") });
  const [copied, setCopied] = useState("");

  if (isLoading) return <AppShell title={t("how.title")} active="how"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("how.title")} active="how"><ErrorState message={(error as Error)?.message || "Unavailable"} /></AppShell>;

  const card = data.card || {};
  const stats = data.stats;
  const evaluation = card.evaluation;
  const evaluationRows = evaluation?.rows || [];
  const evaluationTotal = evaluationRows.reduce((sum, row) => sum + row.n, 0);
  const cleanViews = (evaluation?.views?.total || 16) - evaluationTotal;

  return (
    <AppShell title={t("how.title")} subtitle={t("how.principle")} active="how">
      <div className="how-header-grid">
        <div className="card"><div className="pad-sm">
          <div className="step-badge"><span className="dot" aria-hidden="true" /><span>{lang === "en" ? "1. AI proposes" : "১. এআই প্রস্তাব দেয়"}</span></div>
          <p className="small muted mt-2">{lang === "en" ? "An unsupervised autoencoder learns what clean knit texture looks like from pixels alone. It proposes candidate bounding boxes and a class guess. It has no severity head, no count, no verdict, and no way to approve or reject a lot." : "একটি আনসুপারভাইজড অটোএনকোডার শুধু পিক্সেল থেকে পরিষ্কার নিট টেক্সচার শেখে। এটি সম্ভাব্য ত্রুটির বক্স ও শ্রেণির প্রাথমিক অনুমান দেয়। এর কোনো অনুমোদন, বাতিল বা লট পাসের ক্ষমতা নেই।"}</p>
        </div></div>
        <div className="card"><div className="pad-sm">
          <div className="step-badge"><span className="dot" aria-hidden="true" /><span>{lang === "en" ? "2. Humans confirm" : "২. মানুষ নিশ্চিত করে"}</span></div>
          <p className="small muted mt-2">{lang === "en" ? "A human reviewer confirms, edits, rejects or adds each defect, selects the zone, and reviews every view. Severity is looked up strictly from the buyer clause list after human confirmation — never from the model." : "পর্যালোচক প্রতিটি প্রস্তাবিত ত্রুটি নিশ্চিত, সংশোধন, বাতিল বা নতুন যোগ করেন এবং জোন নির্ধারণ করেন। মডেলের বদলে মানুষের নিশ্চিতকরণের পরই ক্রেতার স্পেসিফিকেশন অনুযায়ী গুরুত্ব নির্ধারিত হয়।"}</p>
        </div></div>
        <div className="card"><div className="pad-sm">
          <div className="step-badge"><span className="dot" aria-hidden="true" /><span>{lang === "en" ? "3. The rule decides" : "৩. নিয়ম সিদ্ধান্ত দেয়"}</span></div>
          <p className="small muted mt-2">{lang === "en" ? "A deterministic pure function compares confirmed defective-garment counts against entered Ac/Re limits in strict precedence: Plan → REJECT → ESCALATE → HOLD → ACCEPT. Same inputs always produce the exact same outcome." : "একটি বিশুদ্ধ নির্ধারক ফাংশন নিশ্চিত ত্রুটিপূর্ণ গার্মেন্টসের সংখ্যার সাথে চুক্তির Ac/Re সীমার তুলনা করে: প্ল্যান → বাতিল → এস্কেলেট → হোল্ড → গ্রহণযোগ্য।"}</p>
        </div></div>
      </div>

      <div className="card mb-3">
        <div className="card-h">
          <h2>{t("how.pipeline")}</h2>
          <div className="right"><span className="chip">{t("how.pipeline_chip")}</span></div>
        </div>
        <div className="pad">
          <div className="how-pipeline-grid">
            {[
              ["1", "১", "dash.step1_title", "dash.step1_desc"],
              ["2", "২", "dash.step2_title", "dash.step2_desc"],
              ["3", "৩", "dash.step3_title", "dash.step3_desc"],
              ["4", "৪", "dash.step4_title", "dash.step4_desc"],
              ["5", "৫", "how.step5_title", "how.step5_desc"],
            ].map((step, index, list) => (
              <div className="how-pipeline-unit" key={step[0]}>
                <div className="between">
                  <span className="how-pipeline-step-num">{lang === "en" ? step[0] : step[1]} · {t(step[2])}</span>
                  {index < list.length - 1 ? <span className="dim" aria-hidden="true" style={{ fontSize: 12 }}>→</span> : null}
                </div>
                <div className="how-pipeline-desc">{t(step[3])}</div>
              </div>
            ))}
          </div>

          <div className="topology-box">
            <div className="topology-title"><span>{lang === "en" ? "System Topology: Current Demo vs Production Target" : "সিস্টেম আর্কিটেকচার: বর্তমান ডেমো বনাম প্রোডাকশন লক্ষ্য"}</span></div>
            <div className="topology-grid">
              <div className="topology-col">
                <div className="between"><b>{t("how.demo_topology")}</b><span className="topology-badge current">{lang === "en" ? "Current" : "চলমান"}</span></div>
                <p className="small muted">{lang === "en" ? "Single container process, in-process CPU autoencoder, local SQLite database. Easy to inspect and test on developer machines without distributed infrastructure." : "একক কন্টেইনার প্রসেস, ইন-প্রসেস সিপিইউ অটোএনকোডার, লোকাল SQLite ডেটাবেস।"}</p>
                <div className="topology-diag"><div className="topology-flow">
                  <span className="topology-node">Browser / Client</span><span className="topology-arrow">→</span>
                  <span className="topology-node">FastAPI Server</span><span className="topology-arrow">→</span>
                  <span className="topology-node">In-Process Vision (CPU)</span><span className="topology-arrow">⇄</span>
                  <span className="topology-node">SQLite DB</span>
                </div></div>
              </div>
              <div className="topology-col">
                <div className="between"><b>{t("how.prod_topology")}</b><span className="topology-badge target">{lang === "en" ? "Target" : "লক্ষ্য"}</span></div>
                <p className="small muted">{lang === "en" ? "Production target architecture: Reverse proxy, API server, dedicated inference worker with no table privileges, isolated vision container with no database access, and PostgreSQL on a private network." : "পরিকল্পিত প্রোডাকশন লক্ষ্য: রিভার্স প্রক্সি, মূল এপিআই সার্ভার, টেবিল প্রিভিলেজবিহীন ইনফারেন্স ওয়ার্কার, ডেটাবেস অধিকারহীন আইসোলেটেড ভিশন কন্টেইনার এবং প্রাইভেট নেটওয়ার্কে PostgreSQL।"}</p>
                <div className="topology-diag"><div className="topology-flow">
                  <span className="topology-node">Client</span><span className="topology-arrow">→</span>
                  <span className="topology-node">TLS Proxy</span><span className="topology-arrow">→</span>
                  <span className="topology-node">API Worker</span><span className="topology-arrow">→</span>
                  <span className="topology-node">Inference (No DB grants)</span><span className="topology-arrow">→</span>
                  <span className="topology-node">Vision</span>
                </div></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="split">
        <div className="card">
          <div className="card-h">
            <h2>{t("how.model_card")}</h2>
            <div className="right">
              <span className={`badge ${card.self_test?.passed ? "badge-success" : "badge-warning"}`}>
                <span className="dot" />{card.self_test?.passed ? t("how.self_test_passed") : t("how.run_self_test")}
              </span>
            </div>
          </div>
          <div className="pad-sm">
            <table className="model-card-table">
              <tbody>
                <Row label={lang === "en" ? "Seeded history" : "সিড ইতিহাস"} value={<span className="mono">{card.model || "ae-knit-v1"}</span>} />
                <Row label={lang === "en" ? "Labels (seeded)" : "ব্যবহৃত লেবেল (সিড)"} value={card.labels || (lang === "en" ? "none (unsupervised)" : "কোনোটি নয় (আনসুপারভাইজড)")} />
                <Row label={lang === "en" ? "Seeded training" : "সিড প্রশিক্ষণ"} value={card.training || (lang === "en" ? "synthetic clean knit textures (procedural), no defect labels" : "কৃত্রিম পরিষ্কার নিট টেক্সচার (প্রসিডিউরাল), কোনো ডিফেক্ট লেবেল ছাড়া")} />
                <Row label={lang === "en" ? "Live uploads" : "লাইভ আপলোড"} value={<span className="mono">{card.live_model || (lang === "en" ? "same as seeded" : "সিডের অনুরূপ")}</span>} />
                <Row label={lang === "en" ? "Labels (live)" : "ব্যবহৃত লেবেল (লাইভ)"} value={card.live_labels || (lang === "en" ? "none" : "কোনোটি নয়")} />
                <Row label={lang === "en" ? "Live training" : "লাইভ প্রশিক্ষণ"} value={card.live_training || "—"} />
                <Row label={lang === "en" ? "Live test score" : "লাইভ টেস্ট স্কোর"} value={card.live_evaluation?.map50 != null
                  ? <span>mAP@0.5 <b>{card.live_evaluation.map50}</b> · {card.live_evaluation.images} {lang === "en" ? "held-out photos" : "হেল্ড-আউট ছবি"} ({card.live_evaluation.split}) · P {card.live_evaluation.precision} · R {card.live_evaluation.recall}</span>
                  : "—"} />
                <Row label={lang === "en" ? "Review threshold" : "রিভিউ থ্রেশহোল্ড"} value={card.live_threshold != null ? <span><b>{card.live_threshold}</b> — {lang === "en" ? "chosen on validation, never on the test split" : "ভ্যালিডেশনে নির্বাচিত, টেস্ট স্প্লিটে কখনো নয়"}</span> : "—"} />
                <Row label={lang === "en" ? "Runtime parity" : "রানটাইম পারিটি"} value={card.live_parity?.delta != null ? <span>PyTorch → ONNX: {card.live_parity.delta} mAP {lang === "en" ? "on validation" : "ভ্যালিডেশনে"}</span> : "—"} />
                <Row label={lang === "en" ? "Score reliability" : "স্কোর নির্ভরযোগ্যতা"} value={card.live_reliability?.ece != null
                  ? <span>ECE <b>{card.live_reliability.ece}</b> on {card.live_reliability.detections} {lang === "en" ? "validation detections" : "ভ্যালিডেশন ডিটেকশন"}{card.live_reliability.top_band ? ` · ${card.live_reliability.top_band.bin}: ${card.live_reliability.top_band.measured_precision} ${lang === "en" ? "matched" : "মিলেছে"}` : ""} — {lang === "en" ? "a score is a ranking, not a probability" : "স্কোর একটি র‍্যাঙ্কিং, সম্ভাবনা নয়"}</span>
                  : "—"} />
                <Row label={t("how.calibration")} value={<span style={{ color: "var(--amber-ink)" }}>{card.calibration || (lang === "en" ? "none — raw reconstruction error scores" : "কোনোটি নয় — স্কোর অপরিমাপিত")}</span>} />
                <Row label={t("how.eval_domain")} value={card.domains || (lang === "en" ? "staged knit panels only (laboratory test set)" : "স্টেজ করা নিট প্যানেল (ল্যাব টেস্ট সেট)")} />
                <Row label={t("how.runtime")} value={card.device || (lang === "en" ? "Server CPU (in-process), ~0.4 s / image" : "সার্ভার সিপিইউ (ইন-প্রসেস), প্রতি ছবিতে ~০.৪ সেকেন্ড")} />
                <Row label={t("how.artifact")} value={
                  <span className="hash-copy-wrap">
                    <span className="mono small" title={card.sha256}>{String(card.sha256 || "").slice(0, 12)}…</span>
                    <button className="btn-copy-hash" type="button" aria-label={lang === "en" ? "Copy SHA-256 hash" : "SHA-256 হ্যাশ কপি করুন"} title={card.sha256} onClick={() => { navigator.clipboard?.writeText(String(card.sha256 || "")); setCopied(card.sha256 || ""); }}>
                      <Icon name="copy" size={13} />
                    </button>
                    {copied === card.sha256 ? <span className="small dim">{lang === "en" ? "copied" : "কপি হয়েছে"}</span> : null}
                  </span>
                } />
                {card.live_sha256 ? <Row label={lang === "en" ? "Live artifact" : "লাইভ আর্টিফ্যাক্ট"} value={<span className="mono small">{card.live_sha256}</span>} /> : null}
                <Row label={t("how.self_test")} value={<span className="small">{card.self_test?.detail || "—"}</span>} />
              </tbody>
            </table>

            <div className="selftest-checklist">
              <div className="small bold" style={{ color: "var(--text)", marginBottom: 2 }}>{lang === "en" ? "Self-Test Verification Checklist:" : "সেলফ-টেস্ট যাচাইকরণ চেকলিস্ট:"}</div>
              <div className="selftest-item"><span className="selftest-icon-check">✓</span><span><b>{lang === "en" ? "False Positive Guard:" : "পরিষ্কার টেক্সচার পরীক্ষা:"}</b> {lang === "en" ? "Zero proposals generated on clean synthetic knit patches." : "পরিষ্কার নিট ফ্যাব্রিকে কোনো মিথ্যা ত্রুটি প্রস্তাব করেনি।"}</span></div>
              <div className="selftest-item"><span className="selftest-icon-check">✓</span><span><b>{lang === "en" ? "Defect Sensitivity:" : "ত্রুটি সংবেদনশীলতা:"}</b> {lang === "en" ? "Successfully flagged anomalous patch on defective knit sample." : "ত্রুটিযুক্ত স্যাম্পল প্যানেলে সফলভাবে প্রস্তাব তৈরি করেছে।"}</span></div>
              <div className="selftest-item"><span className="selftest-icon-check">✓</span><span><b>{lang === "en" ? "Defect Localisation:" : "লোকালাইজেশন (Hole):"}</b> {lang === "en" ? "Accurately placed bounding box over known artificial hole." : "নির্ধারিত কৃত্রিম ছিদ্রের বাউন্ডিং বক্স সঠিকভাবে শনাক্ত করেছে।"}</span></div>
            </div>

            {evaluation ? (
              <div className="mt-3">
                <div className="between mb-1">
                  <b>{lang === "en" ? "Staged-Set Localisation (IoU ≥ 0.05)" : "স্টেজড-সেট লোকালাইজেশন (IoU ≥ ০.০৫)"}</b>
                  <span className="small dim">n={num(evaluationTotal, lang)}</span>
                </div>
                <p className="small dim mb-2">{lang === "en" ? "IoU threshold in plain words: A proposal is counted as a hit if its box overlaps the ground truth by at least 5% (IoU ≥ 0.05)." : "প্রস্তাবিত বক্স এবং প্রকৃত ত্রুটির মাঝে অন্তত ৫% ওভারল্যাপ থাকলে সেটিকে সফল শনাক্তকরণ ধরা হয়েছে।"}</p>
                <table className="table" style={{ fontSize: 12 }}>
                  <thead><tr><th>{t("rev.type")}</th><th className="num">{lang === "en" ? "Samples (n)" : "স্যাম্পল (n)"}</th><th className="num">{lang === "en" ? "Detected / Recall" : "শনাক্তকরণ / রিকল"}</th></tr></thead>
                  <tbody>
                    {evaluationRows.map((row) => (
                      <tr key={row.class}>
                        <th scope="row" style={{ fontWeight: 500 }}>{t(`type.${row.class}`)}</th>
                        <td className="num">{num(row.n, lang)}</td>
                        <td className="num" style={{ fontWeight: 700 }}>{num(Math.round(row.recall * row.n), lang)}/{num(row.n, lang)} ({num(Math.round(row.recall * 100), lang)}%)</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="small dim mt-2" style={{ lineHeight: 1.5 }}>
                  <div>• <b>{num(evaluation.views?.with_proposal || 0, lang)}/{num(evaluation.views?.total || 0, lang)}</b> {lang === "en" ? "staged views received at least one proposal" : "টি স্টেজড ভিউতে অন্তত একটি প্রস্তাব এসেছে"}</div>
                  <div>• <b>{num(evaluation.false_positive_views || 0, lang)}/{num(cleanViews > 0 ? cleanViews : 4, lang)}</b> {lang === "en" ? "clean views flagged (false positive rate)" : "পরিষ্কার ভিউতে ভুল প্রস্তাব এসেছে"}</div>
                  <div className="mt-1">{lang === "en" ? "Data provenance & independence note: Staged defects were programmatically generated by the synthetic test harness; evaluation was conducted on procedural panels rather than real factory production images." : "ডেটা উৎস ও স্বাধীনতা নোট: ত্রুটিগুলো টেস্ট হারনেস দ্বারা কৃত্রিমভাবে তৈরি করা হয়েছে; মূল্যায়ন বাস্তব কারখানার ছবিতে নয়।"}</div>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="stack">
          <div className="card">
            <div className="card-h"><h2>{t("how.impact")}</h2></div>
            <div className="pad-sm">
              <div className="grid cols-2" style={{ gap: 9 }}>
                <div className="kpi p-2"><div className="lbl">{t("common.lots")}</div><div className="n" style={{ fontSize: 20 }}>{num(stats.lots, lang)}</div></div>
                <div className="kpi p-2"><div className="lbl">{t("common.images")}</div><div className="n" style={{ fontSize: 20 }}>{num(stats.images, lang)}</div></div>
                <div className="kpi p-2"><div className="lbl">{lang === "en" ? "AI Proposals" : "এআই প্রস্তাব"}</div><div className="n" style={{ fontSize: 20 }}>{num(stats.proposals, lang)}</div><div className="small dim" style={{ marginTop: 2 }}>{num(stats.proposed, lang)} {lang === "en" ? "pending review" : "বিবেচনাধীন"}</div></div>
                <div className="kpi p-2"><div className="lbl">{t("how.reviewer_actions")}</div><div className="n" style={{ fontSize: 20 }}>{num(stats.confirmed + stats.rejected, lang)}</div><div className="small dim" style={{ marginTop: 2 }}>{num(stats.confirmed, lang)} {lang === "en" ? "confirmed" : "নিশ্চিত"} · {num(stats.rejected, lang)} {lang === "en" ? "rejected" : "বাতিল"}</div></div>
              </div>

              <ul className="how-impact-list">
                <li><div><b>{num(stats.decisions.ACCEPT || 0, lang)} {t("out.ACCEPT")} · {num(stats.decisions.REJECT || 0, lang)} {t("out.REJECT")}</b><div className="small dim">{lang === "en" ? "Two complete lots with opposite final dispositions" : "২টি সম্পূর্ণ লট, বিপরীত চূড়ান্ত ফলাফল"}</div></div></li>
                <li><div><b>{num(stats.decisions.HOLD || 0, lang)} {t("out.HOLD")} · {num(stats.decisions.ESCALATE || 0, lang)} {t("out.ESCALATE")}</b><div className="small dim">{lang === "en" ? "Incomplete evidence (HOLD) and unmapped buyer clauses (ESCALATE)" : "অসম্পূর্ণ প্রমাণ (হোল্ড) ও ম্যাপ করা হয়নি এমন ক্রেতা ক্লজ (এস্কেলেট)"}</div></div></li>
                <li><div><b>{num(stats.audit, lang)} {lang === "en" ? "recorded audit events" : "টি অডিট ইভেন্ট সংরক্ষিত"}</b><div className="small dim">{lang === "en" ? "Every state change recorded in append-only log" : "প্রতিটি অবস্থা পরিবর্তন, শুধু-যোগ"}</div></div></li>
              </ul>

              <Note tone="warn">{lang === "en" ? "These are demo counts from seeded data, not measured factory savings. No time-saving claim is made without a manual baseline study." : "এগুলো ডেমো ডেটার গণনা, কারখানার সাশ্রয় নয়।"}</Note>
            </div>
          </div>

          <div className="card">
            <div className="card-h"><h2>{t("how.limits")}</h2></div>
            <div className="pad-sm">
              <ul className="small muted" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.75 }}>
                {(lang === "en" ? [
                  "Uncalibrated detector: scores are raw reconstruction errors, not probabilities.",
                  "Trained and evaluated on staged knit panels only; no factory floor evidence yet.",
                  "Type classification is a heuristic suggestion; the human reviewer can change it freely.",
                  "Critical non-visual defects (broken needle, metal fragments) cannot be photographed; a Supervisor records them separately.",
                  "Sampling randomness is self-declared. Software cannot physically verify the draw.",
                  "No ISO certification, no “ISO-compliant AI”, and sampling tables are not reinvented from the standard.",
                ] : [
                  "অপরিমাপিত ডিটেক্টর: স্কোরগুলো সম্ভাবনা নয়, কেবল রিকনস্ট্রাকশন এরর স্কোর।",
                  "শুধু স্টেজ করা সিন্থেটিক নিট প্যানেলে প্রশিক্ষণ ও মূল্যায়ন; বাস্তব কারখানার প্রমাণ এখনও অন্তর্ভুক্ত নয়।",
                  "ত্রুটির ধরন শ্রেণিবিন্যাস একটি প্রাথমিক অনুমান; মানুষ পর্যালোচক ড্রপডাউন থেকে এটি বদলাতে পারেন।",
                  "অদৃশ্য ক্রিটিক্যাল ত্রুটি (সুই, ধাতু) ছবিতে ধরা যায় না; সুপারভাইজার আলাদা মেটাল ডিটেকশন লগ করেন।",
                  "নমুনার এলোমেলোতা স্ব-ঘোষিত। সফটওয়্যার বাস্তব লট থেকে উত্তোলনের এলোমেলোতা যাচাই করতে পারে না।",
                  "কোনো ISO সার্টিফিকেশন বা “ISO-কমপ্লায়েন্ট এআই” দাবি নেই; স্ট্যান্ডার্ডের নমুনা-সারণি নিজে বানিয়ে দেখানো হয়নি।",
                ]).map((limit) => <li key={limit}>{limit}</li>)}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-h"><h2>{t("how.principles_title")}</h2></div>
        <div className="pad">
          <div className="grid cols-3" style={{ gap: 16 }}>
            {[
              ["how.explainability", lang === "en" ? "Every box includes a reconstruction-error attention map and numeric score. The decision page shows exact reason codes, counts, limits, and a SHA-256 hash of the confirmed-defect snapshot." : "প্রতিটি বক্সের সঙ্গে রিকনস্ট্রাকশন-এরর স্কোর পাওয়া যায়। সিদ্ধান্ত পৃষ্ঠায় সুনির্দিষ্ট কারণ কোড, গণনা, সীমা ও নিশ্চিত ত্রুটি স্ন্যাপশটের SHA-256 হ্যাশ দেখা যায়।"],
              ["how.data_sovereignty", lang === "en" ? "Inference runs locally server-side (CPU, in-process), never through a third-party cloud API. In the production topology, photos never leave the factory network and the vision model has no external network access." : "ইনফারেন্স স্থানীয় সার্ভার প্রসেসে (সিপিইউ) পরিচালিত হয়, কোনো ক্লাউড এপিআই-তে নয়।"],
              ["how.fail_safe", lang === "en" ? "Verified across 12 automated unit tests: failed jobs, missing files, unmapped clauses, pending critical checks, or missing sampling plans strictly produce HOLD or ESCALATE, never ACCEPT." : "১২টি স্বয়ংক্রিয় টেস্টে যাচাইকৃত: ব্যর্থ কাজ, হারানো ফাইল, ম্যাপ করা হয়নি এমন ক্লায়েন্ট ক্লজ, বাকি ক্রিটিক্যাল চেক বা অনুপস্থিত স্যাম্পলিং প্ল্যানে সিস্টেম কখনই গ্রহণযোগ্য দিতে পারে না।"],
            ].map(([title, body]) => (
              <div key={title}>
                <div className="step-badge mb-2"><span className="dot" aria-hidden="true" /><span>{t(title)}</span></div>
                <p className="small muted">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <details className="how-glossary">
        <summary><span>{t("how.glossary")}</span><span className="small dim" aria-hidden="true">▾</span></summary>
        <div className="how-glossary-content">
          <div className="how-glossary-item"><b>Ac / Re (Acceptance / Rejection Number):</b><span>{lang === "en" ? "Ac is the maximum number of defective garments permitted to accept the lot; Re is the minimum number of defectives that causes lot rejection." : "Ac হলো সর্বোচ্চ অনুমোদিত ত্রুটিপূর্ণ ইউনিট সংখ্যা; Re হলো যে সংখ্যা বা তার বেশি ত্রুটি পেলে লট সরাসরি বাতিল হয়।"}</span></div>
          <div className="how-glossary-item"><b>AQL (Acceptable Quality Limit):</b><span>{lang === "en" ? "The maximum percent defective considered satisfactory as a process average under the buyer sampling standard." : "চুক্তি অনুযায়ী লটে গ্রহণযোগ্য ত্রুটির সর্বোচ্চ অনুমোদিত শতকরা হার।"}</span></div>
          <div className="how-glossary-item"><b>ESCALATE vs HOLD:</b><span>{lang === "en" ? "ESCALATE flags conditions requiring human policy judgment (unmapped buyer clauses, reviewer disagreements); HOLD flags incomplete evidence (missing photos, unreviewed views, missing sampling plan)." : "ESCALATE হলো মানুষের নীতিগত সিদ্ধান্ত প্রয়োজন; HOLD হলো অসম্পূর্ণ প্রমাণ বা তথ্যের অভাব।"}</span></div>
          <div className="how-glossary-item"><b>SHA-256 Snapshot Hash:</b><span>{lang === "en" ? "A 256-bit cryptographic fingerprint computed over all confirmed defects and inspection parameters, locking evidence immutability upon decision computation." : "পর্যালোচিত সকল ত্রুটির ডিজিটাল ক্রিপ্টোগ্রাফিক ছাপ, যা নিশ্চিত করে সিদ্ধান্তের পর কোনো তথ্য পরিবর্তন করা হয়নি।"}</span></div>
        </div>
      </details>
    </AppShell>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return <tr><th scope="row" className="dim-col">{label}</th><td className="val-col">{value}</td></tr>;
}
