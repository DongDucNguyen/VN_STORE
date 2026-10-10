"""Validate full-catalog review exports and list disagreements without changing labels."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

from eval_keyword import ROOT, load_snapshot, validate_queries
from app.catalog.store import CatalogError

TZ = timezone(timedelta(hours=7))


def identity(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def unique_products(packet: dict) -> set[str]:
    rows = packet.get("products")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Packet phải có danh sách sản phẩm không rỗng")
    ids = [p.get("id") if isinstance(p, dict) else None for p in rows]
    if any(not isinstance(pid, str) or not pid.strip() for pid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Packet có ID sản phẩm thiếu/trùng")
    return set(ids)


def validate_packet(packet: dict, catalog_sha256: str, visible_ids: set[str]) -> set[str]:
    if not isinstance(packet, dict):
        raise ValueError("Packet phải là object")
    if packet.get("catalog_sha256") != catalog_sha256:
        raise ValueError("Packet thuộc snapshot catalog khác; tạo packet mới và đối chiếu lại")
    products = unique_products(packet)
    if products != visible_ids:
        raise ValueError("Sản phẩm packet không khớp tập hiển thị; kiểm tra --include-drafts")
    if not isinstance(packet.get("queries"), list):
        raise ValueError("Packet thiếu queries")
    validate_queries(packet["queries"], products)
    return products


def validate_export(rows: list[dict], packet: dict, products: set[str]) -> str:
    validate_queries(rows, products)
    originals = {q["qid"]: q for q in packet["queries"]}
    if {q["qid"] for q in rows} != set(originals):
        raise ValueError("File review phải chứa đúng mọi qid trong packet, không thêm/bớt")
    reviewers = set()
    for q in rows:
        qid = q["qid"]
        if q["verified"] is not True:
            raise ValueError(f"{qid}: nhãn chưa được người kiểm tra xác nhận")
        if q["query"] != originals[qid]["query"] or q["split"] != originals[qid]["split"]:
            raise ValueError(f"{qid}: query/split đã đổi so với packet")
        if q.get("catalog_sha256") != packet["catalog_sha256"]:
            raise ValueError(f"{qid}: thiếu/sai catalog_sha256")
        if set(q["relevance"]) != products:
            raise ValueError(f"{qid}: chưa chấm đủ toàn bộ sản phẩm của packet")
        if not isinstance(q.get("group_id"), str) or not q["group_id"].strip():
            raise ValueError(f"{qid}: thiếu group_id")
        try:
            stamp = datetime.fromisoformat(q["reviewed_at"])
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError("timezone missing")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{qid}: reviewed_at cần ISO datetime có múi giờ") from exc
        reviewers.add(identity(q["labeled_by"]))
    if len(reviewers) != 1:
        raise ValueError("Mỗi file export cần một người kiểm tra nhất quán")
    return next(iter(reviewers))


def compare_exports(left: list[dict], right: list[dict], products: set[str]) -> dict:
    other = {q["qid"]: q for q in right}
    pairs, groups, answer_differences = [], [], []
    matrix = [[0] * 4 for _ in range(4)]
    threshold_same = 0
    for a in left:
        b = other[a["qid"]]
        if a["group_id"] != b["group_id"]:
            groups.append({"qid": a["qid"], "left": a["group_id"], "right": b["group_id"]})
        if a["has_answer"] != b["has_answer"]:
            answer_differences.append({"qid": a["qid"], "left": a["has_answer"], "right": b["has_answer"]})
        for pid in sorted(products):
            x, y = a["relevance"][pid], b["relevance"][pid]
            matrix[x][y] += 1
            threshold_same += (x >= 2) == (y >= 2)
            if x != y:
                pairs.append({"qid": a["qid"], "query": a["query"], "product_id": pid,
                              "left": x, "right": y, "crosses_relevant_threshold": (x >= 2) != (y >= 2)})
    total = len(left) * len(products)
    return {"pairs_compared": total, "exact_agreement": (total - len(pairs)) / total,
            "relevant_threshold_agreement": threshold_same / total,
            "confusion_matrix": {"rows": "left 0..3", "columns": "right 0..3", "counts": matrix},
            "grade_disagreements": pairs, "group_disagreements": groups,
            "has_answer_disagreements": answer_differences,
            "requires_adjudication": bool(pairs or groups or answer_differences)}


def audit(packet: dict, exports: list[list[dict]], catalog_hash: str, visible_ids: set[str]) -> dict:
    products = validate_packet(packet, catalog_hash, visible_ids)
    if len(exports) > 2:
        raise ValueError("Chỉ nhận tối đa hai file review trong một lần đối chiếu")
    reviewers = [validate_export(rows, packet, products) for rows in exports]
    if len(set(reviewers)) != len(reviewers):
        raise ValueError("Hai file có cùng tên/mã người kiểm tra; không tính như hai người độc lập")
    report = {"status": "pending_review" if not exports else "valid_single_review",
              "catalog_sha256": catalog_hash, "queries": len(packet["queries"]),
              "products": len(products), "pairs_per_reviewer": len(products) * len(packet["queries"]),
              "splits": dict(Counter(q["split"] for q in packet["queries"])),
              "reviewers": reviewers,
              "scope": "Kiểm tra cấu trúc và tính nhất quán của export đầy đủ; không xác thực danh tính, tính độc lập, nội dung chấm hay quyết định nghiệm thu benchmark.",
              "exports": [{"queries": len(rows), "grade_counts": dict(sorted(Counter(
                    str(grade) for q in rows for grade in q["relevance"].values()).items())),
                    "no_answer_queries": sum(not q["has_answer"] for q in rows)} for rows in exports]}
    if len(exports) == 2:
        report["comparison"] = compare_exports(exports[0], exports[1], products)
        report["status"] = "requires_adjudication" if report["comparison"]["requires_adjudication"] else "agreement_recorded"
    return report


def read_jsonl(raw: bytes) -> list[dict]:
    rows = []
    for line_no, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL sai tại dòng {line_no}: {exc.msg}") from exc
    return rows


def markdown(report: dict) -> str:
    lines = ["# Kiểm tra nhãn keyword", "", f"- Trạng thái: **{report['status']}**",
             f"- Thời điểm: {report['generated_at']}", ""]
    if "error" in report:
        lines += [report["error"]]
    else:
        lines += [report["scope"], "", f"- {report['queries']} query × {report['products']} sản phẩm = {report['pairs_per_reviewer']} cặp/người.",
                  f"- Số file người kiểm tra: {len(report['reviewers'])}.",
                  f"- Catalog SHA-256: `{report['catalog_sha256']}`", ""]
        if not report["reviewers"]:
            lines.append("Packet đã sẵn sàng để chấm; chưa cung cấp file nhãn người duyệt, chưa có baseline chính thức.")
        if "comparison" in report:
            c = report["comparison"]
            lines += [f"- Tỷ lệ cùng điểm: {c['exact_agreement']:.2%}.",
                      f"- Tỷ lệ cùng quyết định phù hợp (>=2): {c['relevant_threshold_agreement']:.2%}.",
                      f"- Bất đồng điểm: {len(c['grade_disagreements'])}; nhóm: {len(c['group_disagreements'])}; có đáp án: {len(c['has_answer_disagreements'])}.", "",
                      "## Cặp cần phân xử", "", "| qid | product_id | Trái | Phải | Qua ngưỡng phù hợp |", "|---|---|---|---|---|"]
            esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
            lines += [f"| {esc(d['qid'])} | {esc(d['product_id'])} | {d['left']} | {d['right']} | {d['crosses_relevant_threshold']} |" for d in c["grade_disagreements"]]
            lines += ["", "Bất đồng nhóm/has_answer và ma trận điểm có trong JSON cùng tên. Người phân xử cần ghi quyết định trong file nhãn riêng; công cụ không gộp hoặc chọn điểm."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--packet", type=Path, required=True)
    ap.add_argument("--review", type=Path, action="append", default=[])
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports/benchmark")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    inputs = []
    try:
        packet_raw = args.packet.read_bytes()
        inputs.append({"kind": "packet", "path": str(args.packet), "sha256": hashlib.sha256(packet_raw).hexdigest()})
        exports = []
        for path in args.review:
            raw = path.read_bytes()
            inputs.append({"kind": "review", "path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
            exports.append(read_jsonl(raw))
        snap = load_snapshot(args.catalog, include_drafts=args.include_drafts)
        report = audit(json.loads(packet_raw), exports, snap.sha256, set(snap.products))
    except (OSError, ValueError, KeyError, TypeError, CatalogError) as exc:
        # Persist load/validation failures as well; no label or catalog mutations.
        report = {"status": "invalid", "error": f"{type(exc).__name__}: {exc}"}
    now = datetime.now(TZ)
    report.update(generated_at=now.isoformat(timespec="seconds"), inputs=inputs)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    target = args.report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_keyword-review-audit.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(f"{report['status']}: {target}")
    return 1 if report["status"] == "invalid" else 2 if report["status"] == "requires_adjudication" else 0


if __name__ == "__main__":
    raise SystemExit(main())
