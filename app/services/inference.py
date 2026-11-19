"""Inference queue: one place that turns an uploaded image into proposals.

The HTTP handlers enqueue a row and return. A daemon worker thread claims the
job and runs the detector away from the request path, so a slow model can never
hold a capture request open. In tests and one-shot scripts ``LOTLINE_INFERENCE_MODE=sync``
runs the same code inline.

The queue is deliberately small and boring: SQLite is already the source of
truth, and the ``inference_job`` table records every state transition. Moving to
a separate worker process is a matter of calling :func:`claim_next` from that
process instead of starting the thread here.
"""
from __future__ import annotations

import os
import queue
import threading
import time

import numpy as np
from PIL import Image

from ..config import INFERENCE_MODE, ZONES
from ..core import db
from . import detector, vision
from . import review as service

_QUEUE: queue.Queue[tuple[int, int, int]] = queue.Queue()
_WORKER: threading.Thread | None = None
_LOCK = threading.Lock()
_ENQUEUE_LOCK = threading.Lock()


def mode() -> str:
    return INFERENCE_MODE


def model_name() -> str:
    return detector.MODEL_NAME if detector.available() else vision.MODEL_NAME


def enqueue(image_id: int, user_id: int) -> str:
    """Accept a scoring request. Returns ``queued``, ``ok`` or ``failed``.

    A second request while a job is queued or running is collapsed into the
    existing job instead of scoring the same image twice.
    """
    if mode() == "sync":
        return run(image_id, user_id)

    with _ENQUEUE_LOCK:
        existing = db.one(
            "SELECT id FROM inference_job WHERE image_id=? AND status IN ('queued','running')"
            " ORDER BY id DESC LIMIT 1", (image_id,))
        if existing:
            return "queued"

        job_id = db.x(
            "INSERT INTO inference_job(image_id,status,model_version,created_at) VALUES (?,?,?,?)",
            (image_id, "queued", model_name(), db.now()))
        db.audit(user_id, str(user_id), "inference.queued", "image", image_id, after={"job_id": job_id})
        _QUEUE.put((job_id, image_id, user_id))
        start()
    return "queued"


def run(image_id: int, user_id: int) -> str:
    """Score one image inline. Used by sync mode and by the worker."""
    image = db.one("SELECT * FROM image WHERE id=?", (image_id,))
    if not image:
        return "failed"
    job_id = db.x(
        "INSERT INTO inference_job(image_id,status,model_version,created_at) VALUES (?,?,?,?)",
        (image_id, "running", model_name(), db.now()))
    return _execute(job_id, image, user_id)


def process_job(job_id: int, image_id: int, user_id: int) -> str:
    """Worker entry point: mark the queued row running, then score it."""
    image = db.one("SELECT * FROM image WHERE id=?", (image_id,))
    if not image:
        db.x("UPDATE inference_job SET status='failed', error=?, finished_at=? WHERE id=?",
             ("image missing", db.now(), job_id))
        return "failed"
    db.x("UPDATE inference_job SET status='running' WHERE id=? AND status='queued'", (job_id,))
    return _execute(job_id, image, user_id)


def _execute(job_id: int, image, user_id: int) -> str:
    started = time.time()
    lot = service.lot(image["lot_id"])
    model = model_name()
    try:
        with Image.open(os.path.join(service.STORE, image["stored_name"])) as handle:
            result = detector.detect(np.array(handle.convert("RGB")))
        for proposal in result["proposals"]:
            critical = 0
            if lot:
                for zone in ZONES:
                    clause = service.map_clause(lot["buyer_id"], proposal["type"], zone, None)
                    if clause and clause["severity"] == "critical":
                        critical = 1
            db.x(
                "INSERT INTO prediction(job_id,image_id,defect_type,score,x1,y1,x2,y2,review_state,"
                "provisional_critical,created_at) VALUES (?,?,?,?,?,?,?,?,'proposed',?,?)",
                (job_id, image["id"], proposal["type"], proposal["score"], proposal["box"][0],
                 proposal["box"][1], proposal["box"][2], proposal["box"][3], critical, db.now()))
        actual_model = result.get("model", model)
        db.x("UPDATE inference_job SET status='succeeded', model_version=?, finished_at=?, latency_ms=?"
             " WHERE id=?", (actual_model, db.now(), int((time.time() - started) * 1000), job_id))
        db.audit(user_id, str(user_id), "inference.succeeded", "image", image["id"],
                 after={"proposals": len(result["proposals"]), "model": actual_model})
        return "ok"
    except Exception as exc:  # a detector failure must never block manual review
        db.x("UPDATE inference_job SET status='failed', error=?, finished_at=? WHERE id=?",
             (str(exc)[:300], db.now(), job_id))
        db.audit(user_id, str(user_id), "inference.failed", "image", image["id"],
                 after={"error": str(exc)[:200]})
        return "failed"


def _drain() -> None:
    while True:
        job_id, image_id, user_id = _QUEUE.get()
        try:
            process_job(job_id, image_id, user_id)
        except Exception:  # the job row is the error report; keep the worker alive
            try:
                db.x("UPDATE inference_job SET status='failed', error=?, finished_at=? WHERE id=?",
                     ("worker failure", db.now(), job_id))
            except Exception:
                pass
        finally:
            _QUEUE.task_done()


def start() -> None:
    """Start the background worker once. Safe to call from every request."""
    global _WORKER
    if mode() != "background":
        return
    with _LOCK:
        if _WORKER and _WORKER.is_alive():
            return
        _WORKER = threading.Thread(target=_drain, name="lotline-inference", daemon=True)
        _WORKER.start()


def stop() -> None:
    """Wait for accepted jobs to finish. Used by tests and graceful shutdown."""
    if _WORKER and _WORKER.is_alive():
        _QUEUE.join()


def wait_for_idle(timeout: float = 30.0) -> bool:
    """Wait for the queue to empty. Returns False when the timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _QUEUE.unfinished_tasks == 0:
            return True
        time.sleep(0.02)
    return False
