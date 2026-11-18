# VERSIONS — Lotline frontend build

**Last updated:** 18 November 2026 (Phase 0)
**Rule:** every dependency is pinned to an exact version. Existing ranges are recorded as debt; they are not changed in Phase 0.

> **Plan-mode note:** staged at `C:\Users\Jitu\.opencode\plan\VERSIONS.md`; not yet in the repo. Copy to `D:\ai-builders-congress\VERSIONS.md` when the build agent starts.

## Runtime (backend — not modified)

| Component | Declared | Verified in this environment | Notes |
|---|---|---|---|
| Python | 3.11 target | 3.11.9 | `pyproject.toml` target `py311` |
| FastAPI | `0.163.2` (pinned) | **not installed** | Server cannot start until `pip install -r requirements.txt` |
| Uvicorn | `0.51.0` (pinned) | **not installed** | — |
| Jinja2 | `>=3.1` | 3.1.6 | range = existing debt; propose pin `3.1.6` |
| python-multipart | `>=0.0.9` | not verified | range = existing debt |
| argon2-cffi | `>=25.1.0` | not verified | range = existing debt |
| fpdf2 | `>=2.8` | not verified | range = existing debt |
| Pillow | `>=12.0` | 12.2.0 | range = existing debt |
| numpy | `>=2.3` | 2.4.4 | range = existing debt |
| pytest | `>=8.0` | not verified | dev only |
| httpx | `>=0.27` | 0.28.1 | dev only |
| SQLite | stdlib | Python 3.11.9 bundled | WAL mode |

## Frontend runtime

| Component | Version | License | Notes |
|---|---|---|---|
| Jinja2 templates | n/a (server-rendered) | — | No client framework, no build step |
| `static/app.css` | project file | — | Replaced in Phase 1 |
| `static/app.js` | project file | — | Vanilla JS; no dependency |
| Inter | **5.3.0** (`@fontsource/inter` package; woff2 subset) | OFL-1.1 | Self-hosted; no Google Fonts/CDN request |
| Lucide icons | **1.75.0** (`lucide-static`) | ISC | Vendor only the SVG paths used; no icon font/CDN |
| Playwright | **1.65.1** (`@playwright/test`) | Apache-2.0 | **Dev/test only**; not shipped to the browser |

## Explicitly not used

- React, React DOM, Vite, TypeScript, Tailwind CSS, shadcn/ui, Recharts, Konva, npm runtime bundles.
- Any CDN, analytics, external font, or third-party script.
- `localStorage` / `sessionStorage` for tokens or sensitive data.

## Pin policy

- New runtime assets (fonts/icons) are committed as files with the exact source version above.
- Playwright is installed only for Phase 5 verification; it is not part of the demo runtime.
- The existing `requirements.txt` ranges (Jinja2, python-multipart, argon2-cffi, fpdf2, Pillow, numpy, pytest, httpx) should be pinned to the verified versions before submission. That is a dependency-file change, not application logic; owner approval is requested because the backend is frozen.
- No dependency is added without a one-line justification in `PROGRESS.md`.

## Security notes tied to versions

- Session cookie: existing `ll_session`; Security v0.4 SES-02 asks for `__Host-` + `Secure` + `HttpOnly` + `SameSite=Strict`. Frontend cannot change the server cookie.
- CSRF: existing per-session token in forms; the server also sets a readable `ll_csrf` cookie. The new UI will not read that cookie; it will render the token into forms/meta only.
- No CSP header currently exists. A restrictive `<meta http-equiv="Content-Security-Policy">` can be added in `base.html`; header-level policies (frame-ancestors, HSTS) need backend changes.
- No request-ID middleware; error pages cannot show a real request ID.
