"""Compare keyword runs only when snapshots, metric protocol and eligible qids match.

Read-only: never changes runs, labels or catalog. Latency is not compared because
the existing run format does not record hardware/load adequately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
METRICS = {"ndcg_10": "ndcg_10", "success_5": "success_5", "mrr_10": "rr_10",
           "recall_20": "recall_20", "no_match_false_accept_rate": "false_accept"}
EVALUATOR = "scripts/benchmark/eval_keyword.py"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def mean(values):
    return round(sum(values) / len(values), 4) if values else None


def validate_run(run: dict, rows: list[dict]) -> dict[str, dict]:
    require(isinstance(run, dict), "run.json must be an object")
    for field in ("catalog_sha256", "queries_sha256"):
        require(isinstance(run.get(field), str) and re.fullmatch(r"[0-9a-f]{64}", run[field]),
                f"Missing/invalid {field}")
    require(type(run.get("include_drafts")) is bool, "Missing include_drafts")
    require("split" in run and run["split"] in (None, "train", "dev", "test"), "Invalid split")
    require(isinstance(run.get("metric_policy"), str) and run["metric_policy"].strip(), "Missing metric_policy")
    code = run.get("code_files_sha256")
    require(isinstance(code, dict) and isinstance(code.get(EVALUATOR), str)
            and re.fullmatch(r"[0-9a-f]{64}", code[EVALUATOR]), "Missing evaluator hash; legacy run unsupported")
    qids = run.get("selected_qids")
    require(isinstance(qids, list) and qids and all(isinstance(q, str) and q.strip() for q in qids),
            "Missing selected_qids")
    require(len(qids) == len(set(qids)), "Duplicate selected_qids")
    require(isinstance(rows, list) and len(rows) == len(qids), "Prediction count mismatch")
    indexed = {}
    for row in rows:
        require(isinstance(row, dict), "Prediction must be an object")
        qid = row.get("qid")
        require(isinstance(qid, str) and qid in qids and qid not in indexed, "Unexpected/duplicate prediction qid")
        require(isinstance(row.get("query"), str) and row["query"].strip(), f"{qid}: missing query")
        require(row.get("split") in ("train", "dev", "test"), f"{qid}: invalid split")
        require(run["split"] is None or row["split"] == run["split"], f"{qid}: split disagrees with run")
        require(type(row.get("has_answer")) is bool, f"{qid}: invalid has_answer")
        require(type(row.get("judgments_cover_catalog")) is bool, f"{qid}: missing judgment coverage")
        ranked = row.get("predictions")
        require(isinstance(ranked, list) and all(isinstance(p, str) and p for p in ranked), f"{qid}: invalid predictions")
        require(len(ranked) <= 20 and len(ranked) == len(set(ranked)), f"{qid}: repeated/too many predictions")
        unjudged = row.get("unjudged_at_20")
        require(isinstance(unjudged, list) and all(isinstance(p, str) for p in unjudged)
                and len(unjudged) == len(set(unjudged)) and set(unjudged) <= set(ranked), f"{qid}: invalid unjudged list")
        if row["judgments_cover_catalog"]:
            require(not unjudged, f"{qid}: full coverage contradicts unjudged results")
        if row["has_answer"]:
            for key, cutoff in (("ndcg_10", 10), ("success_5", 5), ("rr_10", 10), ("recall_20", 20)):
                require(key in row, f"{qid}: missing {key}")
                value = row[key]
                incomplete = bool(set(ranked[:cutoff]) & set(unjudged))
                require((value is None) == incomplete, f"{qid}: {key} null policy mismatch")
                if value is not None:
                    if key == "success_5":
                        require(type(value) is bool, f"{qid}: success_5 must be boolean")
                    else:
                        require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1,
                                f"{qid}: invalid {key}")
        else:
            require(type(row.get("false_accept")) is bool and row["false_accept"] == bool(ranked),
                    f"{qid}: false_accept contradicts predictions")
        indexed[qid] = row
    require(set(indexed) == set(qids), "Prediction qids mismatch")
    unverified = run.get("unverified_queries")
    require(type(unverified) is int and 0 <= unverified <= len(rows), "Invalid unverified_queries")
    require(not unverified or all(r["split"] != "test" for r in rows), "Unverified test split")
    incomplete = sum(bool(r["unjudged_at_20"]) for r in rows)
    expected_status = "smoke_unverified" if unverified else "incomplete_judgments" if incomplete else "reviewed_pool"
    require(run.get("evaluation_status") == expected_status, "evaluation_status mismatch")
    summary = run.get("metrics")
    require(isinstance(summary, dict) and isinstance(summary.get("eligible_queries"), dict), "Missing metrics/eligible_queries")
    for key, value in {"n_queries": len(rows), "n_with_answer": sum(r["has_answer"] for r in rows),
                       "n_no_answer": sum(not r["has_answer"] for r in rows),
                       "queries_with_unjudged_results": incomplete}.items():
        require(type(summary.get(key)) is int and summary[key] == value, f"Summary mismatch: {key}")
    for aggregate, key in METRICS.items():
        eligible = cohort(indexed, key)
        expected = mean([indexed[q][key] for q in eligible])
        actual = summary.get(aggregate)
        require(aggregate in summary and (actual is None if expected is None else
                type(actual) in (int, float) and math.isfinite(actual) and abs(actual - expected) <= 1e-9),
                f"Summary mismatch: {aggregate}")
        if key != "false_accept":
            count = summary["eligible_queries"].get(key)
            require(type(count) is int and count == len(eligible), f"Eligible count mismatch: {key}")
    return indexed


def cohort(rows, key):
    return sorted(qid for qid, row in rows.items()
                  if row["has_answer"] == (key != "false_accept") and row.get(key) is not None)


def compare_runs(left, left_rows, right, right_rows):
    a, b = validate_run(left, left_rows), validate_run(right, right_rows)
    reasons = []
    for field in ("catalog_sha256", "queries_sha256", "include_drafts", "split", "metric_policy", "unverified_queries"):
        if left[field] != right[field]:
            reasons.append(f"Different {field}")
    if left["code_files_sha256"][EVALUATOR] != right["code_files_sha256"][EVALUATOR]:
        reasons.append("Different evaluator implementation; metric compatibility not established")
    if set(a) != set(b):
        reasons.append("Different selected qids")
    else:
        for qid in sorted(a):
            for key in ("query", "split", "has_answer", "judgments_cover_catalog"):
                if a[qid][key] != b[qid][key]:
                    reasons.append(f"{qid}: different {key}")
    cohorts = {}
    for aggregate, key in METRICS.items():
        ac, bc = cohort(a, key), cohort(b, key)
        cohorts[aggregate] = {"left": ac, "right": bc}
        if ac != bc:
            reasons.append(f"Different eligible qids: {aggregate}")
    report = {"status": "incompatible" if reasons else "comparable_descriptive",
              "reasons": reasons, "eligible_qids": cohorts,
              "scope": "Descriptive comparison only; not statistical significance, model selection or official baseline approval.",
              "unverified_labels": bool(left["unverified_queries"] or right["unverified_queries"]),
              "latency": {"status": "not_compared", "reason": "Runs lack a hardware/load record adequate for latency comparison."},
              "metrics": {}, "per_query": []}
    if reasons:
        return report
    for aggregate, key in METRICS.items():
        ids = cohorts[aggregate]["left"]
        av, bv = mean([a[q][key] for q in ids]), mean([b[q][key] for q in ids])
        report["metrics"][aggregate] = {"left": av, "right": bv,
            "delta_right_minus_left": round(bv - av, 4) if ids else None,
            "eligible_queries": len(ids), "better": "lower" if key == "false_accept" else "higher"}
    for qid in sorted(a):
        keys = ["false_accept"] if not a[qid]["has_answer"] else ["ndcg_10", "success_5", "rr_10", "recall_20"]
        report["per_query"].append({"qid": qid, "query": a[qid]["query"],
            "ranking_changed": a[qid]["predictions"] != b[qid]["predictions"],
            "deltas": {k: round(float(b[qid][k]) - float(a[qid][k]), 6)
                       if a[qid][k] is not None and b[qid][k] is not None else None for k in keys}})
    return report


def markdown(report):
    esc = lambda v: str(v).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    lines = ["# So sánh hai lần chạy keyword", "", f"- Trạng thái: **{report['status']}**",
             f"- Thời điểm: {report['generated_at']}", ""]
    for item in report["inputs"]:
        lines.append(f"- {item['side']} {item['kind']}: `{item['path']}`; SHA-256 `{item['sha256']}`")
    if report.get("error"):
        return "\n".join(lines + ["", esc(report["error"])]) + "\n"
    lines += ["", report["scope"], "", "Nhãn chưa duyệt — chỉ so sánh smoke, không phải baseline." if report["unverified_labels"]
              else "Có metadata nhãn đã duyệt; công cụ không xác minh danh tính hoặc nội dung chấm.",
              "", "Không so sánh latency do thiếu hồ sơ cấu hình máy/tải.", ""]
    if report["reasons"]:
        lines += ["## Không xuất chênh lệch điểm", ""] + [f"- {esc(r)}" for r in report["reasons"]]
    else:
        lines += ["| Metric | Trái | Phải | Phải − trái | Số query | Tốt hơn |", "|---|---|---|---|---|---|"]
        for key, v in report["metrics"].items():
            lines.append(f"| {key} | {v['left']} | {v['right']} | {v['delta_right_minus_left']} | {v['eligible_queries']} | {v['better']} |")
        lines += ["", f"Số truy vấn đổi thứ hạng: {sum(r['ranking_changed'] for r in report['per_query'])}.",
                  "Chi tiết từng truy vấn và tập đủ nhãn nằm trong JSON cùng tên. Null không được tính như 0."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--left", type=Path, required=True, help="run.json before change")
    ap.add_argument("--right", type=Path, required=True, help="run.json after change")
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports/benchmark")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    inputs, bundles = [], []
    try:
        for side, path in (("left", args.left), ("right", args.right)):
            pair = []
            for kind, file in (("run", path), ("predictions", path.with_name("predictions.jsonl"))):
                raw = file.read_bytes()
                inputs.append({"side": side, "kind": kind, "path": str(file), "sha256": hashlib.sha256(raw).hexdigest()})
                text = raw.decode("utf-8-sig")
                pair.append(json.loads(text) if kind == "run" else [json.loads(line) for line in text.splitlines() if line.strip()])
            bundles.append(pair)
        report = compare_runs(*bundles[0], *bundles[1])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        report = {"status": "invalid", "error": f"{type(exc).__name__}: {exc}"}
    now = datetime.now().astimezone()
    report.update(generated_at=now.isoformat(timespec="seconds"), inputs=inputs)
    report["comparison_policy"] = "keyword-comparison-v1"
    report["comparison_code_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    target = args.report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_keyword-comparison.json"
    with target.open("x", encoding="utf-8") as output:
        output.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    with target.with_suffix(".md").open("x", encoding="utf-8") as output:
        output.write(markdown(report))
    print(f"{report['status']}: {target}")
    return {"comparable_descriptive": 0, "invalid": 1, "incompatible": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
