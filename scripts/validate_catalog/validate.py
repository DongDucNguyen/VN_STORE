"""Kiểm tra database.json và ghi báo cáo chất lượng dữ liệu.

Cách chạy (từ thư mục gốc dự án):
    .venv/Scripts/python scripts/validate_catalog/validate.py
    .venv/Scripts/python scripts/validate_catalog/validate.py --catalog path/to/catalog.json --no-report

Mã thoát 1 nếu có lỗi (error); cảnh báo (warning) không làm hỏng lệnh.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.catalog.validation import quality_report, validate_catalog  # noqa: E402

MISSING_LABELS = {
    "khong_co_file_anh_hop_le": "Sản phẩm không có file ảnh hợp lệ",
    "khong_co_anh_du_quyen_va_file": "Sản phẩm không có ảnh đủ quyền và file hợp lệ",
    "khong_co_gia_bien_the": "Biến thể chưa có giá",
    "khong_co_anh": "Sản phẩm không có ảnh",
    "duoi_2_anh": "Sản phẩm dưới 2 ảnh",
    "anh_chua_ro_quyen": "Ảnh chưa rõ quyền sử dụng",
    "khong_co_mo_ta_ngan": "Thiếu mô tả ngắn",
    "khong_co_chat_lieu": "Thiếu chất liệu",
    "khong_co_thuong_hieu": "Không có thương hiệu",
    "khong_co_nha_san_xuat": "Không có nhà sản xuất",
    "khong_co_tieu_chi_viet_true": "Chưa có tiêu chí Việt đã có nguồn",
    "chua_review": "Chưa review",
}


def render_markdown(catalog_path: Path, report: dict, result) -> str:
    lines = [
        f"# Báo cáo chất lượng catalog — {report['catalog_version']}",
        "",
        f"- File: `{catalog_path.name}`",
        f"- Thời điểm: {report['generated_at']}",
        f"- Kết quả kiểm tra: **{'ĐẠT' if result.ok else 'KHÔNG ĐẠT'}** "
        f"({len(result.errors)} lỗi, {len(result.warnings)} cảnh báo)",
        "",
        "## Số lượng",
        "",
        "| Collection | Số bản ghi |",
        "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in report["counts"].items()]
    lines += ["", "## Trạng thái sản phẩm", ""]
    if report["status"]:
        lines += ["| Trạng thái | Số lượng |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in report["status"].items()]
    else:
        lines.append("Chưa có sản phẩm.")
    lines += ["", "## Theo nhóm danh mục gốc", ""]
    if report["products_by_root_category"]:
        lines += ["| Nhóm | Số sản phẩm |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in report["products_by_root_category"].items()]
    else:
        lines.append("Chưa có sản phẩm.")
    lines += ["", "## Tỷ lệ thiếu dữ liệu", "", "| Chỉ số | Số lượng | Trên tổng | % |", "|---|---|---|---|"]
    for k, v in report["missing"].items():
        lines.append(f"| {MISSING_LABELS.get(k, k)} | {v['count']} | {v['total']} | {v['pct']} |")
    lines += ["", "## Kiểm tra file ảnh", "", report["image_files"]["scope"], "",
              "| Trạng thái file | Số ảnh |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in report["image_files"]["by_status"].items()]
    lines += ["", f"Ảnh đủ quyền và có file hợp lệ: {report['image_files']['with_usable_rights_and_valid_file']}"]
    lines += ["", "## Ảnh trùng (SHA-256)", ""]
    if report["duplicate_images_sha256"]:
        for h, imgs in report["duplicate_images_sha256"].items():
            lines.append(f"- `{h[:12]}…`: {', '.join(imgs)}")
    else:
        lines.append("Không phát hiện.")
    lines += ["", "## URL ảnh dùng chung cho nhiều sản phẩm", ""]
    if report["duplicate_image_urls"]:
        lines.append("Thường là ảnh bao bì/ảnh chung; không nên dùng làm ảnh đại diện hay đưa vào gallery benchmark.")
        lines.append("")
        for u, pids in report["duplicate_image_urls"].items():
            lines.append(f"- {u}: {', '.join(pids)}")
    else:
        lines.append("Không phát hiện.")
    lines += ["", f"Perceptual hash: {report['perceptual_hash']}", "", "## Lỗi và cảnh báo", ""]
    if result.issues:
        lines += [f"- {i}" for i in result.issues[:500]]
        if len(result.issues) > 500:
            lines.append(f"- … và {len(result.issues) - 500} mục khác (xem file JSON)")
    else:
        lines.append("Không có.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", type=Path, default=REPO_ROOT / "database.json")
    ap.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports" / "data_quality")
    ap.add_argument("--no-report", action="store_true", help="Chỉ kiểm tra, không ghi báo cáo")
    ap.add_argument("--no-files", action="store_true", help="Bỏ qua kiểm tra file ảnh")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    catalog_path = args.catalog.resolve()
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Không đọc được {catalog_path}: {e}", file=sys.stderr)
        return 1

    result = validate_catalog(data, catalog_path.parent, check_files=not args.no_files)
    for issue in result.issues:
        print(issue)
    print(f"{len(result.errors)} lỗi, {len(result.warnings)} cảnh báo")

    if result.ok and not args.no_report:
        report = quality_report(data, catalog_path.parent)
        args.report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d")
        stem = f"{stamp}_{report['catalog_version']}"
        payload = {**report, "issues": [i.__dict__ for i in result.issues]}
        (args.report_dir / f"{stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.report_dir / f"{stem}.md").write_text(
            render_markdown(catalog_path, report, result), encoding="utf-8")
        print(f"Đã ghi báo cáo: {args.report_dir / (stem + '.md')}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
