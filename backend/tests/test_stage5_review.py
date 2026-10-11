"""Regression cases discovered during the GĐ5 review; all labels are synthetic."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fakes import ByteHistogramEmbedder
from tests.test_voice_image_benchmark import FIXTURE, image_manifest, judgment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
import ablate
import eval_image as ei
import screen_models as sm
import calibrate_no_match as cn
import compare_runs as cr

from app.image.index import ImageIndex
from app.search.engine import SearchEngine
from app.modalities import ImageService, Status
from tests.media_samples import png


def args(**overrides):
    return SimpleNamespace(**{**dict(split="dev", warmup=1, latency_rounds=1, timeout=5, samples=100,
                                    include_drafts=False, allow_unreviewed=False, catalog=FIXTURE), **overrides})


def keyword_results(tmp_path, positives=1, negatives=5, variants=("baseline", "coverage")):
    spec = {"keyword": {"candidates": [{"name": "bm25"}], "variants": [{"name": v} for v in variants]}}
    results = []
    for variant in variants:
        name = f"bm25-{variant}"
        path = tmp_path / name
        path.mkdir()
        run = {"name": name, "split": "dev", "evaluation_status": "dev", "metrics": {}}
        rows = [{"qid": str(i), "group_id": str(i), "split": "dev", "has_answer": i < positives,
                 "judgments_cover_catalog": True, "ndcg_10": 1.0 if i < positives else None,
                 "success_5": True if i < positives else None, "false_accept": False if i >= positives else None}
                for i in range(positives + negatives)]
        (path / "run.json").write_text(json.dumps(run), encoding="utf-8")
        (path / "predictions.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
        results.append({"name": name, "variant": variant, "candidate": "bm25", "status": "ok", "run_dir": str(path)})
    return spec, results


def test_readiness_requires_primary_metric_clusters_not_only_no_match(tmp_path):
    spec, results = keyword_results(tmp_path)
    report = ablate.report_results(results, "keyword", spec, args())
    assert report["status"] == "needs_data_or_review"
    assert any("ndcg_10" in issue for issue in report["issues"])


def test_baseline_only_is_not_an_ablation_ready_for_selection(tmp_path):
    spec, results = keyword_results(tmp_path, positives=5, variants=("baseline",))
    assert ablate.report_results(results, "keyword", spec, args())["status"] == "needs_data_or_review"


def test_complete_keyword_ablation_can_be_ready(tmp_path):
    spec, results = keyword_results(tmp_path, positives=5)
    assert ablate.report_results(results, "keyword", spec, args())["status"] == "ready_for_selection_review"


def test_keyword_input_changed_during_evaluation_is_not_misattributed(tmp_path, monkeypatch, snap):
    query = {"qid": "q", "group_id": "g", "query": "túi cói", "split": "dev", "verified": True,
             "labeled_by": "synthetic", "catalog_sha256": snap.sha256,
             "has_answer": True, "relevance": {"fx-tui-coi-quai-da": 3}}
    path = tmp_path / "queries.jsonl"
    path.write_text(json.dumps(query), encoding="utf-8")
    original = ablate.ek.evaluate
    def mutate(*a, **kw):
        value = original(*a, **kw)
        path.write_text("changed while running", encoding="utf-8")
        return value
    monkeypatch.setattr(ablate.ek, "evaluate", mutate)
    configs = [{"name": "bm25-baseline", "env": {"VNSTORE_SEARCH_CONFIG": "{}"}}]
    with pytest.raises(ValueError, match="changed"):
        ablate.keyword_runs(configs, args(queries=path), tmp_path / "runs")
    assert not list(tmp_path.glob("runs/*/run.json"))


def test_keyword_matrix_refuses_silently_ignored_voice_settings(tmp_path):
    spec = {"keyword": {"candidates": [{"name": "bm25"}], "variants": [
        {"name": "baseline"}, {"name": "vad", "env": {"VNSTORE_ASR_VAD": "0"}}]}}
    path = tmp_path / "m.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError, match="keyword"):
        ablate.load_matrix(path, "keyword")


def test_ocr_cold_start_and_warmup_failures_are_recorded(tmp_path, snap):
    manifest = image_manifest(tmp_path, [("q", "exact", None, judgment({"fx-gio-may-co-quai": 3}, "fx-gio-may-co-quai"))])
    samples = json.loads(manifest.read_text(encoding="utf-8"))["samples"]
    class OCR:
        n = 0
        def recognize(self, data):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("first load failed")
            return ""
    emb = ByteHistogramEmbedder()
    rows, metrics = ei.evaluate(samples, manifest.parent, emb, ImageIndex.build(snap, emb), SearchEngine(snap), ocr=OCR())
    assert metrics["latency"]["cold_ocr_first_call_ms"] >= 0
    assert metrics["ocr_startup_errors"]
    assert rows[0]["ocr_error"] is None  # the failure was startup, not the measured request


def test_crop_null_is_not_accepted_as_a_reviewed_crop(tmp_path):
    manifest = image_manifest(tmp_path, [("q", "exact", None, judgment({"fx-gio-may-co-quai": 3}, "fx-gio-may-co-quai"))])
    sample = json.loads(manifest.read_text(encoding="utf-8"))["samples"][0]
    crop = tmp_path / "crops.json"
    crop.write_text(json.dumps({"q": {"sha256": sample["sha256"], "box": None}}), encoding="utf-8")
    assert ei.main(["--adapter", "tests.fakes:Missing", "--manifest", str(manifest), "--catalog", str(FIXTURE),
                    "--split", "dev", "--allow-unreviewed", "--crops", str(crop)]) == 1


def test_screening_cost_includes_ocr_cold_start():
    run = {"metrics": {"latency": {"adapter_load_ms": 1, "index_ms": 2,
                                    "cold_first_call_ms": 3, "cold_ocr_first_call_ms": 100}},
           "pipeline": {"ocr": {"model_id": "test/ocr"}}}
    assert sm.resource_row("image", run)["cold_start_ms"] == 106


def test_legacy_ocr_run_does_not_claim_complete_cold_start_cost():
    run = {"metrics": {"latency": {"adapter_load_ms": 1, "index_ms": 2, "cold_first_call_ms": 3}},
           "pipeline": {"ocr": {"model_id": "test/ocr"}}}
    assert sm.resource_row("image", run)["cold_start_ms"] is None
    run["pipeline"]["ocr"] = None
    assert sm.resource_row("image", run)["cold_start_ms"] == 6


def test_invalid_optional_ocr_keeps_image_service_usable(snap, monkeypatch):
    monkeypatch.setenv("VNSTORE_OCR", "misspelled")
    emb = ByteHistogramEmbedder()
    service = ImageService(emb, Status("ok"), ImageIndex.build(snap, emb))
    result, diagnostics = service.search(png(), SearchEngine(snap))
    assert result["results"] and result["warnings"]
    assert diagnostics["ocr_error"] == "ValueError"


@pytest.mark.parametrize("variant", [{"search": {"ocr_weight": .5}}, {"requires_crops": True},
                                     {"requires_crops": "false"}])
def test_keyword_matrix_rejects_ignored_or_mistyped_options(tmp_path, variant):
    spec = {"keyword": {"candidates": [{"name": "bm25"}], "variants": [
        {"name": "baseline"}, {"name": "invalid", **variant}]}}
    path = tmp_path / "m.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError):
        ablate.load_matrix(path, "keyword")


def test_keyword_smoke_flag_cannot_gain_reviewed_status(tmp_path, snap):
    query = {"qid": "q", "query": "túi cói", "split": "dev", "verified": True,
             "labeled_by": "synthetic", "has_answer": True, "relevance": {"fx-tui-coi-quai-da": 3}}
    path = tmp_path / "queries.jsonl"
    path.write_text(json.dumps(query), encoding="utf-8")
    configs = [{"name": "bm25-baseline", "env": {"VNSTORE_SEARCH_CONFIG": "{}"}}]
    results = ablate.keyword_runs(configs, args(queries=path, allow_unreviewed=True), tmp_path / "runs")
    run = json.loads((Path(results[0]["run_dir"]) / "run.json").read_text(encoding="utf-8"))
    assert run["evaluation_status"] == "smoke_unreviewed"


@pytest.mark.parametrize("key,value", [("group_id", "different"), ("has_answer", False)])
def test_keyword_pairing_rejects_changed_group_or_label(key, value):
    row = {"qid": "q", "group_id": "g", "has_answer": True, "ndcg_10": 1}
    with pytest.raises(cr.Incomparable):
        ablate.paired_keyword([row], [{**row, key: value}])


def test_calibration_refuses_ocr_startup_failure():
    with pytest.raises(ValueError, match="failed"):
        cn.calibrate({"split": "dev", "evaluation_status": "dev", "metrics": {"ocr_startup_errors": ["failed"]}}, [])


@pytest.mark.parametrize("problem", [None, "few_similar", "unlocked", "ocr_startup"])
def test_image_readiness_requires_each_task_and_locked_plan(tmp_path, problem):
    spec = {"candidate_status": "selected_on_reviewed_dev", "image": {
        "candidates": [{"name": "a"}, {"name": "b"}],
        "variants": [{"name": "baseline"}, {"name": "variant"}]}}
    results = []
    for candidate in ("a", "b"):
        for variant in ("baseline", "variant"):
            name = f"{candidate}-{variant}"
            directory = tmp_path / name
            directory.mkdir()
            rows = []
            for task in ("exact", "similar", "image_text", "negative"):
                n = 1 if task == "similar" and problem == "few_similar" else 5
                for i in range(n):
                    row = {"qid": f"{task}-{i}", "family_id": f"{task}-{i}", "split": "dev",
                           "task": "exact" if task == "negative" else task, "has_answer": task != "negative"}
                    if task == "negative":
                        row["false_accept"] = False
                    else:
                        row["false_reject"] = False
                        row["recall_5" if task == "exact" else "ndcg_10"] = 1
                    rows.append(row)
            run = {"name": name, "split": "dev", "evaluation_status": "dev",
                   "split_plan": {"status": "not_checked" if problem == "unlocked" else "locked", "sha256": "same"},
                   "metrics": {"ocr_startup_errors": ["failed"] if problem == "ocr_startup" else []}}
            (directory / "run.json").write_text(json.dumps(run), encoding="utf-8")
            (directory / "predictions.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
            results.append({"name": name, "candidate": candidate, "variant": variant,
                            "status": "ok", "run_dir": str(directory)})
    report = ablate.report_results(results, "image", spec, args())
    assert report["status"] == ("needs_data_or_review" if problem else "ready_for_selection_review")
    if problem == "few_similar":
        assert any("similar_ndcg_10" in issue for issue in report["issues"])


def test_comparison_refuses_changed_split_plan():
    rows = [{"qid": "q", "family_id": "f", "recall_5": 1}]
    with pytest.raises(cr.Incomparable, match="split_plan"):
        cr.compare(({"split_plan": {"sha256": "a"}}, rows), ({"split_plan": {"sha256": "b"}}, rows))
