"""Turn machine relevance suggestions into a MACHINE-LABELED query file (never human-verified labels).

    .venv/Scripts/python scripts/benchmark/machine_labels.py --suggestions benchmarks/keyword/suggestions/claude_assist_v1.json \
        --queries benchmarks/keyword/seed_unverified.jsonl --queries benchmarks/keyword/dev_candidates_unverified.jsonl \
        --out benchmarks/keyword/machine/claude_assist_v1_dev.jsonl

Rows keep verified=false and carry label_source="machine"; eval_keyword.py only accepts them with --machine-labels on
train/dev and records evaluation_status="machine_labeled". Use for a machine-judged baseline chosen by the project
owner; not for the locked test, and do not tune the system on these labels and then report gains on the same labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def build(suggestions: dict, raw_suggestions: bytes, query_rows: list[dict]) -> list[dict]:
    if suggestions.get("kind") != "keyword_relevance_suggestions":
        raise ValueError("not a keyword suggestion file")
    out = []
    for q in query_rows:
        entry = suggestions["queries"].get(q["qid"])
        if entry is None:
            raise ValueError(f"{q['qid']}: no machine suggestion")
        if q["split"] == "test":
            raise ValueError(f"{q['qid']}: machine labels are never used for the test split")
        relevance = {pid: v["score"] for pid, v in entry["relevance"].items()}
        out.append({
            "qid": q["qid"], "query": q["query"], "split": q["split"], "group_id": q.get("group_id", q["qid"]),
            **({"intent": q["intent"]} if "intent" in q else {}),
            "has_answer": any(s >= 2 for s in relevance.values()), "relevance": relevance,
            "labeled_by": f"{suggestions['version']} (máy)", "verified": False, "label_source": "machine",
            "label_scope": entry["scope"], "catalog_sha256": suggestions["catalog_sha256"],
            "suggestions_sha256": hashlib.sha256(raw_suggestions).hexdigest(),
        })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suggestions", type=Path, required=True)
    ap.add_argument("--queries", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    raw = args.suggestions.read_bytes()
    rows = [json.loads(line) for path in args.queries for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        labels = build(json.loads(raw), raw, rows)
    except (ValueError, KeyError) as exc:
        ap.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in labels), encoding="utf-8")
    print(f"{len(labels)} truy vấn nhãn máy ({sum(r['has_answer'] for r in labels)} có đáp án) → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
