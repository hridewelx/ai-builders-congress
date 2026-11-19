import { useState } from "react";
import { useSession } from "../lib/session";
import { Badge, Button, Field, Icon } from "./ui";
import type { Prediction } from "../lib/review_types";

export function ProposalCard({
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
