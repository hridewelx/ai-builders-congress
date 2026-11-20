"""Strings for the auth screens."""
from __future__ import annotations

CATALOG: dict[str, tuple[str, str]] = {
    "login.title": ("Sign in", "সাইন ইন"),
    "login.subtitle": ("Knitwear QC, made auditable.", "নিটওয়্যার কিউসি, অডিটযোগ্য।"),
    "login.email": ("Email", "ইমেইল"),
    "login.password": ("Password", "পাসওয়ার্ড"),
    "login.submit": ("Sign in", "সাইন ইন"),
    "login.demo": ("One-click demo access", "এক ক্লিকে ডেমো"),
    "login.demo_note": ("Demo accounts are seeded. No real personal data is used.", "ডেমো অ্যাকাউন্ট তৈরি করা আছে। কোনো বাস্তব ব্যক্তিগত তথ্য নেই।"),
    "login.failed": ("Email or password is not correct.", "ইমেইল বা পাসওয়ার্ড সঠিক নয়।"),
    "login.rl": ("Too many attempts. Try again shortly.", "অনেকবার চেষ্টা হয়েছে। কিছুক্ষণ পরে চেষ্টা করুন।"),
    "login.github": ("Continue with GitHub", "GitHub দিয়ে চালিয়ে যান"),
    "login.or": ("or", "অথবা"),
    "login.oauth": ("GitHub sign-in failed. Try again.", "GitHub সাইন-ইন ব্যর্থ হয়েছে। আবার চেষ্টা করুন।"),
}
