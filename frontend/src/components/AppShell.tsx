import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useSession } from "../lib/session";
import { DemoTag, Dialog, Icon, IconButton } from "./ui";
import { ThemeToggle } from "./ThemeToggle";

const NAV_GROUPS = [
  { key: "main", label: "" },
  { key: "workspace", label: "Workspace" },
  { key: "oversight", label: "Oversight" },
];

export function AppShell({
  title,
  subtitle,
  active,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  active: "dashboard" | "lots" | "audit" | "admin" | "how";
  children: ReactNode;
}) {
  const { user, lang, t, setLang, logout, data } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const [configOpen, setConfigOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("drawer-open", drawerOpen);
    return () => document.body.classList.remove("drawer-open");
  }, [drawerOpen]);

  useEffect(() => {
    document.body.classList.toggle("rail-collapsed", collapsed);
    return () => document.body.classList.remove("rail-collapsed");
  }, [collapsed]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  if (!user) return null;

  const isAdmin = user.role === "admin";
  const isSupervisor = user.role === "supervisor";

  const changeLang = async () => {
    await setLang(lang === "en" ? "bn" : "en");
  };

  const signOut = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="shell">
      <div className="mobile-scrim" aria-hidden="true" onClick={() => setDrawerOpen(false)} />
      <aside className="rail" id="sidebar" aria-label="Primary navigation">
        <div className="rail-head">
          <Link className="brand" to="/" aria-label="Lotline home">
            <img className="brand-full" src="/static/brand/logo-full-light.svg" alt="Lotline" />
            <img className="brand-icon" src="/static/brand/logo-icon.svg" alt="Lotline" />
          </Link>
          <button
            className="rail-toggle"
            type="button"
            onClick={() => setCollapsed((value) => !value)}
            aria-label="Collapse sidebar"
            aria-expanded={!collapsed}
            aria-controls="sidebar"
          >
            <Icon name="panel-left-close" size={17} />
          </button>
          <button
            className="rail-toggle rail-close"
            type="button"
            onClick={() => setDrawerOpen(false)}
            aria-label="Close menu"
          >
            <Icon name="x" size={17} />
          </button>
        </div>

        <nav className="nav" aria-label="Primary">
          <div className="nav-group">
            <Link to="/" className={active === "dashboard" ? "on" : ""} aria-current={active === "dashboard" ? "page" : undefined}>
              <Icon name="layout-dashboard" />
              <span className="lbl">{t("nav.dashboard")}</span>
            </Link>
            <Link to="/lots" className={active === "lots" ? "on" : ""} aria-current={active === "lots" ? "page" : undefined}>
              <Icon name="layers" />
              <span className="lbl">{t("nav.lots")}</span>
            </Link>
          </div>

          {(isAdmin || isSupervisor) ? (
            <div className="nav-group">
              <div className="nav-label">Workspace</div>
              <button className="nav-item is-btn" type="button" onClick={() => setConfigOpen(true)}>
                <Icon name="settings" />
                <span className="lbl">Configuration</span>
                <span className="nav-badge">{t("nav.view_only")}</span>
              </button>
            </div>
          ) : null}

          {(isAdmin || isSupervisor) ? (
            <div className="nav-group">
              <div className="nav-label">Oversight</div>
              {isSupervisor || isAdmin ? (
                <Link to="/audit" className={active === "audit" ? "on" : ""} aria-current={active === "audit" ? "page" : undefined}>
                  <Icon name="scroll-text" />
                  <span className="lbl">{t("nav.audit")}</span>
                </Link>
              ) : null}
              {isAdmin ? (
                <Link to="/admin?tab=users" className={active === "admin" ? "on" : ""} aria-current={active === "admin" ? "page" : undefined}>
                  <Icon name="users" />
                  <span className="lbl">User management</span>
                </Link>
              ) : null}
            </div>
          ) : null}
        </nav>

        <div className="spacer" />
        <div className="railcard">
          <b>{t("dash.principle")}</b>
          Every count, reason and override is recorded.
        </div>
        <div className="rail-user">
          <span className="avatar" aria-hidden="true">{user.display_name.slice(0, 1)}</span>
          <div className="who">
            <b>{user.display_name}</b>
            {data.is_guest ? <span className="guest-tag">{t("guest.label")}</span> : <span>{t(`common.${user.role}`)}</span>}
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button
            className="menu-btn"
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            aria-expanded={drawerOpen}
            aria-controls="sidebar"
          >
            <Icon name="menu" size={20} />
          </button>
          <div className="title-wrap">
            <nav className="crumb" aria-label="Breadcrumb">
              <Link to="/">Lotline</Link>
              <span className="sep" aria-hidden="true">/</span>
              <span>{active === "dashboard" ? t("nav.dashboard") : active === "lots" ? t("nav.lots") : active === "audit" ? t("nav.audit") : active === "admin" ? t("nav.admin") : t("nav.how")}</span>
            </nav>
            <h1>{title}</h1>
            <div className="sub">{subtitle}</div>
          </div>
          <div className="top-actions">
            <ThemeToggle />
            <span className="top-demo"><DemoTag label={t("lot.demo_data")} /></span>
            <button className="lang-link" type="button" onClick={changeLang} aria-label="Switch language">
              <Icon name="languages" size={15} />
              <span>{lang === "en" ? "বাংলা" : "English"}</span>
            </button>
            <details className="user-menu">
              <summary aria-label="Account menu">
                <span className="avatar" aria-hidden="true">{user.display_name.slice(0, 1)}</span>
                <span className="user-name">{user.display_name}</span>
                <Icon name="chevron-down" size={14} />
              </summary>
              <div className="menu-panel">
                <div className="menu-head">
                  <b>{user.display_name}</b>
                  <span>{user.email}</span>
                </div>
                <Link to="/how">
                  <Icon name="help-circle" size={16} />
                  {t("nav.how")}
                </Link>
                <button type="button" onClick={signOut}>
                  <Icon name="log-out" size={16} />
                  {t("nav.logout")}
                </button>
              </div>
            </details>
          </div>
        </header>

        <main className="content" id="main-content">
          {children}
        </main>
        <footer className="foot">
          <span>{t("foot.demo_note")}</span>
          <Link to="/how">{t("nav.how")}</Link>
        </footer>
      </div>

      <Dialog
        title="System Configuration & Catalog"
        open={configOpen}
        onClose={() => setConfigOpen(false)}
        actions={<button className="btn ghost sm" type="button" onClick={() => setConfigOpen(false)}>Close</button>}
      >
        <div className="note info config-note">
          <b>Catalog & Buyer Clauses</b>
          <div className="small dim mt-2">
            Products, buyers, and defect severity clauses are seeded demo data, read-only for admin.
          </div>
        </div>
        <div className="grid cols-2 config-grid">
          <div className="config-box">
            <div className="lbl config-box-lbl">Registered Buyers</div>
            <ul className="small dim catalog-list">
              {data.catalogs.buyers.map((buyer) => (
                <li key={buyer.id}><b>{buyer.name}</b> ({buyer.country})</li>
              ))}
            </ul>
          </div>
          <div className="config-box">
            <div className="lbl config-box-lbl">Active Knit Garments</div>
            <ul className="small dim catalog-list">
              {data.catalogs.products.map((product) => (
                <li key={product.id}><b>{product.name}</b> ({product.family})</li>
              ))}
            </ul>
          </div>
        </div>
        {isAdmin ? (
          <div className="dialog-actions">
            <a className="btn sm" href="/admin?tab=clauses">View Full Clause Matrix →</a>
          </div>
        ) : null}
      </Dialog>
    </div>
  );
}
