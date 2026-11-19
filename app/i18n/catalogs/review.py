"""Strings for the review screens."""
from __future__ import annotations

CATALOG: dict[str, tuple[str, str]] = {
    "rev.title": ("Image review", "ছবি পর্যালোচনা"),
    "rev.queue": ("Review queue", "পর্যালোচনা তালিকা"),
    "rev.queue_empty": ("Every view is reviewed.", "সব ভিউ পর্যালোচিত।"),
    "rev.proposals": ("Detector proposals", "ডিটেক্টর প্রস্তাব"),
    "rev.no_proposals": ("No proposals. This is not a pass — review the photo.", "কোনো প্রস্তাব নেই। এটি পাস নয় — ছবিটি দেখুন।"),
    "rev.uncalibrated": ("Uncalibrated research model. Scores are not probabilities of a defect.", "অপরিমাপিত রিসার্চ মডেল। স্কোর ত্রুটির সম্ভাবনা নয়।"),
    "rev.confirm": ("Confirm defect", "ত্রুটি নিশ্চিত"),
    "rev.reject": ("Reject proposal", "প্রস্তাব বাতিল"),
    "rev.add": ("Add a missed defect", "মিস হওয়া ত্রুটি যোগ"),
    "rev.type": ("Defect type", "ত্রুটির ধরন"),
    "rev.zone": ("Zone", "জোন"),
    "rev.size_band": ("Size band", "সাইজ ব্যান্ড"),
    "rev.clean": ("Reviewed — no defects", "পর্যালোচিত — কোনো ত্রুটি নেই"),
    "rev.retake": ("Needs retake", "আবার ছবি দরকার"),
    "rev.finish_manual": ("Finish manually (no detector)", "ম্যানুয়ালি শেষ করুন (ডিটেক্টর ছাড়া)"),
    "rev.severity_server": ("Severity comes from the buyer's clause list, not the model.", "সিরিয়িটি ক্রেতার ক্লজ লিস্ট থেকে, মডেল থেকে নয়।"),
    "rev.unmapped": ("No buyer clause for this type/zone → ESCALATE", "এই ধরন/জোনের জন্য ক্রেতার ক্লজ নেই → এসকেলেট"),
    "rev.heat": ("Model attention", "মডেলের দৃষ্টি"),
    "rev.second_review": ("Critical rejection needs a second review", "ক্রিটিক্যাল বাতিলের জন্য দ্বিতীয় পর্যালোচনা দরকার"),
}
