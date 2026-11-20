"""The demo scenario: six outcomes, staged photos, a complete audit trail."""
from __future__ import annotations

import json
import os

from ...core import db
from .. import detector, vision
from .. import review as service
from .fixtures import add_buyer, add_clause, add_guest, add_lot, add_user
from .models import register_live_model
from .photos import BASE_COLORS, settle_view, upload_photo


def run(force: bool = False) -> None:
    db.init()
    if db.one("SELECT id FROM organization") and not force:
        add_guest()
        register_live_model()
        return
    if force:
        for t in ("override_approval", "override", "decision", "view_review", "prediction", "inference_job",
                  "image", "unit_view", "sample_unit", "plan", "lot", "clause_mapping", "buyer", "product",
                  "model_activation", "model_selftest", "model_version", "audit_event", "login_attempt",
                  "user_session", "app_user", "organization"):
            db.x(f"DELETE FROM {t}")
        db.reset_sequences()

    db.x("INSERT INTO organization(id,name) VALUES (1,'Demo Knitwear Ltd')")
    add_user("admin@lotline.demo", "Nadia Rahman", "admin")
    sup = add_user("supervisor@lotline.demo", "Farhan Chowdhury", "supervisor")
    add_user("lead@lotline.demo", "Ayesha Karim", "supervisor")
    insp = add_user("inspector@lotline.demo", "Rakib Hasan", "inspector")
    add_guest()
    db.x("INSERT INTO product(organization_id,name,family) VALUES (1,'Essential Crew Tee','knit — single jersey tee')")

    nordika = add_buyer("Nordika Retail", "Sweden")
    for z in ("I", "II", "III"):
        add_clause(nordika, "hole", z, "critical", f"N-4.2.{z}")
    add_clause(nordika, "oil_stain", "I", "major", "N-4.3.I")
    add_clause(nordika, "oil_stain", "II", "major", "N-4.3.II")
    add_clause(nordika, "oil_stain", "III", "minor", "N-4.3.III")
    add_clause(nordika, "needle_line", "I", "major", "N-4.4.I")
    add_clause(nordika, "needle_line", "II", "minor", "N-4.4.II")
    add_clause(nordika, "needle_line", "III", "minor", "N-4.4.III")
    add_clause(nordika, "dropped_stitch", "I", "major", "N-4.5.I")
    add_clause(nordika, "dropped_stitch", "II", "major", "N-4.5.II")
    add_clause(nordika, "dropped_stitch", "III", "minor", "N-4.5.III")
    add_clause(nordika, "skipped_stitch", "I", "major", "N-4.6.I")
    add_clause(nordika, "skipped_stitch", "II", "major", "N-4.6.II")
    add_clause(nordika, "skipped_stitch", "III", "minor", "N-4.6.III")
    add_clause(nordika, "shade_band", "I", "minor", "N-4.7.I")
    add_clause(nordika, "shade_band", "II", "minor", "N-4.7.II")

    sakura = add_buyer("Sakura Apparel", "Japan")
    for z in ("I", "II", "III"):
        add_clause(sakura, "hole", z, "critical", f"S-11.{z}")
    add_clause(sakura, "oil_stain", "I", "major", "S-12.I")      # no II or III on purpose
    add_clause(sakura, "needle_line", "I", "major", "S-13.I")
    add_clause(sakura, "skipped_stitch", "I", "major", "S-14.I")
    add_clause(sakura, "shade_band", "I", "minor", "S-15.I")

    plan8 = {"n": 8, "mode": "highest_class_only", "critical": (0, 1), "major": (1, 2), "minor": (2, 3)}

    # ---------------- Lot 1: a real rejection driven by one critical unit
    lot1 = add_lot("LT-2026-014", nordika, "Navy", 480, insp, plan8, units=8, nonvisual="done")
    units1 = db.q("SELECT * FROM sample_unit WHERE lot_id=? ORDER BY id", (lot1,))
    for i, u in enumerate(units1):
        for v in db.q("SELECT * FROM unit_view WHERE sample_unit_id=? ORDER BY id", (u["id"],)):
            defects = []
            if i == 1 and v["side"] == "front":
                defects = ["hole"]
            elif i == 4 and v["side"] == "back":
                defects = ["oil_stain"]
            elif i == 6 and v["side"] == "front":
                defects = ["needle_line"]
            img_id = upload_photo(lot1, v["id"], insp, 1000 + i * 10 + (0 if v["side"] == "front" else 1),
                                 defects, BASE_COLORS["navy"])
            if i == 1 and v["side"] == "front":
                settle_view(img_id, insp, 0, "I", as_type="hole")
            elif i == 4 and v["side"] == "back":
                settle_view(img_id, insp, 0, "II", as_type="oil_stain")
            elif i == 6 and v["side"] == "front":
                settle_view(img_id, insp, 0, "I", as_type="needle_line")
            else:
                settle_view(img_id, insp)

    # ---------------- Lot 2: a clean sample that can accept
    lot2 = add_lot("LT-2026-015", nordika, "Ecru", 320, insp, plan8, units=8, nonvisual="done")
    for i, u in enumerate(db.q("SELECT * FROM sample_unit WHERE lot_id=? ORDER BY id", (lot2,))):
        for v in db.q("SELECT * FROM unit_view WHERE sample_unit_id=? ORDER BY id", (u["id"],)):
            img_id = upload_photo(lot2, v["id"], insp, 2000 + i * 10 + (0 if v["side"] == "front" else 1),
                                 [], BASE_COLORS["ecru"])
            settle_view(img_id, insp)

    # ---------------- Lot 3: incomplete sample -> HOLD
    lot3 = add_lot("LT-2026-016", nordika, "Black", 240, insp, plan8, units=5, nonvisual="done")
    for i, u in enumerate(db.q("SELECT * FROM sample_unit WHERE lot_id=? ORDER BY id", (lot3,))):
        for v in db.q("SELECT * FROM unit_view WHERE sample_unit_id=? ORDER BY id", (u["id"],)):
            img_id = upload_photo(lot3, v["id"], insp, 3000 + i * 10 + (0 if v["side"] == "front" else 1),
                                 [], BASE_COLORS["black"])
            settle_view(img_id, insp)

    # ---------------- Lot 4: unmapped buyer clause -> ESCALATE
    plan6 = {"n": 6, "mode": "every_class", "critical": (0, 1), "major": (1, 2), "minor": (2, 3)}
    lot4 = add_lot("LT-2026-017", sakura, "Sage", 150, insp, plan6, units=6, nonvisual="done")
    for i, u in enumerate(db.q("SELECT * FROM sample_unit WHERE lot_id=? ORDER BY id", (lot4,))):
        for v in db.q("SELECT * FROM unit_view WHERE sample_unit_id=? ORDER BY id", (u["id"],)):
            defects = ["oil_stain"] if (i == 2 and v["side"] == "back") else []
            img_id = upload_photo(lot4, v["id"], insp, 4000 + i * 10 + (0 if v["side"] == "front" else 1),
                                 defects, BASE_COLORS["sage"])
            if defects:
                settle_view(img_id, insp, 0, "II", as_type="oil_stain")   # Sakura has no oil_stain clause for zone II
            else:
                settle_view(img_id, insp)

    # ---------------- Lot 5: no plan yet -> HOLD_PLAN_MISSING
    lot5 = add_lot("LT-2026-018", nordika, "Plum", 600, insp, None, units=8, nonvisual="pending")

    # ---------------- Lot 6: live demo — an open critical proposal awaits a human
    lot6 = add_lot("LT-2026-019", nordika, "Maroon", 220, insp, plan8, units=8, nonvisual="done")
    for i, u in enumerate(db.q("SELECT * FROM sample_unit WHERE lot_id=? ORDER BY id", (lot6,))):
        for v in db.q("SELECT * FROM unit_view WHERE sample_unit_id=? ORDER BY id", (u["id"],)):
            defects = ["hole"] if (i == 0 and v["side"] == "front") else []
            img_id = upload_photo(lot6, v["id"], insp, 6000 + i * 10 + (0 if v["side"] == "front" else 1),
                                 defects, BASE_COLORS["maroon"])
            if not defects:
                settle_view(img_id, insp)

    # ---------------- Lots 7-11: realistic floor lots with styles, buyers, and colors
    lot7 = add_lot("LT-2026-020", nordika, "Charcoal", 360, insp, plan8, units=4, nonvisual="done")
    lot8 = add_lot("LT-2026-021", sakura, "Olive", 240, insp, plan6, units=6, nonvisual="pending")
    lot9 = add_lot("LT-2026-022", nordika, "Indigo", 520, insp, plan8, units=8, nonvisual="done")
    lot10 = add_lot("LT-2026-023", sakura, "Oatmeal", 180, insp, plan6, units=3, nonvisual="pending")
    lot11 = add_lot("LT-2026-024", nordika, "Burgundy", 440, insp, plan8, units=8, nonvisual="done")

    # ---------------- model registry (append-only)
    ok, detail = vision.selftest()
    sha = vision.model_sha()
    db.x("INSERT INTO model_version(name,artifact_sha,classes,eval_note,created_at) VALUES (?,?,?,?,?)",
         (vision.MODEL_NAME, sha, json.dumps(list(vision.MODEL_CLASSES)),
          "Unsupervised autoencoder on local patch embeddings. Trained on synthetic clean knit patches only; "
          "no defect labels used. Evaluation is staged-image only; not factory evidence.", db.now()))
    db.x("INSERT INTO model_selftest(model_name,passed,detail,created_at) VALUES (?,?,?,?)",
         (vision.MODEL_NAME, 1 if ok else 0, detail, db.now()))
    db.x("INSERT INTO model_activation(model_name,action,actor,reason,created_at) VALUES (?,?,?,?,?)",
         (vision.MODEL_NAME, "activate", "host-operator",
          "Initial activation after a passing self-test and staged-set review.", db.now()))

    ev = vision.evaluate_staged(16)
    live = detector.available()
    card = {"model": vision.MODEL_NAME, "sha256": sha, "self_test": {"passed": ok, "detail": detail},
            "labels": "none (unsupervised)",
            "calibration": "none - anomaly scores are uncalibrated", "evaluation": ev,
            "training": "synthetic clean knit textures (procedural), no defect labels",
            "domains": "staged knit panels only", "device": "CPU, in-process, ~0.4 s/image",
            "live_model": detector.MODEL_NAME if live else "not enabled (numpy baseline)",
            "live_labels": ("supervised: BDFD9 factory fabric (CC BY 4.0) plus staged panels"
                            if live else "none"),
            "live_training": ("BDFD9 train/valid plus staged train; official test held out"
                              if live else "n/a"),
            "live_domains": detector.MODEL_DOMAIN if live else "n/a"}
    os.makedirs(os.path.join(os.path.dirname(service.STORE), "models"), exist_ok=True)
    with open(os.path.join(os.path.dirname(service.STORE), "models", "model_card.json"), "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2)
    register_live_model()

    # ---------------- first decisions
    for lot_id in (lot1, lot2, lot3, lot4, lot5, lot6, lot7, lot8, lot9, lot10, lot11):
        service.compute_decision(lot_id, sup)
    print("Seed complete: lots", [lot1, lot2, lot3, lot4, lot5, lot6, lot7, lot8, lot9, lot10, lot11])
