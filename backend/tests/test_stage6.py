"""Synthetic release evidence and browser timings; never evaluates project test data."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
import stage6_readiness as stage6
import browser_timings as bt
from app.search.config import SearchConfig
from tests.test_voice_image_benchmark import FIXTURE, voice_manifest, image_manifest


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.fixture
def selection(tmp_path):
    config = SearchConfig().to_dict()
    code = tmp_path / "pipeline.py"
    code.write_text("# synthetic", encoding="utf-8")
    sel = {"status": "selected_on_reviewed_dev", "selected_by": "SYNTHETIC", "selected_at": "2026-10-11",
           "rationale": "synthetic evidence for regression", "catalog_sha256": "same", "include_drafts": False}
    for kind in ("voice", "image"):
        directory = tmp_path / kind
        directory.mkdir()
        run = {"split": "dev", "evaluation_status": "dev", "catalog_sha256": "same", "include_drafts": False,
               "model": {"adapter": "tests.fakes:Synthetic", "model_id": "synthetic", "revision": "1"},
               "search_config": config, "pipeline": {"search": config}}
        write(directory / "run.json", run)
        (directory / "predictions.jsonl").write_text('{"qid":"synthetic"}\n', encoding="utf-8")
        report = {"status": "ready_for_selection_review", "split": "dev", "modality": kind, "issues": [],
                  "code_sha256": {str(code): stage6.digest(code)}, "results": [{"name": "chosen", "status": "ok",
                    "run_dir": str(directory), "adapter": "tests.fakes:Synthetic",
                    "env": {"VNSTORE_SEARCH_CONFIG": json.dumps(config)}}]}
        path = write(tmp_path / f"{kind}.json", report)
        sel[kind] = {"ablation_report": str(path), "report_sha256": stage6.digest(path), "run_name": "chosen",
                     "run_sha256": stage6.digest(directory / "run.json"),
                     "predictions_sha256": stage6.digest(directory / "predictions.jsonl")}
    return write(tmp_path / "selection.json", sel)


def test_selection_preserves_frozen_model_and_configuration(selection):
    chosen, models = stage6.check_selection(selection, "same")
    assert chosen["selected_by"] == "SYNTHETIC"
    assert models["voice"]["model"]["revision"] == "1"


@pytest.mark.parametrize("field,value", [("status", "draft"), ("selected_by", ""), ("rationale", None),
                                      ("catalog_sha256", "other"), ("include_drafts", "false")])
def test_selection_rejects_unapproved_or_changed_context(selection, field, value):
    data = json.loads(selection.read_bytes())
    data[field] = value
    write(selection, data)
    with pytest.raises(ValueError):
        stage6.check_selection(selection, "same")


@pytest.mark.parametrize("path", ["voice.json", "voice/run.json", "voice/predictions.jsonl", "pipeline.py"])
def test_selection_rejects_mutated_evidence(selection, path):
    with (selection.parent / path).open("a", encoding="utf-8") as stream:
        stream.write(" ")
    with pytest.raises(ValueError):
        stage6.check_selection(selection, "same")


def test_empty_project_reports_blockers_without_inference(tmp_path, monkeypatch):
    voice = voice_manifest(tmp_path / "voice", [])
    image = image_manifest(tmp_path / "image", [])
    args = SimpleNamespace(catalog=FIXTURE, selection=tmp_path / "missing.json", voice_manifest=voice,
                           voice_queries=None, keyword_queries=None, image_manifest=image, families=tmp_path / "families.json",
                           split_plan=tmp_path / "split.json", image_crops=None)
    monkeypatch.setattr(stage6.ev, "load_adapter", lambda *a: pytest.fail("preflight must not load model"))
    report = stage6.preflight(args)
    assert report["status"] == "blocked" and report["inference_executed"] is False
    assert sum(c["status"] == "blocked" for c in report["checks"]) == 4


def sample(ms, kind="voice", model="synthetic"):
    return {"kind": kind, "browser_ms": ms, "catalog_version": "fixture", "model_id": model, "revision": "1"}


def export(rows):
    return {"version": 1, "quality_benchmark": False, "samples": rows}


def test_browser_summary_separates_models_and_excludes_declared_warmup():
    report = bt.summarize(export([sample(900), sample(10), sample(20), sample(500, model="other")]))
    a, b = report["groups"]
    assert (a["p50_ms"], a["p95_ms"], a["n_measured"]) == (10, 20, 2)
    assert b["p95_ms"] is None
    assert report["benchmark_approved"] is False and a["sample_warning"]


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, "1"])
def test_browser_summary_rejects_invalid_timings(value):
    with pytest.raises(ValueError):
        bt.summarize(export([sample(value)]))


@pytest.mark.parametrize("box", [None, [0, 0, 0, 1], [0, 0, float("nan"), 1]])
def test_test_crop_must_be_explicit_and_valid(tmp_path, box):
    path = write(tmp_path / "crop.json", {"q": {"sha256": "same", "box": box}})
    with pytest.raises(ValueError):
        stage6.check_crops(path, [{"qid": "q", "sha256": "same"}])


def test_test_crop_hash_and_missing_source(tmp_path):
    samples = [{"qid": "q", "sha256": "same"}]
    with pytest.raises(ValueError, match="requires"):
        stage6.check_crops(None, samples)
    path = write(tmp_path / "crop.json", {"q": {"sha256": "same", "box": [0, 0, 1, 1]}})
    assert stage6.check_crops(path, samples) == stage6.digest(path)
    with pytest.raises(ValueError, match="hash"):
        stage6.check_crops(path, [{"qid": "q", "sha256": "changed"}])


def test_browser_summary_v2_reports_failures_and_cancellations():
    outcomes = {"keyword": {"error": 0, "cancelled": 1}, "voice": {"error": 2, "cancelled": 0},
                "image": {"error": 0, "cancelled": 0}}
    report = bt.summarize({"version": 2, "quality_benchmark": False, "outcomes": outcomes,
                           "samples": [sample(10), sample(20)]})
    voice = report["outcomes"]["voice"]
    assert (voice["succeeded"], voice["attempts"], voice["error_rate"]) == (2, 4, 0.5)
    assert report["outcomes"]["image"]["error_rate"] is None
    only_failures = bt.summarize({"version": 2, "quality_benchmark": False, "outcomes": outcomes, "samples": []})
    assert only_failures["groups"] == [] and only_failures["outcomes"]["keyword"]["cancelled"] == 1
    assert bt.summarize(export([sample(10)]))["outcomes"] is None  # v1: no failure counts


@pytest.mark.parametrize("outcomes", [None, {"keyword": {"error": 0, "cancelled": 0}},
                                      {k: {"error": -1, "cancelled": 0} for k in ("keyword", "voice", "image")},
                                      {k: {"error": 0, "cancelled": 0} for k in ("keyword", "voice", "image")}])
def test_browser_summary_v2_rejects_invalid_or_empty_outcomes(outcomes):
    with pytest.raises(ValueError):
        bt.summarize({"version": 2, "quality_benchmark": False, "outcomes": outcomes, "samples": []})


def test_browser_summary_never_pools_cached_refilters():
    rows = [sample(900, "image"), sample(800, "image"), {**sample(5, "image"), "cached": True}]
    full, cached = bt.summarize(export(rows), warmup=1)["groups"]
    assert (full["cached"], full["n_measured"], full["p95_ms"]) == (False, 1, 800)
    assert (cached["cached"], cached["warmup_discarded"], cached["p95_ms"]) == (True, 0, 5)
    with pytest.raises(ValueError, match="cached"):
        bt.summarize(export([{**sample(5), "cached": "yes"}]))
