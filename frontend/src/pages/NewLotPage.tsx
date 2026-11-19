import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useSession } from "../lib/session";
import { AppShell } from "../components/AppShell";
import { ErrorState, Field, Icon, Spinner } from "../components/ui";

interface CatalogData {
  buyers: Array<{ id: number; name: string; country: string }>;
  products: Array<{ id: number; name: string; family: string }>;
}

export function NewLotPage() {
  const { t, lang } = useSession();
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({
    queryKey: ["new-lot"],
    queryFn: () => api.get<CatalogData>("/api/lots/new"),
  });
  const [form, setForm] = useState({
    lot_code: "",
    color: "",
    buyer_id: "",
    product_id: "",
    lot_size: "240",
    selection_method: "self-declared random",
  });
  const [problem, setProblem] = useState<"exists" | "invalid" | "">("");
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((previous) => ({ ...previous, [key]: event.target.value }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setProblem("");
    try {
      const result = await api.post<{ id: number }>("/api/lots", {
        ...form,
        buyer_id: Number(form.buyer_id),
        product_id: Number(form.product_id),
        lot_size: Number(form.lot_size),
      });
      navigate(`/lots/${result.id}`);
    } catch (caught) {
      const detail = caught instanceof ApiError ? caught.detail : "";
      setProblem(detail === "exists" ? "exists" : "invalid");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell title={t("newlot.title")} subtitle={t("newlot.subtitle")} active="lots">
      {problem === "exists" ? (
        <div className="note bad" style={{ marginBottom: 18 }}>
          <b style={{ color: "var(--red-ink)" }}>{lang === "en" ? "Lot code already exists" : "লট কোডটি ইতিমধ্যে ব্যবহৃত হয়েছে"}</b>
          <div className="small dim" style={{ marginTop: 3 }}>
            {lang === "en"
              ? "A lot with this code is already registered in the system. Lot codes must be unique across the organization."
              : "এই কোডের একটি লট ইতিমধ্যে নিবন্ধিত আছে। পুরো প্রতিষ্ঠানে লট কোড একক (ইউনিক) হতে হবে।"}
          </div>
        </div>
      ) : problem === "invalid" ? (
        <div className="note bad" style={{ marginBottom: 18 }}>
          <b style={{ color: "var(--red-ink)" }}>{lang === "en" ? "Invalid lot details" : "লটের তথ্যে ত্রুটি রয়েছে"}</b>
          <div className="small dim" style={{ marginTop: 3 }}>
            {lang === "en"
              ? "Please fill in all required fields. Lot code cannot be blank, and lot size must be an integer of at least 1."
              : "সকল আবশ্যক ঘর পূরণ করুন। লট কোড খালি রাখা যাবে না এবং লট সাইজ অবশ্যই কমপক্ষে ১ হতে হবে।"}
          </div>
        </div>
      ) : null}

      <div className="split">
        <div className="card">
          <div className="card-h">
            <h3 style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14.5, fontWeight: 650 }}>
              <Icon name="plus-circle" size={16} />
              <span>{t("common.details")}</span>
            </h3>
          </div>
          <div className="pad" style={{ padding: 24 }}>
            {isLoading ? <Spinner /> : error ? <ErrorState message={(error as Error).message} /> : (
              <form onSubmit={submit} id="newLotForm">
                <div className="grid cols-2" style={{ gap: 16 }}>
                  <Field label={t("newlot.code")} required hint={lang === "en" ? "Unique identifier for the production lot" : "উৎপাদন লটের জন্য একক শনাক্তকারী কোড"}>
                    <input
                      id="lot-code"
                      required
                      placeholder="LT-2026-020"
                      style={{ textTransform: "uppercase", fontFamily: "var(--mono)", fontWeight: 600 }}
                      autoComplete="off"
                      autoFocus
                      pattern="[A-Za-z0-9_-]+"
                      value={form.lot_code}
                      onChange={set("lot_code")}
                    />
                  </Field>
                  <Field label={t("newlot.color")} hint={lang === "en" ? "Primary shade or dye color" : "প্রধান শেড বা রঙের নাম"}>
                    <input id="lot-color" placeholder="Navy / Black / Olive" value={form.color} onChange={set("color")} />
                  </Field>
                  <Field label={t("newlot.buyer")} required hint={lang === "en" ? "Determines acceptance clauses and defect severity" : "গ্রহণযোগ্যতার ক্লজ ও ডিফেক্ট সিরিয়িটি নির্ধারণ করে"}>
                    <select id="lot-buyer" required value={form.buyer_id} onChange={set("buyer_id")}>
                      <option value="" disabled>{lang === "en" ? "Select buyer…" : "ক্রেতা নির্বাচন করুন…"}</option>
                      {data!.buyers.map((buyer) => (
                        <option key={buyer.id} value={buyer.id}>{buyer.name} · {buyer.country}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label={t("newlot.product")} required hint={lang === "en" ? "Garment style family and inspection profile" : "পোশাকের স্টাইল ও ইন্সপেকশন প্রোফাইল"}>
                    <select id="lot-product" required value={form.product_id} onChange={set("product_id")}>
                      <option value="" disabled>{lang === "en" ? "Select product…" : "পণ্য নির্বাচন করুন…"}</option>
                      {data!.products.map((product) => (
                        <option key={product.id} value={product.id}>{product.name} · {product.family}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label={`${t("newlot.size")} (N)`} required hint={lang === "en" ? "Total pieces in lot (integer ≥ 1)" : "লটের মোট সংখ্যা (পূর্ণসংখ্যা ≥ ১)"}>
                    <input id="lot-size" type="number" min={1} required className="font-mono" value={form.lot_size} onChange={set("lot_size")} />
                  </Field>
                  <Field label={t("newlot.selection")} hint={lang === "en" ? "Sampling method applied on the floor" : "ফ্লোরে প্রয়োগকৃত স্যাম্পলিং পদ্ধতি"}>
                    <select id="lot-selection" value={form.selection_method} onChange={set("selection_method")}>
                      <option value="self-declared random">{lang === "en" ? "self-declared random" : "স্ব-ঘোষিত র্যান্ডম"}</option>
                      <option value="operator choice">{lang === "en" ? "operator choice" : "অপারেটরের পছন্দ"}</option>
                      <option value="not recorded">{lang === "en" ? "not recorded" : "নথিভুক্ত নয়"}</option>
                    </select>
                  </Field>
                </div>

                <div className="note warn" style={{ margin: "20px 0 16px" }}>
                  <div className="small dim">
                    {lang === "en"
                      ? "Lotline cannot verify that garments were drawn at random. The selection method is stored and printed as self-declared."
                      : "লটলাইন স্বাধীনভাবে নিশ্চিত করতে পারে না যে নমুনা এলোমেলোভাবে সংগ্রহ করা হয়েছে। স্যাম্পলিং পদ্ধতি স্ব-ঘোষিত হিসেবে সংরক্ষিত ও রিপোর্টে মুদ্রিত হয়।"}
                  </div>
                </div>

                <div className="btnrow" style={{ gap: 10 }}>
                  <button className="btn primary" type="submit" disabled={busy}>{t("newlot.submit")}</button>
                  <button className="btn ghost" type="button" onClick={() => navigate("/lots")}>{t("common.cancel")}</button>
                </div>
              </form>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Icon name="compass" size={16} />
              <span>{lang === "en" ? "What happens next" : "এরপরের ধাপসমূহ"}</span>
            </h3>
          </div>
          <div className="pad-sm" style={{ padding: 18 }}>
            <ol className="pipeline is-vertical" aria-label="Lifecycle guide">
              {[
                [t("lot.plan"), lang === "en" ? "A Supervisor configures sample size n and per-class Ac/Re limits. Without an active plan the lot remains on HOLD." : "সুপারভাইজার নমুনা আকার n এবং প্রতিটি ক্লাসে Ac/Re সীমা দেন। প্ল্যান ছাড়া লট HOLD থাকে।"],
                [t("lot.capture"), lang === "en" ? "Inspectors register garments and upload front and back photos using phone cameras." : "ইন্সপেক্টররা ফোন ক্যামেরা দিয়ে সামনে ও পিছনের ছবি তুলবেন।"],
                [t("lot.review"), lang === "en" ? "Inspectors review on-device AI proposals. Every proposal requires human verification; blank reviews are never an automatic pass." : "ইন্সপেক্টর এআই প্রস্তাব যাচাই করবেন। খালি পর্যালোচনা কখনো স্বয়ংক্রিয় পাস নয়।"],
                [t("lot.decision"), lang === "en" ? "The deterministic decision engine evaluates confirmed defect counts against the configured plan limits." : "ডিসিশন ইঞ্জিন নিশ্চিত ডিফেক্ট সংখ্যা ও প্ল্যান সীমা তুলনা করে সিদ্ধান্ত প্রস্তুত করে।"],
              ].map(([label, description], index) => (
                <li className="pipeline-step is-pending" key={label}>
                  <span className="pipeline-dot">{index + 1}</span>
                  <div className="pipeline-copy">
                    <span className="pipeline-label">{label}</span>
                    <span className="pipeline-desc">{description}</span>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
