"""Strings for the auth screens."""
from __future__ import annotations

CATALOG: dict[str, tuple[str, str]] = {
    "login.title": ("Sign in", "সাইন ইন"),
    "login.subtitle": ("Knitwear QC, made auditable.", "নিটওয়্যার কিউসি, অডিটযোগ্য।"),
    "login.email": ("Email", "ইমেইল"),
    "login.password": ("Password", "পাসওয়ার্ড"),
    "login.failed": ("Email or password is not correct.", "ইমেইল বা পাসওয়ার্ড সঠিক নয়।"),
    "login.rl": ("Too many attempts. Try again shortly.", "অনেকবার চেষ্টা হয়েছে। কিছুক্ষণ পরে চেষ্টা করুন।"),
    "login.github": ("Continue with GitHub", "GitHub দিয়ে চালিয়ে যান"),
    "login.google": ("Continue with Google", "Google দিয়ে চালিয়ে যান"),
    "login.guest": ("Continue as guest", "অতিথি হিসেবে দেখুন"),
    "login.guest_hint": ("Read-only: browse the staged lots, review and decisions. Nothing can be changed.",
                         "শুধু পড়ার জন্য: স্টেজ করা লট, রিভিউ ও সিদ্ধান্ত দেখা যাবে। কিছুই পরিবর্তন করা যাবে না।"),
    "guest.label": ("Guest · read-only", "অতিথি · শুধু পড়া"),
    "guest.warning": ("Creating lots, uploading photos, confirming defects, and decisions are disabled for guest accounts.",
                      "অতিথি অ্যাকাউন্টে লট তৈরি, ছবি আপলোড, ডিফেক্ট নিশ্চিতকরণ ও সিদ্ধান্ত নেওয়া বন্ধ আছে।"),
    "login.or": ("or", "অথবা"),
    "login.oauth": ("Sign-in failed. Try again.", "সাইন-ইন ব্যর্থ হয়েছে। আবার চেষ্টা করুন।"),
}
