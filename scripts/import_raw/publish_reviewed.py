"""Chuyển sản phẩm draft đã được người duyệt sang published, qua execute_import (preview, diff, kiểm tra hash).

    .venv/Scripts/python scripts/import_raw/publish_reviewed.py --catalog-version <mới> --note "<ai/khi nào duyệt>" \
        [--internal-demo] [--exclude <product_id> ...] [--decided-by <tên>] [--dry-run]

Chỉ chạy khi người phụ trách đã xác nhận đã duyệt nguồn dữ liệu; script không tự đánh giá nội dung.
--internal-demo ghi publication_policy (mode internal_demo): validator cho phép ảnh quyền 'unknown' trên sản phẩm
published nhưng KHÔNG đổi trạng thái quyền; web hiện cảnh báo "demo nội bộ". Không dùng cho bản công khai.
Sản phẩm không qua validator (vd. thiếu tiêu chí Việt) làm cả lần chạy bị chặn: loại bằng --exclude.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def publish(current: dict, *, exclude: set[str], stamp: str, note: str, internal_demo: bool,
            decided_by: str | None) -> tuple[dict, list[str]]:
    out = copy.deepcopy(current)
    unknown = exclude - {p["id"] for p in out["products"]}
    if unknown:
        raise ValueError(f"--exclude chứa ID không có trong catalog: {sorted(unknown)}")
    if internal_demo and "publication_policy" not in out:
        out["publication_policy"] = {"mode": "internal_demo", "allow_unverified_image_rights": True,
                                     "decided_at": stamp, "decided_by": decided_by, "note": note}
    changed = []
    for product in out["products"]:
        if product["status"] != "draft" or product["id"] in exclude:
            continue
        product.update(status="published", reviewed_at=stamp, updated_at=stamp)
        changed.append(product["id"])
    return out, changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--catalog-version", required=True)
    ap.add_argument("--note", required=True, help="ai xác nhận duyệt, khi nào, phạm vi (ghi vào báo cáo/chính sách)")
    ap.add_argument("--exclude", nargs="*", default=[], help="product_id giữ draft")
    ap.add_argument("--internal-demo", action="store_true")
    ap.add_argument("--decided-by", default=None, help="tên người quyết định; bỏ trống nếu không được cung cấp")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(ROOT / "backend"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app.catalog.validation import validate_catalog
    from safe_import import digest, execute_import

    dest = args.catalog.resolve()
    original = dest.read_bytes()
    current = json.loads(original)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    conflicts = []
    try:
        out, changed = publish(current, exclude=set(args.exclude), stamp=stamp, note=args.note.strip(),
                               internal_demo=args.internal_demo, decided_by=args.decided_by)
    except ValueError as exc:
        out, changed = current, []
        conflicts.append({"code": "publish_input", "path": "$.products", "message": str(exc)})
    if out != current:
        if args.catalog_version == current["catalog_version"]:
            conflicts.append({"code": "catalog_version_required", "path": "$.catalog_version"})
        out["catalog_version"] = args.catalog_version
        out["updated_at"] = stamp
    result = validate_catalog(out, dest.parent)
    code, report = execute_import(catalog_path=dest, original=original, proposed=out, generated={},
                                 conflicts=conflicts, validation=result, dry_run=args.dry_run, root=ROOT,
                                 inputs={"note": digest(args.note.encode("utf-8")),
                                         "exclude": digest(json.dumps(sorted(args.exclude)).encode())},
                                 kind="publish")
    print(f"{len(changed)} sản phẩm → published; giữ draft: {sorted(args.exclude)}; "
          f"{len(result.errors)} lỗi, {len(result.warnings)} cảnh báo, {len(conflicts)} xung đột. Báo cáo: {report}")
    for issue in result.errors[:10]:
        print(f"  lỗi {issue.code} {issue.path}: {issue.message}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
