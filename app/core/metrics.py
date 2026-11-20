"""Process-local request metrics: enough to see latency and 5xx drift.

The demo has one process, so an in-memory counter is honest and needs no new
dependency. Every value is exposed at ``/metrics`` as JSON; the same snapshot is
included in the admin/health surface when an operator wants it.
"""
from __future__ import annotations

import threading
import time

_STARTED = time.time()
_LOCK = threading.Lock()
_REQUESTS = 0
_IN_FLIGHT = 0
_ERRORS_5XX = 0
_BY_STATUS: dict[str, int] = {}
_BY_METHOD: dict[str, int] = {}
_LATENCY_COUNT = 0
_LATENCY_SUM = 0.0
_LATENCY_MAX = 0.0


def observe(method: str, status: int, seconds: float) -> None:
    global _REQUESTS, _IN_FLIGHT, _ERRORS_5XX
    global _LATENCY_COUNT, _LATENCY_SUM, _LATENCY_MAX
    group = f"{status // 100}xx"
    with _LOCK:
        _REQUESTS += 1
        _BY_STATUS[group] = _BY_STATUS.get(group, 0) + 1
        _BY_METHOD[method] = _BY_METHOD.get(method, 0) + 1
        _LATENCY_COUNT += 1
        _LATENCY_SUM += seconds
        _LATENCY_MAX = max(_LATENCY_MAX, seconds)
        if status >= 500:
            _ERRORS_5XX += 1


def begin() -> None:
    global _IN_FLIGHT
    with _LOCK:
        _IN_FLIGHT += 1


def end() -> None:
    global _IN_FLIGHT
    with _LOCK:
        _IN_FLIGHT = max(0, _IN_FLIGHT - 1)


def snapshot() -> dict:
    with _LOCK:
        count = _LATENCY_COUNT
        average_ms = (_LATENCY_SUM / count * 1000) if count else 0.0
        data = {
            "uptime_seconds": round(time.time() - _STARTED, 1),
            "requests_total": _REQUESTS,
            "in_flight": _IN_FLIGHT,
            "errors_5xx": _ERRORS_5XX,
            "responses": dict(sorted(_BY_STATUS.items())),
            "methods": dict(sorted(_BY_METHOD.items())),
            "latency_ms": {
                "count": count,
                "avg": round(average_ms, 1),
                "max": round(_LATENCY_MAX * 1000, 1),
            },
        }
    # Flat aliases keep the counters easy to scrape and to assert on in tests.
    data["latency_ms_avg"] = data["latency_ms"]["avg"]
    data["status_5xx"] = data["errors_5xx"]
    return data


def reset() -> None:
    """Test helper: start each suite from zero."""
    global _REQUESTS, _IN_FLIGHT, _ERRORS_5XX
    global _LATENCY_COUNT, _LATENCY_SUM, _LATENCY_MAX
    with _LOCK:
        _REQUESTS = 0
        _IN_FLIGHT = 0
        _ERRORS_5XX = 0
        _BY_STATUS.clear()
        _BY_METHOD.clear()
        _LATENCY_COUNT = 0
        _LATENCY_SUM = 0.0
        _LATENCY_MAX = 0.0
