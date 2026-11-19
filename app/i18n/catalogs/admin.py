"""Strings for the admin screens."""
from __future__ import annotations

CATALOG: dict[str, tuple[str, str]] = {
    "admin.title": ("Admin panel", "অ্যাডমিন প্যানেল"),
    "admin.users": ("Users", "ব্যবহারকারী"),
    "admin.audit": ("Audit", "অডিট"),
    "admin.models": ("Model versions", "মডেল সংস্করণ"),
    "admin.health": ("System health", "সিস্টেম স্বাস্থ্য"),
    "admin.clauses": ("Buyer clauses", "ক্রেতার ক্লজ"),
    "admin.new_user": ("New user", "নতুন ব্যবহারকারী"),
    "admin.display_name": ("Display name", "প্রদর্শিত নাম"),
    "admin.disable": ("Disable", "নিষ্ক্রিয়"),
    "admin.enable": ("Enable", "সক্রিয়"),
    "admin.reset": ("Reset", "রিসেট"),
    "admin.reset_full": ("Reset password", "পাসওয়ার্ড রিসেট"),
    "admin.temp_pw": ("Temporary password shown once", "অস্থায়ী পাসওয়ার্ড একবার দেখানো হয়"),
    "admin.activate": ("Activate", "সক্রিয় করুন"),
    "admin.selftest": ("Run self-test", "সেলফ-টেস্ট চালান"),
    "admin.last_admin": ("The last active Admin cannot be disabled.", "শেষ অ্যাডমিনকে নিষ্ক্রিয় করা যাবে না।"),
    "admin.clause_readonly": ("Clause lists are seeded in Version 1. Editing is Version 2.", "সংস্করণ ১-এ ক্লজ লিস্ট সিড করা। সম্পাদনা সংস্করণ ২-এ।"),
}
