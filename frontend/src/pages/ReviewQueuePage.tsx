import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import { num } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { LotTabs } from "../components/LotTabs";
import { Button, EmptyState, ErrorState, Icon, Pipeline, Spinner } from "../components/ui";

interface QueueData {
  lot: { id: number; lot_code: string; buyer_name: string; status: string };
  queue: Array<{
    unit: { id: number; garment_code: string };
    view: {
      id: number; side: string; image: { id: number } | null; inference_status: string;
      open_proposals: number; predictions: Array<{ id: number; review_state: string }>;
    };
    priority: number;
  }>;
}

export function ReviewQueuePage() {
  const { lotId } = useParams();
  const id = Number(lotId);
  const { t, lang } = useSession();
  const { data, isLoading, error } = useQuery({
    queryKey: ["review-queue", id],
    queryFn: () => api.get<QueueData>(`/api/lots/${id}/review`),
  });

  if (isLoading) return <AppShell title={t("rev.queue")} active="lots"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("rev.queue")} active="lots"><ErrorState message={(error as Error)?.message || "Not found"} /></AppShell>;

  const { lot, queue } = data;
  return (
    <AppShell title={t("rev.queue")} subtitle={`${lot.lot_code} · ${lot.buyer_name}`} active="lots">
      <LotTabs lotId={id} isAdmin={false} />
      <Pipeline steps={[
        { label: lang === "en" ? "1. AI Detection" : "১. এআই শনাক্তকরণ", value: `${queue.length} ${lang === "en" ? "views in queue" : "ভিউ তালিকায়"}`, state: queue.length ? "active" : "done" },
        { label: lang === "en" ? "2. Human Review" : "২. মানুষ পর্যালোচনা", value: queue.length ? (lang === "en" ? "Reviewing…" : "পর্যালোচনাধীন") : (lang === "en" ? "All reviewed" : "সব পর্যালোচিত"), state: queue.length ? "active" : "done" },
        { label: lang === "en" ? "3. Decision Engine" : "৩. নির্ধারক ইঞ্জিন", value: `${t("common.status")}: ${lot.status}`, state: lot.status === "decided" ? "done" : "pending" },
      ]} />

      <div className="card">
        <div className="card-h">
          <h2>{t("rev.queue")}</h2>
          <div className="right">
            <span className="chip">{queue.length} {lang === "en" ? (queue.length === 1 ? "view" : "views") : "ভিউ"}</span>
            {queue.length && queue[0].view.image ? (
              <Button href={`/review/${queue[0].view.image.id}`} size="sm" variant="primary" iconAfter="chevron-right">{t("common.continue")}</Button>
            ) : null}
          </div>
        </div>

        {queue.length ? (
          <div className="tblwrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("lot.unit")}</th>
                  <th>{t("cap.side")}</th>
                  <th>{t("common.status")}</th>
                  <th>{lang === "en" ? "Priority" : "অগ্রাধিকার"}</th>
                  <th className="right">{t("common.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={`${item.unit.id}-${item.view.id}`}>
                    <td style={{ fontWeight: 600 }}>{item.unit.garment_code}</td>
                    <td><span className="badge badge-neutral">{t(`cap.${item.view.side}`)}</span></td>
                    <td>
                      {!item.view.image ? <span className="badge badge-neutral">{lang === "en" ? "no photo" : "ছবি নেই"}</span>
                        : ["failed", "not_inferred"].includes(item.view.inference_status) ? <span className="badge badge-warning"><span className="dot" />{lang === "en" ? "manual review" : "ম্যানুয়াল"}</span>
                          : item.view.open_proposals ? <span className="badge badge-pending"><span className="dot" />{item.view.open_proposals} {lang === "en" ? "open proposal(s)" : "খোলা প্রস্তাব"}</span>
                            : <span className="badge badge-neutral">{lang === "en" ? "clean / no proposals" : "প্রস্তাব নেই"}</span>}
                    </td>
                    <td>
                      {item.priority === 3 ? <span className="badge badge-danger"><span className="dot" />{lang === "en" ? "critical routing" : "ক্রিটিক্যাল"}</span>
                        : item.priority === 2 ? <span className="badge badge-warning"><span className="dot" />{lang === "en" ? "manual" : "ম্যানুয়াল"}</span>
                          : item.priority === 1 ? <span className="badge badge-pending"><span className="dot" />{lang === "en" ? "review" : "পর্যালোচনা"}</span>
                            : <span className="dim">—</span>}
                    </td>
                    <td className="right">
                      {item.view.image ? <Link className="btn sm primary" to={`/review/${item.view.image.id}`}>{t("common.open")} →</Link>
                        : <Link className="btn sm" to={`/lots/${id}/capture`}>{t("lot.capture")}</Link>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="pad review-queue-empty">
            <EmptyState
              title={t("rev.queue_empty")}
              body={lang === "en" ? "A complete sample is reviewed. Proceed to compute decision." : "সম্পূর্ণ নমুনা পর্যালোচিত। সিদ্ধান্ত গণনার দিকে এগিয়ে যান।"}
              icon="check-circle"
              actionLabel={t("dec.compute")}
              actionHref={`/lots/${id}/decision`}
            />
          </div>
        )}
      </div>
    </AppShell>
  );
}
