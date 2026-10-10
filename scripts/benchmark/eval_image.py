"""Đánh giá tìm bằng ảnh trên bộ query độc lập (PLAN.md mục 7, 8.2).

    .venv/Scripts/python scripts/benchmark/eval_image.py --adapter my_pkg.image:SigLIP2Base --split dev --name siglip2-base

Chạy audit_image_queries.audit() trước; manifest sai thì dừng. Gallery = ảnh catalog cố định (theo
include_drafts của manifest), dựng chỉ mục trong bộ nhớ hoặc nạp từ --index-dir nếu khớp. Mọi query đi
qua đúng đường của API: embedding → cosine gộp theo sản phẩm → SearchEngine.search_visual (+ text_vi).
- exact: Recall@1/5/10 và MRR@10 theo exact_product_id.
- similar, image_text: nDCG@10, mAP@10, Success@5 (retrieval_metrics.py; chưa chấm đủ top K → None).
- no-match: chưa có ngưỡng đã hiệu chỉnh, nên chỉ ghi phân bố top_similarity của query có/không có đáp án
  để chọn ngưỡng trên dev; không báo false accept giả định.
Ghi run.json + predictions.jsonl vào experiments/results/<thời điểm>_image_<tên>/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import retrieval_metrics as rm  # noqa: E402
from audit_image_queries import audit  # noqa: E402

from app.adapters import AdapterError, ImageEmbedder, load_adapter  # noqa: E402
from app.catalog.store import CatalogSnapshot, load_snapshot  # noqa: E402
from app.image.index import ImageIndex, IndexUnavailable  # noqa: E402
from app.search.engine import SearchEngine  # noqa: E402

MANIFEST = ROOT / "benchmarks" / "image" / "manifest.json"
TOP = 20


def usable(sample: dict, allow_unreviewed: bool) -> bool:
    if sample["judgment"] is None:
        return False
    review = sample["independence_review"]
    if review is not None and not review["independent"]:
        return False
    rights_ok = sample["usage_rights"]["status"] != "unknown"
    return allow_unreviewed or (review is not None and rights_ok)


def get_index(snap: CatalogSnapshot, embedder: ImageEmbedder, index_dir: Path | None) -> tuple[ImageIndex, str]:
    if index_dir is not None:
        try:
            index = ImageIndex.load(index_dir)
            index.check(snap, embedder)
            return index, "loaded"
        except IndexUnavailable as e:
            print(f"Không dùng được chỉ mục {index_dir}: {e}; dựng lại trong bộ nhớ.")
    return ImageIndex.build(snap, embedder), "built_in_memory"


def score(sample: dict, ranked: list[str]) -> dict:
    j = sample["judgment"]
    labels = j["relevance"]
    out: dict = {}
    if not j["has_answer"]:
        return out
    if sample["task"] == "exact":
        target = j["exact_product_id"]
        out.update({f"recall_{k}": rm.exact_recall_at(ranked, target, k) for k in (1, 5, 10)})
        out["rr_10"] = rm.exact_rr_at(ranked, target, 10)
    else:
        out.update({"ndcg_10": rm.ndcg_at(ranked, labels, 10), "ap_10": rm.ap_at(ranked, labels, 10),
                    "success_5": rm.success_at(ranked, labels, 5)})
    return out


def evaluate(samples: list[dict], base: Path, embedder: ImageEmbedder, index: ImageIndex, engine: SearchEngine,
             warmup: int = 1) -> tuple[list[dict], dict]:
    data = {s["qid"]: (base / s["image_path"]).read_bytes() for s in samples}
    for s in samples[:warmup]:
        embedder.embed([data[s["qid"]]])
    allowed = set(engine.snap.products)
    rows = []
    for s in samples:
        t = time.perf_counter()
        (vec,) = embedder.embed([data[s["qid"]]])
        ms = (time.perf_counter() - t) * 1000
        hits = index.query(vec, allowed)
        res = engine.search_visual(hits, s["text_vi"] or "", limit=TOP)
        ranked = [r["id"] for r in res["results"]]
        rows.append({"qid": s["qid"], "task": s["task"], "split": s["split"], "family_id": s["family_id"],
                     "text_vi": s["text_vi"], "has_answer": s["judgment"]["has_answer"],
                     "predictions": ranked, "top_similarity": hits[0].similarity if hits else None,
                     "applied_filters": [a["label"] for a in res["applied_filters"]],
                     "unjudged_at_10": [p for p in ranked[:10] if p not in s["judgment"]["relevance"]],
                     "embed_ms": round(ms, 2), **score(s, ranked)})
    return rows, summarize(rows)


def summarize(rows: list[dict]) -> dict:
    def task(name: str) -> list[dict]:
        return [r for r in rows if r["task"] == name and r["has_answer"]]

    exact = task("exact")

    def ranking(rs: list[dict]) -> dict:
        return {"n": len(rs), **{k: rm.mean([r[k] for r in rs]) for k in ("ndcg_10", "ap_10", "success_5")},
                "eligible": {k: sum(r[k] is not None for r in rs) for k in ("ndcg_10", "ap_10", "success_5")}}

    sims = lambda rs: [r["top_similarity"] for r in rs if r["top_similarity"] is not None]  # noqa: E731
    neg = [r for r in rows if not r["has_answer"]]
    pos = [r for r in rows if r["has_answer"]]
    lat = [r["embed_ms"] for r in rows]
    return {
        "n_queries": len(rows), "n_no_answer": len(neg),
        "exact": {"n": len(exact), **{f"recall_{k}": rm.mean([r[f"recall_{k}"] for r in exact]) for k in (1, 5, 10)},
                  "mrr_10": rm.mean([r["rr_10"] for r in exact])},
        "similar": ranking(task("similar")),
        "image_text": ranking(task("image_text")),
        "no_match_calibration": {
            "top_similarity_p50_no_answer": rm.percentile(sims(neg), 0.5),
            "top_similarity_p50_with_answer": rm.percentile(sims(pos), 0.5),
            "note": "Chưa có ngưỡng; chọn ngưỡng trên dev rồi mới báo precision/recall no-match.",
        },
        "embed_ms_p50": rm.percentile(lat, 0.5), "embed_ms_p95": rm.percentile(lat, 0.95),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", required=True, help="module:thuộc_tính của ImageEmbedder")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--split", choices=("train", "dev", "test"), required=True)
    ap.add_argument("--index-dir", type=Path, default=None, help="thư mục chỉ mục đã dựng (manifest.json)")
    ap.add_argument("--allow-unreviewed", action="store_true", help="smoke trên train/dev khi review chưa đủ")
    ap.add_argument("--confirm-locked-test", action="store_true")
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--name", default="image")
    ap.add_argument("--out-root", type=Path, default=ROOT / "experiments" / "results")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.name):
        ap.error("--name chỉ gồm chữ/số/gạch nối/gạch dưới, tối đa 80 ký tự")
    if args.split == "test" and (args.allow_unreviewed or not args.confirm_locked_test):
        print("invalid: split test cần --confirm-locked-test và không nhận --allow-unreviewed", file=sys.stderr)
        return 1

    report = audit(args.manifest, args.catalog)
    if report["status"] == "invalid":
        print(f"invalid: audit manifest thất bại ({len(report['issues'])} lỗi); chạy audit_image_queries.py",
              file=sys.stderr)
        return 1
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    in_split = [s for s in manifest["samples"] if s["split"] == args.split]
    samples = [s for s in in_split if usable(s, args.allow_unreviewed)]
    if not samples:
        print(f"{report['status']}: split {args.split} có {len(in_split)} query, 0 query dùng được để chấm; "
              f"không ghi kết quả.")
        return 0
    try:
        embedder = load_adapter(args.adapter, ImageEmbedder)
    except AdapterError as e:
        print(e, file=sys.stderr)
        return 2
    snap = load_snapshot(args.catalog, include_drafts=manifest["include_drafts"])
    index, index_source = get_index(snap, embedder, args.index_dir)
    rows, metrics = evaluate(samples, args.manifest.parent, embedder, index, SearchEngine(snap), args.warmup)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    now = datetime.now(timezone(timedelta(hours=7)))
    out = args.out_root / f"{now:%Y%m%d-%H%M%S-%f}_image_{args.name}"
    out.mkdir(parents=True, exist_ok=False)
    code = [Path(__file__), Path(rm.__file__), ROOT / "backend/app/image/index.py", ROOT / "backend/app/search/engine.py"]
    run = {
        "name": args.name, "created_at": now.isoformat(timespec="seconds"),
        "evaluation_status": "smoke_unreviewed" if report["status"] != "recorded_checks_passed"
        else ("locked_test" if args.split == "test" else "dev"),
        "audit_status": report["status"], "benchmark_approved": False,
        "model": {"adapter": args.adapter, "model_id": embedder.model_id, "revision": embedder.revision,
                  "preprocess": getattr(embedder, "preprocess", None), "license": getattr(embedder, "license", None)},
        "index": {"source": index_source, "entries": len(index.entries), "dim": index.dim},
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "catalog_version": snap.version, "catalog_sha256": snap.sha256, "include_drafts": snap.include_drafts,
        "split": args.split, "selected_qids": [s["qid"] for s in samples],
        "skipped_unjudged_or_unreviewed": len(in_split) - len(samples),
        "metric_policy": "relevance 0..3, relevant >= 2; nDCG gain 2^r-1, log2(rank+1); mAP@10 / min(#relevant,10); "
                         "unjudged in top K => None; exact = product-level",
        "latency_protocol": {"warmup_queries": args.warmup, "batch": 1, "scope": "embedder.embed only"},
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "code_files_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in code},
        "metrics": metrics,
    }
    (out / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "predictions.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                                           encoding="utf-8")
    print(f"Đã ghi {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
