import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import { num } from "../lib/format";
import { AppShell } from "../components/AppShell";
import type { LotCardData } from "../components/LotCard";
import { DecisionBadge, EmptyState, ErrorState, Icon, Spinner } from "../components/ui";

interface LotsData {
  cards: LotCardData[];
  state: string;
  outcome: string;
  q: string;
}

export function LotsPage() {
  const { t, lang, user } = useSession();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "");
  const [state, setState] = useState(params.get("state") || "");
  const [outcome, setOutcome] = useState(params.get("outcome") || "");

  const { data, isLoading, error } = useQuery({
    queryKey: ["lots", params.toString()],
    queryFn: () => api.get<LotsData>(`/api/lots?${params.toString()}`),
  });

  useEffect(() => {
    setQ(params.get("q") || "");
    setState(params.get("state") || "");
    setOutcome(params.get("outcome") || "");
  }, [params]);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const next = new URLSearchParams();
    if (q) next.set("q", q);
    if (state) next.set("state", state);
    if (outcome) next.set("outcome", outcome);
    setParams(next);
  };

  return (
    <AppShell title={t("lots.title")} subtitle={t("dash.subtitle")} active="lots">
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="pad-sm">
          <form onSubmit={submit} className="lot-filter-form" style={{ display: "flex", alignItems: "flex-end", gap: 12, flexWrap: "wrap" }}>
            <div className="field" style={{ flex: 2, minWidth: 240, margin: 0 }}>
              <label htmlFor="filter-q" style={{ fontSize: 11.5, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>{t("common.search")}</label>
              <div style={{ position: "relative" }}>
                <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--muted)", pointerEvents: "none", display: "flex" }}>
                  <Icon name="search" size={14} />
                </span>
                <input id="filter-q" className="input sm" style={{ paddingLeft: 32 }} value={q} onChange={(event) => setQ(event.target.value)} placeholder={`${t("lots.code")} / ${t("lots.buyer")} / ${t("lots.product")}`} />
              </div>
            </div>

            <div className="field" style={{ minWidth: 140, margin: 0 }}>
              <label htmlFor="filter-state" style={{ fontSize: 11.5, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>{t("common.status")}</label>
              <select id="filter-state" className="select sm" value={state} onChange={(event) => setState(event.target.value)}>
                <option value="">{t("common.all")}</option>
                {["open", "decided", "reopened", "archived"].map((value) => (
                  <option key={value} value={value}>{value.charAt(0).toUpperCase() + value.slice(1)}</option>
                ))}
              </select>
            </div>

            <div className="field" style={{ minWidth: 140, margin: 0 }}>
              <label htmlFor="filter-outcome" style={{ fontSize: 11.5, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>{t("common.outcome")}</label>
              <select id="filter-outcome" className="select sm" value={outcome} onChange={(event) => setOutcome(event.target.value)}>
                <option value="">{t("common.all")}</option>
                {["ACCEPT", "REJECT", "HOLD", "ESCALATE"].map((value) => (
                  <option key={value} value={value}>{t(`out.${value}`)}</option>
                ))}
              </select>
            </div>

            <div className="btnrow" style={{ margin: 0, gap: 8 }}>
              <button className="btn sm primary" type="submit">{t("common.filter")}</button>
              {params.toString() ? <Link className="btn sm ghost" to="/lots">{lang === "en" ? "Reset" : "রিসেট"}</Link> : null}
            </div>

            {user && user.role !== "admin" ? (
              <div className="right" style={{ marginLeft: "auto" }}>
                <Link className="btn sm primary" to="/lots/new">
                  <Icon name="plus" size={14} />
                  <span>{t("nav.new_lot")}</span>
                </Link>
              </div>
            ) : null}
          </form>
        </div>
      </div>

      <div className="card">
        {isLoading ? <Spinner /> : error ? <ErrorState message={(error as Error).message} /> : data!.cards.length ? (
          <>
            <div className="card-h" style={{ justifyContent: "space-between" }}>
              <div style={{ fontSize: 13.5, fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                <span>{t("lots.title")}</span>
                <span className="badge ghost" style={{ fontSize: 11 }}>{num(data!.cards.length, lang)} {lang === "en" ? "lots on record" : "টি লট সংরক্ষিত"}</span>
              </div>
            </div>
            <div className="tblwrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("lots.code")}</th>
                    <th>{t("lots.buyer")}</th>
                    <th>{t("lots.product")}</th>
                    <th className="num">{t("lots.size")}</th>
                    <th>{t("lot.progress")}</th>
                    <th>{t("common.status")}</th>
                    <th>{lang === "en" ? "Two-Line Disposition" : "টু-লাইন ডিসপোজিশন"}</th>
                    <th className="right">{t("common.actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data!.cards.map((card) => (
                    <tr key={card.id}>
                      <td>
                        <Link to={`/lots/${card.id}`} style={{ fontWeight: 700, color: "var(--text)", fontSize: 14, letterSpacing: "-0.015em" }}>{card.lot_code}</Link>
                        <div className="small dim" style={{ marginTop: 2, fontSize: 11.5 }}>{card.color}</div>
                      </td>
                      <td><span className="ink-soft" style={{ fontWeight: 600 }}>{card.buyer_name}</span></td>
                      <td className="muted" style={{ fontSize: 13 }}>{card.product_name}</td>
                      <td className="num mono" style={{ fontWeight: 600 }}>{num(card.lot_size, lang)}</td>
                      <td style={{ minWidth: 160 }}>
                        <div className="bar" style={{ height: 5, background: "var(--line)", borderRadius: 999, overflow: "hidden" }}>
                          <i style={{ display: "block", height: "100%", width: `${card.progress.pct_views}%`, background: "linear-gradient(90deg, #65a30d, #84cc16)", borderRadius: 999 }} />
                        </div>
                        <div className="meta" style={{ fontSize: 11, marginTop: 4, display: "flex", justifyContent: "space-between" }}>
                          <span>{num(card.progress.units, lang)}/{card.progress.required_units ? num(card.progress.required_units, lang) : "—"} {t("common.units").toLowerCase()}</span>
                          <span>{num(card.progress.reviewed, lang)}/{num(card.progress.views, lang)} ({num(card.progress.pct_views, lang)}%)</span>
                        </div>
                      </td>
                      <td>
                        {card.status === "decided" ? (
                          <span className="badge decided"><span className="dot" />{t("dash.decided")}</span>
                        ) : (
                          <span className="badge open"><span className="dot" />{t("status.in_progress")}</span>
                        )}
                      </td>
                      <td style={{ minWidth: 180 }}>
                        <div style={{ fontSize: 11.5, lineHeight: 1.45 }}>
                          <div className="row" style={{ gap: 6, alignItems: "center" }}>
                            <span className="dim" style={{ fontSize: 10.5 }}>{lang === "en" ? "Rec:" : "সুপারিশ:"}</span>
                            {card.decision ? <DecisionBadge outcome={card.decision.outcome} label={t(`out.${card.decision.outcome}`)} /> : <span className="dim mono">—</span>}
                          </div>
                          <div className="row" style={{ gap: 6, alignItems: "center", marginTop: 3 }}>
                            <span className="dim" style={{ fontSize: 10.5, fontWeight: 600 }}>
                              {card.status === "decided" ? (lang === "en" ? "Final:" : "চূড়ান্ত:") : (lang === "en" ? "Current:" : "বর্তমান:")}
                            </span>
                            {card.final ? (
                              <>
                                <DecisionBadge outcome={card.final} label={t(`out.${card.final}`)} />
                                {card.override && !card.override.effective ? (
                                  <span className="badge HOLD" style={{ fontSize: 10, padding: "1px 5px" }}>{lang === "en" ? "Pending" : "মুলতুবি"}</span>
                                ) : null}
                              </>
                            ) : <span className="dim mono">—</span>}
                          </div>
                        </div>
                      </td>
                      <td className="right" style={{ whiteSpace: "nowrap" }}>
                        <div className="btnrow" style={{ justifyContent: "flex-end", gap: 6 }}>
                          <Link className="btn sm secondary" to={`/lots/${card.id}`} title={t("common.open")}>
                            <span>{t("common.open")}</span>
                            <Icon name="arrow-right" size={12} />
                          </Link>
                          {card.decision ? (
                            <Link className="btn sm ghost" to={`/lots/${card.id}/decision`} title={t("dec.title")}>
                              <Icon name="clipboard-check" size={14} />
                            </Link>
                          ) : null}
                          {user?.role !== "admin" && card.status === "decided" ? (
                            <Link className="btn sm ghost" to={`/lots/${card.id}/report`} title={t("rep.title")}>
                              <Icon name="file-text" size={14} />
                            </Link>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="pad" style={{ padding: "48px 24px", textAlign: "center" }}>
            <EmptyState
              title={t("lots.empty")}
              body={lang === "en" ? "Try adjusting your search criteria or clear your filters." : "আপনার অনুসন্ধানের ফিল্টার পরিবর্তন করুন বা রিসেট করুন।"}
              icon="search"
            />
            <div style={{ textAlign: "center", marginTop: 16 }}>
              <Link className="btn ghost sm" to="/lots">{lang === "en" ? "Clear All Filters" : "সকল ফিল্টার মুছুন"}</Link>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
