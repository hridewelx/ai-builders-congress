"""Test suite for Secure HTTPS Tunnel, CSRF reverse proxy validation, and QR resolution."""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import pytest
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.lots import tunnel_status
from app.config import (
    DATA_DIR,
    TUNNEL_FILE,
    get_active_tunnel_host,
    get_active_tunnel_url,
    is_valid_tunnel_url,
)
from app.core import db, security
from app.main import SensitiveParamFilter
from app.web.deps import Denied, assert_csrf
from app.web.pages import get_public_base_url
from app.web.routes.capture import qr_code_image


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    db.init()


@pytest.fixture(autouse=True)
def cleanup_tunnel():
    """Ensure tunnel file and env vars are clean before and after each test."""
    if os.path.exists(TUNNEL_FILE):
        try:
            os.remove(TUNNEL_FILE)
        except Exception:
            pass
    old_env = os.environ.pop("PUBLIC_TUNNEL_URL", None)
    yield
    if os.path.exists(TUNNEL_FILE):
        try:
            os.remove(TUNNEL_FILE)
        except Exception:
            pass
    if old_env is not None:
        os.environ["PUBLIC_TUNNEL_URL"] = old_env
    else:
        os.environ.pop("PUBLIC_TUNNEL_URL", None)


def make_request(
    path: str = "/",
    method: str = "GET",
    token: str = "",
    csrf: str = "",
    origin: str = "",
    host: str = "localhost:8077",
    client_ip: str = "127.0.0.1",
    fwd_host: str = "",
    fwd_proto: str = "",
) -> Request:
    headers = []
    if host:
        headers.append((b"host", host.encode()))
    if origin:
        headers.append((b"origin", origin.encode()))
    if token:
        headers.append((b"cookie", f"{security.COOKIE}={token}".encode()))
    if csrf:
        headers.append((b"x-csrf-token", csrf.encode()))
    if fwd_host:
        headers.append((b"x-forwarded-host", fwd_host.encode()))
    if fwd_proto:
        headers.append((b"x-forwarded-proto", fwd_proto.encode()))

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "client": (client_ip, 50000),
        "query_string": b"",
    }
    return Request(scope)


def test_tunnel_url_validation():
    """Verify strict URL and domain validation."""
    assert is_valid_tunnel_url("https://knitwear-demo.trycloudflare.com") is True
    assert is_valid_tunnel_url("https://sub-domain-123.trycloudflare.com") is True
    assert is_valid_tunnel_url("https://custom-domain.com") is True

    # Reject non-https schemes
    assert is_valid_tunnel_url("http://knitwear-demo.trycloudflare.com") is False
    assert is_valid_tunnel_url("ftp://knitwear-demo.trycloudflare.com") is False
    assert is_valid_tunnel_url("javascript:alert(1)") is False

    # Reject invalid characters or malformed hosts
    assert is_valid_tunnel_url("https://") is False
    assert is_valid_tunnel_url("https://bad host.com") is False
    assert is_valid_tunnel_url("https://<script>") is False
    assert is_valid_tunnel_url("") is False


def test_tunnel_lifecycle_file_and_stale_cleanup():
    """Verify tunnel file read, stale age detection, and active host parsing."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. Active valid tunnel file
    with open(TUNNEL_FILE, "w", encoding="utf-8") as f:
        f.write("https://sample-test-subdomain.trycloudflare.com\n")

    assert get_active_tunnel_url() == "https://sample-test-subdomain.trycloudflare.com"
    assert get_active_tunnel_host() == "sample-test-subdomain.trycloudflare.com"

    # 2. Stale tunnel file (> 24 hours old) must be ignored
    stale_time = time.time() - 90000
    os.utime(TUNNEL_FILE, (stale_time, stale_time))
    assert get_active_tunnel_url() is None

    # 3. Clean removal
    os.remove(TUNNEL_FILE)
    assert get_active_tunnel_url() is None


def test_public_base_url_resolution_and_api():
    """Verify both React API and Jinja2 resolve identical base URLs."""
    req = make_request()

    # 1. No tunnel active -> returns LAN / host URL with is_tunnel=False
    base_url_lan, is_tunnel_lan = get_public_base_url(req)
    assert is_tunnel_lan is False
    assert base_url_lan.startswith("http://")

    status_lan = tunnel_status(req)
    assert status_lan["active"] is False
    assert status_lan["public_base_url"] == base_url_lan

    # 2. Tunnel active -> returns HTTPS tunnel URL with is_tunnel=True
    os.environ["PUBLIC_TUNNEL_URL"] = "https://active-demo.trycloudflare.com"

    base_url_tunnel, is_tunnel_tunnel = get_public_base_url(req)
    assert is_tunnel_tunnel is True
    assert base_url_tunnel == "https://active-demo.trycloudflare.com"

    status_tunnel = tunnel_status(req)
    assert status_tunnel["active"] is True
    assert status_tunnel["public_base_url"] == "https://active-demo.trycloudflare.com"


def test_qr_generation_with_tunnel_endpoint():
    """Verify /qr endpoint generates valid PNG bytes for tunnel URLs."""
    tunnel_url = "https://active-demo.trycloudflare.com/lots/3/mobile-cam?session_token=test"
    resp = qr_code_image(tunnel_url)
    assert resp.status_code == 200
    assert resp.media_type == "image/png"
    # PNG signature \x89PNG\r\n\x1a\n
    assert resp.body.startswith(b"\x89PNG\r\n\x1a\n")


def test_csrf_reverse_proxy_security():
    """Verify CSRF Origin/Host check strictly validates reverse proxy headers."""
    user = db.one("SELECT * FROM app_user WHERE role='inspector' AND status='active' LIMIT 1")
    token, csrf = security.create_session(user["id"])
    s = security.current_session(token)

    tunnel_domain = "secure-lotline.trycloudflare.com"
    os.environ["PUBLIC_TUNNEL_URL"] = f"https://{tunnel_domain}"

    # 1. Direct standard request with matching host & origin -> OK
    req1 = make_request(origin="http://localhost:8077", host="localhost:8077")
    assert_csrf(req1, s, csrf)

    # 2. Legitimate reverse-proxied request from localhost (127.0.0.1) with HTTPS tunnel -> OK
    req2 = make_request(
        origin=f"https://{tunnel_domain}",
        host="localhost:8077",
        client_ip="127.0.0.1",
        fwd_host=tunnel_domain,
        fwd_proto="https",
    )
    assert_csrf(req2, s, csrf)

    # 3. Spoofed forwarded headers from untrusted external client IP (192.168.1.50) -> REJECT 403
    req3 = make_request(
        origin=f"https://{tunnel_domain}",
        host="localhost:8077",
        client_ip="192.168.1.50",
        fwd_host=tunnel_domain,
        fwd_proto="https",
    )
    with pytest.raises(Denied) as exc:
        assert_csrf(req3, s, csrf)
    assert exc.value.status == 403

    # 4. Forwarded proto is insecure http -> REJECT 403
    req4 = make_request(
        origin=f"https://{tunnel_domain}",
        host="localhost:8077",
        client_ip="127.0.0.1",
        fwd_host=tunnel_domain,
        fwd_proto="http",
    )
    with pytest.raises(Denied) as exc:
        assert_csrf(req4, s, csrf)
    assert exc.value.status == 403

    # 5. Forwarded host does not match expected active tunnel domain -> REJECT 403
    req5 = make_request(
        origin="https://attacker-domain.com",
        host="localhost:8077",
        client_ip="127.0.0.1",
        fwd_host="attacker-domain.com",
        fwd_proto="https",
    )
    with pytest.raises(Denied) as exc:
        assert_csrf(req5, s, csrf)
    assert exc.value.status == 403


def test_session_token_log_redaction():
    """Verify SensitiveParamFilter redacts session_token from logs."""
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "GET /lots/3/mobile-cam?session_token=secret_verifier_token_abc HTTP/1.1" 200',
        args=("127.0.0.1:50000",),
        exc_info=None,
    )
    param_filter = SensitiveParamFilter()
    param_filter.filter(record)
    assert "secret_verifier_token_abc" not in record.msg
    assert "session_token=[REDACTED]" in record.msg

