import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import { num } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { LotCard, type LotCardData } from "../components/LotCard";
import {
  Button, DecisionBadge, EmptyState, ErrorState, Icon, MetricCard, Spinner,
} from "../components/ui";

interface DashboardData {
  cards: LotCardData[];
  counters: { open: number; HOLD: number; ESCALATE: number; decided: number };
  stats: { images: number; proposals: number; proposed: number; confirmed: number; rejected: number; lots: number; audit: number };
  model: { model: string; model_ok: boolean };
}

export function DashboardPage() {
  const { t, lang, user, data: session } = useSession();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "open" | "decided">("all");
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardData>("/api/dashboard"),
  });

  const cards = data?.cards ?? [];
  const pendingOverrides = cards.filter((card) => card.override && !card.override.effective);
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return cards.filter((card) => {
      if (filter === "open" && card.status === "decided") return false;
      if (filter === "decided" && card.status !== "decided") return false;
      if (!needle) return true;
      return `${card.lot_code} ${card.buyer_name} ${card.product_name} ${card.color}`.toLowerCase().includes(needle);
    });
  }, [cards, filter, query]);

  const title = t("dash.title");
  const subtitle = t("dash.subtitle");

  return (
    <AppShell title={title} subtitle={subtitle} active="dashboard">
      {isLoading ? <Spinner /> : error ? <ErrorState message={(error as Error).message} /> : (
        <>
          <div className="grid cols-4 kpi-grid kpi-grid-dashboard">
            <MetricCard
              label={t("dash.open_lots")}
              value={data!.stats.lots}
              hint={`${num(data!.stats.images, lang)} ${t("common.images").toLowerCase()}`}
              tone="accent"
              icon="layers"
              href="/lots"
            />
            <MetricCard
              label={t("dash.hold")}
              value={data!.counters.HOLD}
              hint={lang === "en" ? "Awaiting evidence review" : "প্রমাণের অপেক্ষায়"}
              tone="warning"
              icon="pause"
              href="/lots?outcome=HOLD"
            />
            <MetricCard
              label={t("dash.escalate")}
              value={data!.counters.ESCALATE}
              hint={lang === "en" ? "Supervisor decision needed" : "সুপারভাইজার সিদ্ধান্ত জরুরি"}
              tone="info"
              icon="arrow-up-right"
              href="/lots?outcome=ESCALATE"
            />
            <MetricCard
              label={t("dash.decided")}
              value={data!.counters.decided}
              hint={`${num(data!.stats.audit, lang)} ${lang === "en" ? "audit events" : "টি অডিট ইভেন্ট"}`}
              badge={lang === "en" ? "Locked" : "লকড"}
              tone="success"
              icon="badge-check"
              href="/lots?state=decided"
            />
          </div>

          {user && (user.role === "supervisor" || user.role === "admin") && pendingOverrides.length ? (
            <div className="card pending-override-card">
              <div className="card-h">
                <h2 className="override-banner-title">
                  <Icon name="git-pull-request" size={18} />
                  <span>{lang === "en" ? "High-Risk Overrides Awaiting Second Supervisor" : "দ্বিতীয় সুপারভাইজারের অনুমোদনের অপেক্ষায় হাই-রিস্ক ওভাররাইড"}</span>
                </h2>
                <div className="right">
                  <span className="badge HOLD">{pendingOverrides.length} {lang === "en" ? "pending approval" : "অনুমোদন বাকি"}</span>
                </div>
              </div>
              <div className="tblwrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t("common.lot")}</th>
                      <th>{lang === "en" ? "Requested By" : "আবেদনকারী"}</th>
                      <th>{lang === "en" ? "Requested Disposition" : "আবেদিত ফলাফল"}</th>
                      <th>{t("common.reason")}</th>
                      <th className="right">{t("common.actions")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingOverrides.map((card) => (
                      <tr key={card.id}>
                        <td>
                          <Link to={`/lots/${card.id}`} className="font-bold">{card.lot_code}</Link>
                          <div className="small dim">{card.buyer_name} · {card.product_name}</div>
                        </td>
                        <td><span className="small font-medium">{card.override?.supervisor || "Supervisor"}</span></td>
                        <td>
                          <span className="badge ACCEPT">
                            <span className="dot" aria-hidden="true" />
                            {(card.override?.final_disposition || "").replace("OVERRIDE_", "")}
                          </span>
                        </td>
                        <td className="small muted">{String(card.override?.reason || "").slice(0, 100)}</td>
                        <td className="right">
                          <Link className="btn sm primary" to={`/lots/${card.id}/decision`}>
                            {lang === "en" ? "Review & Decide" : "যাচাই ও সিদ্ধান্ত"} →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {user?.role === "admin" ? (
            <div className="card admin-health-card">
              <div className="card-h">
                <h2 className="card-title-h3">
                  <span className="navy-ink"><Icon name="activity" size={18} /></span>
                  <span>{t("health.system_status")}</span>
                </h2>
                <div className="right">
                  <Link className="btn sm ghost" to="/admin?tab=health">{lang === "en" ? "Full Health" : "সম্পূর্ণ স্বাস্থ্য"} →</Link>
                </div>
              </div>
              <div className="pad-sm">
                <div className="grid cols-3 admin-health-grid">
                  <div className="admin-stat-box">
                    <div className="between">
                      <span className="small dim">{lang === "en" ? "Inference Engine" : "ইনফারেন্স ইঞ্জিন"}</span>
                      {session.last_selftest && session.last_selftest.passed ? (
                        <span className="badge ACCEPT"><span className="dot" />{t("status.ok")}</span>
                      ) : data!.model.model_ok ? (
                        <span className="badge ACCEPT"><span className="dot" />{t("status.ok")}</span>
                      ) : (
                        <span className="badge HOLD"><span className="dot" />{lang === "en" ? "Check" : "পরীক্ষা করুন"}</span>
                      )}
                    </div>
                    <div className="mono small font-bold mt-6">{data!.model.model}</div>
                    <div className="small dim">{lang === "en" ? "Server-side autoencoder · CPU in-process" : "সার্ভার-সাইড অটোএনকোডার · সিপিইউ (ইন-প্রসেস)"}</div>
                  </div>
                  <div className="admin-stat-box">
                    <div className="between">
                      <span className="small dim">{lang === "en" ? "Audit Log Integrity" : "অডিট লগ ইন্টিগ্রিটি"}</span>
                      <span className="badge ACCEPT"><span className="dot" />{lang === "en" ? "Active" : "সক্রিয়"}</span>
                    </div>
                    <div className="small font-bold mt-6">{num(data!.stats.audit, lang)} {lang === "en" ? "recorded events" : "টি ইভেন্ট সংরক্ষিত"}</div>
                    <div className="small dim">{t("health.append_only")}</div>
                  </div>
                  <div className="admin-stat-box">
                    <div className="between">
                      <span className="small dim">{t("health.policy_title")}</span>
                      <span className="badge ghost">{t("health.policy_badge")}</span>
                    </div>
                    <div className="small font-bold mt-6">{lang === "en" ? "Admin QC Blocked" : "অ্যাডমিন QC নিষিদ্ধ"}</div>
                    <div className="small dim">{t("health.policy_desc")}</div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          <div className="split">
            <div>
              <div className="workspace-head">
                <div className="workspace-head-inner">
                  <div>
                    <h2 className="workspace-title">
                      <span>{t("dash.recent")}</span>
                      <span className="badge ghost badge-count">
                        {t("dash.recent_lots_count", { recent: num(cards.length, lang), total: num(data!.stats.lots, lang) })}
                      </span>
                    </h2>
                    <div className="workspace-subtitle">{t("dash.active_lots_subtitle")}</div>
                  </div>
                  <div className="btnrow btnrow-gap">
                    {user && user.role !== "admin" && !session.is_guest ? (
                      <Button href="/lots/new" variant="primary" size="sm" icon="plus">{t("nav.new_lot")}</Button>
                    ) : null}
                    <Button href="/lots" variant="ghost" size="sm" iconAfter="arrow-right">{t("nav.lots")}</Button>
                  </div>
                </div>

                <div className="lot-toolbar">
                  <div className="search-wrap">
                    <span className="search-icon" aria-hidden="true"><Icon name="search" size={14} /></span>
                    <input
                      type="search"
                      className="input sm search-input"
                      placeholder={lang === "en" ? "Search lot, buyer, style..." : "লট, ক্রেতা, পোশাক খুঁজুন..."}
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                    />
                  </div>
                  <div className="filter-pills" role="group" aria-label="Filter lots">
                    <button type="button" className={`pill-btn${filter === "all" ? " on" : ""}`} onClick={() => setFilter("all")} aria-pressed={filter === "all"}>{t("common.all")}</button>
                    <button type="button" className={`pill-btn${filter === "open" ? " on" : ""}`} onClick={() => setFilter("open")} aria-pressed={filter === "open"}>{t("status.in_progress")}</button>
                    <button type="button" className={`pill-btn${filter === "decided" ? " on" : ""}`} onClick={() => setFilter("decided")} aria-pressed={filter === "decided"}>{t("dash.decided")}</button>
                  </div>
                </div>
              </div>

              {visible.length ? (
                <div className="grid cols-2 lot-cards-grid">
                  {visible.map((card) => <LotCard key={card.id} card={card} />)}
                </div>
              ) : (
                <div className="card">
                  <EmptyState
                    title={t("dash.none")}
                    body={t("newlot.subtitle")}
                    icon="layers"
                  />
                </div>
              )}
            </div>

            <div className="stack dashboard-sidebar-stack">
              <div className="card workflow-card">
                <div className="card-h">
                  <h3 className="card-title-h3">
                    <Icon name="git-commit" size={15} />
                    <span>{t("how.pipeline")}</span>
                  </h3>
                  <span className="badge ghost badge-count">{t("dash.four_steps")}</span>
                </div>
                <div className="card-b card-pad">
                  <ol className="pipeline is-vertical is-explainer" aria-label={t("dash.pipeline_aria")}>
                    {[1, 2, 3, 4].map((step) => (
                      <li className="pipeline-step" key={step}>
                        <span className="pipeline-dot" aria-hidden="true">{num(step, lang)}</span>
                        <div className="pipeline-copy">
                          <span className="pipeline-label">{t(`dash.step${step}_title`)}</span>
                          <span className="pipeline-desc">{t(`dash.step${step}_desc`)}</span>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>

              <div className="card detector-card">
                <div className="card-h">
                  <h3 className="card-title-h3">
                    <Icon name="cpu" size={15} />
                    <span>{t("dash.model")}</span>
                  </h3>
                  <span className={`badge ${data!.model.model_ok ? "ACCEPT" : "HOLD"}`}>
                    <span className="dot" aria-hidden="true" />
                    {data!.model.model_ok ? t("dash.self_test_passed") : t("dash.check_model")}
                  </span>
                </div>
                <div className="card-b card-pad">
                  <div className="detector-model-name">
                    <span className="dot bg-lime" aria-hidden="true" />
                    <span>{data!.model.model}</span>
                  </div>
                  <div className="detector-model-desc">{t("dash.detector_desc")}</div>
                  <div className="small dim" style={{ marginTop: 4 }}>{t("dash.baseline_notice")}</div>
                  <div className="small bold" style={{ marginTop: 14, color: "var(--text)" }}>{t("dash.baseline_proposals")}</div>
                  <div className="grid cols-3 detector-stats-grid" style={{ marginTop: 6 }}>
                    <div className="kpi mini"><div className="lbl">{lang === "en" ? "photos" : "ছবি"}</div><div className="n detector-stat-num">{num(data!.stats.images, lang)}</div></div>
                    <div className="kpi mini"><div className="lbl">{lang === "en" ? "proposals" : "প্রস্তাব"}</div><div className="n detector-stat-num">{num(data!.stats.proposals, lang)}</div></div>
                    <div className="kpi mini"><div className="lbl">{lang === "en" ? "confirmed" : "নিশ্চিত"}</div><div className="n detector-stat-num">{num(data!.stats.confirmed, lang)}</div></div>
                  </div>
                  <Link className="btn sm secondary btn-model-card" to="/how">
                    <span>{t("how.model_card")}</span>
                    <Icon name="arrow-right" size={13} />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}
