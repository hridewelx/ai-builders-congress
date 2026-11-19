from starlette.requests import Request
from app.web.pages import ctx, templates
from app.web.stats import demo_stats, load_model_card

user_admin = {"id": 1, "role": "admin", "display_name": "Nusrat Jahan", "email": "nusrat@lotline.demo"}
card = load_model_card()
stats = demo_stats()

for lang in ["bn", "en"]:
    req = Request({"type": "http", "method": "GET", "path": "/how", "headers": [(b"cookie", f"ll_lang={lang}".encode())], "query_string": b""})
    c = ctx(req, active="how", user=user_admin, card=card, stats=stats)
    html = templates.TemplateResponse(req, "how.html", c).body.decode("utf-8")
    print(f"=== Rendered {lang} successfully (length: {len(html)}) ===")
    assert "Lotline" in html
    assert "data-copy-hash" in html
    assert "caption" in html
    assert "how-glossary" in html
    assert "how-pipeline-grid" in html
    assert "topology-box" in html
    if lang == "bn":
      assert "ডেমো ডেটার সারসংক্ষেপ" in html
      assert "ডিজাইন নীতি" in html
      assert "ম্যাপ করা হয়নি এমন ক্রেতা ক্লজ" in html
      assert "স্ট্যান্ডার্ডের নমুনা-সারণি নিজে বানিয়ে দেখানো হয়নি" in html
      assert "সেলফ-টেস্ট সফল" in html
      assert "১২টি স্বয়ংক্রিয় টেস্টে যাচাইকৃত" in html
    else:
      assert "Demo data summary" in html
      assert "Design principles" in html
      assert "Verified across 12 automated unit tests" in html

print("All assertion checks passed for both bn and en!")

