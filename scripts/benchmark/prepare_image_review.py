"""Tạo packet chấm judgment cho query ảnh (PLAN.md mục 8.1: pool top kết quả của mọi baseline + mẫu ngẫu nhiên).

    .venv-ml/Scripts/python scripts/benchmark/prepare_image_review.py --split dev \
        --adapter app.ml.image:SigLIP2Base --adapter app.ml.image:DINOv2Base --out artifacts/image_judgment/<mới>

Với mỗi query chưa có judgment trong split (hoặc mọi query với --include-judged):
- top K theo cosine ảnh của từng adapter (gộp theo sản phẩm, không lọc theo chữ);
- với image_text: thêm top K của search_visual (ảnh + chữ, bộ lọc cứng) và của BM25 trên text_vi;
- thêm N sản phẩm ngẫu nhiên (cố định theo --seed và qid) để pool không chỉ gồm thứ model đã thấy.
Pool được xáo theo hash nên người chấm không thấy thứ hạng hay model nào tìm ra; phần còn lại của gallery vẫn
có trong trang để chấm khi query không có đáp án (audit yêu cầu nhãn đủ gallery cho no-match).
Script không ghi judgment. Người chấm mở index.html, xuất file JSON, rồi áp bằng apply_image_judgments.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_image_queries import audit  # noqa: E402
from eval_image import MANIFEST, get_index  # noqa: E402

from app.adapters import AdapterError, ImageEmbedder, load_adapter  # noqa: E402
from app.catalog.store import CatalogSnapshot, load_snapshot  # noqa: E402
from app.image.index import model_dir_name  # noqa: E402
from app.search.engine import SearchEngine  # noqa: E402

INDEX_ROOT = ROOT / "artifacts" / "indexes" / "image"
TEMPLATE = Path(__file__).with_name("image_review_template.html")


def hash_order(key: str, ids: list[str]) -> list[str]:
    return sorted(ids, key=lambda pid: hashlib.sha256(f"{key}\0{pid}".encode()).hexdigest())


def product_card(snap: CatalogSnapshot, p: dict, out: Path) -> dict:
    images = [snap.image_path(i["id"]) for i in p["images"]]
    return {
        "id": p["id"], "name": p["name_vi"], "category": snap.categories[p["category_id"]]["name_vi"],
        "description": p["short_description_vi"], "materials": p["materials"], "colors": p["colors"],
        "variants": [{"sku": v["sku"], "name_vi": v.get("name_vi"), "price_vnd": v["price_vnd"]} for v in p["variants"]],
        "images": [Path(os.path.relpath(i, out)).as_posix() for i in images if i is not None][:4],
    }


def build_pool(samples: list[dict], base: Path, snap: CatalogSnapshot, systems: list[tuple[str, ImageEmbedder, object]],
               top_k: int, n_random: int, seed: str) -> dict[str, dict[str, list[str]]]:
    """qid → {product_id: [nguồn]}; nguồn chỉ để lưu hồ sơ, không hiện cho người chấm."""
    engine = SearchEngine(snap)
    allowed = set(snap.products)
    pools: dict[str, dict[str, list[str]]] = {}
    for s in samples:
        pool: dict[str, list[str]] = {}

        def add(pids, source):
            for rank, pid in enumerate(pids[:top_k], 1):
                pool.setdefault(pid, []).append(f"{source}@{rank}")

        data = (base / s["image_path"]).read_bytes()
        for name, embedder, index in systems:
            (vec,) = embedder.embed([data])
            hits = index.query(vec, allowed)
            add([h.product_id for h in hits], f"{name}:visual")
            if s["text_vi"]:
                res = engine.search_visual(hits, s["text_vi"], limit=top_k)
                add([r["id"] for r in res["results"]], f"{name}:image_text")
        if s["text_vi"]:
            add([r["id"] for r in engine.search(s["text_vi"], limit=top_k)["results"]], "bm25:text_vi")
        rest = sorted(allowed - set(pool))
        rng = random.Random(f"{seed}\0{s['qid']}")
        add(rng.sample(rest, min(n_random, len(rest))), "random")
        pools[s["qid"]] = pool
    return pools


def make_packet(manifest_path: Path, catalog_path: Path, split: str, adapters: list[str], out: Path, top_k: int = 10,
                n_random: int = 5, seed: str = "vnstore-image-pool-1", include_judged: bool = False) -> dict:
    report = audit(manifest_path, catalog_path)
    if report["status"] == "invalid":
        raise ValueError(f"audit manifest thất bại ({len(report['issues'])} lỗi); chạy audit_image_queries.py")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = [s for s in manifest["samples"] if s["split"] == split and (include_judged or s["judgment"] is None)]
    if not samples:
        raise ValueError(f"split {split} không có query cần chấm ({report['status']})")
    snap = load_snapshot(catalog_path, include_drafts=manifest["include_drafts"])
    systems, described = [], []
    for spec in adapters:
        embedder = load_adapter(spec, ImageEmbedder)
        saved = INDEX_ROOT / model_dir_name(embedder.model_id, embedder.revision)
        index, source = get_index(snap, embedder, saved if saved.is_dir() else None)
        name = embedder.model_id.rsplit("/", 1)[-1]
        systems.append((name, embedder, index))
        described.append({"adapter": spec, "model_id": embedder.model_id, "revision": embedder.revision,
                          "index_source": source})
    pools = build_pool(samples, manifest_path.parent, snap, systems, top_k, n_random, seed)
    queries = []
    for s in samples:
        pool = pools[s["qid"]]
        queries.append({
            "qid": s["qid"], "task": s["task"], "text_vi": s["text_vi"], "family_id": s["family_id"],
            "sha256": s["sha256"],
            "image": Path(os.path.relpath(manifest_path.parent / s["image_path"], out)).as_posix(),
            "pool": hash_order(s["qid"], list(pool)),
            "rest": hash_order(s["qid"], sorted(set(snap.products) - set(pool))),
            "pool_sources": pool,
            "existing": {"judgment": s["judgment"], "independence_review": s["independence_review"]},
        })
    return {
        "packet_version": "1.0.0", "kind": "image_judgment",
        "catalog_sha256": snap.sha256, "catalog_version": snap.version, "include_drafts": snap.include_drafts,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "split": split,
        "pool_policy": {"top_k": top_k, "random_per_query": n_random, "seed": seed, "systems": described,
                        "text_baseline": "bm25:text_vi cho image_text"},
        "queries": queries,
        "products": [product_card(snap, p, out) for p in snap.products.values()],
        "verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--split", choices=("train", "dev", "test"), required=True)
    ap.add_argument("--adapter", action="append", required=True, help="module:Class của ImageEmbedder; lặp lại được")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--random", type=int, default=5, help="số sản phẩm ngẫu nhiên thêm vào pool mỗi query")
    ap.add_argument("--seed", default="vnstore-image-pool-1")
    ap.add_argument("--include-judged", action="store_true", help="tạo packet cả cho query đã có judgment")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if args.out.exists():
        ap.error("Thư mục đầu ra đã tồn tại; chọn thư mục mới để giữ hồ sơ cũ")
    if args.top_k < 1 or args.random < 0:
        ap.error("--top-k ≥ 1, --random ≥ 0")
    try:
        packet = make_packet(args.manifest, args.catalog, args.split, args.adapter, args.out.resolve(), args.top_k,
                             args.random, args.seed, args.include_judged)
    except (ValueError, OSError, AdapterError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    payload = json.dumps(packet, ensure_ascii=False, indent=1)
    packet_id = hashlib.sha256(payload.encode()).hexdigest()
    payload = json.dumps({**packet, "packet_id": packet_id}, ensure_ascii=False, indent=1)
    args.out.mkdir(parents=True)
    (args.out / "packet.json").write_text(payload + "\n", encoding="utf-8")
    html = TEMPLATE.read_text(encoding="utf-8").replace("__PACKET_JSON__", payload.replace("<", "\\u003c"))
    (args.out / "index.html").write_text(html, encoding="utf-8")
    sizes = [len(q["pool"]) for q in packet["queries"]]
    print(f"{len(sizes)} query, pool {min(sizes)}–{max(sizes)} sản phẩm/query (gallery {len(packet['products'])}). "
          f"Chưa có judgment nào được ghi.")
    if args.split == "test":
        print("Lưu ý: chỉ dùng packet test để chấm nhãn; không xem kết quả model trên test để chỉnh cấu hình.")
    print(args.out / "index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
