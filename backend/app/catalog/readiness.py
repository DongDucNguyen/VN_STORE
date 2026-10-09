"""Read-only publication assessment using the same rules as catalog loading."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import re
from typing import Any

from .validation import quality_report, validate_catalog


def publication_readiness(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    current = validate_catalog(data, base_dir)
    report: dict[str, Any] = {
        "catalog_version": data.get("catalog_version"),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "Mô phỏng published trên bản sao, kiểm tra file và quy tắc validator. Không sửa DB, không xác nhận nội dung hay cấp quyền sử dụng ảnh.",
        "current_validation": {
            "ok": current.ok,
            "errors": len(current.errors),
            "warnings": len(current.warnings),
            "issues": [asdict(i) for i in current.issues],
        },
        "assessment_complete": False,
        "products": [],
    }
    if any(i.code == "schema" for i in current.errors):
        report["assessment_skipped_reason"] = "Catalog sai schema; sửa cấu trúc trước khi đánh giá từng sản phẩm."
        return report

    candidate = deepcopy(data)
    for product in candidate["products"]:
        product["status"] = "published"
    proposed = validate_catalog(candidate, base_dir)
    grouped: dict[int, list[dict[str, Any]]] = {}
    global_issues = []
    for issue in proposed.issues:
        match = re.match(r"^\$\.products\[(\d+)\](?:\.|$)", issue.path)
        if match:
            grouped.setdefault(int(match[1]), []).append(asdict(issue))
        else:
            global_issues.append(asdict(issue))
    global_errors = [i for i in global_issues if i["level"] == "error"]
    blocked_by = Counter()
    for index, product in enumerate(data["products"]):
        issues = grouped.get(index, [])
        blockers = [i for i in issues if i["level"] == "error"]
        warnings = [i for i in issues if i["level"] == "warning"]
        codes = sorted({i["code"] for i in blockers})
        blocked_by.update(codes)
        technical_ready = not blockers and not global_errors
        review_recorded = product["reviewed_at"] is not None
        report["products"].append({
            "id": product["id"], "name_vi": product["name_vi"],
            "current_status": product["status"],
            "technical_ready": technical_ready,
            "review_recorded": review_recorded,
            "passes_recorded_checks": technical_ready and review_recorded,
            "blocker_codes": codes, "blockers": blockers, "warnings": warnings,
            "editorial_gaps": {
                "variants_without_price": sum(v["price_vnd"] is None for v in product["variants"]),
                "missing_materials": not bool(product.get("materials")),
                "missing_brand": product["brand_id"] is None,
                "missing_maker": product["maker_id"] is None,
                "fewer_than_two_images": len(product["images"]) < 2,
            },
        })
    rows = report["products"]
    report.update({
        "assessment_complete": True,
        "global_issues": global_issues,
        "summary": {
            "products": len(rows),
            "technical_ready": sum(p["technical_ready"] for p in rows),
            "review_pending": sum(not p["review_recorded"] for p in rows),
            "passes_recorded_checks": sum(p["passes_recorded_checks"] for p in rows),
            "products_by_blocker_code": dict(sorted(blocked_by.items())),
            "global_errors": len(global_errors),
        },
        "quality": quality_report(data, base_dir),
    })
    return report
