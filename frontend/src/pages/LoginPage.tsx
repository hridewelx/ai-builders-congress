import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../lib/api";
import { useSession } from "../lib/session";
import { Icon } from "../components/ui";
import { ThemeToggle } from "../components/ThemeToggle";

export function LoginPage() {
  const { authenticated, lang, t, data, login, demoLogin, setLang } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<"failed" | "rl" | "oauth" | "">(() => {
    const value = new URLSearchParams(location.search).get("err");
    return value === "oauth" || value === "rl" ? value : "";
  });
  const [busy, setBusy] = useState(false);

  if (authenticated) {
    return <Navigate to="/" replace />;
  }

  const go = () => {
    const from = (location.state as { from?: string } | null)?.from;
    navigate(from && from !== "/login" ? from : "/", { replace: true });
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      go();
    } catch (caught) {
      const detail = caught instanceof ApiError ? caught.detail : "";
      setError(detail === "rl" ? "rl" : "failed");
    } finally {
      setBusy(false);
    }
  };

  const demo = async (role: "inspector" | "supervisor" | "admin") => {
    setBusy(true);
    setError("");
    try {
      await demoLogin(role);
      go();
    } catch {
      setError("failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <section className="left" aria-labelledby="login-headline">
        <div className="login-brand">
          <img src="/static/brand/logo-full-light.svg" alt="Lotline" />
          <div className="tagline">
            {lang === "en"
              ? "Inspect Intelligently. Decide Consistently. Deliver Confidently."
              : "বুদ্ধিমানের সঙ্গে পরিদর্শন। ধারাবাহিকভাবে সিদ্ধান্ত। আত্মবিশ্বাসের সঙ্গে ডেলিভারি।"}
          </div>
        </div>

        <div className="hero-main">
          <h1 id="login-headline">
            <span className="headline-muted">
              {lang === "en" ? <>AI proposes.<br />Humans verify.</> : <>এআই প্রস্তাব দেয়।<br />মানুষ যাচাই করে।</>}
            </span>
            <em>{lang === "en" ? "The engine decides." : "ইঞ্জিন সিদ্ধান্ত দেয়।"}</em>
          </h1>
          <p className="lead">
            {lang === "en"
              ? "A knitwear lot-acceptance decision you can defend: every photo, every human confirmation, every count, and the exact rule that produced the outcome."
              : "একটি নিটওয়্যার লট-গ্রহণ সিদ্ধান্ত যা আপনি প্রমাণ করতে পারবেন: প্রতিটি ছবি, প্রতিটি মানব নিশ্চিতকরণ, প্রতিটি গণনা এবং ঠিক যে নিয়মে ফলাফল এসেছে।"}
          </p>
        </div>

        <div className="hero-bottom">
          <div className="proof" aria-label="Build facts">
            <div><b>4</b><span>{lang === "en" ? "outcomes, never guessed" : "ফলাফল, কখনো অনুমান নয়"}</span></div>
            <div><b>0</b><span>{lang === "en" ? "AI approvals" : "এআই অনুমোদন"}</span></div>
            <div><b>100%</b><span>{lang === "en" ? "auditable changes" : "অডিটযোগ্য পরিবর্তন"}</span></div>
          </div>
          <div className="meta-note hero-footer">
            {lang === "en"
              ? "International AI Builders Congress 2026 · IndustrySphere challenge · staged demo data"
              : "ইন্টারন্যাশনাল এআই বিল্ডার্স কংগ্রেস ২০২৬ · ইন্ডাস্ট্রিস্ফিয়ার · স্টেজ করা ডেমো ডেটা"}
          </div>
        </div>
      </section>

      <section className="auth" aria-labelledby="signin-title">
        <div className="auth-card">
          <div className="between" style={{ marginBottom: 18 }}>
            <span className="pill"><span className="dot" aria-hidden="true" />{lang === "en" ? "Demo build · staged data" : "ডেমো বিল্ড · স্টেজ করা ডেটা"}</span>
            <span className="auth-controls">
              <ThemeToggle />
              <button className="lang-link" type="button" onClick={() => setLang(lang === "en" ? "bn" : "en")}>
                <Icon name="languages" size={15} />
                <span>{lang === "en" ? "বাংলা" : "English"}</span>
              </button>
            </span>
          </div>

          <h2 id="signin-title">{t("login.title")}</h2>
          <p className="subtitle">{t("login.subtitle")}</p>

          {error ? (
            <div className="note bad" role="alert" style={{ marginBottom: 14 }}>
              {error === "oauth" ? t("login.oauth") : error === "rl" ? t("login.rl") : t("login.failed")}
            </div>
          ) : null}

          {data.github_oauth ? (
            <>
              <a className="btn ghost lg" href="/api/auth/github" style={{ width: "100%", marginBottom: 14 }}>
                <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor" style={{ marginRight: 8 }}>
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
                </svg>
                {t("login.github")}
              </a>
              <div className="divider"><span /><b>{t("login.or")}</b><span /></div>
            </>
          ) : null}

          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="email">{t("login.email")}</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="username"
                required
                placeholder="inspector@lotline.demo"
                autoCapitalize="none"
                spellCheck={false}
                autoFocus
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="password">{t("login.password")}</label>
              <div style={{ position: "relative" }}>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  placeholder="••••••••••••"
                  style={{ paddingRight: 40 }}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  className="icon-btn pass-toggle"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((value) => !value)}
                  style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--muted)", display: "flex", alignItems: "center", padding: 4 }}
                >
                  <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
                </button>
              </div>
            </div>
            <button className="btn primary lg" type="submit" style={{ width: "100%" }} disabled={busy}>
              {t("login.submit")}
            </button>
          </form>

          <div className="divider"><span /><b>{t("login.demo")}</b><span /></div>

          <div className="demo-grid">
            <button className="demo-role" type="button" onClick={() => demo("inspector")} disabled={busy}>
              <span className="demo-initial" aria-hidden="true">IN</span>
              <span className="demo-info">
                <span className="demo-name">{t("common.inspector")}</span>
                <span className="demo-email">inspector@lotline.demo</span>
              </span>
            </button>
            <button className="demo-role" type="button" onClick={() => demo("supervisor")} disabled={busy}>
              <span className="demo-initial" aria-hidden="true">A</span>
              <span className="demo-info">
                <span className="demo-name">{lang === "en" ? "Supervisor A" : "সুপারভাইজার এ"}</span>
                <span className="demo-email">supervisor@lotline.demo</span>
              </span>
            </button>
            <button className="demo-role" type="button" onClick={() => demo("admin")} disabled={busy}>
              <span className="demo-initial" aria-hidden="true">AD</span>
              <span className="demo-info">
                <span className="demo-name">{t("common.admin")}</span>
                <span className="demo-email">admin@lotline.demo</span>
              </span>
            </button>
            <button
              className="demo-role"
              type="button"
              onClick={() => {
                setEmail("lead@lotline.demo");
                setPassword("QualityFloor2026!");
              }}
            >
              <span className="demo-initial" aria-hidden="true">B</span>
              <span className="demo-info">
                <span className="demo-name">{lang === "en" ? "Supervisor B" : "সুপারভাইজার বি"}</span>
                <span className="demo-email">lead@lotline.demo</span>
              </span>
            </button>
          </div>

          <div className="demo-box">
            <span className="demo-box-lbl">{lang === "en" ? "Demo credentials" : "ডেমো তথ্য"}:</span>
            <span>{lang === "en" ? "Seeded accounts share" : "সকল অ্যাকাউন্টের একই পাসওয়ার্ড"}</span>
            <code>QualityFloor2026!</code>
          </div>
        </div>
      </section>
    </div>
  );
}
