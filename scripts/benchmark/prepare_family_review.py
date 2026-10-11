"""Tạo trang duyệt offline cho đề xuất họ sản phẩm (benchmarks/families/proposal.json).

    .venv/Scripts/python scripts/benchmark/prepare_family_review.py --out artifacts/family_review/<thư-mục-mới>

Trang có ba phần: họ đề xuất (xác nhận hoặc tách thành nhóm A/B/C…), cặp ứng viên ảnh (gộp hay không) và cụm ảnh
dùng chung (giữ hay loại khỏi gallery — chỉ ghi quyết định cho P0.6, không áp vào catalog). Người duyệt xuất file
quyết định rồi áp bằng apply_family_review.py. Proposal phải khớp hash catalog hiện tại.

Catalog đổi (ví dụ bổ sung chất liệu) làm đổi hash proposal dù nội dung đề xuất giữ nguyên. --carry-drafts-from
<packet.json cũ> cho phép trang mới nạp bản nháp của trang cũ, chỉ khi họ, ứng viên ảnh, cụm ảnh dùng chung và
mã họ của từng sản phẩm trùng khớp hoàn toàn. File quyết định xuất ra vẫn mang hash proposal hiện tại.

--suggestions <json> (build_family_suggestions.py) hiện gợi ý máy và lý do trên từng thẻ; lựa chọn chỉ được đặt
khi người duyệt bấm "Áp gợi ý". File quyết định ghi số gợi ý đã áp và đã sửa.
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
            "shared": shared, "products": products, "compatible_proposal_sha256": []}


def proposal_content(packet: dict) -> dict:
    """Phần quyết định của người duyệt phụ thuộc vào; bỏ hash, phiên bản catalog và đường dẫn ảnh."""
    return {"families": packet["families"], "candidates": packet["candidates"],
            "shared": sorted((s["key"], s["products"], s["illustration"]) for s in packet["shared"]),
            "product_family": {pid: p["family"] for pid, p in packet["products"].items()}}


def carry_drafts(packet: dict, old_paths: list[Path]) -> None:
    for path in old_paths:
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("kind") != "family_review":
            raise ValueError(f"{path}: không phải packet duyệt họ")
        if proposal_content(old) != proposal_content(packet):
            raise ValueError(f"{path}: nội dung đề xuất khác packet mới; bản nháp cũ phải duyệt lại, không chuyển được")
        for sha in [old["proposal_sha256"], *old.get("compatible_proposal_sha256", [])]:
            if sha != packet["proposal_sha256"] and sha not in packet["compatible_proposal_sha256"]:
                packet["compatible_proposal_sha256"].append(sha)


def attach_suggestions(packet: dict, raw: bytes) -> None:
    data = json.loads(raw)
    if data.get("kind") != "family_review_suggestions" or data.get("proposal_sha256") not in (
            packet["proposal_sha256"], *packet["compatible_proposal_sha256"]):
        raise ValueError("Gợi ý dành cho đề xuất khác hoặc sai định dạng")
    if (set(data["families"]) != {f["family_id"] for f in packet["families"]}
            or set(data["candidates"]) != {c["key"] for c in packet["candidates"]}
            or set(data["shared"]) != {s["key"] for s in packet["shared"]}):
        raise ValueError("Gợi ý không phủ đúng các thẻ của trang")
    packet["suggestions"] = {k: data[k] for k in ("version", "author", "policy", "families", "candidates", "shared")}
    packet["suggestions_sha256"] = hashlib.sha256(raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proposal", type=Path, default=PROPOSAL)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--carry-drafts-from", type=Path, action="append", default=[], metavar="PACKET_JSON",
                    help="packet.json của trang cũ có cùng nội dung đề xuất; cho phép nạp bản nháp của trang đó")
    ap.add_argument("--suggestions", type=Path, help="JSON gợi ý máy (build_family_suggestions.py)")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if args.out.exists():
        ap.error("Thư mục đầu ra đã tồn tại; chọn thư mục mới")
    try:
        raw = args.proposal.read_bytes()
        snap = load_snapshot(args.catalog, include_drafts=True)
        packet = make_packet(json.loads(raw), hashlib.sha256(raw).hexdigest(), snap, args.out.resolve())
        carry_drafts(packet, args.carry_drafts_from)
        if args.suggestions:
            attach_suggestions(packet, args.suggestions.read_bytes())
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
    if packet["compatible_proposal_sha256"]:
        print(f"Nạp được bản nháp của {len(packet['compatible_proposal_sha256'])} proposal cũ cùng nội dung")
    return 0


if __name__ == "__main__":
    sys.exit(main())
