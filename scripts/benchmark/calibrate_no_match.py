"""Explore image no-match thresholds on reviewed dev only. Never edits API settings.

This evaluates the reject/accept decision from raw top cosine, not retrieval quality after filtering.
Re-run eval_image with the proposed threshold, same queries/judgments, before selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from compare_runs import load_run


def calibrate(run, rows, max_false_reject=0.05):
    if run.get("split") != "dev" or run.get("evaluation_status") != "dev":
        raise ValueError("calibration requires reviewed dev; train/smoke/test forbidden")
    if (run.get("skipped_unjudged_or_unreviewed", 0) or run.get("metrics", {}).get("ocr_errors", 0)
            or run.get("metrics", {}).get("ocr_startup_errors")):
        raise ValueError("incomplete/failed run cannot calibrate")
    if not 0 <= max_false_reject <= 1:
        raise ValueError("max_false_reject must be in [0, 1]")
    if not rows or len({r["qid"] for r in rows}) != len(rows):
        raise ValueError("empty/duplicate qids")
    if any(r.get("split") != "dev" or type(r.get("has_answer")) is not bool or
           type(r.get("top_similarity")) not in (int, float) or not math.isfinite(r["top_similarity"]) or
           not -1 <= r["top_similarity"] <= 1 for r in rows):
        raise ValueError("invalid row split/labels/cosine")
    positives = sum(r["has_answer"] for r in rows)
    negatives = len(rows) - positives
    if not positives or not negatives:
        raise ValueError("both answerable and no-match queries are required")
    # Include boundaries on both sides of each observed score. The API accepts sim >= threshold.
    scores = {r["top_similarity"] for r in rows}
    thresholds = sorted({-1.0, 1.0, *scores, *(math.nextafter(v, math.inf) for v in scores if v < 1)})
    grid = []
    for threshold in thresholds:
        tp = sum(not r["has_answer"] and r["top_similarity"] < threshold for r in rows)
        fp = sum(r["has_answer"] and r["top_similarity"] < threshold for r in rows)
        fn = negatives - tp
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / negatives
        grid.append({"threshold": threshold, "precision_no_match": precision, "recall_no_match": recall,
                     "f1_no_match": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
                     "false_accept_rate": fn / negatives, "false_reject_rate": fp / positives})
    eligible = [x for x in grid if x["false_reject_rate"] <= max_false_reject]
    best = max(eligible, key=lambda x: (x["f1_no_match"], -x["false_reject_rate"], -x["threshold"]))
    groups = len({r["family_id"] for r in rows})
    return {"status": "dev_exploration_requires_retrieval_rerun", "n_positive": positives, "n_negative": negatives,
            "family_clusters": groups, "max_false_reject": max_false_reject,
            "candidate": best if groups >= 5 else None, "grid": grid,
            "note": "Not a selected production threshold. Top cosine ignores text/user filters. Replay the complete pipeline and check Recall/nDCG and subgroups; no test tuning."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-false-reject", type=float, default=0.05)
    args = ap.parse_args(argv)
    try:
        report = calibrate(*load_run(args.run), args.max_false_reject)
        report["inputs"] = {name: hashlib.sha256((args.run / name).read_bytes()).hexdigest()
                            for name in ("run.json", "predictions.jsonl")}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    except (ValueError, OSError, KeyError) as exc:
        ap.error(str(exc))
    print(f"Wrote {args.out}; rerun full retrieval before selection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
