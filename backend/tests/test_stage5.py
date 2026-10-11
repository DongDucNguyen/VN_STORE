"""GĐ5 regression and leakage guards, synthetic fixtures only."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.image.index import ImageIndex, VisualHit
from app.image.pipeline import crop_image, retrieve
from app.ml.vad import SileroVAD
from app.search.config import SearchConfig
from app.search.engine import SearchEngine, SearchFilters
from tests.fakes import ByteHistogramEmbedder
from tests.media_samples import png, wav
from tests.test_image_index import manual_index
from tests.test_voice_image_benchmark import FIXTURE, voice_manifest
from tests.test_voice_image_benchmark import image_manifest, judgment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
import ablate
import calibrate_no_match as cn
import compare_runs as cr
import eval_voice as ev
import eval_image as ei


@pytest.mark.parametrize("values", [{"rrf_k": 0}, {"rrf_k": True}, {"ocr_weight": float("nan")},
                                   {"image_min_similarity": 2}, {"typo": 1}, {"strict_accents": "yes"}])
def test_invalid_settings_fail(values):
    with pytest.raises((ValueError, TypeError)):
        SearchConfig.from_dict(values)


def test_language_coverage_preserves_plain_queries_and_rejects_partial(snap):
    engine = SearchEngine(snap, SearchConfig(min_token_coverage=1, strict_accents=True))
    assert engine.search("tui coi")["results"][0]["id"].startswith("fx-tui-coi")
    assert engine.search("túi cói xyzkhongcotrongcatalog")["results"] == []
    assert SearchEngine(snap).search("túi cói xyzkhongcotrongcatalog")["results"]
    assert engine.search("khăn lúa")["results"] == []
    assert engine.search("khăn lụa")["results"]


def test_ocr_cannot_create_price_filters_or_override_explicit_filters(snap):
    engine = SearchEngine(snap, SearchConfig(ocr_weight=1))
    hits = [VisualHit(pid, 0.9, "i") for pid in snap.products]
    baseline = engine.search_visual(hits, "dưới 300k không lấy nhựa")
    result = engine.search_visual(hits, "dưới 300k không lấy nhựa", ocr_text="trên 1 triệu giỏ nhựa")
    assert result["applied_filters"] == baseline["applied_filters"]
    assert all(r["price"]["min_vnd"] < 300000 and r["id"] != "fx-gio-nhua-dan" for r in result["results"])
    assert engine.search_visual(hits, ocr_text="dưới 1k")["applied_filters"] == []


def test_similarity_gate_not_bypassed_by_text_or_ocr(snap):
    engine = SearchEngine(snap, SearchConfig(image_min_similarity=0.8, ocr_weight=1))
    assert engine.search_visual([VisualHit("fx-tui-coi-quai-da", 0.7, "i")], "túi cói",
                                ocr_text="túi cói")["results"] == []
    assert engine.search_visual([VisualHit("fx-tui-coi-quai-da", 0.8, "i")])["results"]


def test_zero_text_weight_keeps_visual_order(snap):
    engine = SearchEngine(snap, SearchConfig(text_weight=0))
    hits = [VisualHit("fx-tui-coi-quai-da", .9, "i"), VisualHit("fx-binh-gom-men-lam", .8, "j")]
    out = engine.search_visual(hits, "gốm")
    assert out["results"][0]["id"] == "fx-tui-coi-quai-da"


def test_single_view_is_first_gallery_image_not_best_query_view():
    index = manual_index([("a1", "a", [0, 1]), ("a2", "a", [1, 0]), ("b1", "b", [.5, .5])])
    assert index.query([1, 0])[0].product_id == "a"
    assert index.query([1, 0], multi_view=False)[0].product_id == "b"


def test_ocr_failure_keeps_retrieval_and_records_failure(snap):
    class BrokenOCR:
        def recognize(self, data):
            raise RuntimeError("offline")
    emb = ByteHistogramEmbedder()
    out, diag = retrieve(png(), emb, ImageIndex.build(snap, emb), SearchEngine(snap), ocr=BrokenOCR())
    assert out["results"] and diag["ocr_error"] == "RuntimeError"
    assert any("Chưa đọc được" in w for w in out["warnings"])


@pytest.mark.parametrize("box", [[0, 0, 0, 1], [0, 0, 2, 1], [0, 0, float("nan"), 1], [0, 1]])
def test_crop_rejects_bad_coordinates_before_pillow(box):
    with pytest.raises(ValueError, match="crop"):
        crop_image(png(), box)


def test_voice_settings_and_gate_provenance(monkeypatch, tmp_path):
    from app.ml.asr import PhoWhisperBase
    monkeypatch.setenv("VNSTORE_VAD_THRESHOLD", "0.35")
    monkeypatch.setenv("VNSTORE_VAD_MIN_MS", "150")
    assert PhoWhisperBase().config["vad"]["threshold"] == .35
    assert PhoWhisperBase().config["vad"]["min_speech_ms"] == 150
    with pytest.raises(ValueError):
        SileroVAD(float("nan"))
    manifest = voice_manifest(tmp_path, [("v", wav(1.0), "túi cói", "s", "dev")])
    monkeypatch.setenv("VNSTORE_SILENCE_DBFS", "-50")
    assert ev.main(["--adapter", "tests.fakes:FakeASR", "--manifest", str(manifest), "--catalog", str(FIXTURE),
                    "--split", "dev", "--allow-unreviewed", "--out-root", str(tmp_path / "runs")]) == 0
    run = json.loads(next((tmp_path / "runs").glob("*/run.json")).read_text(encoding="utf-8"))
    assert run["silence_dbfs"] == -50 and "pipeline_ms" in run["metrics"]["latency"]


def calibration_rows():
    return [{"qid": str(i), "split": "dev", "family_id": str(i), "has_answer": i % 2 == 0,
             "top_similarity": .8 if i % 2 == 0 else .2} for i in range(10)]


def test_no_match_calibration_gates_and_boundary():
    run = {"split": "dev", "evaluation_status": "dev"}
    report = cn.calibrate(run, calibration_rows())
    assert .2 < report["candidate"]["threshold"] <= .8
    assert report["candidate"]["f1_no_match"] == 1
    assert cn.calibrate(run, calibration_rows()[:4])["candidate"] is None
    for invalid in ({"split": "test", "evaluation_status": "locked_test"},
                    {"split": "dev", "evaluation_status": "smoke_unreviewed"},
                    {**run, "skipped_unjudged_or_unreviewed": 1}):
        with pytest.raises(ValueError):
            cn.calibrate(invalid, calibration_rows())
    with pytest.raises(ValueError, match="both"):
        cn.calibrate(run, calibration_rows()[::2])


def test_matrix_is_equal_budget_and_does_not_inherit_search_env(monkeypatch):
    monkeypatch.setenv("VNSTORE_SEARCH_CONFIG", '{"ocr_weight":9}')
    path = ROOT / "experiments/configs/ablation.json"
    for modality in ("voice", "image"):
        spec, configs = ablate.load_matrix(path, modality)
        assert len(configs) == 2 * len(spec[modality]["variants"])
        baseline = next(c for c in configs if c["variant"] == "baseline")
        assert json.loads(baseline["env"]["VNSTORE_SEARCH_CONFIG"])["ocr_weight"] == 0
    with pytest.raises(SystemExit):
        ablate.main(["--modality", "image", "--split", "test"])


def test_ablation_records_all_failed_runs_without_selection(tmp_path):
    manifest = voice_manifest(tmp_path, [("v", wav(1), "túi cói", "s", "dev")])
    spec = {"voice": {"candidates": [{"name": "broken", "adapter": "tests.fakes:Missing"}],
                       "variants": [{"name": "baseline"}]}}
    matrix = tmp_path / "matrix.json"
    matrix.write_text(json.dumps(spec), encoding="utf-8")
    out = tmp_path / "out"
    assert ablate.main(["--modality", "voice", "--matrix", str(matrix), "--manifest", str(manifest),
                        "--allow-unreviewed", "--catalog", str(FIXTURE), "--out-root", str(out)]) == 2
    report = json.loads(next(out.glob("*/report.json")).read_text(encoding="utf-8"))
    assert report["selection"] is None and report["results"][0]["status"] == "error"


def test_keyword_bootstrap_uses_paired_eligible_query_groups():
    a = [{"qid": str(i), "group_id": str(i), "ndcg_10": 0.5} for i in range(6)]
    b = [dict(r, ndcg_10=1) for r in a]
    b[0]["ndcg_10"] = None
    result = ablate.paired_keyword(a, b, 100)["ndcg_10"]
    assert result["clusters"] == 5 and result["delta"] == .5 and result["ci95"] == [.5, .5]


def test_image_comparison_rejects_different_catalog():
    a = {"split": "dev", "catalog_sha256": "a"}
    rows = [{"qid": "q", "family_id": "f", "recall_5": 1}]
    with pytest.raises(cr.Incomparable, match="catalog_sha256"):
        cr.compare((a, rows), ({**a, "catalog_sha256": "b"}, rows))


def test_crop_sidecar_stale_hash_rejected_before_loading_model(tmp_path):
    manifest = image_manifest(tmp_path, [("q", "exact", None, judgment({"fx-gio-may-co-quai": 3}, "fx-gio-may-co-quai"))])
    crops = tmp_path / "crops.json"
    crops.write_text(json.dumps({"q": {"sha256": "0" * 64, "box": [0, 0, 1, 1]}}), encoding="utf-8")
    out = tmp_path / "runs"
    assert ei.main(["--adapter", "tests.fakes:Missing", "--manifest", str(manifest), "--catalog", str(FIXTURE),
                    "--split", "dev", "--allow-unreviewed", "--crops", str(crops), "--out-root", str(out)]) == 1
    assert not out.exists()


def test_pending_image_matrix_is_collection_pending():
    args = SimpleNamespace(split="dev", warmup=1, latency_rounds=3, timeout=5, samples=100)
    spec, configs = ablate.load_matrix(ROOT / "experiments/configs/ablation.json", "image")
    results = [{**c, "status": "pending_crops" if c["requires_crops"] else "no_samples"} for c in configs]
    assert ablate.report_results(results, "image", spec, args)["status"] == "pending_collection"
