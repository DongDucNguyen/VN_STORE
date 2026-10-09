"""Metric correctness and invalid-dataset regression tests (synthetic rankings)."""
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/benchmark/eval_keyword.py"
spec = importlib.util.spec_from_file_location("keyword_eval", SCRIPT)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def query(**changes):
    return {"qid": "q1", "query": "test", "split": "dev", "has_answer": True,
            "relevance": {"a": 3, "b": 2}, "labeled_by": "test-human", "verified": True, **changes}


class FixedEngine:
    def __init__(self, ranking):
        self.ranking = ranking
        self.snap = SimpleNamespace(products={p: {} for p in ("a", "b", "c")})
        self.calls = 0

    def search(self, text, limit):
        self.calls += 1
        return {"results": [{"id": p} for p in self.ranking],
                "interpreted_query": {"keywords": text, "price_label": None, "exclusions": []}}


def test_known_rankings_metrics():
    rows, metrics = evaluation.evaluate([query()], FixedEngine(["b", "a"]), warmup=0)
    expected = (3 + 7 / math.log2(3)) / (7 + 3 / math.log2(3))
    assert rows[0]["ndcg_10"] == pytest.approx(expected)
    assert metrics["success_5"] == metrics["mrr_10"] == metrics["recall_20"] == 1
    assert metrics["eligible_queries"]["ndcg_10"] == 1


def test_unjudged_is_not_zero_or_removed_from_ranking():
    rows, metrics = evaluation.evaluate([query()], FixedEngine(["c", "a"]), warmup=0)
    assert rows[0]["predictions"] == ["c", "a"]
    assert rows[0]["unjudged_at_20"] == ["c"]
    assert rows[0]["judged_at_10"] == 0.5
    assert all(rows[0][k] is None for k in ("ndcg_10", "success_5", "rr_10", "recall_20"))
    assert metrics["ndcg_10"] is None
    assert metrics["eligible_queries"]["ndcg_10"] == 0


def test_no_results_are_a_real_miss():
    rows, metrics = evaluation.evaluate([query()], FixedEngine([]), warmup=0)
    assert metrics["ndcg_10"] == metrics["success_5"] == metrics["recall_20"] == 0
    assert rows[0]["unjudged_at_20"] == []


def test_coverage_is_checked_at_each_metric_cutoff():
    q = query(relevance={"a": 3, "b": 0, "c": 0, "d": 0, "e": 0})
    rows, metrics = evaluation.evaluate([q], FixedEngine(["a", "b", "c", "d", "e", "unknown"]), warmup=0)
    assert rows[0]["success_5"] is True
    assert rows[0]["ndcg_10"] is None
    assert metrics["eligible_queries"]["success_5"] == 1
    assert metrics["eligible_queries"]["ndcg_10"] == 0


def test_no_match_reported_separately():
    q = query(has_answer=False, relevance={})
    _, metrics = evaluation.evaluate([q], FixedEngine(["a"]), warmup=0)
    assert metrics["no_match_false_accept_rate"] == 1
    assert metrics["ndcg_10"] is None
    assert metrics["n_with_answer"] == 0


def test_latency_median_and_warmup(monkeypatch):
    ticks = iter([0, .001, 1, 1.003])
    monkeypatch.setattr(evaluation.time, "perf_counter", lambda: next(ticks))
    engine = FixedEngine(["a"])
    _, metrics = evaluation.evaluate([query(), query(qid="q2")], engine, warmup=1)
    assert engine.calls == 4
    assert metrics["latency_ms_p50"] == 2
    assert metrics["latency_ms_p95"] == 3


@pytest.mark.parametrize("change", [
    {"qid": ""}, {"query": " "}, {"query": "x" * 301}, {"split": "oops"},
    {"verified": "false"}, {"has_answer": 1}, {"labeled_by": ""},
    {"relevance": {"a": True}}, {"relevance": {"a": 4}}, {"relevance": {"a": 1.5}},
    {"relevance": {"missing": 3}}, {"has_answer": False}, {"relevance": {}}, {"group_id": []},
])
def test_bad_queries_rejected(change):
    with pytest.raises(ValueError):
        evaluation.validate_queries([query(**change)], {"a", "b"})


@pytest.mark.parametrize("queries", [[], [query(), query()],
    [query(group_id="intent"), query(qid="q2", query="paraphrase", split="test", group_id="intent")],
    [query(query="TÚI  CÓI"), query(qid="q2", query="túi cói", split="test")]])
def test_empty_duplicate_and_split_leakage_rejected(queries):
    with pytest.raises(ValueError):
        evaluation.validate_queries(queries, {"a", "b"})


def test_smoke_requires_explicit_flag_and_never_accepts_unverified_test(tmp_path):
    path = tmp_path / "queries.jsonl"
    q = query(verified=False)
    path.write_text(json.dumps(q), encoding="utf-8")
    with pytest.raises(ValueError, match="allow-unverified"):
        evaluation.load_queries(path, {"a", "b"})
    assert len(evaluation.load_queries(path, {"a", "b"}, allow_unverified=True)) == 1
    q["split"] = "test"
    path.write_text(json.dumps(q), encoding="utf-8")
    with pytest.raises(ValueError, match="split test"):
        evaluation.load_queries(path, {"a", "b"}, allow_unverified=True)


def test_empty_selection_and_invalid_json_rejected(tmp_path):
    path = tmp_path / "queries.jsonl"
    path.write_text(json.dumps(query()), encoding="utf-8")
    with pytest.raises(ValueError, match="Không có truy vấn"):
        evaluation.load_queries(path, {"a", "b"}, split="test")
    path.write_text('{"qid":', encoding="utf-8")
    with pytest.raises(ValueError, match="dòng 1"):
        evaluation.load_queries(path, {"a", "b"})
