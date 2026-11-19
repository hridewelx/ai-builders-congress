import { Link, useLocation } from "react-router-dom";
import { useSession } from "../lib/session";
import { Icon } from "./ui";

export function LotTabs({ lotId, isAdmin }: { lotId: number; isAdmin: boolean }) {
  const { t } = useSession();
  const location = useLocation();
  const base = `/lots/${lotId}`;
  const on = (suffix: string) => location.pathname === base + suffix;
  const tab = (href: string, label: string, icon: string, active: boolean) => (
    <Link to={href} className={active ? "on" : ""} aria-current={active ? "page" : undefined}>
      <Icon name={icon} size={14} />
      <span>{label}</span>
    </Link>
  );
  return (
    <nav className="tabs" aria-label="Lot sections">
      {tab(base, t("lot.overview"), "layers", on(""))}
      {!isAdmin ? tab(`${base}/plan`, t("lot.plan"), "sliders", on("/plan")) : null}
      {!isAdmin ? tab(`${base}/capture`, t("lot.capture"), "camera", on("/capture")) : null}
      {!isAdmin ? tab(`${base}/review`, t("lot.review"), "eye", on("/review")) : null}
      {tab(`${base}/decision`, t("lot.decision"), "clipboard-check", on("/decision"))}
      <Link to={`${base}/#history`}>
        <Icon name="clock" size={14} />
        <span>History</span>
      </Link>
      {!isAdmin ? tab(`${base}/report`, t("lot.report"), "file-text", on("/report")) : null}
    </nav>
  );
}
