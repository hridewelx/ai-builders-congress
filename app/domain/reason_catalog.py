"""Canonical reason-code explanations shown in the UI and the report.

The deterministic engine owns the codes and the outcome text. This module owns
the plain-language title, condition and next step, in both UI languages, so the
React client and the PDF renderer read the same words.
"""
from __future__ import annotations

# code: {en: (title, condition, next), bn: (title, condition, next)}
REASON_CATALOG: dict[str, dict[str, tuple[str, str, str]]] = {
    "HOLD_PLAN_MISSING": {
        "en": ("Plan missing",
               "The lot has no saved, confirmed sampling plan.",
               "A Supervisor enters the plan."),
        "bn": ("প্ল্যান নেই",
               "লটে কোনো সংরক্ষিত, নিশ্চিত স্যাম্পলিং প্ল্যান নেই।",
               "সুপারভাইজার প্ল্যান দেবেন।"),
    },
    "HOLD_PLAN_INVALID": {
        "en": ("Plan invalid",
               "The plan is incomplete or breaks the single-sampling rule: n is absent or below 1, "
               "a class has Re not equal to Ac + 1, the counting mode is unset, or a class limit is missing.",
               "A Supervisor enters a valid plan version."),
        "bn": ("প্ল্যান অবৈধ",
               "প্ল্যান অসম্পূর্ণ অথবা সিঙ্গেল-স্যাম্পলিং নিয়ম ভাঙে: n নেই বা ১-এর কম, কোনো শ্রেণিতে "
               "Re = Ac + 1 নয়, গণনার পদ্ধতি সেট নয়, বা কোনো শ্রেণির সীমা নেই।",
               "সুপারভাইজার একটি বৈধ প্ল্যান সংস্করণ দেবেন।"),
    },
    "REJECT_CRITICAL_NONVISUAL_FAILED": {
        "en": ("Critical non-visual check failed",
               "The recorded critical non-visual check failed, regardless of how complete the sample is.",
               "Not overridable (OV-10, PROPOSED). The Supervisor re-records the check after a real re-check and recomputes."),
        "bn": ("ক্রিটিক্যাল নন-ভিজ্যুয়াল চেক ব্যর্থ",
               "নমুনা যতটাই সম্পূর্ণ হোক, রেকর্ড করা ক্রিটিক্যাল নন-ভিজ্যুয়াল চেক ব্যর্থ হয়েছে।",
               "ওভাররাইড করা যায় না (OV-10, প্রস্তাবিত)। সুপারভাইজার বাস্তবে আবার যাচাই করে চেক রেকর্ড করে পুনরায় গণনা করবেন।"),
    },
    "REJECT_LIMIT_REACHED": {
        "en": ("Rejection limit reached",
               "The sample is complete, reviewed and verified, and at least one class count is at or above its Re.",
               "No workflow action. The plan has been applied to this sample."),
        "bn": ("রিজেকশন সীমায় পৌঁছেছে",
               "নমুনা সম্পূর্ণ, পর্যালোচিত ও যাচাইকৃত, এবং অন্তত একটি শ্রেণির গণনা তার Re-তে বা তার উপরে।",
               "কোনো কর্মপ্রবাহ নেই। এই নমুনায় প্ল্যান প্রয়োগ হয়েছে।"),
    },
    "ESCALATE_CRITICAL_UNREVIEWED": {
        "en": ("Critical proposal unanswered",
               "A proposal on an included image routes to a critical clause, or has no clause so critical cannot be excluded, and no human has resolved it.",
               "The reviewer answers the proposal."),
        "bn": ("ক্রিটিক্যাল প্রস্তাবের উত্তর নেই",
               "অন্তর্ভুক্ত ছবির একটি প্রস্তাব ক্রিটিক্যাল ক্লজে যায়, অথবা ক্লজ নেই তাই ক্রিটিক্যাল বাদ দেওয়া যায় না, এবং মানুষ এটি নিষ্পত্তি করেনি।",
               "পর্যালোচক প্রস্তাবের উত্তর দেবেন।"),
    },
    "ESCALATE_UNMAPPED_CLAUSE": {
        "en": ("No buyer clause",
               "A confirmed defect has no mapped buyer clause, including type other, or a confirmed human type outside the trained list has no clause.",
               "A Supervisor maps the clause, then the decision is recomputed."),
        "bn": ("ক্রেতার ক্লজ নেই",
               "নিশ্চিত ত্রুটির জন্য ক্রেতার ক্লজ ম্যাপ করা নেই, যার মধ্যে other ধরন অন্তর্ভুক্ত, অথবা প্রশিক্ষিত তালিকার বাইরের নিশ্চিত ধরনের ক্লজ নেই।",
               "সুপারভাইজার ক্লজ ম্যাপ করবেন, তারপর সিদ্ধান্ত পুনরায় গণনা হবে।"),
    },
    "ESCALATE_CRITICAL_REJECTION_UNCONFIRMED": {
        "en": ("Critical rejection needs a second review",
               "A reviewer rejected a proposal that routes to a critical clause and the second review is still pending.",
               "A Supervisor completes the second review."),
        "bn": ("ক্রিটিক্যাল বাতিলের দ্বিতীয় পর্যালোচনা দরকার",
               "পর্যালোচক ক্রিটিক্যাল ক্লজে যাওয়া একটি প্রস্তাব বাতিল করেছেন এবং দ্বিতীয় পর্যালোচনা এখনো বাকি।",
               "সুপারভাইজার দ্বিতীয় পর্যালোচনা সম্পূর্ণ করবেন।"),
    },
    "ESCALATE_SECOND_OPINION_REQUESTED": {
        "en": ("Second opinion requested",
               "The reviewer asked for a second opinion on a possible critical, or a confirmed-type change touches a critical mapping, or a manually added critical defect has no confirmed critical proposal on that image.",
               "A Supervisor completes the second review."),
        "bn": ("দ্বিতীয় মত চাওয়া হয়েছে",
               "পর্যালোচক সম্ভাব্য ক্রিটিক্যালে দ্বিতীয় মত চেয়েছেন, অথবা নিশ্চিত ধরনের পরিবর্তন ক্রিটিক্যাল ম্যাপিংয়ে লাগে, অথবা হাতে যোগ করা ক্রিটিক্যাল ত্রুটির বিপরীতে ওই ছবিতে নিশ্চিত ক্রিটিক্যাল প্রস্তাব নেই।",
               "সুপারভাইজার দ্বিতীয় পর্যালোচনা সম্পূর্ণ করবেন।"),
    },
    "HOLD_UNITS_MISSING": {
        "en": ("Garments missing",
               "Fewer sample units than min(n, lot size), or a unit lacks its required image.",
               "Register and photograph the missing units."),
        "bn": ("গার্মেন্টস বাকি",
               "min(n, লট সাইজ)-এর চেয়ে কম নমুনা ইউনিট, অথবা একটি ইউনিটের আবশ্যক ছবি নেই।",
               "বাকি ইউনিট নিবন্ধন করে ছবি তুলুন।"),
    },
    "HOLD_VIEWS_PENDING": {
        "en": ("Views pending",
               "A required view is not reviewed: no current image, no review, an unanswered proposal, a live inference job, a failed or never-run inference without manual review, or a retake requested.",
               "Upload, review, or finish the view manually. Manual review is never blocked."),
        "bn": ("ভিউ বাকি",
               "একটি আবশ্যক ভিউ পর্যালোচিত নয়: বর্তমান ছবি নেই, পর্যালোচনা নেই, প্রস্তাবের উত্তর নেই, ইনফারেন্স চলছে, ব্যর্থ বা কখনো না-চালানো ইনফারেন্সে ম্যানুয়াল পর্যালোচনা নেই, অথবা পুনরায় ছবি চাওয়া হয়েছে।",
               "ছবি আপলোড করুন, পর্যালোচনা করুন, বা ম্যানুয়ালি ভিউ শেষ করুন। ম্যানুয়াল পর্যালোচনা কখনো আটকায় না।"),
    },
    "HOLD_CRITICAL_NONVISUAL_PENDING": {
        "en": ("Critical non-visual check pending",
               "The critical non-visual status is still pending. It blocks ACCEPT but not REJECT.",
               "A Supervisor records the check."),
        "bn": ("ক্রিটিক্যাল নন-ভিজ্যুয়াল চেক বাকি",
               "ক্রিটিক্যাল নন-ভিজ্যুয়াল অবস্থা এখনো বাকি। এটি ACCEPT আটকায়, REJECT নয়।",
               "সুপারভাইজার চেক রেকর্ড করবেন।"),
    },
    "HOLD_VIEW_STATE_INCONSISTENT": {
        "en": ("View state inconsistent",
               "The review state of a current view contradicts its confirmed defects.",
               "The reviewer corrects the view."),
        "bn": ("ভিউ অবস্থা অসঙ্গত",
               "বর্তমান ভিউয়ের পর্যালোচনা অবস্থা তার নিশ্চিত ত্রুটির সঙ্গে মিলছে না।",
               "পর্যালোচক ভিউটি ঠিক করবেন।"),
    },
    "HOLD_EVIDENCE_INTEGRITY": {
        "en": ("Evidence integrity failure",
               "An included image file is missing or fails its size or SHA-256 check.",
               "Restore the file from backup or retake the photo."),
        "bn": ("প্রমাণ অখণ্ডতা ব্যর্থ",
               "অন্তর্ভুক্ত ছবির ফাইল অনুপস্থিত অথবা আকার বা SHA-256 যাচাই ব্যর্থ।",
               "ব্যাকআপ থেকে ফাইল ফিরিয়ে আনুন বা আবার ছবি তুলুন।"),
    },
    "HOLD_COMPUTE_ERROR": {
        "en": ("Compute error",
               "A technical error stopped verification or computation, but the database could still record the decision row.",
               "Retry the computation."),
        "bn": ("গণনা ত্রুটি",
               "প্রযুক্তিগত ত্রুটি যাচাই বা গণনা থামিয়েছে, তবে ডেটাবেস সিদ্ধান্তের সারি রেকর্ড করতে পেরেছে।",
               "গণনা আবার চালান।"),
    },
    "ACCEPT_PLAN_MET": {
        "en": ("Plan met",
               "Every class count is at or below Ac, and the critical non-visual check is done or not required.",
               "No workflow action. This is a statistical inference, not proof the lot is defect-free."),
        "bn": ("প্ল্যান পূরণ",
               "প্রতিটি শ্রেণির গণনা Ac-তে বা তার নিচে, এবং ক্রিটিক্যাল নন-ভিজ্যুয়াল চেক সম্পন্ন বা প্রয়োজন নেই।",
               "কোনো কর্মপ্রবাহ নেই। এটি পরিসংখ্যানগত অনুমান, লট ত্রুটিমুক্ত হওয়ার প্রমাণ নয়।"),
    },
}
