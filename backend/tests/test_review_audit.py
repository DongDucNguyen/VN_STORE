import copy
import json
from pathlib import Path
import sys

import pytest

from app.catalog.validation import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts/benchmark"))
from audit_reviews import audit, main, read_jsonl, validate_export

HASH = "a" * 64


@pytest.fixture()
def packet():
    return {"catalog_sha256": HASH, "products": [{"id": "a"}, {"id": "b"}], "queries": [
        {"qid": "q1", "query": "Giỏ tre", "split": "dev", "verified": False,
         "has_answer": True, "relevance": {"a": 3}, "labeled_by": "draft"},
        {"qid": "q2", "query": "Bát gốm", "split": "dev", "verified": False,
         "has_answer": False, "relevance": {}, "labeled_by": "draft"}]}


def export(packet, reviewer="Reviewer A"):
    rows = copy.deepcopy(packet["queries"])
    for row in rows:
        row.update(verified=True, labeled_by=reviewer, reviewed_at="2026-10-10T02:00:00+07:00",
                   catalog_sha256=HASH, group_id=row["qid"])
        row["relevance"].setdefault("a", 0)
        row["relevance"].setdefault("b", 0)
    return rows


def test_pending_packet_does_not_create_labels(packet):
    before = copy.deepcopy(packet)
    report = audit(packet, [], HASH, {"a", "b"})
    assert report["status"] == "pending_review" and report["pairs_per_reviewer"] == 4
    assert not report["reviewers"] and packet == before


def test_single_export_is_valid_but_not_a_benchmark(packet):
    report = audit(packet, [export(packet)], HASH, {"a", "b"})
    assert report["status"] == "valid_single_review"
    assert report["exports"][0]["grade_counts"] == {"0": 3, "3": 1}
    assert report["exports"][0]["no_answer_queries"] == 1


def test_comparison_reports_grade_threshold_group_and_answer_disagreements(packet):
    left, right = export(packet), export(packet, "Reviewer B")
    right[0]["relevance"]["a"] = 1
    right[0]["has_answer"] = False
    right[1]["group_id"] = "g2"
    before = copy.deepcopy((left, right))
    report = audit(packet, [left, right], HASH, {"a", "b"})
    c = report["comparison"]
    assert report["status"] == "requires_adjudication"
    assert c["exact_agreement"] == c["relevant_threshold_agreement"] == .75
    assert c["confusion_matrix"]["counts"][3][1] == 1
    assert len(c["grade_disagreements"]) == len(c["group_disagreements"]) == len(c["has_answer_disagreements"]) == 1
    assert (left, right) == before


def test_order_independent_and_agreement_recorded(packet):
    left, right = export(packet), export(packet, "Reviewer B")[::-1]
    report = audit(packet, [left, right], HASH, {"a", "b"})
    assert report["status"] == "agreement_recorded"
    assert report["comparison"]["exact_agreement"] == 1


def test_same_reviewer_cannot_count_twice(packet):
    with pytest.raises(ValueError, match="cùng tên"):
        audit(packet, [export(packet), export(packet, "  REVIEWER  a ")], HASH, {"a", "b"})


@pytest.mark.parametrize("field,value", [
    ("verified", False), ("catalog_sha256", "b" * 64), ("query", "Changed query"),
    ("split", "train"), ("reviewed_at", None), ("reviewed_at", "2026-10-10"),
    ("group_id", ""), ("relevance", {"a": 3}), ("relevance", {"a": True, "b": 0}),
])
def test_export_rejects_missing_or_changed_metadata(packet, field, value):
    rows = export(packet)
    rows[0][field] = value
    with pytest.raises(ValueError):
        validate_export(rows, packet, {"a", "b"})


def test_export_requires_exact_qids_and_one_reviewer(packet):
    rows = export(packet)
    with pytest.raises(ValueError, match="qid"):
        validate_export(rows[:1], packet, {"a", "b"})
    rows[1]["labeled_by"] = "Another person"
    with pytest.raises(ValueError, match="nhất quán"):
        validate_export(rows, packet, {"a", "b"})


def test_cross_split_group_leakage_is_rejected(packet):
    packet["queries"][1]["split"] = "test"
    rows = export(packet)
    rows[1]["group_id"] = rows[0]["group_id"]
    with pytest.raises(ValueError, match="nhiều split"):
        audit(packet, [rows], HASH, {"a", "b"})


def test_packet_stale_or_wrong_visible_set(packet):
    with pytest.raises(ValueError, match="snapshot"):
        audit(packet, [], "b" * 64, {"a", "b"})
    with pytest.raises(ValueError, match="hiển thị"):
        audit(packet, [], HASH, {"a"})
    packet["products"].append({"id": "a"})
    with pytest.raises(ValueError, match="trùng"):
        audit(packet, [], HASH, {"a", "b"})


def test_jsonl_handles_bom_and_reports_line_number():
    assert read_jsonl(b'\xef\xbb\xbf{"qid":"a"}\n\n') == [{"qid": "a"}]
    with pytest.raises(ValueError, match="dòng 2"):
        read_jsonl(b'{}\ninvalid')


def test_cli_missing_review_saves_failure_without_creating_label_file(tmp_path, monkeypatch):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text("{}", encoding="utf-8")
    missing = tmp_path / "missing-review.jsonl"
    monkeypatch.setattr(sys, "argv", ["audit_reviews.py", "--packet", str(packet_path),
                                      "--review", str(missing), "--report-dir", str(tmp_path / "reports")])
    assert main() == 1
    assert not missing.exists()
    report = json.loads(next((tmp_path / "reports").glob("*.json")).read_bytes())
    assert report["status"] == "invalid"


def test_cli_real_packet_is_pending_without_reviews(tmp_path, monkeypatch):
    from app.catalog.store import load_snapshot
    from prepare_review import make_packet
    snap = load_snapshot(REPO_ROOT / "database.json", include_drafts=True)
    queries = read_jsonl((REPO_ROOT / "benchmarks/keyword/seed_unverified.jsonl").read_bytes())
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(make_packet(queries, snap, tmp_path)), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["audit_reviews.py", "--packet", str(packet_path),
                                      "--include-drafts", "--report-dir", str(tmp_path / "reports")])
    assert main() == 0
    report = json.loads(next((tmp_path / "reports").glob("*.json")).read_bytes())
    assert report["status"] == "pending_review"
    assert report["queries"] == 12 and report["pairs_per_reviewer"] == 12 * len(snap.products)


# ---------- Packet theo pool (prepare_review.py --pool-top) ----------

@pytest.fixture()
def pool_packet(packet):
    packet["products"].append({"id": "c"})
    return {**packet, "pool": {"q1": ["b", "a"], "q2": ["c"]}}


def pool_export(packet, reviewer="Reviewer A", q1=None, q2=None):
    rows = copy.deepcopy(packet["queries"])
    for row in rows:
        row.update(verified=True, labeled_by=reviewer, reviewed_at="2026-10-10T02:00:00+07:00",
                   catalog_sha256=HASH, group_id=row["qid"])
    rows[0]["relevance"] = q1 if q1 is not None else {"a": 3, "b": 0}
    rows[1]["relevance"] = q2 if q2 is not None else {"a": 0, "b": 1, "c": 0}  # no-match: đủ catalog
    return rows


def test_pool_export_needs_pool_and_full_catalog_only_for_no_match(pool_packet):
    ids = {"a", "b", "c"}
    report = audit(pool_packet, [pool_export(pool_packet)], HASH, ids)
    assert report["status"] == "valid_single_review" and report["label_scope"] == "pool"
    assert report["pairs_per_reviewer"] == 3  # 2 + 1 cặp bắt buộc
    with pytest.raises(ValueError, match="chưa chấm đủ pool"):
        audit(pool_packet, [pool_export(pool_packet, q1={"a": 3})], HASH, ids)
    with pytest.raises(ValueError, match="không có đáp án"):
        audit(pool_packet, [pool_export(pool_packet, q2={"c": 0})], HASH, ids)


def test_pool_comparison_uses_only_pairs_both_labeled(pool_packet):
    ids = {"a", "b", "c"}
    left = pool_export(pool_packet)
    right = pool_export(pool_packet, "Reviewer B", q1={"a": 2, "b": 0, "c": 0})
    c = audit(pool_packet, [left, right], HASH, ids)["comparison"]
    assert c["pairs_compared"] == 5 and c["pairs_labeled_by_one_reviewer"] == 1
    assert c["coverage_differences"] == [{"qid": "q1", "labeled_by_one_reviewer": ["c"]}]
    assert [(d["product_id"], d["left"], d["right"]) for d in c["grade_disagreements"]] == [("a", 3, 2)]


def test_pool_packet_rejects_bad_pool(pool_packet):
    for bad in ({"q1": ["a"]}, {"q1": [], "q2": ["c"]}, {"q1": ["a", "a"], "q2": ["c"]}, {"q1": ["x"], "q2": ["c"]}):
        with pytest.raises(ValueError, match="pool"):
            audit({**pool_packet, "pool": bad}, [], HASH, {"a", "b", "c"})


def test_real_pool_packet_from_bm25_and_random(tmp_path):
    from app.catalog.store import load_snapshot
    from prepare_review import make_packet
    snap = load_snapshot(REPO_ROOT / "database.json", include_drafts=True)
    queries = read_jsonl((REPO_ROOT / "benchmarks/keyword/seed_unverified.jsonl").read_bytes())
    packet = make_packet(queries, snap, tmp_path, pool_top=5, n_random=3)
    again = make_packet(queries, snap, tmp_path, pool_top=5, n_random=3)
    assert packet["pool"] == again["pool"] and packet["scope"] == "pool_then_full_catalog_for_no_match"
    for q in queries:
        pool, order = packet["pool"][q["qid"]], packet["candidate_order"][q["qid"]]
        assert order[:len(pool)] == pool and sorted(order) == sorted(snap.products)
        tags = [s.split("@")[0] for v in packet["pool_sources"][q["qid"]].values() for s in v]
        assert tags.count("random") == 3 and set(packet["pool_sources"][q["qid"]]) == set(pool)
    assert len(packet["pool"]["kw-seed-001"]) < len(snap.products)
    assert audit(packet, [], snap.sha256, set(snap.products))["status"] == "pending_review"
