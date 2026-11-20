"""Cloudinary service: secure backend-mediated authorization and upload workflow.

Provides:
- Signature generation for direct mobile-client upload (secrets never sent to browser).
- Server-side fallback upload via httpx.
- Offline/mock graceful fallback when credentials are not present in demo environments.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

from ..config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_FOLDER,
)


def is_configured() -> bool:
    """Return True if Cloudinary credentials are fully provided."""
    return bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)


def generate_signature(params: dict[str, Any], api_secret: str) -> str:
    """Compute Cloudinary standard SHA-1/SHA-256 signature for parameters.

    Excludes 'file', 'cloud_name', 'resource_type', 'api_key', 'signature'.
    Sorts keys alphabetically and appends the api_secret.
    """
    excluded = {"file", "cloud_name", "resource_type", "api_key", "signature"}
    sorted_items = sorted(
        (k, str(v)) for k, v in params.items() if k not in excluded and v is not None and str(v) != ""
    )
    serialized = "&".join(f"{k}={v}" for k, v in sorted_items)
    to_sign = f"{serialized}{api_secret}"
    return hashlib.sha1(to_sign.encode("utf-8")).hexdigest()


def sign_upload_params(lot_id: int, view_id: int, garment_code: str = "") -> dict[str, Any]:
    """Generate signature and authorization payload for direct mobile capture upload.

    The API secret is never returned; only the signature and public API key.
    """
    ts = int(time.time())
    folder = f"{CLOUDINARY_FOLDER}/lot_{lot_id}"
    tags = f"lot_{lot_id},view_{view_id},garment_{garment_code or 'unknown'},lotline"

    if is_configured():
        params_to_sign = {
            "folder": folder,
            "tags": tags,
            "timestamp": ts,
        }
        sig = generate_signature(params_to_sign, CLOUDINARY_API_SECRET)
        return {
            "configured": True,
            "cloud_name": CLOUDINARY_CLOUD_NAME,
            "api_key": CLOUDINARY_API_KEY,
            "timestamp": ts,
            "folder": folder,
            "tags": tags,
            "signature": sig,
            "upload_url": f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload",
        }

    # Demo/Local fallback when Cloudinary environment variables are absent
    return {
        "configured": False,
        "cloud_name": "",
        "api_key": "",
        "timestamp": ts,
        "folder": folder,
        "tags": tags,
        "signature": "local_mock_sig",
        "upload_url": f"/lots/{lot_id}/views/{view_id}/mobile-upload",
    }


async def upload_to_cloudinary(
    data: bytes,
    lot_id: int,
    view_id: int,
    filename: str = "capture.jpg",
    garment_code: str = "",
) -> dict[str, Any]:
    """Upload raw image bytes to Cloudinary via backend-mediated HTTP call."""
    if not is_configured():
        # Fallback local pseudo-cloudinary response
        sha = hashlib.sha256(data).hexdigest()
        return {
            "public_id": f"lotline_local_{sha[:16]}",
            "secure_url": f"/static/uploads/{sha[:16]}.jpg",
            "bytes": len(data),
            "format": "jpg",
            "status": "local_fallback",
        }

    import httpx

    ts = int(time.time())
    folder = f"{CLOUDINARY_FOLDER}/lot_{lot_id}"
    tags = f"lot_{lot_id},view_{view_id},garment_{garment_code or 'unknown'},lotline"
    params = {
        "folder": folder,
        "tags": tags,
        "timestamp": ts,
    }
    sig = generate_signature(params, CLOUDINARY_API_SECRET)
    upload_url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"

    form_data = {
        "api_key": CLOUDINARY_API_KEY,
        "timestamp": str(ts),
        "folder": folder,
        "tags": tags,
        "signature": sig,
    }

    files = {"file": (filename, data, "image/jpeg")}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(upload_url, data=form_data, files=files)
        resp.raise_for_status()
        res = resp.json()
        return {
            "public_id": res.get("public_id"),
            "secure_url": res.get("secure_url"),
            "width": res.get("width"),
            "height": res.get("height"),
            "bytes": res.get("bytes", len(data)),
            "format": res.get("format", "jpg"),
            "status": "cloudinary_uploaded",
        }

