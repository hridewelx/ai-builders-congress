from app.core import db
print("Checking lot table:")
for r in db.q("SELECT id, lot_code, lot_size, buyer_id, color, status FROM lot"):
    print(dict(r))

