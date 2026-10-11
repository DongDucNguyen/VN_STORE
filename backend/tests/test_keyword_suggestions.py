"""Machine-assisted keyword suggestions stay suggestions: validation, embedding and audit (synthetic data)."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
import audit_reviews  # noqa: E402
import build_keyword_suggestions as bks  # noqa: E402
import prepare_review  # noqa: E402


def packet(pool=True):
    p = {"catalog_sha256": "cat", "queries_sha256": "qs",
         "queries": [{"qid": "q1", "query": "giỏ tre", "split": "dev", "has_answer": True, "relevance": {"a": 3},
                      "labeled_by": "draft", "verified": False},
                     {"qid": "q2", "query": "nồi cơm", "split": "dev", "has_answer": False, "relevance": {},
                      "labeled_by": "draft", "verified": False}],
         "products": [{"id": x} for x in "abc"]}
    if pool:
        p["pool"] = {"q1": ["a", "b"], "q2": ["c"]}
    return p


def judgments(**overrides):
    j = {"q1": {"note": "n", "scores": {0: (3, "giỏ tre")}, "full": False},
         "q2": {"note": "n", "scores": {}, "full": True}}
    j.update(overrides)
    return j


def test_build_fills_pool_and_full_catalog():
    out = bks.build(judgments(), [packet()])
    assert out["queries"]["q1"]["relevance"] == {"a": {"score": 3, "reason": "giỏ tre"},
                                                 "b": {"score": 0, "reason": "không đáp ứng loại/thuộc tính chính"}}
    assert set(out["queries"]["q2"]["relevance"]) == {"a", "b", "c"}  # no answer → whole catalog checked
    assert out["queries"]["q2"]["suggested_has_answer"] is False


@pytest.mark.parametrize("bad,match", [
    ({"q1": {"note": "n", "scores": {0: (1, "yếu")}, "full": False}}, "whole catalog"),
    ({"q1": {"note": "n", "scores": {7: (3, "x")}, "full": False}}, "out of range"),
    ({"q1": {"note": "n", "scores": {0: (4, "x")}, "full": False}}, "0..3"),
    ({"q1": {"note": "n", "scores": {0: (3, " ")}, "full": False}}, "reason"),
    ({"q3": {"note": "n", "scores": {}, "full": True}}, "differ"),
])
def test_build_rejects_unfounded_or_invalid(bad, match):
    with pytest.raises(ValueError, match=match):
        bks.build(judgments(**bad), [packet()])


def test_attach_requires_same_catalog_queries_and_pool_coverage():
    raw = json.dumps(bks.build(judgments(), [packet()])).encode()
    p = packet()
    prepare_review.attach_suggestions(p, raw)
    assert p["suggestions_sha256"] == hashlib.sha256(raw).hexdigest()
    assert p["suggestions"]["queries"]["q1"]["relevance"]["a"]["score"] == 3
    for change in ({"catalog_sha256": "other"}, {"queries_sha256": "other"}, {"pool": {"q1": ["a", "c"], "q2": ["c"]}}):
        with pytest.raises(ValueError):
            prepare_review.attach_suggestions({**packet(), **change}, raw)


def export(assist=None, reviewer="r1"):
    rows = []
    for q in packet()["queries"]:
        rel = {"a": 3, "b": 0} if q["qid"] == "q1" else {"a": 0, "b": 0, "c": 0}
        rows.append({**q, "relevance": rel, "has_answer": q["qid"] == "q1", "group_id": q["qid"], "verified": True,
                     "labeled_by": reviewer, "reviewed_at": "2026-10-11T10:00:00+07:00", "catalog_sha256": "cat",
                     **({"assist": assist} if assist else {})})
    return rows


def test_audit_reports_assistance_and_warns_when_both_reviewers_assisted():
    good = {"version": "v1", "suggestions_sha256": "s", "applied": 2, "kept_unchanged": 1, "changed": 1}
    p = packet()
    report = audit_reviews.audit(p, [export(good), export(reviewer="r2")], "cat", {"a", "b", "c"})
    assert report["exports"][0]["assisted"]["applied"] == 4 and report["exports"][1]["assisted"] is None
    assert "independence_warning" not in report
    both = audit_reviews.audit(p, [export(good), export(good, "r2")], "cat", {"a", "b", "c"})
    assert "không độc lập" in both["independence_warning"]
    with pytest.raises(ValueError, match="assist"):
        audit_reviews.audit(p, [export({**good, "changed": 5})], "cat", {"a", "b", "c"})


def test_project_suggestions_match_current_packets():
    """The committed suggestions must stay valid for the current seed-006 packets (no relabelling here)."""
    sug = json.loads((ROOT / "benchmarks/keyword/suggestions/claude_assist_v1.json").read_text(encoding="utf-8"))
    for name in ("dev-107", "seed-12"):
        path = ROOT / f"artifacts/keyword_review/2026-10-11_seed-006_{name}-pool/packet.json"
        if not path.exists():
            pytest.skip("packet artifacts not present")
        p = json.loads(path.read_text(encoding="utf-8"))
        prepare_review.attach_suggestions(p, json.dumps(sug).encode())
    assert sug["author"].startswith("Claude (AI)") and "không phải nhãn" in sug["author"]


# ---------- nhãn máy (machine_labels.py + eval_keyword --machine-labels) ----------
import machine_labels  # noqa: E402
import eval_keyword  # noqa: E402
from tests.conftest import FIXTURE  # noqa: E402


def machine_file(tmp_path, split="dev", catalog=None):
    sha = catalog or hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    sug = {"kind": "keyword_relevance_suggestions", "version": "v-test", "catalog_sha256": sha,
           "queries": {"m1": {"scope": "pool_plus_listed",
                              "relevance": {"fx-gio-may-co-quai": {"score": 3, "reason": "r"}}}}}
    raw = json.dumps(sug).encode()
    rows = machine_labels.build(sug, raw, [{"qid": "m1", "query": "giỏ mây", "split": split}])
    path = tmp_path / "machine.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path, rows


def test_machine_labels_are_marked_and_never_verified(tmp_path):
    _, rows = machine_file(tmp_path)
    assert rows[0]["label_source"] == "machine" and rows[0]["verified"] is False
    assert rows[0]["labeled_by"] == "v-test (máy)" and rows[0]["has_answer"] is True
    with pytest.raises(ValueError, match="test split"):
        machine_file(tmp_path, split="test")


def test_eval_records_machine_labeled_status_and_refuses_mixups(tmp_path):
    path, _ = machine_file(tmp_path)
    base = ["--queries", str(path), "--catalog", str(FIXTURE), "--split", "dev", "--warmup", "0",
            "--out-root", str(tmp_path / "runs")]
    with pytest.raises(SystemExit):
        eval_keyword.main(base)  # machine labels need the explicit flag
    with pytest.raises(SystemExit):
        eval_keyword.main(base + ["--machine-labels", "--allow-unverified"])
    assert eval_keyword.main(base + ["--machine-labels"]) == 0
    run = json.loads(next((tmp_path / "runs").iterdir()).joinpath("run.json").read_text(encoding="utf-8"))
    assert (run["evaluation_status"], run["label_source"]) == ("machine_labeled", "machine")
    (tmp_path / "x").mkdir()
    stale, _ = machine_file(tmp_path / "x", catalog="other")  # labels judged on another catalog
    with pytest.raises(SystemExit):
        eval_keyword.main(["--queries", str(stale), "--catalog", str(FIXTURE), "--split", "dev", "--machine-labels",
                           "--out-root", str(tmp_path / "runs2")])
