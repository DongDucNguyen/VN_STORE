"""Build machine-assisted relevance SUGGESTIONS for keyword review packets (never labels).

Input: a judgments module (index-based, see benchmarks/keyword/suggestions/claude_assist_v1_judgments.py) and the
packets it was written against. Output: one JSON keyed by qid → product_id → {score, reason}, with the catalog
and query-set hashes it is valid for. prepare_review.py --suggestions embeds it in a separate "assisted" packet.

Checks: every pool member gets a suggestion (unlisted → 0); a query whose suggestions reach no 2–3 must have
been checked against the whole catalog (full=True), otherwise "no answer" would be unfounded.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = "claude-assist-v1"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("judgments", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(judgments: dict, packets: list[dict], extra_by_id: dict | None = None) -> dict:
    catalog = {p["catalog_sha256"] for p in packets}
    if len(catalog) != 1:
        raise ValueError("packets belong to different catalogs")
    order = [p["id"] for p in packets[0]["products"]]
    if any([p["id"] for p in packet["products"]] != order for packet in packets):
        raise ValueError("packets list products in a different order; indices would be ambiguous")
    queries = {q["qid"]: (q, packet) for packet in packets for q in packet["queries"]}
    if set(judgments) != set(queries):
        raise ValueError(f"judgments/packet qids differ: missing {sorted(set(queries) - set(judgments))}, "
                         f"extra {sorted(set(judgments) - set(queries))}")
    out = {}
    for qid, entry in judgments.items():
        q, packet = queries[qid]
        scores = entry["scores"]
        for index, (score, reason) in scores.items():
            if type(index) is not int or not 0 <= index < len(order):
                raise ValueError(f"{qid}: product index {index!r} out of range")
            if type(score) is not int or not 0 <= score <= 3 or not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"{qid}: suggestion needs score 0..3 and a reason")
        pool = packet["pool"][qid] if "pool" in packet else order
        suggested = {order[i]: {"score": s, "reason": r} for i, (s, r) in scores.items()}
        for pid, (score, reason) in (extra_by_id or {}).get(qid, {}).items():
            # Later additions judged by product id (e.g. new pool members after a catalog update).
            if pid not in order or type(score) is not int or not 0 <= score <= 3 or not reason.strip():
                raise ValueError(f"{qid}: invalid extra suggestion for {pid}")
            if pid in suggested and suggested[pid]["score"] != score:
                raise ValueError(f"{qid}: extra suggestion contradicts earlier score for {pid}")
            suggested.setdefault(pid, {"score": score, "reason": reason})
        filler = ("đã rà toàn catalog: không đáp ứng" if entry["full"] else "không đáp ứng loại/thuộc tính chính")
        for pid in (order if entry["full"] else pool):
            suggested.setdefault(pid, {"score": 0, "reason": filler})
        has_answer = any(v["score"] >= 2 for v in suggested.values())
        if not has_answer and not entry["full"]:
            raise ValueError(f"{qid}: no suggestion reaches 2; check the whole catalog and set full=True")
        out[qid] = {"note": entry["note"], "scope": "full_catalog" if entry["full"] else "pool_plus_listed",
                    "suggested_has_answer": has_answer, "draft_has_answer": q["has_answer"],
                    "relevance": dict(sorted(suggested.items()))}
    return {"kind": "keyword_relevance_suggestions", "version": VERSION, "catalog_sha256": catalog.pop(),
            "queries_sha256": sorted({p["queries_sha256"] for p in packets}),
            "author": "Claude (AI) — gợi ý máy, không phải nhãn",
            "policy": "Người chấm phải xem và quyết định từng cặp. Người chấm thứ hai dùng packet KHÔNG có gợi ý.",
            "queries": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--judgments", type=Path, required=True)
    ap.add_argument("--packet", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        packets = [json.loads(p.read_text(encoding="utf-8")) for p in args.packet]
        module = load_module(args.judgments)
        result = build(module.S, packets, getattr(module, "EXTRA_BY_ID", {}))
    except (ValueError, OSError, KeyError) as exc:
        ap.error(str(exc))
    result["judgments_sha256"] = hashlib.sha256(args.judgments.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    qs = result["queries"].values()
    pairs = sum(len(q["relevance"]) for q in qs)
    flips = [qid for qid, q in result["queries"].items() if q["suggested_has_answer"] != q["draft_has_answer"]]
    print(f"{len(result['queries'])} truy vấn, {pairs} cặp gợi ý; có đáp án theo gợi ý: "
          f"{sum(q['suggested_has_answer'] for q in qs)}; khác nhãn nháp cũ: {flips}")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
