import { Link } from "react-router-dom";
import { useSession } from "../lib/session";
import { num, numGrouped } from "../lib/format";
import { DecisionBadge, Icon, ProgressBar } from "./ui";

export interface LotCardData {
  id: number;
  lot_code: string;
  buyer_name: string;
  product_name: string;
  color: string;
  lot_size: number;
  status: string;
  decision: { outcome: string; sequence: number; created_at: string } | null;
  override: { effective?: boolean; status?: string; final_disposition?: string; supervisor?: string; reason?: string; created_at?: string } | null;
  final: string | null;
  progress: {
    units: number;
    required_units: number;
    views: number;
    reviewed: number;
    pct_views: number;
  };
}

export function LotCard({ card }: { card: LotCardData }) {
  const { t, lang, user } = useSession();
  const same = card.decision && card.final && card.decision.outcome === card.final;
  return (
    <div className="card lot-card" data-lot-card data-lot-status={card.status}>
      <div className="lot-card-head">
        <div className="grow">
          <div className="disp-row">
            <Link to={`/lots/${card.id}`} className="lot-code-link">{card.lot_code}</Link>
            {card.status === "decided" ? (
              <span className="badge decided"><span className="dot" aria-hidden="true" />{t("dash.decided")}</span>
            ) : (
              <span className="badge open"><span className="dot" aria-hidden="true" />{t("status.in_progress")}</span>
            )}
          </div>
          <div className="lot-meta-sub">
            <span className="buyer-pill">{card.buyer_name}</span>
            <span className="meta-sep" aria-hidden="true">·</span>
            <span>{card.product_name}</span>
            {card.color ? <><span className="meta-sep" aria-hidden="true">·</span><span>{card.color}</span></> : null}
          </div>
        </div>
      </div>

      <div className="disp-cockpit">
        {same ? (
          <div className="disp-row">
            <span className="disp-lbl bold">{t("dash.single_decision")}</span>
            <DecisionBadge outcome={card.final!} label={t(`out.${card.final}`)} />
          </div>
        ) : (
          <>
            <div className="disp-row">
              <span className="disp-lbl">{lang === "en" ? "System Recommendation:" : "সিস্টেম সুপারিশ:"}</span>
              {card.decision ? (
                <DecisionBadge outcome={card.decision.outcome} label={t(`out.${card.decision.outcome}`)} />
              ) : (
                <span className="small dim mono">—</span>
              )}
            </div>
            <div className="disp-row">
              <span className="disp-lbl bold">
                {card.status === "decided" ? t("dash.final_disposition") : t("dash.current_decision")}
              </span>
              {card.final ? (
                <DecisionBadge outcome={card.final} label={t(`out.${card.final}`)} />
              ) : (
                <span className="small dim mono">—</span>
              )}
            </div>
          </>
        )}
      </div>

      <div className="lot-progress-wrap">
        <ProgressBar value={card.progress.pct_views} />
        <div className="lot-progress-meta">
          {card.progress.required_units ? (
            <span>{num(card.progress.units, lang)}/{num(card.progress.required_units, lang)} {t("common.units").toLowerCase()}</span>
          ) : card.progress.units ? (
            <span>{num(card.progress.units, lang)} {t(card.progress.units === 1 ? "common.unit" : "common.units").toLowerCase()}</span>
          ) : (
            <span>{t("dash.no_garments")}</span>
          )}
          <span>
            {num(card.progress.reviewed, lang)}/{num(card.progress.views, lang)} {t("lot.views_reviewed")} ({num(card.progress.pct_views, lang)}%)
          </span>
        </div>
      </div>

      <div className="lot-card-foot">
        <div className="small dim">
          {lang === "en" ? "Lot size" : "লট সাইজ"}: <b>{numGrouped(card.lot_size, lang)}</b>
          {card.override ? (
            <span>
              {card.override.effective ? (
                <span className="badge badge-pending">{t("dec.overridden")}</span>
              ) : (
                <span className="badge HOLD"><span className="dot" />{lang === "en" ? "Pending Override" : "মুলতুবি ওভাররাইড"}</span>
              )}
            </span>
          ) : null}
        </div>
        <Link className="btn sm secondary" to={`/lots/${card.id}`}>
          <span>{user?.role === "admin" ? t("common.view") : t("common.open")}</span>
          <Icon name="arrow-right" size={13} />
        </Link>
      </div>
    </div>
  );
}
