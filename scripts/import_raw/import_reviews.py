"""Nhập đánh giá sản phẩm CÓ NGUỒN vào kho của trợ lý (var/assistant/assistant.db).

    .venv/Scripts/python -X utf8 scripts/import_raw/import_reviews.py reviews.jsonl [--dry-run] [--db PATH]

Mỗi dòng JSONL: {"product_id", "source_id", "source_url"?, "rating" (1–5)?, "body_vi", "created_at"?,
"verified_purchase"?, "author_display"?}. Kiểm: sản phẩm có trong catalog, source_id có trong `sources` của catalog,
nội dung qua luật kiểm duyệt (app/assistant/moderation.py) — đạt thì approved, nghi vấn thì pending. Trùng (cùng sản
phẩm/nguồn/nội dung) bị bỏ qua. Không bao giờ tạo hay sửa nội dung đánh giá; chỉ ẩn thông tin cá nhân.
Báo cáo ghi vào reports/data_quality/<thời điểm>_import-reviews.json.

Ngày 15/10/2026: 183 trang sản phẩm đã lưu (đợt 002) có dữ liệu cấu trúc, 0 đánh giá thật (Hanoia để aggregateRating
rỗng; Hanhsilk/SenSilk chỉ có CSS của plugin đánh giá). Chưa có tệp nào để nhập.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main(argv=None) -> int:
    from app.assistant import moderation
    from app.assistant.privacy import redact
    from app.assistant.store import Store

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--db", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    cat = json.loads(args.catalog.read_text(encoding="utf-8"))
    products = {p["id"] for p in cat["products"]}
    sources = {s["id"]: s for s in cat["sources"]}
    store = None if args.dry_run else Store(args.db)
    rows, report = [], {"accepted": 0, "pending": 0, "duplicate": 0, "rejected": []}
    for n, line in enumerate(args.file.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            report["rejected"].append({"line": n, "reason": f"JSON lỗi: {e}"})
            continue
        problems = []
        if r.get("product_id") not in products:
            problems.append("product_id không có trong catalog")
        if r.get("source_id") not in sources:
            problems.append("source_id không có trong catalog.sources")
        rating = r.get("rating")
        if rating is not None and (not isinstance(rating, int) or not 1 <= rating <= 5):
            problems.append("rating phải là số nguyên 1–5")
        body = redact(str(r.get("body_vi", "")).strip())
        if len(body) < 10:
            problems.append("nội dung quá ngắn")
        if problems:
            report["rejected"].append({"line": n, "reason": "; ".join(problems)})
            continue
        ok, reason = moderation.check(body)
        status = "approved" if ok and moderation.auto_approve_enabled() else "pending"
        review = {"product_id": r["product_id"], "origin": "imported_source", "source_id": r["source_id"],
                  "source_url": r.get("source_url") or sources[r["source_id"]].get("url"),
                  "author_display": r.get("author_display"), "rating": rating, "body_vi": body,
                  "verified_purchase": bool(r.get("verified_purchase")), "status": status,
                  "moderation_note": "nhập có nguồn; tự động: " + reason, "created_at": r.get("created_at")}
        rows.append(review)
        if store is not None and not store.add_review(review):
            report["duplicate"] += 1
            continue
        report["accepted" if status == "approved" else "pending"] += 1
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S")
    out = ROOT / "reports" / "data_quality" / f"{stamp}_import-reviews.json"
    out.write_text(json.dumps({"file": str(args.file), "dry_run": args.dry_run, **report}, ensure_ascii=False,
                              indent=1), encoding="utf-8")
    print(f"Đăng {report['accepted']}, chờ duyệt {report['pending']}, trùng {report['duplicate']}, "
          f"từ chối {len(report['rejected'])}. Báo cáo: {out}")
    return 1 if report["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
