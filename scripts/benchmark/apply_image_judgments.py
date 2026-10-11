"""Áp file judgment do người chấm xuất từ trang packet ảnh (prepare_image_review.py) vào benchmarks/image/manifest.json.

    .venv/Scripts/python scripts/benchmark/apply_image_judgments.py image-judgments-xxxx.json [--dry-run]

Kiểm tra trước khi ghi: catalog_sha256 của file xuất = của manifest = hash database.json hiện tại (catalog
đổi thì phải chấm lại, không chỉ thay hash); mỗi qid có trong manifest và sha256 ảnh không đổi; query đã có
judgment/independence_review khác chỉ được thay khi có --replace-judged. Sau khi gộp, chạy audit() trên bản
tạm cạnh manifest; audit `invalid` thì không ghi gì. Script không tạo nhãn hay tên người chấm: mọi giá trị
lấy nguyên từ file người chấm xuất.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_image_queries import audit  # noqa: E402
from eval_image import MANIFEST  # noqa: E402

FIELDS = ("judgment", "independence_review", "family_review")


class ApplyError(ValueError):
    pass


def merge(manifest: dict, export: dict, catalog_sha: str, replace: bool) -> tuple[dict, dict[str, int]]:
    if export.get("kind") != "image_judgment_export" or not isinstance(export.get("items"), list):
        raise ApplyError("File không phải judgment xuất từ trang chấm ảnh")
    if export.get("catalog_sha256") != manifest["catalog_sha256"]:
        raise ApplyError("catalog_sha256 của file chấm khác manifest; cần chấm lại trên catalog hiện tại")
    if manifest["catalog_sha256"] != catalog_sha:
        raise ApplyError("database.json đã đổi so với manifest; đối chiếu lại nhãn trước khi áp")
    rows = {s["qid"]: dict(s) for s in manifest["samples"]}
    stats = {"applied": 0, "unchanged": 0}
    seen = set()
    for item in export["items"]:
        qid = item.get("qid")
        if qid in seen:
            raise ApplyError(f"{qid}: xuất hiện hai lần trong file chấm")
        seen.add(qid)
        if qid not in rows:
            raise ApplyError(f"{qid}: không có trong manifest")
        row = rows[qid]
        if item.get("sha256") != row["sha256"]:
            raise ApplyError(f"{qid}: ảnh query đã đổi so với lúc tạo packet (sha256 khác)")
        extra = set(item) - {"qid", "sha256", "family_id", "source_family_id", *FIELDS}
        if extra:
            raise ApplyError(f"{qid}: trường không mong đợi {sorted(extra)}")
        changed = False
        if "family_id" in item:
            if not item.get("family_review") or not export.get("family_registry_sha256"):
                raise ApplyError(f"{qid}: đổi họ cần family_review và hash registry đã duyệt")
            if item.get("source_family_id") != row["family_id"] and item["family_id"] != row["family_id"]:
                raise ApplyError(f"{qid}: họ đã đổi từ khi tạo packet; tạo lại packet")
            if item["family_id"] != row["family_id"]:
                if row.get("family_review") is not None and not replace:
                    raise ApplyError(f"{qid}: họ đã được duyệt; dùng --replace-judged")
                row["family_id"] = item["family_id"]
                changed = True
        for field in FIELDS:
            if field not in item or item[field] == row.get(field):
                continue
            if row.get(field) is not None and not replace:
                raise ApplyError(f"{qid}: đã có {field} của {row[field]['reviewed_by']}; dùng --replace-judged")
            row[field] = item[field]
            changed = True
        stats["applied" if changed else "unchanged"] += 1
    return {**manifest, "samples": [rows[s["qid"]] for s in manifest["samples"]]}, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", type=Path)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--families", type=Path)
    ap.add_argument("--require-families", action="store_true")
    ap.add_argument("--split-plan", type=Path)
    ap.add_argument("--replace-judged", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    tmp = None
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        export = json.loads(args.export.read_text(encoding="utf-8"))
        registry_sha = export.get("family_registry_sha256")
        if registry_sha is not None:
            if args.families is None or hashlib.sha256(args.families.read_bytes()).hexdigest() != registry_sha:
                raise ApplyError("File chấm cần --families đúng hash registry của packet")
        catalog_sha = hashlib.sha256(args.catalog.read_bytes()).hexdigest()
        merged, stats = merge(manifest, export, catalog_sha, args.replace_judged)
        fd, tmp = tempfile.mkstemp(dir=args.manifest.parent, prefix=".manifest.", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
            f.write("\n")
        report = audit(Path(tmp), args.catalog, args.families, args.require_families, args.split_plan)
        if report["status"] == "invalid":
            errors = [f"{i['code']} ({i['path']})" for i in report["issues"] if i["level"] == "error"]
            raise ApplyError(f"audit sau khi gộp báo invalid: {errors[:5]}")
    except (ApplyError, OSError, json.JSONDecodeError, KeyError, TypeError) as e:
        if tmp:
            os.unlink(tmp)
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    if export.get("manifest_sha256") != hashlib.sha256(args.manifest.read_bytes()).hexdigest():
        print("Lưu ý: manifest đã thay đổi kể từ lúc tạo packet (ví dụ nhập thêm phiên); đã đối chiếu theo qid + sha256.")
    print(f"áp {stats['applied']}, không đổi {stats['unchanged']}; audit sau khi gộp: {report['status']}")
    if args.dry_run or not stats["applied"]:
        os.unlink(tmp)
        print("không ghi gì" + (" (dry-run)" if args.dry_run else ""))
        return 0
    os.replace(tmp, args.manifest)
    print(f"Đã cập nhật {args.manifest}. SHA-256 manifest: "
          f"{hashlib.sha256(args.manifest.read_bytes()).hexdigest()[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
