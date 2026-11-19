import type { Lang } from "./api";

const BN_DIGITS = "০১২৩৪৫৬৭৮৯";

export function num(value: unknown, lang: Lang): string {
  if (value === null || value === undefined || value === "") return "—";
  const text = String(value);
  if (lang !== "bn") return text;
  return text.replace(/[0-9]/g, (digit) => BN_DIGITS[Number(digit)]);
}

export function numGrouped(value: unknown, lang: Lang): string {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (Number.isNaN(number)) return num(value, lang);
  const text = Number.isInteger(number)
    ? number.toLocaleString("en-US")
    : number.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return num(text, lang);
}

export function dtLocal(value: unknown, lang: Lang): string {
  if (!value) return "—";
  const date = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(lang === "bn" ? "bn-BD" : "en-GB", {
    day: "numeric",
    month: lang === "bn" ? "long" : "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Asia/Dhaka",
  }).format(date);
}

export function shortDate(value: unknown): string {
  if (!value) return "";
  return String(value).slice(0, 16).replace("T", " ");
}

export function pct(part: number, total: number): number {
  if (!total) return 0;
  return Math.round((part / total) * 100);
}
