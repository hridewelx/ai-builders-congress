# VERSIONS — what actually ships

Every dependency is pinned to an exact version in `requirements.txt`. This file
records what those pins are and why; it is not a second source of truth.

**Last verified:** 19 November 2026 against Python 3.14.6 locally and Python 3.12
in the container and in CI.

## Runtime (the demo)

| Component | Pin | Licence | Notes |
|---|---|---|---|
| Python | 3.12 in the image, 3.14 locally | PSF-2.0 | No 3.12-only syntax; both verified |
| FastAPI | `0.163.2` | MIT | — |
| Uvicorn | `0.51.0` | BSD-3-Clause | Single process, `--proxy-headers` behind a proxy |
| Jinja2 | `3.1.6` | BSD-3-Clause | Server-rendered only |
| python-multipart | `0.0.32` | Apache-2.0 | Upload parsing |
| argon2-cffi | `25.1.0` | MIT | Password hashing (Argon2id) |
| fpdf2 | `2.9.0` | LGPL-3.0 | PDF only; no fonts shipped, system DejaVu or ASCII fallback |
| Pillow | `12.2.0` | MIT-CMU | Image decode, EXIF rotation, thumbnails |
| numpy | `2.5.0` | BSD-3-Clause | The fallback detector, and the ONNX input tensor |
| onnxruntime | `1.32.0` | MIT | Optional; the trained detector loads only if the artifact is present |
| pytest | `9.1.1` | MIT | Tests only |
| httpx | `0.28.1` | BSD-3-Clause | Test client only |
| SQLite | stdlib | Public domain | WAL mode, single writer |

## Training only (never in the runtime image)

| Component | Pin | Licence | Notes |
|---|---|---|---|
| torch / torchvision | `2.11.0+cu128` / `0.26.0+cu128` | BSD-3-Clause | `requirements-ml.txt`, GPU box only |
| onnx / onnxscript | `1.23.2` / current | Apache-2.0 / MIT | Export path |

## Frontend

| Component | Version | Licence | Notes |
|---|---|---|---|
| Templates | — | project | Server-rendered; no build step |
| `static/app.css`, `static/app.js` | — | project | Hand-written; no framework |
| Inter | v4 woff2 subset | OFL-1.1 | Self-hosted in `static/fonts/`; no CDN |
| Icons | inline SVG paths | ISC (Lucide) | Committed as a Jinja macro; no icon font |

## Explicitly not used

- React, Vite, TypeScript, Tailwind, any npm runtime bundle.
- Any CDN, analytics, external font, or third-party script.
- `localStorage` / `sessionStorage` for tokens or sensitive data.
