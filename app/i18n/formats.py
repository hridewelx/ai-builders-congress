"""Language-aware number and date formatting for the Bangla/English UI."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = ("জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
             "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর")
EN_MONTHS = ("January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December")
DHAKA_TZ = timezone(timedelta(hours=6))  # Asia/Dhaka has no daylight saving time.


def format_num(val: object, lang: str = "en") -> str:
    """Format integers, floats, and numeric strings using the target language's numerals."""
    if val is None or val == "":
        return "—"
    s = str(val)
    if lang == "bn":
        return s.translate(BN_DIGITS)
    return s


def format_grouped_num(val: object, lang: str = "en") -> str:
    """Format a number with thousands separators, then localise its digits."""
    if val is None or val == "":
        return "—"
    try:
        s = f"{int(val):,}"
    except (TypeError, ValueError):
        try:
            s = f"{float(val):,.2f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            s = str(val)
    return format_num(s, lang)


def format_datetime(val: object, lang: str = "en") -> str:
    """Render a UTC timestamp in Asia/Dhaka, using the language's numerals and month names."""
    if val is None or val == "":
        return "—"
    if isinstance(val, datetime):
        dt = val
    else:
        text = str(val).strip()
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
        except ValueError:
            return str(val)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(DHAKA_TZ)
    months = BN_MONTHS if lang == "bn" else EN_MONTHS
    day = format_num(dt.day, lang)
    year = format_num(dt.year, lang)
    hour = format_num(dt.hour % 12 or 12, lang)
    minute = format_num(f"{dt.minute:02d}", lang)
    suffix = "AM" if dt.hour < 12 else "PM"
    return f"{day} {months[dt.month - 1]} {year}, {hour}:{minute} {suffix}"
