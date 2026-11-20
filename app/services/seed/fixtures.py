"""Users, buyers, clause mappings, lots and sample units for the demo."""
from __future__ import annotations

from ...core import db, security
from .. import review as service

DEMO_PASSWORD = "QualityFloor2026!"

def add_user(email, name, role, must_change=0, password=DEMO_PASSWORD):
    return db.x("INSERT INTO app_user(organization_id,email,display_name,role,password_hash,status,must_change,created_at)"
                " VALUES (1,?,?,?,?,'active',?,?)",
                (email, name, role, security.hash_password(password), must_change, db.now()))


def add_guest():
    """A read-only account for visitors: no lot, no write, no known password."""
    import secrets
    if db.one("SELECT id FROM app_user WHERE email=?", ("guest@lotline.demo",)):
        return None
    return add_user("guest@lotline.demo", "Guest", "inspector", password=secrets.token_urlsafe(32))


def add_buyer(name, country):
    return db.x("INSERT INTO buyer(organization_id,name,country) VALUES (1,?,?)", (name, country))


def add_clause(buyer_id, dtype, zone, severity, ref, band=None):
    return db.x("INSERT INTO clause_mapping(buyer_id,defect_type,zone_code,size_band,severity,clause_ref)"
                " VALUES (?,?,?,?,?,?)", (buyer_id, dtype, zone, band, severity, ref))


def provisional_critical(buyer_id, dtype):
    for z in ("I", "II", "III"):
        c = service.map_clause(buyer_id, dtype, z, None)
        if c and c["severity"] == "critical":
            return 1
    return 0



def _name(uid: int) -> str:
    row = db.one("SELECT display_name FROM app_user WHERE id=?", (uid,))
    return row["display_name"] if row else str(uid)



def add_lot(code, buyer_id, color, size, creator, plan=None, units=0, nonvisual="pending", selection="self-declared random", product_id=None):
    product_id = product_id or db.one("SELECT id FROM product ORDER BY id LIMIT 1")["id"]
    lot_id = db.x("INSERT INTO lot(organization_id,lot_code,product_id,buyer_id,color,lot_size,status,"
                  "critical_nonvisual_status,selection_method,created_by,created_at)"
                  " VALUES (1,?,?,?,?,?, 'open', ?,?,?,?)",
                  (code, product_id, buyer_id, color, size, nonvisual, selection, creator, db.now()))
    if plan:
        db.x("INSERT INTO plan(lot_id,version,n,counting_mode,critical_aql,critical_ac,critical_re,"
             "major_aql,major_ac,major_re,minor_aql,minor_ac,minor_re,inspection_level,sampling_type,"
             "source_edition,source_reference,is_demo,entered_by,created_at)"
             " VALUES (?,1,?,?,?,?,?,?,?,?,?,?,?,'II','single',?,?,1,?,?)",
             (lot_id, plan["n"], plan["mode"], 0.0, plan["critical"][0], plan["critical"][1],
              2.5, plan["major"][0], plan["major"][1], 4.0, plan["minor"][0], plan["minor"][1],
              "DEMO PLAN — not from any standard", "Staged demo plan (invented placeholders)", creator, db.now()))
    for i in range(1, units + 1):
        uid = db.x("INSERT INTO sample_unit(lot_id,garment_code,created_at) VALUES (?,?,?)",
                   (lot_id, f"G-{i:02d}", db.now()))
        for side in ("front", "back"):
            db.x("INSERT INTO unit_view(sample_unit_id,side,required) VALUES (?,?,1)", (uid, side))
    db.audit(creator, _name(creator), "lot.created", "lot", lot_id, after={"lot_code": code, "lot_size": size})
    return lot_id
