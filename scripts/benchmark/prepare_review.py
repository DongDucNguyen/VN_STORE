"""Create an offline annotation packet; all catalog products are included, no ranking bias.

Labels remain unverified until a human grades every candidate and explicitly confirms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from eval_keyword import ROOT, load_snapshot, validate_queries


def make_packet(queries, snap, output: Path):
    validate_queries(queries, {p["id"] for p in snap.data["products"]})
    if not snap.products:
        raise ValueError("Catalog không có sản phẩm hiển thị; kiểm tra --include-drafts")
    products = []
    for p in snap.products.values():
        image = next((i for i in p["images"] if snap.image_path(i["id"]) is not None), None)
        image_path = snap.image_path(image["id"]) if image else None
        products.append({
            "id": p["id"], "name": p["name_vi"], "description": p["short_description_vi"],
            "materials": p["materials"], "colors": p["colors"], "variants": p["variants"],
            "claims": p["origin_claims"], "category": snap.categories[p["category_id"]]["name_vi"],
            "image": Path(os.path.relpath(image_path, output)).as_posix() if image_path else None,
            "sources": [{"url": snap.sources[s]["url"], "title": snap.sources[s].get("title")}
                        for s in p["source_ids"]],
        })
    return {"catalog_sha256": snap.sha256, "catalog_version": snap.version,
            "queries": queries, "products": products,
            "candidate_order": {q["qid"]: sorted(snap.products, key=lambda pid: hashlib.sha256(
                (q["qid"] + "\0" + pid).encode()).hexdigest()) for q in queries},
            "scope": "all_visible_catalog_products", "verified": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queries", type=Path, required=True)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.out.exists():
        ap.error("Thư mục đầu ra đã tồn tại; chọn thư mục mới để giữ hồ sơ cũ")
    try:
        queries = [json.loads(line) for line in args.queries.read_text(encoding="utf-8").splitlines() if line.strip()]
        snap = load_snapshot(args.catalog, include_drafts=args.include_drafts)
        packet = make_packet(queries, snap, args.out.resolve())
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    packet["queries_sha256"] = hashlib.sha256(args.queries.read_bytes()).hexdigest()
    payload = json.dumps(packet, ensure_ascii=False, indent=2)
    template = Path(__file__).with_name("review_template.html").read_text(encoding="utf-8")
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "packet.json").write_text(payload + "\n", encoding="utf-8")
    (args.out / "index.html").write_text(template.replace("__PACKET_JSON__", payload.replace("<", "\\u003c")), encoding="utf-8")
    print(f"{len(queries)} truy vấn × {len(snap.products)} sản phẩm = {len(queries)*len(snap.products)} cặp cần người chấm. Nhãn chưa duyệt.")
    print(args.out / "index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
