import sys
sys.path.insert(0, ".")
from app.core import db
from app.services import review as service

db.init()
sup = db.one("SELECT id FROM app_user WHERE role='supervisor'")
for lid in (7, 8, 9, 10, 11):
    try:
        service.compute_decision(lid, sup["id"])
    except Exception as e:
        print(f"Decision for lot {lid}: {e}")

print("Counters now:")
print(service.counters())
