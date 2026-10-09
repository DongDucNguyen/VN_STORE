"""Write a dated publication checklist without editing the catalog."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.catalog.readiness import publication_readiness  # noqa: E402


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_markdown(report: dict) -> str:
    lines = ["# Kiểm tra điều kiện công bố catalog", "",
             f"- Thời điểm: {report['generated_at']}",
             f"- Catalog: `{report['catalog_version']}`",
             f"- SHA-256: `{report['catalog_sha256']}`", "", report["scope"], "",
             "`passes_recorded_checks` chỉ cho biết các điều kiện đã ghi trong DB đều đạt; không phải quyết định công bố tự động.", "",
             f"Catalog hiện tại: {report['current_validation']['errors']} lỗi, {report['current_validation']['warnings']} cảnh báo.", ""]
    if not report["assessment_complete"]:
        lines.append(report["assessment_skipped_reason"])
    else:
        summary = report["summary"]
        lines += ["## Tổng quan", "",
                  f"- Đạt kiểm tra kỹ thuật: {summary['technical_ready']}/{summary['products']} sản phẩm.",
                  f"- Chưa ghi nhận review: {summary['review_pending']} sản phẩm.",
                  f"- Đạt kỹ thuật và có reviewed_at: {summary['passes_recorded_checks']} sản phẩm.",
                  f"- Lỗi chung của catalog: {summary['global_errors']}.", "",
                  "## File ảnh", "", report["quality"]["image_files"]["scope"], "",
                  "| Trạng thái | Số ảnh |", "|---|---|"]
        lines += [f"| {cell(k)} | {v} |" for k, v in report["quality"]["image_files"]["by_status"].items()]
        lines += ["", f"Ảnh có file hợp lệ và quyền được chấp nhận: {report['quality']['image_files']['with_usable_rights_and_valid_file']}.", "",
                  "## Từng sản phẩm", "",
                  "Thiếu giá/chất liệu/thương hiệu/nhà sản xuất là mục bổ sung biên tập, không tự động chặn published theo schema hiện tại.", "",
                  "| ID / Tên | Trạng thái | Lỗi chặn kỹ thuật | Review | Mục biên tập cần bổ sung |",
                  "|---|---|---|---|---|"]
        labels = {"variants_without_price": "biến thể thiếu giá", "missing_materials": "chất liệu",
                  "missing_brand": "thương hiệu", "missing_maker": "nhà sản xuất",
                  "fewer_than_two_images": "dưới 2 ảnh"}
        for p in report["products"]:
            gaps = [f"{labels[k]} ({v})" if k == "variants_without_price" else labels[k]
                    for k, v in p["editorial_gaps"].items() if v]
            codes = ", ".join(p["blocker_codes"]) or "Không có lỗi riêng"
            lines.append(f"| {cell(p['id'])}: {cell(p['name_vi'])} | {p['current_status']} | {codes} | {'Đã ghi nhận' if p['review_recorded'] else 'Chưa'} | {', '.join(gaps) or '—'} |")
        lines += ["", "## Lỗi/cảnh báo chi tiết khi mô phỏng published", ""]
        for issue in report["global_issues"]:
            lines.append(f"- [{issue['level']}] {issue['code']} — `{issue['path']}`: {issue['message']}")
        for p in report["products"]:
            if p["blockers"] or p["warnings"]:
                lines += ["", f"### {p['id']}", ""]
                lines += [f"- [{i['level']}] {i['code']} — `{i['path']}`: {i['message']}"
                          for i in p["blockers"] + p["warnings"]]
    lines += ["", "## Kiểm tra catalog hiện tại", ""]
    lines += [f"- [{i['level']}] {i['code']} — `{i['path']}`: {i['message']}"
              for i in report["current_validation"]["issues"]] or ["Không có lỗi/cảnh báo."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", type=Path, default=REPO_ROOT / "database.json")
    ap.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports" / "data_quality")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        path = args.catalog.resolve()
        raw = path.read_bytes()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Catalog phải là JSON object")
        report = publication_readiness(data, path.parent)
    except (OSError, ValueError) as exc:
        print(f"Không thể đánh giá catalog: {exc}", file=sys.stderr)
        return 1
    report["catalog_sha256"] = hashlib.sha256(raw).hexdigest()
    report["catalog_file"] = path.name
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stem = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S-%f_publication-readiness")
    target = args.report_dir / stem
    target.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
    print(f"Đã ghi: {target.with_suffix('.md')}")
    if report["assessment_complete"]:
        print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["current_validation"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
