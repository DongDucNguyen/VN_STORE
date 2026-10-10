"""Synthetic run comparisons; these are not human benchmark judgments."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/benchmark" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


comparison = module("compare_keyword")
evaluation = module("eval_keyword")


def bundle(rankings=None, unverified=0):
    rankings = rankings or {"first": ["a", "b"], "second": ["a"], "negative": []}

    class Engine:
        snap = SimpleNamespace(products={"a": {}, "b": {}, "unjudged": {}})

        def search(self, query, limit):
            return {"results": [{"id": p} for p in rankings[query]],
                    "interpreted_query": {"keywords": query, "price_label": None, "exclusions": []}}

    queries = [{"qid": name, "query": name, "has_answer": name != "negative", "split": "dev",
                "relevance": {"a": 3, "b": 1} if name != "negative" else {"a": 0, "b": 0}}
               for name in ("first", "second", "negative")]
    rows, metrics = evaluation.evaluate(queries, Engine(), warmup=0)
    run = {"catalog_sha256": "a" * 64, "queries_sha256": "b" * 64, "include_drafts": True,
           "split": "dev", "metric_policy": "synthetic", "unverified_queries": unverified,
           "code_files_sha256": {comparison.EVALUATOR: "c" * 64},
           "selected_qids": [q["qid"] for q in queries], "metrics": metrics,
           "evaluation_status": "smoke_unverified" if unverified else
               "incomplete_judgments" if metrics["queries_with_unjudged_results"] else "reviewed_pool"}
    return run, rows


def test_reordering_qids_does_not_change_comparability():
    a, rows = bundle()
    b = copy.deepcopy(a)
    b["selected_qids"].reverse()
    report = comparison.compare_runs(a, rows, b, list(reversed(rows)))
    assert report["status"] == "comparable_descriptive"
    assert all(v["delta_right_minus_left"] == 0 for v in report["metrics"].values())
    assert report["latency"]["status"] == "not_compared"


def test_changed_ranking_and_no_match_are_reported_separately():
    a, ar = bundle()
    b, br = bundle({"first": ["b", "a"], "second": ["a"], "negative": ["b"]})
    report = comparison.compare_runs(a, ar, b, br)
    assert report["status"] == "comparable_descriptive"
    assert report["metrics"]["ndcg_10"]["delta_right_minus_left"] < 0
    assert report["metrics"]["no_match_false_accept_rate"]["delta_right_minus_left"] == 1
    assert report["metrics"]["no_match_false_accept_rate"]["better"] == "lower"
    assert sum(r["ranking_changed"] for r in report["per_query"]) == 2


@pytest.mark.parametrize("field,value", [("catalog_sha256", "d" * 64), ("queries_sha256", "e" * 64),
                                        ("include_drafts", False), ("split", None), ("metric_policy", "other")])
def test_different_snapshots_or_protocol_do_not_emit_deltas(field, value):
    a, rows = bundle()
    b = copy.deepcopy(a); b[field] = value
    report = comparison.compare_runs(a, rows, b, rows)
    assert report["status"] == "incompatible"
    assert report["metrics"] == {} and report["per_query"] == []


def test_evaluator_change_rejected_but_search_config_change_allowed():
    a, rows = bundle()
    b = copy.deepcopy(a); b["config"] = {"weight": 2}
    assert comparison.compare_runs(a, rows, b, rows)["status"] == "comparable_descriptive"
    b["code_files_sha256"][comparison.EVALUATOR] = "f" * 64
    assert comparison.compare_runs(a, rows, b, rows)["status"] == "incompatible"


def test_equal_eligible_counts_with_different_qids_are_rejected():
    a, ar = bundle({"first": ["unjudged"], "second": ["a"], "negative": []})
    b, br = bundle({"first": ["a"], "second": ["unjudged"], "negative": []})
    assert a["metrics"]["eligible_queries"] == b["metrics"]["eligible_queries"]
    report = comparison.compare_runs(a, ar, b, br)
    assert report["status"] == "incompatible"
    assert "Different eligible qids: ndcg_10" in report["reasons"]


def test_no_eligible_queries_stay_null():
    a, rows = bundle({"first": ["unjudged"], "second": ["unjudged"], "negative": []}, unverified=3)
    report = comparison.compare_runs(a, rows, a, rows)
    assert report["unverified_labels"] is True
    assert report["metrics"]["ndcg_10"] == {"left": None, "right": None,
        "delta_right_minus_left": None, "eligible_queries": 0, "better": "higher"}
    assert comparison.markdown({**report, "generated_at": "test", "inputs": []}).find("smoke") >= 0


@pytest.mark.parametrize("key,value", [("ndcg_10", float("nan")), ("recall_20", float("inf")),
    ("rr_10", -1), ("ndcg_10", True), ("success_5", 1), ("ndcg_10", None),
    ("predictions", ["a", "a"]), ("unjudged_at_20", ["absent"]), ("has_answer", 1)])
def test_bad_prediction_values_rejected(key, value):
    run, rows = bundle(); rows[0][key] = value
    with pytest.raises(ValueError):
        comparison.validate_run(run, rows)


@pytest.mark.parametrize("change", ["aggregate", "count", "eligible", "status", "missing_evaluator", "duplicate_qid", "missing_row"])
def test_inconsistent_run_rejected(change):
    run, rows = bundle()
    if change == "aggregate": run["metrics"]["ndcg_10"] = .1234
    elif change == "count": run["metrics"]["n_queries"] = 10
    elif change == "eligible": run["metrics"]["eligible_queries"]["ndcg_10"] = 10
    elif change == "status": run["evaluation_status"] = "smoke_unverified"
    elif change == "missing_evaluator": run.pop("code_files_sha256")
    elif change == "duplicate_qid": rows[1]["qid"] = rows[0]["qid"]
    elif change == "missing_row": rows.pop()
    with pytest.raises(ValueError):
        comparison.validate_run(run, rows)


def test_query_text_change_rejected_despite_same_claimed_hash():
    a, ar = bundle(); b, br = bundle(); br[0]["query"] = "changed"
    assert comparison.compare_runs(a, ar, b, br)["status"] == "incompatible"


def test_false_accept_must_agree_with_ranking():
    run, rows = bundle(); rows[-1]["false_accept"] = True
    with pytest.raises(ValueError, match="false_accept"):
        comparison.validate_run(run, rows)


@pytest.mark.parametrize("mode,exit_code,status", [("valid", 0, "comparable_descriptive"),
    ("incompatible", 2, "incompatible"), ("missing", 1, "invalid"), ("bad_json", 1, "invalid")])
def test_cli_writes_auditable_reports_without_changing_inputs(tmp_path, monkeypatch, mode, exit_code, status):
    before = {}
    for side in ("left", "right"):
        d = tmp_path / side; d.mkdir()
        run, rows = bundle(unverified=3)
        if side == "right" and mode == "incompatible": run["catalog_sha256"] = "f" * 64
        (d / "run.json").write_text(json.dumps(run), encoding="utf-8")
        if side == "right" and mode == "missing": continue
        raw = "\n".join(json.dumps(r) for r in rows)
        (d / "predictions.jsonl").write_text("{" if side == "right" and mode == "bad_json" else raw, encoding="utf-8")
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    monkeypatch.setattr("sys.argv", ["compare_keyword.py", "--left", str(tmp_path / "left/run.json"),
        "--right", str(tmp_path / "right/run.json"), "--report-dir", str(tmp_path / "reports")])
    assert comparison.main() == exit_code
    output = list((tmp_path / "reports").glob("*.json"))
    assert len(output) == 1 and output[0].with_suffix(".md").exists()
    report = json.loads(output[0].read_bytes())
    assert report["status"] == status and report["inputs"]
    assert report["comparison_policy"] == "keyword-comparison-v1"
    assert len(report["comparison_code_sha256"]) == 64
    assert all(p.read_bytes() == raw for p, raw in before.items())
