import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useSession } from "../lib/session";
import { Icon } from "../components/ui";
import { ThemeToggle } from "../components/ThemeToggle";

export function LoginPage() {
  const { authenticated, lang, t, data, setLang, demoLogin } = useSession();
  const location = useLocation();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<"failed" | "rl" | "oauth" | "">(() => {
    const value = new URLSearchParams(location.search).get("err");
    return value === "oauth" || value === "rl" ? value : "";
  });

  if (authenticated) {
    return <Navigate to="/" replace />;
  }

  const guest = async () => {
    setBusy(true);
    setError("");
    try {
      await demoLogin("guest");
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== "/login" ? from : "/", { replace: true });
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
            <a className="signin" href="/api/auth/github">
              <svg width="17" height="17" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
              </svg>
              {t("login.github")}
            </a>
          ) : (
            <div className="auth-note" role="note">
              {lang === "en"
                ? "GitHub sign-in is not enabled on this instance. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to turn it on."
                : "এই ইনস্ট্যান্সে গিটহাব সাইন-ইন চালু নেই। চালু করতে GITHUB_CLIENT_ID ও GITHUB_CLIENT_SECRET সেট করুন।"}
            </div>
          )}

          {data.demo_login ? (
            <>
              <button className="signin signin-guest" type="button" onClick={guest} disabled={busy}>
                <Icon name="eye" size={17} />
                {t("login.guest")}
              </button>
              <p className="signin-hint">{t("login.guest_hint")}</p>
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}
