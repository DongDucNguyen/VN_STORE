"""GĐ5: equal-budget, one-factor ablations; dev/train only, no automatic production selection.

python scripts/benchmark/ablate.py --modality image --split dev --families ... --split-plan ...
python scripts/benchmark/ablate.py --modality voice --split dev --queries ... --include-drafts
python scripts/benchmark/ablate.py --modality keyword --split dev --queries ... --include-drafts
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_runs as cr
import eval_keyword as ek
import screen_models as sm
import latency_protocol as lp
from app.catalog.store import load_snapshot
from app.search.config import SearchConfig
from app.search.engine import SearchEngine

DEFAULTS = {"VNSTORE_SEARCH_CONFIG": "{}", "VNSTORE_ASR_VAD": "1", "VNSTORE_VAD_THRESHOLD": "0.5",
            "VNSTORE_VAD_MIN_MS": "250", "VNSTORE_SILENCE_DBFS": "-60", "VNSTORE_OCR": "off",
            "VNSTORE_IMAGE_MULTI_VIEW": "1", "VNSTORE_IMAGE_CROPS": "", "VNSTORE_ML_TRT": "0",
            "VNSTORE_ML_DEVICE": "auto", "VNSTORE_ASR_MAX_NEW_TOKENS": "96",
            "VNSTORE_ASR_LANGUAGE": "vi", "VNSTORE_VOICE_MAX_GAIN_DB": "0", "VNSTORE_VOICE_HIGHPASS": "0"}
ENV_BY_MODALITY = {
    "keyword": set(),
    "voice": {"VNSTORE_ASR_VAD", "VNSTORE_VAD_THRESHOLD", "VNSTORE_VAD_MIN_MS", "VNSTORE_SILENCE_DBFS",
              "VNSTORE_ML_TRT", "VNSTORE_ML_DEVICE", "VNSTORE_ASR_MAX_NEW_TOKENS",
              "VNSTORE_ASR_LANGUAGE", "VNSTORE_VOICE_MAX_GAIN_DB", "VNSTORE_VOICE_HIGHPASS"},
    "image": {"VNSTORE_OCR", "VNSTORE_IMAGE_MULTI_VIEW", "VNSTORE_ML_TRT", "VNSTORE_ML_DEVICE"},
}
LANGUAGE_SETTINGS = {"accent_weight", "min_token_coverage", "strict_accents"}


def load_matrix(path: Path, modality: str) -> tuple[dict, list[dict]]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    group = spec[modality]
    candidates, variants = group["candidates"], group["variants"]
    if not candidates or not variants or variants[0] != {"name": "baseline"}:
        raise ValueError("matrix needs candidates and an unchanged baseline first")
    for items in (candidates, variants):
        names = [x["name"] for x in items]
        if len(names) != len(set(names)) or any(not sm.NAME.fullmatch(n) for n in names):
            raise ValueError("matrix names must be unique and safe")
    configs = []
    for candidate in candidates:
        if set(candidate) - ({"name"} if modality == "keyword" else {"name", "adapter"}):
            raise ValueError(f"unknown {modality} candidate fields")
        if modality != "keyword" and ":" not in candidate.get("adapter", ""):
            raise ValueError("candidate needs adapter")
        for variant in variants:
            if set(variant) - {"name", "search", "env", "requires_crops"}:
                raise ValueError("unknown variant fields")
            search = SearchConfig.from_dict(variant.get("search", {}))
            if modality != "image" and set(variant.get("search", {})) - LANGUAGE_SETTINGS:
                raise ValueError(f"image search settings are not used by {modality}")
            env = variant.get("env", {})
            if not isinstance(env, dict) or any(k not in DEFAULTS or not isinstance(v, str) for k, v in env.items()):
                raise ValueError("unknown/non-string ablation environment setting")
            if "VNSTORE_SEARCH_CONFIG" in env:
                raise ValueError("use the search object, not an encoded environment override")
            if set(env) - ENV_BY_MODALITY[modality]:
                raise ValueError(f"environment setting not used by {modality}")
            if type(variant.get("requires_crops", False)) is not bool:
                raise ValueError("requires_crops must be boolean")
            if variant.get("requires_crops") and modality != "image":
                raise ValueError(f"crops are not used by {modality}")
            cfg = {"name": f"{candidate['name']}-{variant['name']}", "candidate": candidate["name"],
                   "variant": variant["name"], "adapter": candidate.get("adapter"),
                   "requires_crops": variant.get("requires_crops", False),
                   "env": {**DEFAULTS, **env, "VNSTORE_SEARCH_CONFIG": json.dumps(search.to_dict())}}
            if not sm.NAME.fullmatch(cfg["name"]):
                raise ValueError("combined name too long")
            configs.append(cfg)
    return spec, configs


def paired_keyword(left, right, samples=2000):
    a, b = {r["qid"]: r for r in left}, {r["qid"]: r for r in right}
    if set(a) != set(b) or len(a) != len(left) or len(b) != len(right):
        raise cr.Incomparable("keyword qids changed or duplicated")
    for qid in a:
        for key in ("group_id", "has_answer", "split"):
            if a[qid].get(key) != b[qid].get(key):
                raise cr.Incomparable(f"{qid}: keyword {key} changed")
    result = {}
    for metric in ("ndcg_10", "success_5", "false_accept"):
        groups = {}
        for qid, row in a.items():
            other = b[qid]
            if row.get(metric) is None or other.get(metric) is None:
                continue
            pair = groups.setdefault(row["group_id"], ([], []))
            pair[0].append(row)
            pair[1].append(other)
        result[metric] = cr.bootstrap(list(groups.values()), lambda rs: cr.mean_of(rs, metric), samples, 13)
    return result


def keyword_runs(configs, args, out):
    snap = load_snapshot(args.catalog, include_drafts=args.include_drafts)
    query_hash = hashlib.sha256(args.queries.read_bytes()).hexdigest()
    queries = ek.load_queries(args.queries, set(snap.products), args.split, args.allow_unreviewed)
    def check_inputs():
        for path, expected in ((args.queries, query_hash), (args.catalog, snap.sha256)):
            try:
                unchanged = hashlib.sha256(path.read_bytes()).hexdigest() == expected
            except OSError:
                unchanged = False
            if not unchanged:
                raise ValueError(f"input changed during keyword evaluation: {path}")
    check_inputs()
    if any(q.get("catalog_sha256", snap.sha256) != snap.sha256 for q in queries):
        raise ValueError("keyword labels belong to another catalog")
    if not args.allow_unreviewed and any(q.get("catalog_sha256") != snap.sha256 for q in queries):
        raise ValueError("reviewed keyword labels require matching catalog_sha256")
    if not args.allow_unreviewed and any(not q["has_answer"] and set(q["relevance"]) != set(snap.products) for q in queries):
        raise ValueError("no-match labels must cover the entire visible catalog")
    if not queries:
        return []
    results = []
    for cfg in configs:
        engine = SearchEngine(snap, SearchConfig.from_dict(json.loads(cfg["env"]["VNSTORE_SEARCH_CONFIG"])))
        rows, metrics = ek.evaluate(queries, engine, args.warmup)
        timing = [[r["latency_ms"] for r in rows]]
        for _ in range(args.latency_rounds - 1):
            extra, _ = ek.evaluate(queries, engine, 0)
            timing.append([r["latency_ms"] for r in extra])
        metrics["search_ms"] = lp.rounds_summary(timing)
        for q, row in zip(queries, rows):
            row["group_id"] = q.get("group_id", q["qid"])
        check_inputs()
        directory = out / cfg["name"]
        directory.mkdir(parents=True)
        run = {"name": cfg["name"], "split": args.split, "catalog_sha256": snap.sha256,
               "include_drafts": snap.include_drafts,
               "queries_sha256": query_hash,
               "evaluation_status": "smoke_unreviewed" if args.allow_unreviewed else args.split,
               "config": engine.config.to_dict(), "metrics": metrics}
        (directory / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        (directory / "predictions.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        results.append({**cfg, "status": "ok", "run_dir": str(directory)})
    return results


def report_results(results, modality, spec, args):
    comparisons, baselines, issues = [], {}, []
    runs = {}
    for result in results:
        if result["status"] != "ok":
            issues.append(f"{result['name']}: {result['status']}")
            continue
        run, rows = cr.load_run(Path(result["run_dir"]))
        runs[result["name"]] = (run, rows)
        if result["variant"] == "baseline":
            baselines[result["candidate"]] = (run, rows)
        if run["evaluation_status"] != "dev" or run["split"] != "dev":
            issues.append(f"{result['name']}: not reviewed dev")
        if modality == "voice" and (not run.get("retrieval") or run["retrieval"].get("status") != "reviewed_pool"):
            issues.append(f"{result['name']}: missing reviewed retrieval labels")
        if run.get("skipped_unjudged_or_unreviewed"):
            issues.append(f"{result['name']}: not all dev queries evaluated")
        if modality == "image" and ({r["task"] for r in rows} != {"exact", "similar", "image_text"}
                                    or not any(not r["has_answer"] for r in rows)):
            issues.append(f"{result['name']}: missing task coverage (exact/similar/image_text/no_match)")
        if modality == "image" and run.get("split_plan", {}).get("status") != "locked":
            issues.append(f"{result['name']}: missing locked image split plan")
        if run["metrics"].get("ocr_errors") or run["metrics"].get("ocr_startup_errors"):
            issues.append(f"{result['name']}: OCR failed")
        if any(r.get("unjudged_at_10") or r.get("unjudged_at_20") for r in rows):
            issues.append(f"{result['name']}: expand and review the judgment pool")
        if modality == "keyword" and any(not r["has_answer"] and not r["judgments_cover_catalog"] for r in rows):
            issues.append(f"{result['name']}: no-match judgments do not cover catalog (smoke only)")
    if runs:
        first_run, first_rows = next(iter(runs.values()))
        for name, (run, rows) in runs.items():
            for key in ("catalog_sha256", "manifest_sha256", "queries_sha256", "split", "include_drafts", "split_plan"):
                if run.get(key) != first_run.get(key):
                    issues.append(f"{name}: changed {key} across candidates")
            if {r["qid"] for r in rows} != {r["qid"] for r in first_rows}:
                issues.append(f"{name}: changed query coverage across candidates")
    for result in results:
        if result["name"] not in runs or result["variant"] == "baseline":
            continue
        baseline = baselines.get(result["candidate"])
        if baseline is None:
            issues.append(f"{result['name']}: missing baseline")
            continue
        try:
            metrics = (paired_keyword(baseline[1], runs[result["name"]][1], args.samples) if modality == "keyword"
                       else cr.compare(baseline, runs[result["name"]], args.samples)["metrics"])
            if modality == "image":
                for task in ("similar", "image_text"):
                    left = [r for r in baseline[1] if r["task"] == task]
                    right = [r for r in runs[result["name"]][1] if r["task"] == task]
                    if left and right:
                        task_metrics = cr.compare((baseline[0], left), (runs[result["name"]][0], right), args.samples)["metrics"]
                        metrics[f"{task}_ndcg_10"] = task_metrics.get("ndcg_10", {})
            comparisons.append({"name": result["name"], "vs": baseline[0]["name"], "metrics": metrics})
            required = {"keyword": ("ndcg_10", "success_5", "false_accept"),
                        "voice": ("wer_normalized", "asr_ndcg_10", "asr_success_5", "asr_false_accept"),
                        "image": ("recall_5", "similar_ndcg_10", "image_text_ndcg_10", "false_accept", "false_reject")}
            for metric in required[modality]:
                if not metrics.get(metric, {}).get("ci95"):
                    issues.append(f"{result['name']}: insufficient clusters for {metric} CI")
        except cr.Incomparable as exc:
            issues.append(f"{result['name']}: {exc}")
    for candidate in spec[modality]["candidates"]:
        if not any(c["vs"] == f"{candidate['name']}-baseline" for c in comparisons):
            issues.append(f"{candidate['name']}: no successful ablation comparison")
    if modality != "keyword" and (spec.get("candidate_status") != "selected_on_reviewed_dev" or len(baselines) != 2):
        issues.append("The two finalists from GĐ4 have not been recorded as selected_on_reviewed_dev")
    if not results or (all(r["status"] in ("no_samples", "pending_crops") for r in results)
                       and any(r["status"] == "no_samples" for r in results)):
        status = "pending_collection"
    else:
        status = "needs_data_or_review" if issues else "ready_for_selection_review"
    return {"status": status, "modality": modality, "split": args.split,
            "selection": None, "issues": issues, "comparisons": comparisons, "results": results,
            "budget": {"variants_per_candidate": len(spec[modality]["variants"]),
                       "warmup": args.warmup, "latency_rounds": args.latency_rounds,
                       "timeout_seconds_each": args.timeout},
            "note": "Paired dev exploration, not independent confirmation. Inspect subgroup, entity, no-match and latency regressions before selecting; locked test is never tuned here."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modality", choices=("voice", "image", "keyword"), required=True)
    ap.add_argument("--split", choices=("train", "dev"), default="dev")
    ap.add_argument("--matrix", type=Path, default=ROOT / "experiments/configs/ablation.json")
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    for name in ("manifest", "queries", "families", "split-plan", "crops"):
        ap.add_argument("--" + name, type=Path)
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--allow-unreviewed", action="store_true")
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--latency-rounds", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--out-root", type=Path, default=ROOT / "experiments/ablations")
    args = ap.parse_args(argv)
    if min(args.latency_rounds, args.timeout, args.samples) < 1 or args.warmup < 0:
        ap.error("positive rounds/timeout/bootstrap and non-negative warmup required")
    if args.modality == "keyword" and not args.queries:
        ap.error("keyword requires --queries")
    now = datetime.now(timezone(timedelta(hours=7)))
    out = args.out_root / f"{now:%Y%m%d-%H%M%S-%f}_{args.modality}"
    try:
        matrix_hash = hashlib.sha256(args.matrix.read_bytes()).hexdigest()
        code = sorted((ROOT / "backend/app").rglob("*.py")) + sorted((ROOT / "scripts/benchmark").glob("*.py"))
        code_hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in code}
        spec, configs = load_matrix(args.matrix, args.modality)
        if args.modality == "keyword":
            results = keyword_runs(configs, args, out / "runs")
        else:
            passthrough = ["--split", args.split, "--catalog", str(args.catalog), "--warmup", str(args.warmup),
                           "--latency-rounds", str(args.latency_rounds)]
            for name in (("manifest", "queries") if args.modality == "voice" else ("manifest", "families", "split_plan")):
                if getattr(args, name):
                    passthrough += ["--" + name.replace("_", "-"), str(getattr(args, name))]
            if args.allow_unreviewed:
                passthrough += ["--allow-unreviewed"]
            if args.modality == "voice" and args.include_drafts:
                passthrough += ["--include-drafts"]
            results = []
            for cfg in configs:
                if cfg["requires_crops"]:
                    if not args.crops:
                        results.append({**cfg, "status": "pending_crops"})
                        continue
                    cfg["env"]["VNSTORE_IMAGE_CROPS"] = str(args.crops.resolve())
                result = sm.run_one(cfg, args.modality, passthrough, "ab", out / "runs", args.timeout, args.python)
                results.append({**cfg, **result})
        report = report_results(results, args.modality, spec, args)
    except (ValueError, KeyError, OSError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    report["matrix_sha256"] = matrix_hash
    report["code_sha256"] = code_hashes
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "matrix.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# GĐ5 {args.modality}: {report['status']}", "", report["note"], "", "## Runs", "",
             "| Configuration | Status |", "|---|---|"]
    lines += [f"| {r['name']} | {r['status']} |" for r in results]
    lines += ["", "## Gates", ""] + ["- " + i for i in report["issues"]]
    lines += ["", "## Paired comparisons to each model's baseline", "",
              "| Variant | Metric | Baseline | Variant | Delta | 95% CI | Clusters |",
              "|---|---|---|---|---|---|---|"]
    for comparison in report["comparisons"]:
        for key, metric in comparison["metrics"].items():
            lines.append(f"| {comparison['name']} | {key} | {metric.get('left')} | {metric.get('right')} | "
                         f"{metric.get('delta')} | {metric.get('ci95')} | {metric.get('clusters')} |")
    lines += ["", "No production config selected. Full metrics, resources and per-query errors remain in each run."]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{report['status']}: {out / 'report.md'}")
    return 2 if any(r["status"] not in ("ok", "no_samples", "pending_crops") for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
