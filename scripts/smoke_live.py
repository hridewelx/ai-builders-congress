"""Smoke-test a deployed Lotline demo from the outside (standard library only).

    python scripts/smoke_live.py https://lotline-demo.onrender.com
    python scripts/smoke_live.py https://lotline-demo.onrender.com --expect-detector onnx --expect-model frcnn-mnv3-v2
    python scripts/smoke_live.py http://127.0.0.1:8077 --mutate

What it proves, in the order a judge would hit it:
  1. cold start: how long until /healthz answers (Render free sleeps after 15 idle minutes)
  2. one-click demo login sets a session and a CSRF cookie
  3. dashboard and every seeded lot page, decision page and HTML report render
  4. every report.pdf is a real PDF (a font-less Linux image makes fpdf2 raise on "—", "•", "…")
  5. evidence images and the proposal heat map load, and the heat map is not slow
  6. the Bangla UI actually renders Bengali text
  7. optional: /readyz reports the detector you expect, /how names the model you expect
  8. optional (--mutate): a Recompute POST goes through CSRF and returns a reason code.
     This appends a decision row to the live demo, so it is off by default.

Exit code 0 = no FAIL (WARN is allowed), 1 = at least one FAIL.
"""
from __future__ import annotations

import argparse
import http.client
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

BENGALI = re.compile(r"[ঀ-৿]{3,}")
REASON = re.compile(r"\b(?:ACCEPT|REJECT|ESCALATE|HOLD)_[A-Z_]+\b")


@dataclass
class Resp:
    status: int
    ctype: str
    body: bytes
    ms: float
    error: str = ""

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Client:
    def __init__(self, base: str, timeout: float):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", "lotline-smoke/1.0")]

    def cookie(self, name: str) -> str | None:
        for item in self.jar:
            if item.name == name:
                return item.value
        return None

    def get(self, path: str) -> Resp:
        return self._open(urllib.request.Request(self.base + path))

    def post(self, path: str, fields: dict[str, str]) -> Resp:
        data = urllib.parse.urlencode(fields).encode()
        request = urllib.request.Request(self.base + path, data=data, method="POST",
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
        return self._open(request)

    def _open(self, request: urllib.request.Request) -> Resp:
        started = time.perf_counter()
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body, status, ctype = response.read(), response.status, response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:  # 4xx / 5xx still carry a body
            body, status, ctype = exc.read(), exc.code, exc.headers.get("Content-Type", "")
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:  # DNS, TLS, reset, timeout
            return Resp(0, "", b"", (time.perf_counter() - started) * 1000, error=repr(exc)[:120])
        return Resp(status, ctype, body, (time.perf_counter() - started) * 1000)


@dataclass
class Report:
    rows: list[tuple[str, str, str, float | None, str]] = field(default_factory=list)

    def add(self, level: str, name: str, detail: str = "", ms: float | None = None) -> None:
        self.rows.append((level, name, detail, ms, ""))
        timing = f"{ms:8.0f} ms" if ms is not None else " " * 11
        print(f"{level:4s} {name:34s} {timing}  {detail}", flush=True)

    def check(self, ok: bool, name: str, detail: str = "", ms: float | None = None, warn: bool = False) -> bool:
        self.add("PASS" if ok else ("WARN" if warn else "FAIL"), name, detail, ms)
        return ok

    @property
    def failures(self) -> int:
        return sum(1 for row in self.rows if row[0] == "FAIL")

    @property
    def warnings(self) -> int:
        return sum(1 for row in self.rows if row[0] == "WARN")


def wait_ready(client: Client, seconds: int) -> tuple[bool, float, int]:
    """Poll /healthz until it answers 200; return (ready, elapsed seconds, attempts)."""
    started = time.perf_counter()
    attempts = 0
    while True:
        attempts += 1
        response = client.get("/healthz")
        if response.status == 200:
            return True, time.perf_counter() - started, attempts
        if time.perf_counter() - started > seconds:
            return False, time.perf_counter() - started, attempts
        time.sleep(5)


def run(args: argparse.Namespace) -> int:
    client = Client(args.url, args.timeout)
    report = Report()
    ids = [int(part) for part in args.lots.split(",") if part.strip()]

    # 1. cold start ----------------------------------------------------------
    ready, elapsed, attempts = wait_ready(client, args.wait)
    report.check(ready, "cold start /healthz", f"{elapsed:.1f} s, {attempts} attempt(s)", elapsed * 1000)
    if not ready:
        print("\nService never became healthy; stopping.")
        return 1
    report.check(elapsed <= args.cold_warn, "cold start under budget",
                 f"budget {args.cold_warn:.0f} s (a judge will not wait longer)", warn=True)

    ready_resp = client.get("/readyz")
    detail = ready_resp.text[:140].replace("\n", " ")
    report.check(ready_resp.status == 200, "/readyz", detail, ready_resp.ms)
    if args.expect_detector:
        try:
            reported = json.loads(ready_resp.text).get("detector")
        except ValueError:
            reported = None
        report.check(reported == args.expect_detector, f"detector is {args.expect_detector}",
                     f"/readyz says {reported!r}")

    # 2. demo login ----------------------------------------------------------
    login = client.get("/demo/inspector")
    csrf = client.cookie("ll_csrf")
    report.check(login.status == 200 and csrf is not None, "one-click login (inspector)",
                 f"status {login.status}, csrf cookie {'set' if csrf else 'MISSING'}", login.ms)

    # 3. dashboard + lots ----------------------------------------------------
    dashboard = client.get("/")
    report.check(dashboard.status == 200 and args.lot_prefix in dashboard.text, "dashboard lists seeded lots",
                 f"status {dashboard.status}, '{args.lot_prefix}' {'found' if args.lot_prefix in dashboard.text else 'NOT found'}",
                 dashboard.ms)
    for lot in ids:
        for suffix, label in (("", "lot"), ("/decision", "decision"), ("/report", "report html")):
            response = client.get(f"/lots/{lot}{suffix}")
            report.check(response.status == 200, f"/lots/{lot}{suffix or ''} ({label})",
                         f"status {response.status}", response.ms)

    # 4. PDFs ----------------------------------------------------------------
    for lot in ids:
        response = client.get(f"/lots/{lot}/report.pdf")
        is_pdf = response.status == 200 and "pdf" in response.ctype.lower() and response.body.startswith(b"%PDF")
        complete = b"%%EOF" in response.body[-64:]  # a truncated file has no end marker
        note = f"status {response.status}, {len(response.body)} bytes"
        if response.status >= 500:
            note += "  <- server error: check fonts / non-Latin-1 characters in report.py"
        elif is_pdf and not complete:
            note += "  <- PDF has no %%EOF marker (truncated?)"
        report.check(is_pdf and complete, f"/lots/{lot}/report.pdf", note, response.ms)

    # 5. images + heat map ---------------------------------------------------
    for image in [int(part) for part in args.images.split(",") if part.strip()]:
        raw = client.get(f"/images/{image}")
        report.check(raw.status == 200 and raw.body[:2] == b"\xff\xd8", f"/images/{image}",
                     f"status {raw.status}, {len(raw.body)} bytes", raw.ms)
        heat = client.get(f"/images/{image}/heat")
        report.check(heat.status == 200 and heat.body[:2] == b"\xff\xd8", f"/images/{image}/heat",
                     f"status {heat.status}", heat.ms)
        report.check(heat.ms <= args.slow_ms, f"heat map under {args.slow_ms} ms",
                     "this route re-runs detection on every request", warn=True)

    # 6. model page ----------------------------------------------------------
    how = client.get("/how")
    report.check(how.status == 200, "/how (model card page)", f"status {how.status}", how.ms)
    if args.expect_model:
        report.check(args.expect_model in how.text, f"/how names {args.expect_model}",
                     "found" if args.expect_model in how.text else "NOT found on the page")

    # 7. optional state-changing check --------------------------------------
    if args.mutate:
        response = client.post(f"/lots/{args.mutate_lot}/decisions", {"csrf": csrf or "", "note": "smoke test"})
        codes = sorted(set(REASON.findall(response.text)))
        report.check(response.status == 200 and bool(codes), f"Recompute lot {args.mutate_lot}",
                     f"status {response.status}, reason codes {codes[:3]}", response.ms)

    # 8. Bangla --------------------------------------------------------------
    first = ids[0] if ids else 1
    client.get("/lang/bn?next=" + urllib.parse.quote(f"/lots/{first}"))
    bangla = client.get(f"/lots/{first}")
    report.check(bangla.status == 200 and bool(BENGALI.search(bangla.text)), "Bangla UI renders Bengali text",
                 f"status {bangla.status}", bangla.ms)
    client.get("/lang/en?next=/")

    print(f"\n{report.failures} failure(s), {report.warnings} warning(s)")
    return 1 if report.failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="base URL, e.g. https://lotline-demo.onrender.com")
    parser.add_argument("--wait", type=int, default=300, help="seconds to wait for /healthz (default 300)")
    parser.add_argument("--cold-warn", type=float, default=60, help="warn when the first healthy answer takes longer (s)")
    parser.add_argument("--timeout", type=float, default=60, help="per-request timeout in seconds")
    parser.add_argument("--lots", default="1,2,3,4,5,6", help="seeded lot ids to visit")
    parser.add_argument("--images", default="1", help="evidence image ids to fetch")
    parser.add_argument("--lot-prefix", default="LT-2026", help="text the dashboard must contain")
    parser.add_argument("--slow-ms", type=int, default=3000, help="warn when the heat map takes longer")
    parser.add_argument("--expect-detector", choices=["onnx", "numpy"], help="require /readyz to report this backend")
    parser.add_argument("--expect-model", help="require /how to mention this model name")
    parser.add_argument("--mutate", action="store_true", help="also POST a Recompute (appends a decision row)")
    parser.add_argument("--mutate-lot", type=int, default=6)
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
