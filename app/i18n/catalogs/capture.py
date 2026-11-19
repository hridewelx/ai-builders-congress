"""Strings for the capture screens."""
from __future__ import annotations

CATALOG: dict[str, tuple[str, str]] = {
    "cap.title": ("Capture garment photos", "গার্মেন্টসের ছবি তুলুন"),
    "cap.guidance": ("Keep the garment panel inside the frame.", "গার্মেন্টসের প্যানেল ফ্রেমের মধ্যে রাখুন।"),
    "cap.side": ("Side", "দিক"),
    "cap.front": ("Front", "সামনে"),
    "cap.back": ("Back", "পিছনে"),
    "cap.detail": ("Detail", "বিস্তারিত"),
    "cap.upload": ("Upload photo", "ছবি আপলোড"),
    "cap.replace": ("Replace photo", "ছবি পরিবর্তন"),
    "cap.infer": ("Run detector", "ডিটেক্টর চালান"),
    "cap.not_inferred": ("Not inferred — manual review available", "ইনফারেন্স হয়নি — ম্যানুয়াল পর্যালোচনা সম্ভব"),
    "cap.duplicate": ("This photo is already in the lot.", "এই ছবি লটে আগেই আছে।"),
    "cap.too_big": ("File is larger than 15 MB.", "ফাইল ১৫ মেগাবাইটের বেশি।"),
    "cap.bad_type": ("Only JPEG and PNG are accepted.", "শুধু JPEG ও PNG গ্রহণ করা হয়।"),
}
