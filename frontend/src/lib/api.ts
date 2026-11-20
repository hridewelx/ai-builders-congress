export type Lang = "en" | "bn";

export interface CatalogPair {
  en: string;
  bn: string;
}

export interface ReasonEntry {
  en: [string, string, string];
  bn: [string, string, string];
}

export interface Bootstrap {
  authenticated: boolean;
  lang: Lang;
  user: LotlineUser | null;
  csrf: string;
  catalog: Record<string, CatalogPair>;
  reasons: Record<string, ReasonEntry>;
  zones: string[];
  human_classes: string[];
  demo_login: boolean;
  is_guest: boolean;
  github_oauth: boolean;
  catalogs: {
    buyers: Array<{ id: number; name: string; country: string }>;
    products: Array<{ id: number; name: string; family: string }>;
  };
  model: { model: string; detector: string; model_ok: boolean; card: Record<string, unknown> };
  last_selftest: Record<string, unknown> | null;
}

export interface LotlineUser {
  id: number;
  email: string;
  display_name: string;
  role: "admin" | "inspector" | "supervisor";
  status: string;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

let csrfToken = "";

export function setCsrfToken(token: string): void {
  csrfToken = token;
}

function readCookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  const method = (init.method || "GET").toUpperCase();
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    headers.set("X-CSRF-Token", csrfToken || readCookie("ll_csrf"));
  }
  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? body;
    } catch {
      // A non-JSON error body is still reported with its status.
    }
    if (response.status === 401) {
      window.dispatchEvent(new CustomEvent("lotline:unauthorized"));
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    const detail = error.detail as { errors?: Record<string, string> } | null;
    if (detail?.errors) return Object.values(detail.errors).join(" ");
  }
  return error instanceof Error ? error.message : "Request failed";
}
