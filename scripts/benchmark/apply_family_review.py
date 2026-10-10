"""Áp quyết định duyệt họ sản phẩm (từ trang prepare_family_review.py) thành benchmarks/families/families.json.

    .venv/Scripts/python scripts/benchmark/apply_family_review.py family-review-xxxx.json [--dry-run]

Yêu cầu: file quyết định cùng proposal_sha256 với proposal.json hiện tại, proposal khớp hash database.json, có tên
người duyệt, và đủ quyết định cho mọi họ đề xuất và mọi cặp ứng viên ảnh. Họ "split" được tách theo nhóm người
duyệt gán (fam-…-a, fam-…-b…); cặp ứng viên "merge" gộp hai họ đang chứa hai sản phẩm. Quyết định về ảnh dùng chung
được chép nguyên vào file để nhóm dữ liệu xử lý (không sửa catalog). Không có quyết định thì không ghi gì.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "benchmarks" / "families" / "proposal.json"
OUT = ROOT / "benchmarks" / "families" / "families.json"


class ReviewError(ValueError):
    pass


def apply(proposal: dict, proposal_sha: str, decisions: dict, catalog_sha: str,
          catalog_product_ids: set[str] | None = None) -> dict:
    if not isinstance(proposal, dict) or not isinstance(decisions, dict):
        raise ReviewError("Đề xuất và quyết định phải là JSON object")
    if proposal.get("status") != "proposed_unreviewed":
        raise ReviewError("Cần đề xuất chưa duyệt")
    if decisions.get("kind") != "family_review_decisions":
        raise ReviewError("File không phải quyết định duyệt họ")
    if decisions.get("proposal_sha256") != proposal_sha:
        raise ReviewError("Quyết định dành cho đề xuất khác; tạo lại trang duyệt từ proposal.json hiện tại")
    if proposal["catalog_sha256"] != catalog_sha:
        raise ReviewError("database.json đã đổi so với đề xuất; chạy lại propose_families.py và duyệt lại")
    if decisions.get("catalog_sha256") != catalog_sha:
        raise ReviewError("Quyết định dành cho catalog khác")
    who = decisions.get("reviewed_by")
    if not isinstance(who, str) or not who.strip():
        raise ReviewError("Thiếu người duyệt hoặc thời điểm")
    who = who.strip()
    try:
        stamp = datetime.fromisoformat(decisions["reviewed_at"].replace("Z", "+00:00"))
        if stamp.utcoffset() is None:
            raise ValueError("Missing timezone")
    except (KeyError, TypeError, AttributeError, ValueError):
        raise ReviewError("Thời điểm duyệt phải là ISO datetime có múi giờ") from None
    fam_dec, cand_dec = decisions.get("families", {}), decisions.get("candidates", {})
    shared = decisions.get("shared", {})
    if not all(isinstance(d, dict) for d in (fam_dec, cand_dec, shared)):
        raise ReviewError("families, candidates, shared phải là JSON object")
    family = proposal["product_family"]
    if not isinstance(family, dict) or not family or not all(
        isinstance(p, str) and p.strip() and isinstance(f, str) and f.strip() for p, f in family.items()
    ):
        raise ReviewError("product_family không hợp lệ")
    if catalog_product_ids is not None and set(family) != catalog_product_ids:
        raise ReviewError("product_family phải bao phủ đúng mọi sản phẩm trong catalog")
    proposed_members = defaultdict(set)
    for pid, fid in family.items():
        proposed_members[fid].add(pid)
    listed = {}
    for f in proposal["families"]:
        fid, pids = f["family_id"], f["products"]
        if fid in listed or len(pids) != len(set(pids)) or len(pids) < 2:
            raise ReviewError("Danh sách họ đề xuất bị trùng hoặc thiếu thành viên")
        listed[fid] = set(pids)
    if listed != {f: p for f, p in proposed_members.items() if len(p) > 1}:
        raise ReviewError("Danh sách họ không khớp product_family")
    for c in proposal["visual_candidates"]:
        if c["a"] not in family or c["b"] not in family or c["a"] == c["b"]:
            raise ReviewError("Ứng viên ảnh tham chiếu sản phẩm không hợp lệ")
    shared_keys = {",".join(c["images"]) for c in proposal["shared_image_clusters"]}
    if set(shared) - shared_keys or any(v not in ("keep", "exclude") for v in shared.values()):
        raise ReviewError("Quyết định ảnh dùng chung phải thuộc đề xuất và là keep hoặc exclude")
    missing = [f["family_id"] for f in proposal["families"] if f["family_id"] not in fam_dec]
    keys = {f"{c['a']}|{c['b']}" for c in proposal["visual_candidates"]}
    missing += sorted(keys - set(cand_dec))
    if missing:
        raise ReviewError(f"Còn {len(missing)} mục chưa quyết định, ví dụ {missing[:3]}")
    if set(cand_dec) - keys or set(fam_dec) - {f["family_id"] for f in proposal["families"]}:
        raise ReviewError("Có quyết định cho mục không có trong đề xuất")
    family = dict(proposal["product_family"])
    split_constraints = []
    reserved = set(family.values())
    for f in proposal["families"]:
        d = fam_dec[f["family_id"]]
        if not isinstance(d, dict):
            raise ReviewError(f"{f['family_id']}: quyết định phải là JSON object")
        if d.get("action") == "confirm":
            continue
        groups = d.get("groups", {})
        if d.get("action") != "split" or not isinstance(groups, dict) or set(groups) != set(f["products"]) \
                or not all(isinstance(g, str) and g.strip() for g in groups.values()):
            raise ReviewError(f"{f['family_id']}: tách cần gán nhóm cho mọi sản phẩm, ít nhất 2 nhóm")
        groups = {pid: g.strip().lower() for pid, g in groups.items()}
        if len(set(groups.values())) < 2:
            raise ReviewError(f"{f['family_id']}: tách cần ít nhất 2 nhóm sau chuẩn hóa hoa/thường và khoảng trắng")
        new_ids = {f"{f['family_id']}-{g}" for g in groups.values()}
        if new_ids & reserved:
            raise ReviewError(f"{f['family_id']}: mã họ sau tách trùng mã họ khác; đổi tên nhóm")
        reserved.update(new_ids)
        split_constraints.append((f["family_id"], groups))
        for pid, g in groups.items():
            family[pid] = f"{f['family_id']}-{g}"
    merged = 0
    for k, v in cand_dec.items():
        if v not in ("merge", "separate"):
            raise ReviewError(f"{k}: quyết định phải là merge hoặc separate")
        if v == "merge":
            a, b = k.split("|")
            fa, fb = family[a], family[b]
            if fa != fb:
                keep, drop = sorted((fa, fb))
                family = {p: (keep if x == drop else x) for p, x in family.items()}
                merged += 1
    # Check the final partition: transitive merges must not undo explicit separation.
    for k, v in cand_dec.items():
        a, b = k.split("|")
        if v == "separate" and family[a] == family[b]:
            raise ReviewError(f"Mâu thuẫn: {k} chọn khác họ nhưng nằm cùng họ sau gộp; duyệt lại")
    for fid, groups in split_constraints:
        final_groups = defaultdict(set)
        for pid, group in groups.items():
            final_groups[family[pid]].add(group)
        if any(len(g) > 1 for g in final_groups.values()):
            raise ReviewError(f"Mâu thuẫn: {fid} đã tách nhưng bị gộp lại qua ứng viên ảnh; duyệt lại")
    members = defaultdict(list)
    for pid, fid in family.items():
        members[fid].append(pid)
    return {"status": "reviewed", "catalog_sha256": catalog_sha, "proposal_sha256": proposal_sha,
            "reviewed_by": who, "reviewed_at": decisions["reviewed_at"],
            "product_family": dict(sorted(family.items())),
            "families": [{"family_id": fid, "products": sorted(p)} for fid, p in sorted(members.items()) if len(p) > 1],
            "shared_image_decisions": shared,
            "stats": {"products": len(family), "families": len(members),
                      "split": sum(1 for d in fam_dec.values() if d.get("action") == "split"), "merged_pairs": merged}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("decisions", type=Path)
    ap.add_argument("--proposal", type=Path, default=PROPOSAL)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        raw = args.proposal.read_bytes()
        catalog_raw = args.catalog.read_bytes()
        result = apply(json.loads(raw), hashlib.sha256(raw).hexdigest(),
                       json.loads(args.decisions.read_text(encoding="utf-8")),
                       hashlib.sha256(catalog_raw).hexdigest(),
                       {p["id"] for p in json.loads(catalog_raw)["products"]})
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    s = result["stats"]
    print(f"{s['products']} sản phẩm → {s['families']} họ (tách {s['split']} họ đề xuất, gộp {s['merged_pairs']} cặp); "
          f"người duyệt {result['reviewed_by']}")
    if args.dry_run:
        print("dry-run: không ghi gì")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=args.out.parent, prefix=".families.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, args.out)
    print(f"Đã ghi {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
