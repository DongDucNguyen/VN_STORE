"""Tạo trang duyệt offline cho đề xuất họ sản phẩm (benchmarks/families/proposal.json).

    .venv/Scripts/python scripts/benchmark/prepare_family_review.py --out artifacts/family_review/<thư-mục-mới>

Trang có ba phần: họ đề xuất (xác nhận hoặc tách thành nhóm A/B/C…), cặp ứng viên ảnh (gộp hay không) và cụm ảnh
dùng chung (giữ hay loại khỏi gallery — chỉ ghi quyết định cho P0.6, không áp vào catalog). Người duyệt xuất file
quyết định rồi áp bằng apply_family_review.py. Proposal phải khớp hash catalog hiện tại.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.catalog.store import load_snapshot  # noqa: E402

PROPOSAL = ROOT / "benchmarks" / "families" / "proposal.json"
TEMPLATE = Path(__file__).with_name("family_review_template.html")


def make_packet(proposal: dict, proposal_sha: str, snap, out: Path) -> dict:
    if proposal.get("status") != "proposed_unreviewed":
        raise ValueError("proposal.json không phải đề xuất chưa duyệt")
    if proposal["catalog_sha256"] != snap.sha256:
        raise ValueError("Đề xuất dựng cho catalog khác; chạy lại propose_families.py")
    rel = lambda p: Path(os.path.relpath(p, out)).as_posix()  # noqa: E731
    needed = {p for f in proposal["families"] for p in f["products"]}
    needed |= {x for c in proposal["visual_candidates"] for x in (c["a"], c["b"])}
    needed |= {p for c in proposal["shared_image_clusters"] for p in c["products"]}
    products = {}
    for pid in sorted(needed):
        p = snap.products[pid]
        imgs = [snap.image_path(i["id"]) for i in p["images"]]
        products[pid] = {"name": p["name_vi"], "skus": [v["sku"] for v in p["variants"]],
                         "family": proposal["product_family"][pid],
                         "images": [rel(i) for i in imgs if i is not None][:4]}
    image_files = {i["id"]: snap.image_path(i["id"]) for p in snap.products.values() for i in p["images"]}
    shared = [{"key": ",".join(c["images"]), "products": c["products"],
               "images": [rel(image_files[i]) for i in c["images"] if image_files.get(i)][:3],
               "illustration": len(c["products"]) >= 3}
              for c in sorted(proposal["shared_image_clusters"], key=lambda c: -len(c["products"]))]
    return {"kind": "family_review", "proposal_sha256": proposal_sha, "catalog_sha256": snap.sha256,
            "catalog_version": snap.version, "families": proposal["families"],
            "candidates": [{**c, "key": f"{c['a']}|{c['b']}"} for c in proposal["visual_candidates"]],
            "shared": shared, "products": products}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proposal", type=Path, default=PROPOSAL)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if args.out.exists():
        ap.error("Thư mục đầu ra đã tồn tại; chọn thư mục mới")
    try:
        raw = args.proposal.read_bytes()
        snap = load_snapshot(args.catalog, include_drafts=True)
        packet = make_packet(json.loads(raw), hashlib.sha256(raw).hexdigest(), snap, args.out.resolve())
    except (ValueError, OSError, KeyError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    payload = json.dumps(packet, ensure_ascii=False, indent=1)
    args.out.mkdir(parents=True)
    (args.out / "packet.json").write_text(payload + "\n", encoding="utf-8")
    html = TEMPLATE.read_text(encoding="utf-8").replace("__PACKET_JSON__", payload.replace("<", "\\u003c"))
    (args.out / "index.html").write_text(html, encoding="utf-8")
    print(f"{len(packet['families'])} họ, {len(packet['candidates'])} ứng viên ảnh, {len(packet['shared'])} cụm ảnh dùng chung "
          f"cần quyết định → {args.out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
