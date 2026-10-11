"""GĐ6 locked-test ledger, evaluator guards and acceptance report on synthetic runs only."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
import locked_ledger as ledger  # noqa: E402
import locked_test as lt  # noqa: E402
import eval_keyword as ek  # noqa: E402
import eval_voice as ev  # noqa: E402
import eval_image as ei  # noqa: E402
from tests.test_voice_image_benchmark import FIXTURE, image_manifest, judgment, voice_manifest, wav  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    monkeypatch.setenv("VNSTORE_LOCKED_TEST_LEDGER", str(path))
    monkeypatch.delenv("VNSTORE_LOCKED_TEST_ID", raising=False)
    return path


def open_session(sid="LT001-x", modalities=ledger.MODALITIES, **extra):
    return ledger.append({"event": "opened", "id": sid, "opened_by": "SYNTHETIC", "attempt": 1, "rerun_reason": None,
                          "modalities": list(modalities), "fingerprint": {"m": "1"}, "same_test_data_as": [],
                          "selection_sha256": "s", "readiness_report": "r", "readiness_sha256": "r", **extra})


# ---------- ledger ----------

def test_ledger_hash_chain_detects_edits(isolated_ledger):
    open_session()
    ledger.append({"event": "closed", "id": "LT001-x", "status": "aborted"})
    assert [e["event"] for e in ledger.read()] == ["opened", "closed"]
    text = isolated_ledger.read_text(encoding="utf-8")
    isolated_ledger.write_text(text.replace("SYNTHETIC", "SOMEONE"), encoding="utf-8")
    with pytest.raises(ledger.LedgerError, match="hash chain"):
        ledger.read()
    isolated_ledger.write_text(text.splitlines()[1] + "\n", encoding="utf-8")  # deleting the opening
    with pytest.raises(ledger.LedgerError):
        ledger.read()


def test_require_open_rules(monkeypatch, tmp_path):
    with pytest.raises(ledger.LedgerError, match="locked_test.py open"):
        ledger.require_open("voice")
    monkeypatch.setenv("VNSTORE_LOCKED_TEST_ID", "LT001-x")
    with pytest.raises(ledger.LedgerError, match="not open"):
        ledger.require_open("voice")
    open_session(modalities=["voice"])
    with pytest.raises(ledger.LedgerError, match="not part"):
        ledger.require_open("image")
    assert ledger.require_open("voice") == "LT001-x"
    run = tmp_path / "run"
    run.mkdir()
    (run / "run.json").write_text("{}", encoding="utf-8")
    (run / "predictions.jsonl").write_text("", encoding="utf-8")
    ledger.record_run("LT001-x", "voice", run)
    with pytest.raises(ledger.LedgerError, match="already ran"):
        ledger.require_open("voice")
    ledger.append({"event": "closed", "id": "LT001-x", "status": "completed"})
    with pytest.raises(ledger.LedgerError, match="not open"):
        ledger.require_open("voice")


# ---------- evaluator guards ----------

def keyword_queries(tmp_path, split="test"):
    path = tmp_path / "kw.jsonl"
    row = {"qid": "kt1", "query": "giỏ mây", "split": split, "has_answer": True,
           "relevance": {"fx-gio-may-co-quai": 3}, "labeled_by": "SYNTHETIC", "verified": True}
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def test_keyword_test_split_requires_open_session_and_records_once(tmp_path, monkeypatch):
    out = tmp_path / "runs"
    base = ["--queries", str(keyword_queries(tmp_path)), "--catalog", str(FIXTURE), "--split", "test",
            "--warmup", "0", "--out-root", str(out)]
    for extra in ([], ["--confirm-locked-test", "--no-write"], ["--confirm-locked-test"]):
        with pytest.raises(SystemExit):
            ek.main(base + extra)
    assert not out.exists()
    open_session(modalities=["keyword"])
    monkeypatch.setenv("VNSTORE_LOCKED_TEST_ID", "LT001-x")
    assert ek.main(base + ["--confirm-locked-test"]) == 0
    run_dir = next(out.iterdir())
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    row = json.loads((run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert run["locked_test_id"] == "LT001-x" and row["group_id"] == "kt1"
    assert ledger.sessions(ledger.read())["LT001-x"]["runs"]["keyword"]["run_sha256"] == lt.digest(run_dir / "run.json")
    with pytest.raises(SystemExit):
        ek.main(base + ["--confirm-locked-test"])  # second evaluation in the same session
    assert len(list(out.iterdir())) == 1


def reviewed_voice(tmp_path):
    m = voice_manifest(tmp_path, [("a", wav(1.0), "giỏ mây", "s1", "test")])
    data = json.loads(m.read_text(encoding="utf-8"))
    for s in data["samples"]:
        s["consent"] = {"status": "granted", "evidence": "synthetic-form"}
        s["transcript_review"] = {"reviewed_by": "SYNTHETIC", "reviewed_at": "2026-10-11T00:00:00+07:00"}
    m.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return m


def test_voice_and_image_test_split_refuse_without_session(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "load_adapter", lambda *a: pytest.fail("must not load model"))
    monkeypatch.setattr(ei, "load_adapter", lambda *a: pytest.fail("must not load model"))
    out = tmp_path / "out"
    voice = reviewed_voice(tmp_path / "v")
    assert ev.main(["--adapter", "tests.fakes:FakeASR", "--manifest", str(voice), "--catalog", str(FIXTURE),
                    "--split", "test", "--confirm-locked-test", "--out-root", str(out)]) == 1
    image = image_manifest(tmp_path / "i", [("q", "exact", None, judgment({"fx-gio-may-co-quai": 3}, "fx-gio-may-co-quai"))])
    assert ei.main(["--adapter", "tests.fakes:ByteHistogramEmbedder", "--manifest", str(image), "--catalog",
                    str(FIXTURE), "--split", "test", "--confirm-locked-test", "--out-root", str(out)]) == 1
    assert not out.exists()


# ---------- running plan ----------

def models(requires_crops=False):
    search = {**lt.SearchConfig().to_dict(), "accent_weight": 0.3, "ocr_weight": 0.35}
    return {"voice": {"model": {"adapter": "x:Voice"}, "env": {"VNSTORE_ASR_VAD": "1"}, "search": search},
            "image": {"model": {"adapter": "x:Image"}, "env": {"VNSTORE_OCR": "latin", "VNSTORE_IMAGE_CROPS": "dev.json"},
                      "search": search, "requires_crops": requires_crops}}


def test_plan_uses_frozen_settings_and_test_crops(tmp_path, monkeypatch):
    args = SimpleNamespace(catalog=FIXTURE, keyword_queries=Path("kw"), voice_queries=Path("vq"),
                           voice_manifest=Path("vm"), image_manifest=Path("im"), families=Path("f"),
                           split_plan=Path("p"), image_crops=Path("test-crops.json"), ml_python="ml")
    plan = lt.plan_commands(args, {"include_drafts": False}, models(), "LT001-x", tmp_path)
    keyword = json.loads(plan["keyword"]["env"]["VNSTORE_SEARCH_CONFIG"])
    assert keyword["accent_weight"] == 0.3 and keyword["ocr_weight"] == 0.0  # language settings only
    assert plan["image"]["env"]["VNSTORE_IMAGE_CROPS"] == "" and "--crops" not in plan["image"]["args"]
    assert all("--include-drafts" not in p["args"] for p in plan.values())
    crops = lt.plan_commands(args, {"include_drafts": True}, models(True), "LT001-x", tmp_path)["image"]["args"]
    assert crops[crops.index("--crops") + 1] == "test-crops.json"
    monkeypatch.setenv("VNSTORE_IMAGE_CROPS", "dev.json")
    monkeypatch.setenv("VNSTORE_MODEL_DIR", "models")
    env = lt.clean_env({"VNSTORE_OCR": "latin"}, "LT001-x")
    assert "VNSTORE_IMAGE_CROPS" not in env and env["VNSTORE_MODEL_DIR"] == "models"
    assert env["VNSTORE_LOCKED_TEST_ID"] == "LT001-x" and env["VNSTORE_OCR"] == "latin"


def test_open_refuses_when_blocked_or_already_opened(tmp_path, isolated_ledger):
    voice = voice_manifest(tmp_path / "v", [])
    image = image_manifest(tmp_path / "i", [])
    args = ["open", "--opened-by", "SYNTHETIC", "--catalog", str(FIXTURE), "--selection", str(tmp_path / "none.json"),
            "--voice-manifest", str(voice), "--image-manifest", str(image), "--families", str(tmp_path / "f.json"),
            "--split-plan", str(tmp_path / "p.json"), "--out-root", str(tmp_path / "acc")]
    assert lt.main(args) == 2
    assert not isolated_ledger.exists() and list((tmp_path / "acc").glob("*_stage6-readiness.json"))
    open_session()
    assert lt.main(args) == 1  # still open
    ledger.append({"event": "closed", "id": "LT001-x", "status": "aborted"})
    assert lt.main(args) == 1  # second opening needs a reason
    assert lt.main(args + ["--rerun-reason", "synthetic"]) == 2  # reason given, preflight still blocked
    assert len(ledger.read()) == 2


# ---------- acceptance report ----------

def write_run(tmp_path, modality, run, rows, sid="LT001-x"):
    d = tmp_path / modality
    d.mkdir()
    (d / "run.json").write_text(json.dumps({"split": "test", "locked_test_id": sid, **run}), encoding="utf-8")
    (d / "predictions.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    ledger.record_run(sid, modality, d)
    return d


def synthetic_session(tmp_path, exact_hit=True, voice_regions=("nam", "bac")):
    open_session()
    write_run(tmp_path, "keyword", {"evaluation_status": "reviewed_pool", "metrics": {"latency_ms_p95": 12.0}},
              [{"qid": f"k{i}", "group_id": f"g{i}", "has_answer": True, "success_5": True} for i in range(6)])
    voice_rows = []
    for i in range(10):
        voice_rows.append({"qid": f"v{i}", "speaker_id": f"s{i}", "region": voice_regions[i % len(voice_regions)],
                           "reference": "giỏ mây dưới 300k", "price_ref": [0, 300000], "price_hyp": [0, 300000],
                           "negation_ref": [["material", "nhựa"]], "negation_hyp": [["material", "nhựa"]],
                           "duration_s": 3.0, "pipeline_ms": 400.0, "keyword_qid": f"k{i}",
                           "retrieval_has_answer": True, "success_5_drop": 0.0, "asr_success_5": True})
    write_run(tmp_path, "voice", {"evaluation_status": "locked_test", "model": {"model_id": "asr", "revision": "1"},
                                  "metrics": {"latency": {"peak_vram_mb": 900}}, "resources": {"peak_rss_mb": 1400}},
              voice_rows)
    image_rows = [{"qid": f"e{i}", "task": "exact", "has_answer": True, "family_id": f"f{i}",
                   "recall_5": exact_hit, "pipeline_ms": 500.0} for i in range(6)]
    image_rows += [{"qid": f"s{i}", "task": "similar", "has_answer": True, "family_id": f"h{i}",
                    "ndcg_10": 0.8, "pipeline_ms": 520.0} for i in range(6)]
    write_run(tmp_path, "image", {"evaluation_status": "locked_test", "model": {"model_id": "img", "revision": "1"},
                                  "metrics": {"ocr_errors": 0, "latency": {}}}, image_rows)
    ledger.append({"event": "closed", "id": "LT001-x", "status": "completed"})


def statuses(rep):
    return {c["criterion"]: c["status"] for c in rep["criteria"]}


def test_report_all_targets_met_still_needs_signoff(tmp_path):
    synthetic_session(tmp_path)
    rep = lt.build_report("LT001-x", [])
    assert rep["targets_status"] == "all_targets_met", statuses(rep)
    assert rep["benchmark_approved"] is False and rep["acceptance"] == "awaiting_human_signoff"
    assert statuses(rep)["voice_region_gap_success_5"] == "met"
    path = lt.publish("LT001-x", [], tmp_path / "acc").with_suffix(".json")
    with pytest.raises(ValueError, match="--note"):
        lt.cmd_signoff(SimpleNamespace(id="LT001-x", report=path, by="SYNTHETIC", decision="accepted", note=" ",
                                       accept_with_limits=False))
    assert lt.main(["signoff", "--id", "LT001-x", "--report", str(path), "--by", "SYNTHETIC",
                    "--decision", "accepted", "--note", "synthetic"]) == 0
    assert ledger.sessions(ledger.read())["LT001-x"]["signoffs"][0]["decision"] == "accepted"


def test_report_flags_misses_small_groups_and_tampering(tmp_path):
    synthetic_session(tmp_path, exact_hit=False, voice_regions=("nam", "bac", "trung"))
    rep = lt.build_report("LT001-x", [])
    s = statuses(rep)
    assert s["image_exact_recall_5"] == "not_met" and rep["targets_status"] == "targets_not_met"
    assert s["voice_region_gap_success_5"] == "insufficient_sample"  # < 5 speakers per region
    path = lt.publish("LT001-x", [], tmp_path / "acc").with_suffix(".json")
    signoff = ["signoff", "--id", "LT001-x", "--report", str(path), "--by", "SYNTHETIC", "--decision", "accepted",
               "--note", "synthetic"]
    assert lt.main(signoff) == 1  # accepting a miss needs explicit limits
    assert lt.main(signoff + ["--accept-with-limits"]) == 0
    with (tmp_path / "image/predictions.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="changed"):
        lt.build_report("LT001-x", [])


def test_browser_timings_need_selected_model_and_twenty_samples(tmp_path):
    synthetic_session(tmp_path)
    summary = tmp_path / "browser.json"
    groups = [{"kind": "voice", "model_id": "asr", "n_measured": 25, "p95_ms": 2500},
              {"kind": "image", "model_id": "img", "n_measured": 8, "p95_ms": 900},
              {"kind": "image", "model_id": "other", "n_measured": 50, "p95_ms": 100},
              {"kind": "image", "model_id": "img", "cached": True, "n_measured": 50, "p95_ms": 5}]
    summary.write_text(json.dumps({"status": "descriptive_browser_timings", "context": "synthetic", "groups": groups}),
                       encoding="utf-8")
    s = statuses(lt.build_report("LT001-x", [summary]))
    assert s["voice_browser_p95_ms"] == "met" and s["image_browser_p95_ms"] == "insufficient_sample"  # cached ignored
    summary.write_text(json.dumps({"status": "descriptive_browser_timings", "groups": groups}), encoding="utf-8")
    with pytest.raises(ValueError, match="context"):
        lt.build_report("LT001-x", [summary])


def test_cluster_bootstrap_needs_five_clusters():
    rows = [{"c": i % 3, "x": 1.0} for i in range(9)]
    assert lt.cluster_bootstrap(rows, "c", lt.mean_key("x"))["ci95"] is None
    rows = [{"c": i, "x": float(i % 2)} for i in range(10)]
    out = lt.cluster_bootstrap(rows, "c", lt.mean_key("x"))
    assert out["value"] == 0.5 and out["clusters"] == 10 and out["ci95"][0] < 0.5 < out["ci95"][1]


def test_open_runs_evaluators_in_subprocesses_and_writes_report(tmp_path, monkeypatch, isolated_ledger):
    """Real subprocess path with fake ASR; preflight is stubbed because synthetic data cannot pass it."""
    selection = tmp_path / "selection.json"
    selection.write_text("{}", encoding="utf-8")
    voice = reviewed_voice(tmp_path / "v")
    monkeypatch.setattr(lt.stage6, "preflight", lambda args: {
        "status": "ready_for_locked_test_review", "inputs": {"voice_manifest": {"sha256": "x"}},
        "selected_configuration": {}, "checks": [], "note": "stub"})
    monkeypatch.setenv("VNSTORE_IMAGE_CROPS", "must-not-leak.json")

    def plan(args, sel, chosen, sid, out_root):
        common = ["--split", "test", "--confirm-locked-test", "--catalog", str(FIXTURE), "--name", f"locked-{sid}",
                  "--out-root", str(out_root)]
        return {"keyword": {"python": sys.executable, "env": {},
                            "args": common + ["--queries", str(keyword_queries(tmp_path)), "--warmup", "0"]},
                "voice": {"python": sys.executable, "env": {},
                          "args": common + ["--adapter", "tests.fakes:FakeASR", "--manifest", str(voice),
                                            "--latency-rounds", "1"]}}
    monkeypatch.setattr(lt, "plan_commands", plan)
    acc = tmp_path / "acc"
    args = ["open", "--opened-by", "SYNTHETIC", "--selection", str(selection), "--out-root", str(acc),
            "--results-root", str(tmp_path / "runs")]
    assert lt.main(args) == 0
    (sid, session), = ledger.sessions(ledger.read()).items()
    assert sid.startswith("LT001-") and session["opened"]["modalities"] == ["keyword", "voice"]
    assert session["closed"]["status"] == "completed" and set(session["runs"]) == {"keyword", "voice"}
    assert len(session["reports"]) == 1 and (acc / sid / "voice.log").exists()
    rep = json.loads(Path(session["reports"][0]["report"]).read_text(encoding="utf-8"))
    # Fixture search returns unlabelled products: reported as incomplete, never as a miss or a pass.
    assert rep["targets_status"] == "incomplete" and rep["benchmark_approved"] is False
    assert rep["issues"] == ["keyword: evaluation_status=incomplete_judgments"]
    assert rep["runs"]["voice"]["evaluation_status"] == "locked_test"
    assert lt.main(args) == 1  # a second opening without a reason is refused
