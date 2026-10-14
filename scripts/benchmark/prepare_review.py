"""Create an offline annotation packet; all catalog products are included, no ranking bias.

Labels remain unverified until a human grades every candidate and explicitly confirms.

Với --pool-top K (PLAN.md mục 8.1, khi catalog lớn): mỗi truy vấn có một pool phải chấm = top K của BM25
trên câu gốc + top K của BM25 trên phần từ khóa (bỏ bộ lọc giá/phủ định) + --random N sản phẩm ngẫu nhiên
cố định theo seed và qid. Pool được xáo theo hash, không theo thứ hạng. Truy vấn không có sản phẩm 2–3
vẫn phải chấm toàn catalog để ghi nhận no-match. Không có --pool-top thì chấm toàn catalog như trước.

Với --pool-runs RUN_DIR… (kèm --pool-top K): thêm top K dự đoán của các run eval_keyword.py (vd. hệ thống mới như
BM25 + từ điển, kết hợp ngữ nghĩa) vào pool, theo chuẩn pooling nhiều hệ thống. Run phải cùng catalog_sha256 và có
đủ qid; nguồn ghi "run:<tên>@hạng" trong pool_sources.

Với --suggestions (build_keyword_suggestions.py): tạo packet "có hỗ trợ" hiện gợi ý máy cạnh từng cặp. Ô chấm
vẫn trống cho tới khi người chấm tự chọn hoặc bấm áp gợi ý; export ghi số gợi ý đã áp và đã sửa. Chỉ người chấm
thứ nhất/người phân xử dùng packet này; người chấm thứ hai dùng packet không gợi ý để giữ độc lập.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path

from eval_keyword import ROOT, SearchEngine, load_snapshot, validate_queries


def hash_order(qid: str, ids) -> list[str]:
    return sorted(ids, key=lambda pid: hashlib.sha256((qid + "\0" + pid).encode()).hexdigest())


def load_pool_runs(run_dirs, snap, qids: set[str]) -> dict[str, dict[str, list[str]]]:
    """Tên run → qid → dự đoán. Chặn run khác catalog, thiếu qid hoặc dự đoán sản phẩm không hiển thị."""
    runs = {}
    for d in run_dirs:
        meta = json.loads((d / "run.json").read_text(encoding="utf-8"))
        if meta.get("catalog_sha256") != snap.sha256:
            raise ValueError(f"{d.name}: run trên catalog khác ({str(meta.get('catalog_sha256'))[:12]}…)")
        preds = {}
        for line in (d / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                preds[row["qid"]] = row["predictions"]
        if qids - set(preds):
            raise ValueError(f"{d.name}: thiếu {len(qids - set(preds))} qid của bộ truy vấn")
        unknown = {pid for qid in qids for pid in preds[qid]} - set(snap.products)
        if unknown:
            raise ValueError(f"{d.name}: dự đoán sản phẩm không hiển thị, kiểm tra --include-drafts")
        name = meta.get("name") or d.name
        if name in runs:
            raise ValueError(f"Hai run cùng tên {name!r}")
        runs[name] = preds
    return runs


def build_pools(queries, snap, top_k: int, n_random: int, seed: str, runs: dict | None = None
                ) -> tuple[dict, dict]:
    """qid → pool (thứ tự hash) và qid → {product_id: [nguồn@hạng]} (chỉ lưu hồ sơ, trang không hiện)."""
    engine = SearchEngine(snap)
    pools, sources = {}, {}
    for q in queries:
        found: dict[str, list[str]] = {}

        def add(ids, name):
            for rank, pid in enumerate(ids[:top_k], 1):
                found.setdefault(pid, []).append(f"{name}@{rank}")

        res = engine.search(q["query"], limit=top_k)
        add([r["id"] for r in res["results"]], "bm25")
        keywords = res["interpreted_query"]["keywords"]
        if keywords and keywords != q["query"]:
            add([r["id"] for r in engine.search(keywords, limit=top_k)["results"]], "bm25:keywords")
        for name, preds in (runs or {}).items():
            add(preds[q["qid"]], f"run:{name}")
        rest = sorted(set(snap.products) - set(found))
        add(random.Random(f"{seed}\0{q['qid']}").sample(rest, min(n_random, len(rest))), "random")
        pools[q["qid"]] = hash_order(q["qid"], found)
        sources[q["qid"]] = found
    return pools, sources


def make_packet(queries, snap, output: Path, pool_top: int | None = None, n_random: int = 5,
                seed: str = "vnstore-keyword-pool-1", pool_runs=()):
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
            # Capture the actual displayed bytes now; relative paths alone cannot
            # prove that an image has stayed unchanged when migrating old drafts.
            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest() if image_path else None,
            "sources": [{"url": snap.sources[s]["url"], "title": snap.sources[s].get("title")}
                        for s in p["source_ids"]],
        })
    packet = {"kind": "keyword_review", "review_content_version": 1,
              "catalog_sha256": snap.sha256, "catalog_version": snap.version,
              "queries": queries, "products": products,
              "candidate_order": {q["qid"]: hash_order(q["qid"], snap.products) for q in queries},
              "scope": "all_visible_catalog_products", "verified": False}
    if pool_top is not None:
        runs = load_pool_runs(pool_runs, snap, {q["qid"] for q in queries}) if pool_runs else {}
        pools, sources = build_pools(queries, snap, pool_top, n_random, seed, runs)
        # Pool đứng đầu danh sách, phần còn lại của catalog phía sau (đều theo thứ tự hash).
        packet["candidate_order"] = {qid: pool + [p for p in packet["candidate_order"][qid] if p not in pool]
                                     for qid, pool in pools.items()}
        packet.update(scope="pool_then_full_catalog_for_no_match", pool=pools, pool_sources=sources,
                      pool_policy={"top_k": pool_top, "random_per_query": n_random, "seed": seed,
                                   "systems": ["bm25", "bm25:keywords", *(f"run:{n}" for n in runs)]})
    return packet


def attach_suggestions(packet: dict, raw: bytes) -> None:
    data = json.loads(raw)
    if data.get("kind") != "keyword_relevance_suggestions" or data.get("catalog_sha256") != packet["catalog_sha256"]:
        raise ValueError("Gợi ý thuộc catalog khác hoặc sai định dạng")
    if packet["queries_sha256"] not in data["queries_sha256"]:
        raise ValueError("Gợi ý được lập cho bộ truy vấn khác")
    products = {p["id"] for p in packet["products"]}
    chosen = {}
    for q in packet["queries"]:
        entry = data["queries"].get(q["qid"])
        if entry is None:
            raise ValueError(f"{q['qid']}: thiếu gợi ý")
        rel = entry["relevance"]
        if set(rel) - products or any(type(v["score"]) is not int or not 0 <= v["score"] <= 3 for v in rel.values()):
            raise ValueError(f"{q['qid']}: gợi ý chứa sản phẩm ngoài packet hoặc điểm sai")
        missing = set(packet["pool"][q["qid"]] if "pool" in packet else products) - set(rel)
        if missing:
            raise ValueError(f"{q['qid']}: pool hiện tại có {len(missing)} sản phẩm chưa có gợi ý")
        chosen[q["qid"]] = {k: entry[k] for k in ("note", "scope", "suggested_has_answer", "relevance")}
    packet["suggestions"] = {"version": data["version"], "author": data["author"], "policy": data["policy"],
                             "queries": chosen}
    packet["suggestions_sha256"] = hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queries", type=Path, required=True)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pool-top", type=int, default=None, help="chỉ bắt buộc chấm pool top K + ngẫu nhiên")
    ap.add_argument("--random", type=int, default=5, help="số sản phẩm ngẫu nhiên thêm vào pool (với --pool-top)")
    ap.add_argument("--seed", default="vnstore-keyword-pool-1")
    ap.add_argument("--suggestions", type=Path, help="JSON gợi ý máy; tạo packet có hỗ trợ cho người chấm thứ nhất")
    ap.add_argument("--pool-runs", type=Path, nargs="+", default=(),
                    help="thư mục run eval_keyword.py; top K dự đoán mỗi run vào pool (cần --pool-top)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.out.exists():
        ap.error("Thư mục đầu ra đã tồn tại; chọn thư mục mới để giữ hồ sơ cũ")
    if (args.pool_top is not None and args.pool_top < 1) or args.random < 0:
        ap.error("--pool-top ≥ 1, --random ≥ 0")
    if args.pool_runs and args.pool_top is None:
        ap.error("--pool-runs cần --pool-top")
    try:
        queries = [json.loads(line) for line in args.queries.read_text(encoding="utf-8").splitlines() if line.strip()]
        snap = load_snapshot(args.catalog, include_drafts=args.include_drafts)
        packet = make_packet(queries, snap, args.out.resolve(), args.pool_top, args.random, args.seed,
                             args.pool_runs)
    except (ValueError, OSError, KeyError) as exc:
        ap.error(str(exc))
    packet["queries_sha256"] = hashlib.sha256(args.queries.read_bytes()).hexdigest()
    if args.suggestions:
        try:
            attach_suggestions(packet, args.suggestions.read_bytes())
        except (ValueError, OSError, KeyError, TypeError) as exc:
            ap.error(str(exc))
    payload = json.dumps(packet, ensure_ascii=False, indent=2)
    template = Path(__file__).with_name("review_template.html").read_text(encoding="utf-8")
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "packet.json").write_text(payload + "\n", encoding="utf-8")
    (args.out / "index.html").write_text(template.replace("__PACKET_JSON__", payload.replace("<", "\\u003c")), encoding="utf-8")
    if "pool" in packet:
        n = sum(map(len, packet["pool"].values()))
        print(f"{len(queries)} truy vấn, pool {n} cặp bắt buộc chấm (toàn catalog {len(queries)*len(snap.products)}); "
              f"truy vấn không có đáp án vẫn phải chấm đủ catalog. Nhãn chưa duyệt.")
    else:
        print(f"{len(queries)} truy vấn × {len(snap.products)} sản phẩm = {len(queries)*len(snap.products)} cặp cần người chấm. Nhãn chưa duyệt.")
    print(args.out / "index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
