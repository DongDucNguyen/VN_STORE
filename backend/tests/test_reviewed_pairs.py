"""Pair exports must not silently promote machine references or discard zero labels."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/benchmark"))
from analyze_reviewed_pairs import audit, compare, evaluate, query_variant_checks, validate_pairs  # noqa: E402


def pair(pid="p1", status="human_corrected", machine=2, corrected=0):
    types = {"human_corrected": "explicit_incorrect", "human_accepted_explicit": "explicit_correct",
             "human_accepted_inferred": "confirmed_scope", "unreviewed": "outside_confirmed_scope"}
    ev = {"source_file": "source.jsonl", "source_line": 1, "type": types[status]}
    if status in ("human_corrected", "human_accepted_explicit"):
        ev.update(manual_export="manual.json", verdict="incorrect" if status == "human_corrected" else "correct")
    if status == "human_accepted_inferred":
        ev["scope"] = "scope.json#confirmed"
    return {"qid": "q1", "query": "hộp", "product_id": pid, "machine_score": machine,
            "corrected_score": corrected, "final_score": corrected if corrected is not None else machine,
            "review_status": status, "is_human_reviewed": status != "unreviewed",
            "review_evidence": json.dumps(ev), "note": "original note"}


def inputs():
    rows = [pair(), pair("p2", "human_accepted_inferred", 3, None),
            pair("p3", "unreviewed", 0, None), pair("p4", "human_accepted_explicit", 1, None)]
    sources = {"source.jsonl": [{"qid": "q1", "query": "hộp", "split": "train", "catalog_sha256": "sha",
                                "relevance": {r["product_id"]: r["machine_score"] for r in rows}}]}
    return rows, deepcopy([r for r in rows if r["is_human_reviewed"]]), sources, {"p1", "p2", "p3", "p4"}, "sha"


def test_audit_preserves_zero_null_evidence_and_inputs():
    args = inputs()
    before = deepcopy(args)
    result, _ = audit(*args)
    assert args == before
    assert result["pairs"] == 4 and result["reviewed_pairs"] == 3
    assert result["changed_scores"] == result["relevance_threshold_changes"] == 1
    assert result["cohorts"]["human_corrected"]["machine_to_final"][2][0] == 1
    assert result["partial_catalog_reviewed_queries"] == 1


@pytest.mark.parametrize("field,value", [
    ("machine_score", True), ("final_score", "0"), ("corrected_score", False),
    ("corrected_score", 4), ("final_score", 2), ("corrected_score", None),
    ("is_human_reviewed", 1), ("is_human_reviewed", False),
    ("review_status", "unreviewed"), ("review_evidence", "{}"), ("note", None),
])
def test_rejects_invalid_scores_flags_and_evidence(field, value):
    row = pair()
    row[field] = value
    with pytest.raises(ValueError):
        validate_pairs([row])


def test_duplicate_and_missing_pairs_are_errors():
    with pytest.raises(ValueError, match="duplicate"):
        validate_pairs([pair(), pair()])
    rows, reviewed, sources, products, sha = inputs()
    with pytest.raises(ValueError, match="exactly equal"):
        audit(rows, reviewed[:-1], sources, products, sha)
    with pytest.raises(ValueError, match="missing source pair"):
        audit(rows[:-1], reviewed[:-1], sources, products, sha)


@pytest.mark.parametrize("field,value", [("catalog_sha256", "stale"), ("query", "khác"), ("split", "test")])
def test_stale_source_or_test_split_rejected(field, value):
    rows, reviewed, sources, products, sha = inputs()
    sources["source.jsonl"][0][field] = value
    with pytest.raises(ValueError):
        audit(rows, reviewed, sources, products, sha)


def test_line_endings_exception_is_explicit_and_narrow():
    rows, reviewed, sources, products, _ = inputs()
    with pytest.raises(ValueError, match="hash mismatch"):
        audit(rows, reviewed, sources, products, "crlf")
    result, _ = audit(rows, reviewed, sources, products, "crlf", "sha")
    assert result["catalog_match"] == "CRLF_to_LF_only"


def test_incorrect_verdict_can_keep_the_same_score():
    rows, reviewed, sources, products, sha = inputs()
    rows[0]["corrected_score"] = rows[0]["final_score"] = rows[0]["machine_score"]
    reviewed[0] = deepcopy(rows[0])
    result, _ = audit(rows, reviewed, sources, products, sha)
    assert result["changed_scores"] == 0
    assert result["incorrect_verdict_unchanged_score"] == 1


class FakeEngine:
    def __init__(self, ranked):
        self.ranked = ranked
        self.snap = SimpleNamespace(products={"p1": {}, "p2": {}, "p3": {}, "p4": {}}, include_drafts=False)
        self.config = SimpleNamespace(to_dict=lambda: {})

    def search(self, query, limit):
        return {"results": [{"id": pid} for pid in self.ranked]}


def test_missing_top_result_is_unknown_and_explicit_cohort_is_separate():
    _, reviewed, _, _, _ = inputs()
    metadata = {"q1": {"split": "train"}}
    out = evaluate(reviewed, metadata, FakeEngine(["p3", "p2"]))
    assert out["queries"][0]["metrics"]["all_reviewed"]["ndcg_at_10"] is None
    out = evaluate(reviewed, metadata, FakeEngine(["p2", "p4", "p1"]))
    metrics = out["queries"][0]["metrics"]
    assert metrics["all_reviewed"]["ndcg_at_10"] == 1
    assert metrics["explicit_only"]["ndcg_at_10"] is None
    assert metrics["explicit_only"]["false_accept"] is None  # no positive != no-match


def test_comparison_uses_common_eligible_queries_and_checks_inputs():
    def report(values):
        return {"inputs": {"all": "hash"}, "evaluation": {"include_drafts": False, "queries": [
            {"qid": qid, "query": qid, "split": "train", "metrics": {
                c: {"ndcg_at_10": value} for c in ("all_reviewed", "explicit_only")}}
            for qid, value in values.items()]}}
    before, after = report({"a": .2, "b": None}), report({"a": .4, "b": 1})
    result = compare(before, after)["train"]["all_reviewed"]
    assert result["common_eligible_queries"] == 1 and result["mean_delta"] == .2
    after["inputs"]["all"] = "different"
    with pytest.raises(ValueError, match="identical"):
        compare(before, after)


def test_accent_variant_disagreement_and_split_overlap_are_reported_without_relabeling():
    a, b = pair(), pair()
    a["query"], b["query"], b["qid"] = "đồ sơn mài", "do son mai", "q2"
    b["corrected_score"] = b["final_score"] = 3
    rows = [a, b]
    original = deepcopy(rows)
    result = query_variant_checks(rows, {
        "q1": {"query": a["query"], "split": "train"}, "q2": {"query": b["query"], "split": "dev"}})
    assert len(result["conflicting_pairs"]) == len(result["cross_split_candidates"]) == 1
    assert rows == original
