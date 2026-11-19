import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useSession } from "../lib/session";
import { num } from "../lib/format";
import { AppShell } from "../components/AppShell";
import { Button, ErrorState, Field, Icon, Note, Spinner, Toast } from "../components/ui";

interface AdminUser {
  id: number; email: string; display_name: string; role: string; status: string;
  must_change: number; created_at: string;
}

interface AdminData {
  tab: string;
  user: AdminUser;
  users: AdminUser[];
  models: Array<{ id: number; name: string; artifact_sha: string; classes: string; eval_note: string; created_at: string }>;
  tests: Array<{ id: number; model_name: string; passed: number; detail: string; created_at: string }>;
  activations: Array<{ id: number; model_name: string; action: string; reason: string; actor: string; created_at: string }>;
  clauses: Array<{ id: number; buyer_name: string; defect_type: string; zone_code: string; size_band: string | null; severity: string; clause_ref: string }>;
  health: {
    db_bytes: number; disk_free: number; disk_total: number; images: number;
    jobs_ok: number; jobs_failed: number; audit_rows: number; sessions: number;
    model: string; model_loaded: boolean; model_sha: string;
  };
  card: Record<string, unknown>;
}

const TABS = ["users", "models", "health", "clauses"] as const;

export function AdminPage() {
  const { t, lang } = useSession();
  const queryClient = useQueryClient();
  const [params] = useSearchParams();
  const tab = (TABS as readonly string[]).includes(params.get("tab") || "") ? params.get("tab")! : "users";
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", tab],
    queryFn: () => api.get<AdminData>(`/api/admin?tab=${tab}`),
  });
  const [toast, setToast] = useState("");
  const [errorText, setErrorText] = useState("");
  const [temp, setTemp] = useState("");
  const [busy, setBusy] = useState(false);
  const [create, setCreate] = useState({ email: "", display_name: "", role: "inspector", password: "" });
  const [activateReason, setActivateReason] = useState("");

  if (isLoading) return <AppShell title={t("admin.title")} active="admin"><Spinner /></AppShell>;
  if (error || !data) return <AppShell title={t("admin.title")} active="admin"><ErrorState message={(error as Error)?.message || "Forbidden"} /></AppShell>;

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin"] });
  };

  const run = async (fn: () => Promise<unknown>, success = t("flash.saved")) => {
    setBusy(true);
    setErrorText("");
    try {
      await fn();
      setToast(success);
      await refresh();
    } catch (caught) {
      const detail = caught instanceof ApiError ? String(caught.detail) : "";
      setErrorText(
        detail === "last_admin" ? (lang === "en" ? "Cannot disable the last active administrator." : "একমাত্র সক্রিয় অ্যাডমিন নিষ্ক্রিয় করা যাবে না।")
          : detail === "self_role" ? (lang === "en" ? "Self role change is forbidden." : "নিজের ভূমিকা পরিবর্তন নিষিদ্ধ।")
            : detail === "policy" ? (lang === "en" ? "Password policy not met: 15+ characters, no account/context words." : "পাসওয়ার্ড নীতি পূরণ হয়নি।")
              : detail === "invalid" ? (lang === "en" ? "Invalid user details." : "প্রদত্ত তথ্য সঠিক নয়।")
                : t("err.failed"),
      );
    } finally {
      setBusy(false);
    }
  };

  const userAction = (user: AdminUser, action: string, role?: string) =>
    run(async () => {
      const result = await api.post<{ temp_password?: string }>(`/api/admin/users/${user.id}`, { action, role });
      if (result.temp_password) setTemp(result.temp_password);
    }, lang === "en" ? "User account updated." : "ব্যবহারকারীর তথ্য সংরক্ষিত হয়েছে।");

  const createUser = (event: React.FormEvent) => {
    event.preventDefault();
    run(async () => {
      await api.post("/api/admin/users", create);
      setCreate({ email: "", display_name: "", role: "inspector", password: "" });
    }, lang === "en" ? "User created." : "ব্যবহারকারী তৈরি হয়েছে।");
  };

  const { health } = data;
  const activeAdmins = data.users.filter((user) => user.role === "admin" && user.status === "active");

  return (
    <AppShell title={t("admin.title")} subtitle={lang === "en" ? "Accounts, model activation, audit and system health." : "অ্যাকাউন্ট, মডেল সক্রিয়করণ, অডিট ও সিস্টেম স্বাস্থ্য।"} active="admin">
      {toast ? <Toast message={toast} onClose={() => setToast("")} /> : null}

      <div className="tabs" style={{ marginBottom: 18 }}>
        {TABS.map((key) => (
          <Link key={key} to={`/admin?tab=${key}`} className={tab === key ? "on" : ""} aria-current={tab === key ? "page" : undefined}>
            {t(`admin.${key === "users" ? "users" : key === "models" ? "models" : key === "health" ? "health" : "clauses"}`)}
          </Link>
        ))}
        <Link to="/audit">{t("admin.audit")} ↗</Link>
      </div>

      {temp ? (
        <div className="note ok" style={{ marginBottom: 16 }}>
          <div className="row" style={{ gap: 8, alignItems: "flex-start" }}>
            <span style={{ color: "var(--success)", marginTop: 2 }}><Icon name="check-circle" size={16} /></span>
            <div>
              <b>{lang === "en" ? "Temporary Password Generated" : "অস্থায়ী পাসওয়ার্ড তৈরি হয়েছে"}</b>
              <div className="row" style={{ marginTop: 4, gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                <span className="mono" style={{ fontSize: 16, fontWeight: 750, background: "var(--subtle)", padding: "3px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--line)" }}>{temp}</span>
                <Button size="sm" icon="copy" onClick={() => { navigator.clipboard?.writeText(temp); setToast(lang === "en" ? "Copied" : "কপি হয়েছে"); }}>{lang === "en" ? "Copy Password" : "কপি করুন"}</Button>
                <span className="small dim">{lang === "en" ? "Copy now; shown only once and requires a change at first login." : "এখনই কপি করুন; এটি শুধু একবার দেখানো হবে।"}</span>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {errorText ? <Note tone="bad">{errorText}</Note> : null}

      {tab === "users" ? (
        <div className="split">
          <div className="card">
            <div className="card-h">
              <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="users" size={16} /><span>{t("admin.users")}</span></h2>
              <div className="right"><span className="chip">{data.users.length} {lang === "en" ? "accounts" : "অ্যাকাউন্ট"}</span></div>
            </div>
            <div className="tblwrap">
              <table className="table">
                <thead><tr><th>{t("common.user")}</th><th>{t("common.role")}</th><th>{t("common.status")}</th><th className="right">{t("common.actions")}</th></tr></thead>
                <tbody>
                  {data.users.map((user) => {
                    const lastAdmin = user.role === "admin" && user.status === "active" && activeAdmins.length <= 1;
                    const self = user.id === data.user.id;
                    return (
                      <tr key={user.id}>
                        <td>
                          <div style={{ fontWeight: 650, color: "var(--text)" }}>{user.display_name}</div>
                          <div className="small dim mono" style={{ fontSize: 11 }}>{user.email}</div>
                        </td>
                        <td><span className="badge badge-neutral">{t(`common.${user.role}`)}</span></td>
                        <td><span className={`badge ${user.status === "active" ? "ACCEPT" : "REJECT"}`}><span className="dot" />{user.status}</span></td>
                        <td className="right">
                          <div className="btnrow" style={{ justifyContent: "flex-end", gap: 6, alignItems: "center" }}>
                            {lastAdmin ? <button className="btn sm ghost" disabled title={lang === "en" ? "Cannot disable last active administrator" : "একমাত্র সক্রিয় অ্যাডমিন নিষ্ক্রিয় করা যাবে না"}><Icon name="lock" size={12} />{t("admin.disable")}</button>
                              : <Button size="sm" variant="ghost" disabled={busy} onClick={() => userAction(user, user.status === "active" ? "disable" : "enable")}>{user.status === "active" ? t("admin.disable") : t("admin.enable")}</Button>}
                            {self ? <span className="small dim mono" style={{ fontSize: 11 }} title={lang === "en" ? "Self-demotion forbidden" : "নিজের ভূমিকা পরিবর্তন নিষিদ্ধ"}><Icon name="shield" size={12} /> {lang === "en" ? "Self (locked)" : "নিজের অ্যাকাউন্ট"}</span>
                              : (
                                <span className="inline" style={{ gap: 4 }}>
                                  <select value={user.role} style={{ width: "auto", padding: "4px 8px", fontSize: 12, margin: 0 }} onChange={(event) => userAction(user, "role", event.target.value)} disabled={busy}>
                                    {["inspector", "supervisor", "admin"].map((role) => <option key={role} value={role}>{t(`common.${role}`)}</option>)}
                                  </select>
                                </span>
                              )}
                            <Button size="sm" variant="ghost" disabled={busy} title={lang === "en" ? "Issue temporary password" : "অস্থায়ী পাসওয়ার্ড দিন"} onClick={() => userAction(user, "reset")}>{t("admin.reset")}</Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-h"><h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="user-plus" size={16} /><span>{t("admin.new_user")}</span></h2></div>
            <div className="pad">
              <form onSubmit={createUser}>
                <Field label={t("login.email")} required>
                  <input type="email" required autoComplete="off" placeholder="user@lotline.demo" value={create.email} onChange={(event) => setCreate((previous) => ({ ...previous, email: event.target.value }))} />
                </Field>
                <Field label={t("admin.display_name")} required>
                  <input required autoComplete="off" placeholder="Full Name" value={create.display_name} onChange={(event) => setCreate((previous) => ({ ...previous, display_name: event.target.value }))} />
                </Field>
                <Field label={t("common.role")} required hint={lang === "en" ? "Inspector: capture/review; Supervisor: plan/override; Admin: user/system" : "ইন্সপেক্টর: ক্যাপচার/রিভিউ; সুপারভাইজার: প্ল্যান/ওভাররাইড; অ্যাডমিন: ইউজার/সিস্টেম"}>
                  <select required value={create.role} onChange={(event) => setCreate((previous) => ({ ...previous, role: event.target.value }))}>
                    {["inspector", "supervisor", "admin"].map((role) => <option key={role} value={role}>{t(`common.${role}`)}</option>)}
                  </select>
                </Field>
                <Field label={t("login.password")} required>
                  <input type="text" required minLength={15} placeholder="Minimum 15 characters…" value={create.password} onChange={(event) => setCreate((previous) => ({ ...previous, password: event.target.value }))} />
                </Field>
                <Note tone="info">
                  <span style={{ fontSize: 11.5, lineHeight: 1.4 }}>{lang === "en" ? "15+ characters, no composition rules, checked against common and context words. Temporary password forces a change at first login." : "১৫+ অক্ষর, কম্পোজিশন নিয়ম নেই, সাধারণ শব্দ যাচাই হয়।"}</span>
                </Note>
                <Button type="submit" variant="primary" disabled={busy}>{t("common.save")}</Button>
              </form>
            </div>
          </div>
        </div>
      ) : null}

      {tab === "models" ? (
        <div className="split">
          <div className="stack">
            <div className="card">
              <div className="card-h">
                <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="cpu" size={16} /><span>{t("admin.models")}</span></h2>
                <div className="right"><Button size="sm" variant="primary" disabled={busy} onClick={() => run(() => api.post("/api/admin/models/selftest"), lang === "en" ? "Self-test completed." : "সেলফ-টেস্ট সম্পন্ন।")}>{t("admin.selftest")}</Button></div>
              </div>
              <div className="pad-sm">
                {data.models.map((model, index) => (
                  <div key={model.id} style={{ padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
                    <div className="between"><b className="mono">{model.name}</b><span className="badge ACCEPT">{index === 0 ? "active" : "registered"}</span></div>
                    <div className="small dim mono" style={{ marginTop: 4, fontSize: 11 }}>SHA-256: {model.artifact_sha.slice(0, 32)}…</div>
                    <div className="small dim" style={{ marginTop: 2 }}>{lang === "en" ? "classes" : "শ্রেণি"}: <span className="mono">{model.classes}</span></div>
                    <div className="small muted" style={{ marginTop: 4 }}>{model.eval_note}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-h"><h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="activity" size={16} /><span>{lang === "en" ? "Self-test history" : "সেলফ-টেস্ট ইতিহাস"}</span></h2></div>
              <div className="pad-sm">
                {data.tests.length ? data.tests.map((test) => (
                  <div key={test.id} className="between" style={{ padding: "8px 0", borderBottom: "1px solid var(--line)", alignItems: "center" }}>
                    <span className={`badge ${test.passed ? "ACCEPT" : "REJECT"}`}>{test.passed ? "PASS" : "FAIL"}</span>
                    <span className="small dim mono" style={{ flex: 1, marginLeft: 10 }}>{test.detail}</span>
                    <span className="small dim mono" style={{ fontSize: 11 }}>{test.created_at.slice(0, 16)}</span>
                  </div>
                )) : <div className="empty">{t("common.none")}</div>}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-h"><h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="check-circle" size={16} /><span>{t("admin.activate")}</span></h2></div>
            <div className="pad">
              <p className="small muted" style={{ marginBottom: 14, lineHeight: 1.5 }}>{lang === "en" ? "Activation is append-only and requires a passing self-test. Model files are immutable; old decisions keep their original model version." : "সক্রিয়করণ শুধু যোগ হয় এবং সফল সেলফ-টেস্ট দরকার।"}</p>
              <form onSubmit={(event) => { event.preventDefault(); run(() => api.post("/api/admin/models/activate", { reason: activateReason }), lang === "en" ? "Model activated." : "মডেল সক্রিয় হয়েছে।"); }}>
                <Field label={t("common.reason")} required>
                  <textarea rows={3} minLength={20} required value={activateReason} onChange={(event) => setActivateReason(event.target.value)} placeholder={lang === "en" ? "Reason for model activation (minimum 20 characters)…" : "মডেল সক্রিয়করণের কারণ (কমপক্ষে ২০ অক্ষর)…"} />
                </Field>
                <Button type="submit" variant="primary" disabled={busy || activateReason.trim().length < 20}>{t("admin.activate")}</Button>
              </form>
              <Note tone="warn">{lang === "en" ? "No model upload endpoint exists. A checkpoint is placed on the host by the operator and hash-verified before loading." : "মডেল আপলোড এন্ডপয়েন্ট নেই।"}</Note>
              <div className="list" style={{ marginTop: 14 }}>
                {data.activations.map((activation) => (
                  <li key={activation.id}>
                    <span className="badge badge-neutral">{activation.action}</span>
                    <div className="grow">
                      <div className="small">{activation.reason}</div>
                      <div className="small dim mono" style={{ fontSize: 11 }}>{activation.actor} · {activation.created_at.slice(0, 16)}</div>
                    </div>
                  </li>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {tab === "health" ? (
        <>
          <div className="grid cols-4" style={{ marginBottom: 18 }}>
            <div className="kpi accent"><div className="lbl">{t("dash.model")}</div><div className="n" style={{ fontSize: 20 }}>{health.model_loaded ? "online" : "offline"}</div><div className="small dim mono" style={{ marginTop: 4 }}>{health.model}</div></div>
            <div className="kpi"><div className="lbl">{lang === "en" ? "Database" : "ডেটাবেস"}</div><div className="n" style={{ fontSize: 20 }}>{Math.round(health.db_bytes / 1024)} KB</div><div className="small dim">{health.sessions} sessions</div></div>
            <div className="kpi"><div className="lbl">{lang === "en" ? "Disk free" : "ডিস্ক খালি"}</div><div className="n" style={{ fontSize: 20 }}>{(health.disk_free / 1073741824).toFixed(1)} GB</div><div className="small dim">{lang === "en" ? "of" : "মোট"} {(health.disk_total / 1073741824).toFixed(1)} GB</div></div>
            <div className="kpi"><div className="lbl">{lang === "en" ? "Inference jobs" : "ইনফারেন্স কাজ"}</div><div className="n" style={{ fontSize: 20 }}>{num(health.jobs_ok, lang)}<small> ok / {num(health.jobs_failed, lang)} failed</small></div><div className="small dim">{health.images} {lang === "en" ? "images" : "ছবি"}</div></div>
          </div>

          <div className="split">
            <div className="card">
              <div className="card-h"><h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="shield-check" size={16} /><span>{lang === "en" ? "Checks" : "যাচাই"}</span></h2></div>
              <div className="pad-sm">
                <div className="list">
                  <li><span className="badge ACCEPT">ok</span><div className="grow"><b>{lang === "en" ? "Audit chain" : "অডিট চেইন"}</b><div className="small dim">{health.audit_rows} {lang === "en" ? "append-only rows" : "শুধু-যোগ রেকর্ড"}</div></div></li>
                  <li><span className="badge ACCEPT">ok</span><div className="grow"><b>{lang === "en" ? "Evidence integrity" : "প্রমাণ অখণ্ডতা"}</b><div className="small dim">{lang === "en" ? "SHA-256 checked at every decision and report" : "প্রতিটি সিদ্ধান্ত ও রিপোর্টে SHA-256 যাচাই"}</div></div></li>
                  <li><span className="badge HOLD">manual</span><div className="grow"><b>{lang === "en" ? "Backup" : "ব্যাকআপ"}</b><div className="small dim">{lang === "en" ? "Operator action: nightly copy + restore drill. Not automated in this demo." : "অপারেটর কাজ: রাতের কপি + রিস্টোর ড্রিল।"}</div></div></li>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-h"><h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="file-text" size={16} /><span>{lang === "en" ? "Model artifact" : "মডেল আর্টিফ্যাক্ট"}</span></h2></div>
              <div className="pad-sm small">
                <div className="mono dim" style={{ wordBreak: "break-all", fontSize: 11 }}>{health.model_sha}</div>
                <Note tone="info"><span style={{ fontSize: 11.5, lineHeight: 1.4 }}>{lang === "en" ? "The Vision service has no database access and the API has no route to it. The detector runs here in-process for the single-container demo." : "ভিশন সার্ভিসের ডেটাবেস অ্যাক্সেস নেই।"}</span></Note>
              </div>
            </div>
          </div>
        </>
      ) : null}

      {tab === "clauses" ? (
        <div className="card">
          <div className="card-h">
            <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="book-open" size={16} /><span>{t("admin.clauses")} (Buyer Quality Specifications)</span></h2>
            <div className="right"><span className="chip">{data.clauses.length} {lang === "en" ? "rules" : "নিয়ম"}</span></div>
          </div>
          <div className="pad-sm"><Note tone="info">{t("admin.clause_readonly")}</Note></div>
          <div className="tblwrap">
            <table className="table">
              <thead><tr><th>{t("lots.buyer")}</th><th>{t("rev.type")}</th><th>{t("rev.zone")}</th><th>{t("rev.size_band")}</th><th>{lang === "en" ? "Severity" : "সিরিয়িটি"}</th><th>{lang === "en" ? "Clause" : "ক্লজ"}</th></tr></thead>
              <tbody>
                {data.clauses.map((clause) => (
                  <tr key={clause.id}>
                    <td><b style={{ color: "var(--text)" }}>{clause.buyer_name}</b></td>
                    <td>{t(`type.${clause.defect_type}`)}</td>
                    <td className="mono" style={{ fontWeight: 600 }}>{clause.zone_code}</td>
                    <td>{clause.size_band || "—"}</td>
                    <td><span className={`badge ${clause.severity}`}>{t(`severe.${clause.severity}`)}</span></td>
                    <td className="mono dim" style={{ fontSize: 11.5 }}>{clause.clause_ref}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
