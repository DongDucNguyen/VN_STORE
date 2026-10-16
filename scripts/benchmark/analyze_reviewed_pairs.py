"""Audit pair-level review exports and optionally diagnose retrieval on train/dev.

Preserves explicit/inferred evidence. Never promotes these exports to verified
benchmark queries or treats unreviewed/missing pairs as zero relevance.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieval_metrics import mean, ndcg_at, success_at  # noqa: E402
from app.search.normalize import normalize, strip_accents  # noqa: E402

STATUSES = {
    "human_corrected": "explicit_incorrect",
    "human_accepted_explicit": "explicit_correct",
    "human_accepted_inferred": "confirmed_scope",
    "unreviewed": "outside_confirmed_scope",
}
EXPLICIT = {"human_corrected", "human_accepted_explicit"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(row)
    if not rows:
        raise ValueError(f"{path}: empty export")
    return rows


def validate_pairs(rows: list[dict]) -> dict[tuple[str, str], dict]:
    pairs, queries = {}, {}
    for i, row in enumerate(rows, 1):
        for key in ("qid", "query", "product_id", "review_status", "review_evidence"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"row {i}: missing/invalid {key}")
        pair = row["qid"], row["product_id"]
        if pair in pairs:
            raise ValueError(f"duplicate pair: {pair}")
        if queries.setdefault(row["qid"], row["query"]) != row["query"]:
            raise ValueError(f"{pair}: inconsistent query")
        status = row["review_status"]
        if status not in STATUSES or type(row.get("is_human_reviewed")) is not bool:
            raise ValueError(f"{pair}: invalid review status/flag")
        if row["is_human_reviewed"] != (status != "unreviewed"):
            raise ValueError(f"{pair}: inconsistent review status/flag")
        for key in ("machine_score", "final_score", "corrected_score"):
            if key not in row:
                raise ValueError(f"{pair}: missing {key}")
            value = row[key]
            if key == "corrected_score" and value is None:
                continue
            if type(value) is not int or not 0 <= value <= 3:
                raise ValueError(f"{pair}: {key} must be integer 0..3 (or null for correction)")
        corrected = row["corrected_score"]
        if (corrected is not None) != (status == "human_corrected"):
            raise ValueError(f"{pair}: correction/status mismatch")
        expected = corrected if corrected is not None else row["machine_score"]
        if row["final_score"] != expected:
            raise ValueError(f"{pair}: final_score mismatch")
        if not isinstance(row.get("note"), str):
            raise ValueError(f"{pair}: note must be a string")
        try:
            ev = json.loads(row["review_evidence"])
        except ValueError as exc:
            raise ValueError(f"{pair}: invalid review_evidence JSON") from exc
        if not isinstance(ev, dict) or ev.get("type") != STATUSES[status]:
            raise ValueError(f"{pair}: evidence/status mismatch")
        if status in EXPLICIT:
            verdict = "incorrect" if status == "human_corrected" else "correct"
            if ev.get("verdict") != verdict or not ev.get("manual_export"):
                raise ValueError(f"{pair}: missing explicit evidence")
        if status == "human_accepted_inferred" and not ev.get("scope"):
            raise ValueError(f"{pair}: missing scope reference")
        pairs[pair] = row
    return pairs


def query_variant_checks(reviewed: list[dict], metadata: dict) -> dict:
    """Surface candidates for review, never adjudicate accent-ambiguous queries."""
    variants, judgments = defaultdict(list), defaultdict(list)
    for qid, query in metadata.items():
        key = strip_accents(normalize(query["query"]))
        variants[key].append({"qid": qid, "query": query["query"], "split": query["split"]})
    for row in reviewed:
        key = strip_accents(normalize(row["query"])), row["product_id"]
        judgments[key].append(row)
    conflicts = []
    for (query_key, pid), rows in judgments.items():
        if len({r["final_score"] for r in rows}) > 1:
            conflicts.append({"query_without_accents": query_key, "product_id": pid, "judgments": [
                {k: r[k] for k in ("qid", "query", "final_score", "review_status", "note")}
                for r in rows]})
    return {"conflicting_pairs": conflicts,
            "cross_split_candidates": [qs for qs in variants.values() if len({q["split"] for q in qs}) > 1],
            "interpretation": "Accent folding is ambiguous: candidates need adjudication, not automatic relabeling."}


def audit(rows: list[dict], reviewed: list[dict], sources: dict[str, list[dict]],
          product_ids: set[str], catalog_sha: str, catalog_lf_sha: str | None = None) -> tuple[dict, dict]:
    pairs, subset = validate_pairs(rows), validate_pairs(reviewed)
    expected = {key: r for key, r in pairs.items() if r["is_human_reviewed"]}
    if subset != expected:
        raise ValueError("reviewed export must exactly equal the is_human_reviewed=true subset")
    metadata, source_pairs = {}, set()
    for name, queries in sources.items():
        for line, query in enumerate(queries, 1):
            qid = query["qid"]
            if qid in metadata:
                raise ValueError(f"duplicate source qid: {qid}")
            if query.get("split") not in ("train", "dev"):
                raise ValueError(f"{qid}: only train/dev diagnostics allowed")
            if query.get("catalog_sha256") not in {catalog_sha, catalog_lf_sha or catalog_sha}:
                raise ValueError(f"{qid}: source catalog hash mismatch")
            metadata[qid] = {**query, "source_file": name, "source_line": line}
            for pid, score in query["relevance"].items():
                key = qid, pid
                source_pairs.add(key)
                if key not in pairs:
                    raise ValueError(f"missing source pair: {key}")
                r = pairs[key]
                if pid not in product_ids or type(score) is not int or not 0 <= score <= 3:
                    raise ValueError(f"{key}: invalid source product/score")
                ev = json.loads(r["review_evidence"])
                if (r["query"] != query["query"] or r["machine_score"] != score
                        or ev.get("source_file") != name or ev.get("source_line") != line):
                    raise ValueError(f"{key}: source query/score/provenance mismatch")
    if source_pairs != pairs.keys():
        raise ValueError("pair export contains pairs absent from source judgments")
    changed = [r for r in reviewed if r["machine_score"] != r["final_score"]]
    corrected = [r for r in reviewed if r["review_status"] == "human_corrected"]
    by_query = defaultdict(list)
    for r in reviewed:
        by_query[r["qid"]].append(r)
    cohorts = {}
    for status in STATUSES:
        selected = [r for r in rows if r["review_status"] == status]
        matrix = [[0] * 4 for _ in range(4)]
        for r in selected:
            matrix[r["machine_score"]][r["final_score"]] += 1
        cohorts[status] = {"pairs": len(selected), "machine_to_final": matrix}
    result = {
        "status": "exploratory_review_diagnostics", "pairs": len(rows),
        "catalog_match": "exact_bytes" if all(q["catalog_sha256"] == catalog_sha for q in metadata.values())
                         else "CRLF_to_LF_only",
        "reviewed_pairs": len(reviewed), "queries": len(metadata), "reviewed_queries": len(by_query),
        "cohorts": cohorts, "changed_scores": len(changed),
        "incorrect_verdict_unchanged_score": len(corrected) - len(changed),
        "relevance_threshold_changes": sum((r["machine_score"] >= 2) != (r["final_score"] >= 2)
                                           for r in reviewed),
        "full_catalog_reviewed_queries": sum(len(rs) == len(product_ids) for rs in by_query.values()),
        "partial_catalog_reviewed_queries": sum(len(rs) < len(product_ids) for rs in by_query.values()),
        "correction_notes": dict(Counter(r["note"] for r in corrected).most_common()),
        "most_corrected_queries": [
            {"qid": qid, "query": metadata[qid]["query"], "pairs": n}
            for qid, n in Counter(r["qid"] for r in corrected).most_common()],
        "query_variant_checks": query_variant_checks(reviewed, metadata),
        "limitations": [
            "Scope acceptance is inferred, not an independent per-pair confirmation.",
            "Explicit reviews are selected examples; their agreement is not population accuracy.",
            "Evidence references are preserved; original manual export/scope files are not authenticated here.",
            "Missing/unreviewed judgments are never zero; partial-pool IDCG uses known labels only.",
            "No official verification, reviewer identity, timestamp or locked-test acceptance is fabricated.",
        ],
    }
    return result, metadata


def evaluate(reviewed: list[dict], metadata: dict, engine) -> dict:
    by_query = defaultdict(list)
    for row in reviewed:
        by_query[row["qid"]].append(row)
    predictions = []
    for qid, rows in by_query.items():
        visible = [r for r in rows if r["product_id"] in engine.snap.products]
        result = engine.search(rows[0]["query"], limit=10)
        ranked = [p["id"] for p in result["results"]]
        metrics = {}
        for cohort in ("all_reviewed", "explicit_only"):
            labels = {r["product_id"]: r["final_score"] for r in visible
                      if cohort == "all_reviewed" or r["review_status"] in EXPLICIT}
            # No positives in a partial pool does not establish that the query is a no-match.
            positive = any(v >= 2 for v in labels.values())
            complete = set(labels) == set(engine.snap.products)
            metrics[cohort] = {
                "judged_pairs": len(labels), "covers_catalog": complete, "known_positive": positive,
                "ndcg_at_10": ndcg_at(ranked, labels) if positive else None,
                "success_at_5": success_at(ranked, labels) if positive else None,
                "false_accept": bool(ranked) if complete and not positive else None,
            }
        predictions.append({"qid": qid, "query": rows[0]["query"], "split": metadata[qid]["split"],
                            "ranked": ranked, "metrics": metrics})
    aggregates = {}
    for split in ("train", "dev"):
        aggregates[split] = {}
        for cohort in ("all_reviewed", "explicit_only"):
            values = [p["metrics"][cohort] for p in predictions if p["split"] == split]
            aggregates[split][cohort] = {
                metric: {"mean": mean(v[metric] for v in values),
                         "eligible_queries": sum(v[metric] is not None for v in values)}
                for metric in ("ndcg_at_10", "success_at_5", "false_accept")}
    return {"config": engine.config.to_dict(), "include_drafts": engine.snap.include_drafts,
            "visible_products": len(engine.snap.products), "aggregates": aggregates, "queries": predictions}


def compare(before: dict, after: dict) -> dict:
    if (before["inputs"] != after["inputs"]
            or before["evaluation"]["include_drafts"] != after["evaluation"]["include_drafts"]):
        raise ValueError("comparison requires identical input hashes and catalog visibility")
    old = {r["qid"]: r for r in before["evaluation"]["queries"]}
    output = {}
    for split in ("train", "dev"):
        output[split] = {}
        for cohort in ("all_reviewed", "explicit_only"):
            common = []
            for row in after["evaluation"]["queries"]:
                if row["split"] != split or row["qid"] not in old:
                    continue
                a = old[row["qid"]]["metrics"][cohort]["ndcg_at_10"]
                b = row["metrics"][cohort]["ndcg_at_10"]
                if a is not None and b is not None:
                    common.append({"qid": row["qid"], "query": row["query"], "before": a, "after": b,
                                   "delta": b - a})
            output[split][cohort] = {
                "common_eligible_queries": len(common), "before": mean(r["before"] for r in common),
                "after": mean(r["after"] for r in common), "mean_delta": mean(r["delta"] for r in common),
                "improved": sum(r["delta"] > 1e-9 for r in common),
                "regressed": sum(r["delta"] < -1e-9 for r in common),
                "changes": sorted([r for r in common if abs(r["delta"]) > 1e-9], key=lambda r: r["delta"]),
            }
    return output


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", type=Path, default=ROOT / "all_labels_review_status.jsonl")
    ap.add_argument("--reviewed", type=Path, default=ROOT / "human_reviewed_labels.jsonl")
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--baseline", type=Path)
    args = ap.parse_args(argv)
    if args.baseline and not args.evaluate:
        ap.error("--baseline requires --evaluate")
    rows, reviewed = read_jsonl(args.all), read_jsonl(args.reviewed)
    validate_pairs(rows)
    sources, source_hashes = {}, {}
    for name in sorted({json.loads(r["review_evidence"]).get("source_file", "") for r in rows}):
        path = (ROOT / name).resolve()
        if not name or ROOT.resolve() not in path.parents:
            raise ValueError("source_file must point inside the repository")
        sources[name], source_hashes[name] = read_jsonl(path), digest(path)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    lf_sha = hashlib.sha256(args.catalog.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    result, metadata = audit(rows, reviewed, sources, {p["id"] for p in catalog["products"]},
                             digest(args.catalog), lf_sha)
    result["inputs"] = {"all": digest(args.all), "reviewed": digest(args.reviewed),
                        "catalog": digest(args.catalog), "catalog_lf": lf_sha, "sources": source_hashes}
    result["code_hashes"] = {str(p.relative_to(ROOT)): digest(p)
                             for p in sorted((ROOT / "backend/app/search").glob("*.py"))}
    result["code_hashes"][str(Path(__file__).resolve().relative_to(ROOT))] = digest(Path(__file__))
    if args.evaluate:
        from app.catalog.store import load_snapshot
        from app.search.config import SearchConfig
        from app.search.engine import SearchEngine
        engine = SearchEngine(load_snapshot(args.catalog, include_drafts=args.include_drafts), SearchConfig())
        result["evaluation"] = evaluate(reviewed, metadata, engine)
    if args.baseline:
        result["comparison"] = compare(json.loads(args.baseline.read_text(encoding="utf-8")), result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("pairs", "reviewed_pairs", "changed_scores",
                                           "partial_catalog_reviewed_queries")}, ensure_ascii=False))
    if args.evaluate:
        print(json.dumps(result["evaluation"]["aggregates"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
