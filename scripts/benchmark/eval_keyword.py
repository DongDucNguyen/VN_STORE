"""Đánh giá tìm kiếm keyword trên một bộ truy vấn có nhãn (PLAN.md mục 8.2).

    .venv/Scripts/python scripts/benchmark/eval_keyword.py --queries benchmarks/keyword/seed_unverified.jsonl --include-drafts --allow-unverified

Định dạng mỗi dòng JSONL (xem benchmarks/keyword/README.md):
    {"qid": "kw-0001", "query": "...", "split": "dev", "has_answer": true,
     "relevance": {"<product_id>": 0..3}, "labeled_by": "...", "verified": false}

Metric (relevance 0–3; "phù hợp" = relevance >= 2):
- nDCG@10: gain 2^rel - 1, discount log2(rank + 1); ideal từ các nhãn đã gán.
- Success@5, MRR@10, Recall@20: chỉ tính truy vấn has_answer = true.
- No-match: tỷ lệ truy vấn has_answer = false mà hệ thống vẫn trả kết quả (false accept).
- judged@10: tỷ lệ kết quả top 10 đã có nhãn. Kết quả chưa gán nhãn KHÔNG mặc định là không liên quan,
  metric ở cutoff có kết quả chưa gán nhãn trả null; báo riêng số truy vấn đủ nhãn.
Ghi per-query predictions + metrics vào experiments/results/<thời điểm>_keyword_<tên>/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import statistics
import sys
import time
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.catalog.store import load_snapshot  # noqa: E402
from app.search import engine as engine_mod  # noqa: E402
from app.search.engine import SearchEngine  # noqa: E402

RELEVANT = 2


def validate_queries(queries: list[dict], product_ids: set[str]) -> None:
    """Validate the entire input before split selection, including split leakage."""
    if not queries:
        raise ValueError("Bộ truy vấn rỗng")
    ids, groups, texts = set(), {}, {}
    for index, q in enumerate(queries, 1):
        if not isinstance(q, dict):
            raise ValueError(f"Dòng {index}: cần object")
        qid = q.get("qid")
        if not isinstance(qid, str) or not qid.strip() or qid in ids:
            raise ValueError(f"Dòng {index}: qid thiếu hoặc trùng: {qid!r}")
        ids.add(qid)
        query = q.get("query")
        if not isinstance(query, str) or not query.strip() or len(query) > 300:
            raise ValueError(f"{qid}: query cần 1–300 ký tự")
        if q.get("split") not in ("train", "dev", "test"):
            raise ValueError(f"{qid}: split không hợp lệ")
        if type(q.get("has_answer")) is not bool or type(q.get("verified")) is not bool:
            raise ValueError(f"{qid}: has_answer/verified phải là boolean")
        if not isinstance(q.get("labeled_by"), str) or not q["labeled_by"].strip():
            raise ValueError(f"{qid}: thiếu labeled_by")
        labels = q.get("relevance")
        if not isinstance(labels, dict) or any(type(v) is not int or not 0 <= v <= 3 for v in labels.values()):
            raise ValueError(f"{qid}: relevance phải chứa điểm nguyên 0..3")
        unknown = set(labels) - product_ids
        if unknown:
            raise ValueError(f"{qid}: ID sản phẩm không có trong catalog: {sorted(unknown)}")
        if q["has_answer"] != any(v >= RELEVANT for v in labels.values()):
            raise ValueError(f"{qid}: has_answer mâu thuẫn với relevance >= {RELEVANT}")
        group = q.get("group_id", qid)
        if not isinstance(group, str) or not group.strip():
            raise ValueError(f"{qid}: group_id không hợp lệ")
        normalized = " ".join(unicodedata.normalize("NFC", query).casefold().split())
        for key, seen in ((group, groups), (normalized, texts)):
            if key in seen and seen[key] != q["split"]:
                raise ValueError(f"{qid}: truy vấn/group xuất hiện ở nhiều split")
            seen[key] = q["split"]


def load_queries(path: Path, product_ids: set[str], split: str | None = None,
                 allow_unverified: bool = False) -> list[dict]:
    queries = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                queries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON không hợp lệ tại dòng {line_no}: {exc.msg}") from exc
    validate_queries(queries, product_ids)
    selected = [q for q in queries if split is None or q["split"] == split]
    if not selected:
        raise ValueError(f"Không có truy vấn trong split {split!r}")
    if any(not q["verified"] for q in selected):
        if any(q["split"] == "test" for q in selected):
            raise ValueError("Không chạy nhãn chưa duyệt trên split test")
        if not allow_unverified:
            raise ValueError("Nhãn chưa duyệt: chỉ chạy smoke với --allow-unverified")
    return selected


def dcg(rels: list[int]) -> float:
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels))


def evaluate(queries: list[dict], eng: SearchEngine, warmup: int = 1) -> tuple[list[dict], dict]:
    rows = []
    latencies = []
    for _ in range(warmup):
        for q in queries:
            eng.search(q["query"], limit=20)
    for q in queries:
        t = time.perf_counter()
        res = eng.search(q["query"], limit=20)
        ms = (time.perf_counter() - t) * 1000
        latencies.append(ms)
        ranked = [r["id"] for r in res["results"]]
        labels = q.get("relevance", {})
        # Unjudged results retain their rank and never silently become relevance=0.
        complete = {k: all(pid in labels for pid in ranked[:k]) for k in (5, 10, 20)}
        rels10 = [labels[pid] for pid in ranked[:10]] if complete[10] else None
        ideal = sorted(labels.values(), reverse=True)[:10]
        row = {
            "qid": q["qid"], "query": q["query"], "split": q.get("split"), "has_answer": q["has_answer"],
            "predictions": ranked, "latency_ms": round(ms, 3),
            "unjudged_at_20": [pid for pid in ranked[:20] if pid not in labels],
            "judgments_cover_catalog": set(labels) == set(eng.snap.products),
            "judged_at_10": (sum(1 for p in ranked[:10] if p in labels) / min(10, len(ranked))) if ranked else None,
            "interpreted": {"keywords": res["interpreted_query"].get("keywords"),
                            "price": res["interpreted_query"].get("price_label"),
                            "exclusions": [e["value"] for e in res["interpreted_query"]["exclusions"]]},
        }
        if q["has_answer"]:
            relevant = {p for p, r in labels.items() if r >= RELEVANT}
            first = next((i for i, p in enumerate(ranked[:10]) if p in relevant), None)
            row.update({
                "ndcg_10": (dcg(rels10) / dcg(ideal) if dcg(ideal) > 0 else 0.0) if complete[10] else None,
                "success_5": any(p in relevant for p in ranked[:5]) if complete[5] else None,
                "rr_10": (1 / (first + 1) if first is not None else 0.0) if complete[10] else None,
                "recall_20": len(relevant & set(ranked[:20])) / len(relevant) if relevant and complete[20] else None,
            })
        else:
            row["false_accept"] = bool(ranked)
        rows.append(row)

    ans = [r for r in rows if r["has_answer"]]
    neg = [r for r in rows if not r["has_answer"]]
    mean = lambda xs: round(sum(xs) / len(xs), 4) if xs else None  # noqa: E731
    lat = sorted(latencies)
    eligible = lambda key: [r[key] for r in ans if r[key] is not None]
    metrics = {
        "n_queries": len(rows), "n_with_answer": len(ans), "n_no_answer": len(neg),
        "ndcg_10": mean(eligible("ndcg_10")),
        "success_5": mean(eligible("success_5")),
        "mrr_10": mean(eligible("rr_10")),
        "recall_20": mean(eligible("recall_20")),
        "eligible_queries": {k: len(eligible(k)) for k in ("ndcg_10", "success_5", "rr_10", "recall_20")},
        "queries_with_unjudged_results": sum(bool(r["unjudged_at_20"]) for r in rows),
        "no_match_false_accept_rate": mean([float(r["false_accept"]) for r in neg]),
        "judged_at_10": mean([r["judged_at_10"] for r in rows if r["judged_at_10"] is not None]),
        "latency_ms_p50": round(statistics.median(lat), 3) if lat else None,
        "latency_ms_p95": round(lat[max(0, math.ceil(0.95 * len(lat)) - 1)], 3) if lat else None,
    }
    return rows, metrics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queries", type=Path, required=True)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--include-drafts", action="store_true", help="Đánh giá cả sản phẩm draft (chỉ để phát triển)")
    ap.add_argument("--split", choices=("train", "dev", "test"), default=None)
    ap.add_argument("--allow-unverified", action="store_true", help="Smoke trên train/dev; không dùng làm baseline")
    ap.add_argument("--warmup", type=int, default=1, help="Số vòng warm-up không tính latency")
    ap.add_argument("--name", default="bm25")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.name):
        ap.error("--name chỉ gồm chữ/số/gạch nối/gạch dưới, tối đa 80 ký tự")
    if not 0 <= args.warmup <= 100:
        ap.error("--warmup cần nằm trong 0..100")
    snap = load_snapshot(args.catalog, include_drafts=args.include_drafts)
    try:
        queries = load_queries(args.queries, {p["id"] for p in snap.data["products"]},
                               args.split, args.allow_unverified)
        hidden = {pid for q in queries for pid in q["relevance"]} - set(snap.products)
        if hidden:
            raise ValueError("Nhãn tham chiếu sản phẩm không hiển thị; kiểm tra --include-drafts")
        if not snap.products:
            raise ValueError("Catalog không có sản phẩm hiển thị")
        if any(q.get("catalog_sha256", snap.sha256) != snap.sha256 for q in queries):
            raise ValueError("Nhãn được duyệt trên catalog khác; cần đối chiếu lại catalog_sha256")
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    eng = SearchEngine(snap)
    rows, metrics = evaluate(queries, eng, args.warmup)

    unverified = sum(1 for q in queries if not q.get("verified"))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if unverified:
        print(f"CẢNH BÁO: {unverified}/{len(queries)} truy vấn có nhãn chưa được người kiểm tra duyệt — "
              f"không dùng làm baseline.")
    if metrics["queries_with_unjudged_results"]:
        print("CẢNH BÁO: còn kết quả chưa gán nhãn; xem eligible_queries, không so điểm các tập đủ nhãn khác nhau.")

    if not args.no_write:
        now = datetime.now(timezone(timedelta(hours=7)))
        out = ROOT / "experiments" / "results" / f"{now:%Y%m%d-%H%M%S-%f}_keyword_{args.name}"
        out.mkdir(parents=True, exist_ok=False)
        code_paths = sorted((ROOT / "backend/app").rglob("*.py")) + [Path(__file__), ROOT / "database.schema.json"]
        code_hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in code_paths}
        run = {
            "name": args.name,
            "created_at": now.isoformat(timespec="seconds"),
            "queries_file": str(args.queries.relative_to(ROOT)) if args.queries.is_relative_to(ROOT) else str(args.queries),
            "queries_sha256": hashlib.sha256(args.queries.read_bytes()).hexdigest(),
            "catalog_version": snap.version, "catalog_sha256": snap.sha256, "include_drafts": args.include_drafts,
            "split": args.split, "unverified_queries": unverified,
            "evaluation_status": "smoke_unverified" if unverified else "incomplete_judgments" if metrics["queries_with_unjudged_results"] else "reviewed_pool",
            "metric_policy": "Unjudged in top K => metric null; averages use eligible queries only. IDCG/Recall denominator uses known labels, not assumed complete relevance of catalog.",
            "latency_protocol": {"warmup_rounds": args.warmup, "measured_passes": 1, "scope": "in-process search only, excludes loading/index/API", "p50": "median", "p95": "nearest-rank"},
            "selected_qids": [q["qid"] for q in queries],
            "config": {**{name: sorted(value) if isinstance(value, set) else value
                            for name, value in vars(engine_mod).items() if name.isupper()},
                       "bm25": {"k1": next(iter(eng.index.fields.values())).k1,
                                "b": next(iter(eng.index.fields.values())).b}},
            "environment": {"python": platform.python_version(), "platform": platform.platform()},
            "code_commit": None,
            "code_sha256": hashlib.sha256(json.dumps(code_hashes, sort_keys=True).encode()).hexdigest(),
            "code_files_sha256": code_hashes,
            "metrics": metrics,
        }
        (out / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "predictions.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        print(f"Đã ghi {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
