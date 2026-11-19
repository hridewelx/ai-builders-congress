"""Bangla text for the deterministic engine's reason codes."""
from __future__ import annotations

REASON_BN = {
    "HOLD_PLAN_MISSING": "কোনো স্যামপ্লিং প্ল্যান দেওয়া নেই।",
    "HOLD_PLAN_INVALID": "দেওয়া প্ল্যানটি বৈধ সিঙ্গেল-স্যামপ্লিং প্ল্যান নয়।",
    "REJECT_CRITICAL_NONVISUAL_FAILED": "ক্রিটিক্যাল নন-ভিজুয়াল চেক ব্যর্থ হয়েছে।",
    "REJECT_LIMIT_REACHED": "অন্তত একটি শ্রেণি তার রিজেকশন সংখ্যায় পৌঁছেছে।",
    "ESCALATE_CRITICAL_UNREVIEWED": "একটি খোলা প্রস্তাব ক্রিটিক্যাল ক্লজে যাচ্ছে।",
    "ESCALATE_UNMAPPED_CLAUSE": "নিশ্চিত ত্রুটির জন্য ক্রেতার কোনো ক্লজ ম্যাপ করা নেই।",
    "ESCALATE_CRITICAL_REJECTION_UNCONFIRMED": "বাতিল করা ক্রিটিক্যাল প্রস্তাবের দ্বিতীয় পর্যালোচনা দরকার।",
    "ESCALATE_SECOND_OPINION_REQUESTED": "পর্যালোচক দ্বিতীয় মত চেয়েছেন।",
    "HOLD_UNITS_MISSING": "প্রয়োজনীয় নমুনার চেয়ে কম গার্মেন্ট আছে।",
    "HOLD_VIEWS_PENDING": "একটি আবশ্যক ভিউ পর্যালোচনা করা হয়নি।",
    "HOLD_CRITICAL_NONVISUAL_PENDING": "ক্রিটিক্যাল নন-ভিজুয়াল চেক এখনো রেকর্ড হয়নি।",
    "HOLD_VIEW_STATE_INCONSISTENT": "ভিউয়ের অবস্থা তার নিশ্চিত ত্রুটির সঙ্গে মিলছে না।",
    "HOLD_EVIDENCE_INTEGRITY": "সংযুক্ত ছবির ফাইল অনুপস্থিত বা পরিবর্তিত।",
    "HOLD_COMPUTE_ERROR": "কারিগরি ত্রুটির কারণে যাচাই বন্ধ হয়েছে।",
    "ACCEPT_PLAN_MET": "প্রতিটি শ্রেণি তার গ্রহণযোগ্য সংখ্যার মধ্যে আছে।",
}
