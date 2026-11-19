"""Single-row lookups: the lot, its active plan, and its decisions."""
from __future__ import annotations

from ...core import db


def map_clause(buyer_id: int, defect_type: str, zone: str, size_band: str | None):
    """Exact (type, zone, size_band) first, then the row with an empty size band."""
    if defect_type == "other":
        return None
    if size_band:
        row = db.one("SELECT * FROM clause_mapping WHERE buyer_id=? AND defect_type=? AND zone_code=?"
                     " AND size_band=? ORDER BY id LIMIT 1", (buyer_id, defect_type, zone, size_band))
        if row:
            return row
    return db.one("SELECT * FROM clause_mapping WHERE buyer_id=? AND defect_type=? AND zone_code=?"
                  " AND (size_band IS NULL OR size_band='') ORDER BY id LIMIT 1",
                  (buyer_id, defect_type, zone))


def lot(lot_id: int, organization_id: int | None = None):
    sql = ("SELECT l.*, b.name AS buyer_name, b.id AS buyer_id, p.name AS product_name, p.family"
           " FROM lot l JOIN buyer b ON b.id=l.buyer_id JOIN product p ON p.id=l.product_id"
           " WHERE l.id=?")
    args: tuple = (lot_id,)
    if organization_id is not None:
        sql += " AND l.organization_id=?"
        args += (organization_id,)
    return db.one(sql, args)


def active_plan(lot_id: int):
    return db.one("SELECT * FROM plan WHERE lot_id=? ORDER BY version DESC LIMIT 1", (lot_id,))


def plan_dict(row) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"], "version": row["version"], "n": row["n"], "counting_mode": row["counting_mode"],
        "critical": {"ac": row["critical_ac"], "re": row["critical_re"]},
        "major": {"ac": row["major_ac"], "re": row["major_re"]},
        "minor": {"ac": row["minor_ac"], "re": row["minor_re"]},
        "critical_aql": row["critical_aql"], "major_aql": row["major_aql"], "minor_aql": row["minor_aql"],
        "source_edition": row["source_edition"], "source_reference": row["source_reference"],
        "is_demo": bool(row["is_demo"]), "inspection_level": row["inspection_level"],
        "sampling_type": row["sampling_type"],
    }



def latest_decision(lot_id: int):
    return db.one("SELECT d.*, u.display_name AS decided_by FROM decision d JOIN app_user u ON u.id=d.created_by"
                  " WHERE d.lot_id=? ORDER BY d.sequence DESC LIMIT 1", (lot_id,))


def decision_by_id(did: int):
    return db.one("SELECT * FROM decision WHERE id=?", (did,))


def override_for(decision_id: int):
    o = db.one("SELECT o.*, u.display_name AS supervisor FROM override o JOIN app_user u ON u.id=o.supervisor_id"
               " WHERE o.decision_id=?", (decision_id,))
    if not o:
        return None
    d = dict(o)
    ap = db.one("SELECT a.*, u.display_name AS approver FROM override_approval a"
                " JOIN app_user u ON u.id=a.approver_id WHERE a.override_id=?", (o["id"],))
    d["approval"] = dict(ap) if ap else None
    d["effective"] = o["status"] == "effective" or bool(ap and ap["decision"] == "approved")
    return d
