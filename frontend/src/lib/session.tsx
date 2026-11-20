import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage, setCsrfToken, type Bootstrap, type Lang, type ReasonEntry } from "./api";

interface SessionValue {
  data: Bootstrap;
  lang: Lang;
  user: Bootstrap["user"];
  authenticated: boolean;
  t: (key: string, values?: Record<string, string | number>) => string;
  reason: (code: string) => { title: string; text: string; next: string };
  setLang: (lang: Lang) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  demoLogin: (role: "inspector" | "supervisor" | "admin" | "guest") => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<unknown>;
}

const SessionContext = createContext<SessionValue | null>(null);

const FALLBACK: Bootstrap = {
  authenticated: false,
  lang: "en",
  user: null,
  csrf: "",
  catalog: {},
  reasons: {},
  zones: ["I", "II", "III"],
  human_classes: [],
  demo_login: false,
  is_guest: false,
  github_oauth: false,
  google_oauth: false,
  catalogs: { buyers: [], products: [] },
  model: { model: "", detector: "", model_ok: false, card: {} },
  last_selftest: null,
};

function interpolate(text: string, values?: Record<string, string | number>): string {
  if (!values) return text;
  return text.replace(/\{(\w+)\}/g, (match, key) =>
    values[key] === undefined ? match : String(values[key]),
  );
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["bootstrap"],
    queryFn: () => api.get<Bootstrap>("/api/bootstrap"),
    staleTime: Infinity,
    retry: false,
  });
  const data = query.data ?? FALLBACK;
  const [lang, setLangState] = useState<Lang>(data.lang);

  useEffect(() => {
    if (query.data) {
      setLangState(query.data.lang);
      setCsrfToken(query.data.csrf);
    }
  }, [query.data]);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const t = useCallback(
    (key: string, values?: Record<string, string | number>) => {
      const pair = data.catalog[key];
      const text = pair ? pair[lang] : key;
      return interpolate(text, values);
    },
    [data.catalog, lang],
  );

  const reason = useCallback(
    (code: string) => {
      const entry: ReasonEntry | undefined = data.reasons[code];
      if (!entry) return { title: code, text: code, next: "" };
      const [title, text, next] = entry[lang];
      return { title, text, next };
    },
    [data.reasons, lang],
  );

  const setLang = useCallback(
    async (next: Lang) => {
      await api.post(`/api/lang/${next}`);
      setLangState(next);
      await queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
    },
    [queryClient],
  );

  const adopt = useCallback(
    (next: Bootstrap) => {
      queryClient.setQueryData(["bootstrap"], next);
      setCsrfToken(next.csrf);
      setLangState(next.lang);
    },
    [queryClient],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const next = await api.post<Bootstrap>("/api/auth/login", { email, password });
      adopt(next);
      await queryClient.invalidateQueries();
    },
    [adopt, queryClient],
  );

  const demoLogin = useCallback(
    async (role: "inspector" | "supervisor" | "admin" | "guest") => {
      const next = await api.post<Bootstrap>(`/api/auth/demo/${role}`);
      adopt(next);
      await queryClient.invalidateQueries();
    },
    [adopt, queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/api/auth/logout");
    } finally {
      queryClient.clear();
      const next = await api.get<Bootstrap>("/api/bootstrap");
      adopt(next);
    }
  }, [adopt, queryClient]);

  useEffect(() => {
    const onUnauthorized = () => {
      queryClient.setQueryData(["bootstrap"], { ...FALLBACK, lang });
    };
    window.addEventListener("lotline:unauthorized", onUnauthorized);
    return () => window.removeEventListener("lotline:unauthorized", onUnauthorized);
  }, [lang, queryClient]);

  const value = useMemo<SessionValue>(
    () => ({
      data,
      lang,
      user: data.user,
      authenticated: data.authenticated,
      t,
      reason,
      setLang,
      login,
      demoLogin,
      logout,
      refresh: () => queryClient.invalidateQueries({ queryKey: ["bootstrap"] }),
    }),
    [data, lang, t, reason, setLang, login, demoLogin, logout, queryClient],
  );

  if (query.isLoading) {
    return (
      <div className="boot-screen">
        <span className="boot-mark">Lotline</span>
        <span className="boot-note">Loading workspace…</span>
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="boot-screen">
        <span className="boot-mark">Lotline</span>
        <span className="boot-note">{errorMessage(query.error)}</span>
        <button className="btn primary" onClick={() => query.refetch()}>
          Retry
        </button>
      </div>
    );
  }

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}
