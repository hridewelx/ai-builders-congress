import re
import os
import sys
from pathlib import Path

# 1. Extract DB tables
db_code = open('app/core/db.py', encoding='utf-8').read()
tables = re.findall(r'CREATE TABLE IF NOT EXISTS\s+(\w+)', db_code)
print("=== DATABASE TABLES ===")
for t in tables:
    print(t)

# 2. Extract reason codes
engine_code = open('app/domain/engine.py', encoding='utf-8').read()
reasons = re.findall(r'"([A-Z_]+)":\s*\("([A-Z]+)",\s*"([^"]+)"\)', engine_code)
print("\n=== REASON CODES ===")
for code, outcome, desc in reasons:
    print(f"{code} -> {outcome}: {desc}")

# 3. Extract Routes
print("\n=== ROUTES ===")
route_dir = Path("app/web/routes")
for p in route_dir.glob("*.py"):
    if p.name == "__init__.py": continue
    code = p.read_text(encoding="utf-8")
    matches = re.findall(r'@router\.(get|post|put|delete)\("([^"]+)"[^\)]*\)\s*\ndef\s+(\w+)', code)
    for m, path, fn in matches:
        print(f"{m.upper():6} {path:35} {p.name}:{fn}")

# 4. Check Audit log hash chain
print("\n=== AUDIT HASH CHAIN CHECK ===")
print("Is hash_chain implemented in db.py?", "hash_chain" in db_code or "prev_hash" in db_code)

# 5. Extract Roles & permissions
print("\n=== ROLES CHECK ===")
deps_code = open('app/web/deps.py', encoding='utf-8').read()
roles = re.findall(r'def require_(\w+)', deps_code)
print("Role checkers in deps.py:", roles)

