"""Synthetic judgments only: transcript links, paired coverage and safe comparison."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.catalog.store import load_snapshot
from tests.media_samples import wav
from tests.test_voice_image_benchmark import FIXTURE, voice_manifest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/benchmark"))
import eval_voice as ev
import voice_retrieval as vr
from compare_runs import compare, Incomparable


def inputs(tmp_path):
    manifest = voice_manifest(tmp_path, [("v1", wav(1), "túi cói", "s1", "dev")])
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["samples"][0].update(keyword_qid="kw1", transcript_review={
        "reviewed_by": "synthetic", "reviewed_at": "2026-10-11T10:00:00+07:00"},
        consent={"status": "granted", "evidence": "synthetic"})
    manifest.write_text(json.dumps(data), encoding="utf-8")
    snap = load_snapshot(FIXTURE)
    q = {"qid": "kw1", "query": "túi cói", "split": "dev", "verified": True,
         "labeled_by": "synthetic", "catalog_sha256": snap.sha256, "has_answer": True,
         "relevance": {p: (3 if p == "fx-tui-coi-tron" else 0) for p in snap.products}}
    return manifest, data["samples"], snap, q


def queries(tmp_path, q):
    p = tmp_path / "queries.jsonl"
    p.write_text(json.dumps(q, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


@pytest.mark.parametrize("case", ["missing_link", "unknown_link", "split", "text", "hash", "unreviewed",
                                  "no_match_partial", "unknown_product", "silent_link", "leaked_group"])
def test_link_guards(tmp_path, case):
    _, samples, snap, q = inputs(tmp_path)
    if case == "missing_link": samples[0].pop("keyword_qid")
    if case == "unknown_link": samples[0]["keyword_qid"] = "missing"
    if case == "split": q["split"] = "train"
    if case == "text": q["query"] = "túi nhựa"
    if case == "hash": q.pop("catalog_sha256")
    if case == "unreviewed": q["verified"] = False
    if case == "no_match_partial": q.update(has_answer=False, relevance={"fx-tui-coi-tron": 0})
    if case == "unknown_product": q["relevance"]["missing"] = 0
    if case == "silent_link": samples[0]["reference_text"] = None
    path = queries(tmp_path, q)
    if case == "leaked_group":
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({**q, "qid": "other", "split": "train"}) + "\n")
    with pytest.raises(ValueError):
        vr.load_links(path, samples, samples, snap, False)


def test_unreviewed_only_smoke_and_normalization_keeps_accents(tmp_path):
    _, samples, snap, q = inputs(tmp_path)
    q.update(query="TÚI CÓI!", verified=False)
    linked, meta = vr.load_links(queries(tmp_path, q), samples, samples, snap, True)
    assert meta["unreviewed_queries"] == 1 and set(linked) == {"v1"}
    q["query"] = "tui coi"
    with pytest.raises(ValueError, match="transcript"):
        vr.load_links(queries(tmp_path, q), samples, samples, snap, True)
    samples[0]["split"] = q["split"] = "test"
    q["query"] = "túi cói"
    with pytest.raises(ValueError, match="chưa duyệt"):
        vr.load_links(queries(tmp_path, q), samples, samples, snap, True)


def row(hyp="wrong", gate=None):
    return {"qid": "v1", "reference": "right", "hypothesis": hyp, "gate_rejected": gate,
            "region": "nam", "device": "phone", "environment": "quiet", "speaker_id": "s1"}


def test_paired_metrics_empty_asr_and_gate():
    engine = SimpleNamespace(search=lambda text, limit: {"results": [{"id": "a" if text == "right" else "b"}]})
    q = {"qid": "kw1", "has_answer": True, "relevance": {"a": 3, "b": 0}}
    for r in [row(), row(""), row("right", "audio_silent")]:
        r.update(vr.score(r, q, engine))
        assert r["reference_success_5"] is True and r["asr_success_5"] is False
        assert r["ndcg_10_drop"] == 1
        m = vr.summarize([r])
        assert m["paired"]["success_5"]["drop"] == 1
        assert m["by_group"]["region"]["nam"]["n_linked"] == 1
    r = row()
    r.update(vr.score(r, {**q, "relevance": {"a": 3}}, engine))
    assert r["asr_success_5"] is None
    assert vr.summarize([r])["paired"]["success_5"]["n"] == 0
    assert vr.summarize([r])["incomplete_qids"] == ["v1"]


def test_no_match_is_separate():
    r = row("")
    r.update(vr.score(r, {"qid": "kw", "has_answer": False, "relevance": {"a": 0}},
                      SimpleNamespace(search=lambda text, limit: {"results": [{"id": "a"}]})))
    m = vr.summarize([r])
    assert m["paired"]["success_5"]["n"] == 0
    assert m["no_match"] == {"reference_false_accept_rate": 1, "asr_false_accept_rate": 0}


def test_cli_retrieval_and_comparison(tmp_path):
    manifest, _, _, q = inputs(tmp_path)
    path = queries(tmp_path, q)
    args = ["--manifest", str(manifest), "--catalog", str(FIXTURE), "--queries", str(path),
            "--adapter", "tests.fakes:FakeASR", "--split", "dev", "--latency-rounds", "1",
            "--out-root", str(tmp_path / "out")]
    assert ev.main(args) == 0
    d = next((tmp_path / "out").iterdir())
    run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    rows = [json.loads(x) for x in (d / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert run["retrieval"]["status"] == "reviewed_pool"  # fixture, not a real benchmark
    assert run["metrics"]["retrieval"]["paired"]["success_5"]["n"] == 1
    report = compare((run, rows), (run, rows), samples=10)
    assert report["metrics"]["asr_success_5"]["delta"] == 0
    assert report["metrics"]["asr_success_5"]["ci95"] is None  # only one speaker
    for key in ("queries_sha256", "search_code_sha256", "policy", "include_drafts", "links"):
        other = copy.deepcopy(run)
        other["retrieval"][key] = "changed"
        with pytest.raises(Incomparable): compare((run, rows), (other, rows))
    with pytest.raises(Incomparable): compare((run, rows), ({**run, "retrieval": None}, rows))
    q["verified"] = False
    queries(tmp_path, q)
    assert ev.main(args) == 1
    assert ev.main(args + ["--allow-unreviewed"]) == 0
    assert len(list((tmp_path / "out").iterdir())) == 2
