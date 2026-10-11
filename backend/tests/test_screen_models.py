"""Bảng sàng lọc model (screen_models.py), đo tài nguyên (latency_protocol.resources) và tiền xử lý OpenCLIP.

Adapter GIẢ và run tổng hợp: kiểm tra luồng/bảo vệ, không phải benchmark.
"""
import json
import sys
from pathlib import Path

import pytest

from tests.media_samples import wav
from tests.test_voice_image_benchmark import FIXTURE, voice_manifest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))

import latency_protocol as lp  # noqa: E402
import screen_models as sm  # noqa: E402


def write_configs(path: Path, voice=None, image=None) -> Path:
    path.write_text(json.dumps({"version": 1, "voice": voice or [], "image": image or []}), encoding="utf-8")
    return path


def test_load_configs_validates(tmp_path):
    ok = write_configs(tmp_path / "c.json", voice=[{"name": "a", "adapter": "m:A"}, {"name": "b", "adapter": "m:B"}])
    assert [c["name"] for c in sm.load_configs(ok, "voice", ["b"])] == ["b"]
    with pytest.raises(sm.ScreeningError, match="Không có cấu hình"):
        sm.load_configs(ok, "voice", ["zzz"])
    with pytest.raises(sm.ScreeningError, match="không có danh sách"):
        sm.load_configs(ok, "image")
    for bad in ([{"name": "a", "adapter": "m:A"}, {"name": "a", "adapter": "m:B"}],
                [{"name": "a b", "adapter": "m:A"}], [{"name": "a", "adapter": "noColon"}],
                [{"name": "a", "adapter": "m:A", "env": {"PATH": "x"}}]):
        with pytest.raises(sm.ScreeningError):
            sm.load_configs(write_configs(tmp_path / "bad.json", voice=bad), "voice")


def test_repo_screening_config_lists_three_configs_per_modality():
    for modality in ("voice", "image"):
        assert len(sm.load_configs(sm.CONFIGS, modality)) >= 3  # PLAN §8.3 bước 2


def test_run_voice_smoke_records_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, "gpu_status", lambda: None)
    m = voice_manifest(tmp_path, [
        ("v1", wav(1.0), "tìm cho mình cái túi cói dưới ba trăm nghìn", "s1", "dev"),
        ("v2", wav(1.0), "giỏ mây không lấy nhựa", "s2", "dev"),
        ("v3", wav(1.0, amplitude=0.0), None, "s3", "dev"),
    ])
    cfg = write_configs(tmp_path / "c.json", voice=[
        {"name": "fake-a", "adapter": "tests.fakes:FakeASR"},
        {"name": "fake-b", "adapter": "tests.fakes:FakeASR", "env": {"VNSTORE_FAKE_ASR_TEXT": "giỏ mây không lấy nhựa nhé"}},
        {"name": "missing", "adapter": "tests.fakes:NoSuchAdapter"},
    ])
    out, rep_dir = tmp_path / "out", tmp_path / "rep"
    base = ["run", "--modality", "voice", "--split", "dev", "--configs", str(cfg), "--manifest", str(m),
            "--catalog", str(FIXTURE), "--latency-rounds", "1", "--out-root", str(out), "--report-dir", str(rep_dir)]
    assert sm.main(base + ["--allow-unreviewed"]) == 0
    rep = json.loads(next(rep_dir.glob("*-screening.json")).read_text(encoding="utf-8"))
    assert rep["kind"] == "voice" and rep["status"] == "smoke" and rep["recommendation"] is None
    assert [r["name"] for r in rep["rows"]] == ["screen-fake-a", "screen-fake-b"]
    assert [(f["name"], f["status"]) for f in rep["failures"]] == [("missing", "error")]
    by = {r["name"]: r for r in rep["rows"]}
    assert by["screen-fake-a"]["quality"]["wer_normalized"] > 0 and by["screen-fake-b"]["quality"]["wer_normalized"] > 0
    assert by["screen-fake-a"]["primary"] != by["screen-fake-b"]["primary"]  # env riêng từng cấu hình có hiệu lực
    res = by["screen-fake-a"]["resources"]
    assert res["peak_rss_mb"] > 0 and res["model_mb"] is None and res["p95_ms"] is not None
    md = next(rep_dir.glob("*-screening.md")).read_text(encoding="utf-8")
    assert "SMOKE" in md and "missing" in md and "Không gợi ý" in md
    # Nhãn chưa duyệt mà không bật smoke: evaluator từ chối, mọi cấu hình lỗi → exit 3, không ghi bảng mới.
    assert sm.main(base) == 3 and len(list(rep_dir.glob("*-screening.json"))) == 1


def test_run_pending_collection_writes_nothing(tmp_path):
    m = voice_manifest(tmp_path, [("v1", wav(1.0), "giỏ mây", "s1", "train")])
    cfg = write_configs(tmp_path / "c.json", voice=[{"name": "fake", "adapter": "tests.fakes:FakeASR"}])
    rep_dir = tmp_path / "rep"
    assert sm.main(["run", "--modality", "voice", "--split", "dev", "--configs", str(cfg), "--manifest", str(m),
                    "--allow-unreviewed", "--out-root", str(tmp_path / "out"), "--report-dir", str(rep_dir)]) == 0
    assert not rep_dir.exists()
    with pytest.raises(SystemExit):  # split test không nằm trong lựa chọn
        sm.main(["run", "--modality", "voice", "--split", "test", "--configs", str(cfg)])


def image_run(root: Path, name: str, recall5: list[int], p95: float, model_mb: float, status="dev",
              manifest="m" * 64, split="dev") -> Path:
    d = root / name
    d.mkdir(parents=True)
    rows = [{"qid": f"q{i}", "task": "exact", "split": split, "family_id": f"f{i // 2}", "has_answer": True,
             "recall_1": v, "recall_5": v, "rr_10": float(v)} for i, v in enumerate(recall5)]
    mean = sum(recall5) / len(recall5)
    run = {"name": name, "evaluation_status": status, "split": split, "manifest_sha256": manifest,
           "catalog_sha256": "c" * 64, "include_drafts": True, "family_registry_sha256": "f" * 64,
           "family_grouping_policy": "registry-v1", "selected_qids": [r["qid"] for r in rows],
           "model": {"model_id": f"org/{name}", "revision": "abc"}, "index": {"entries": 100, "dim": 512},
           "metrics": {"n_queries": len(rows), "n_no_answer": 0,
                       "exact": {"n": len(rows), "recall_1": mean, "recall_5": mean, "recall_10": mean, "mrr_10": mean},
                       "similar": {"n": 0}, "latency": {"embed_ms": {"p50": p95 / 2, "p95": p95},
                                                        "adapter_load_ms": 10, "cold_first_call_ms": 5, "index_ms": 100,
                                                        "peak_vram_mb": [3000.0], "machine_busy_warnings": []}},
           "latency_protocol": {"idle_check": {"memory_used_mb_before": [1000.0]}},
           "environment": {"gpus": [{"name": "GPU"}], "ml_device_env": None, "tensorrt_env": None},
           "resources": {"peak_rss_mb": 900.0, "model_files": {"total_mb": model_mb}}}
    (d / "run.json").write_text(json.dumps(run), encoding="utf-8")
    (d / "predictions.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return d


def test_summarize_dev_suggests_best_and_cheapest_tied(tmp_path):
    n = 24  # 12 họ
    big = image_run(tmp_path, "big", [1] * n, p95=40, model_mb=800)
    small = image_run(tmp_path, "small", [1] * (n - 1) + [0], p95=10, model_mb=300)  # kém 1 query, rẻ hơn
    bad = image_run(tmp_path, "bad", [0] * n, p95=50, model_mb=900)
    rep = sm.summarize([big, small, bad], [{"name": "oom-model", "adapter": "m:X", "status": "oom", "detail": "OOM"}])
    assert rep["status"] == "dev_screening" and rep["primary_metric"]["key"] == "recall_5"
    by = {r["name"]: r for r in rep["rows"]}
    assert by["big"]["vs_best"] == {"is_best": True}
    assert by["small"]["vs_best"]["verdict"] == "chưa phân biệt được với tốt nhất"
    assert by["bad"]["vs_best"]["verdict"] == "khác rõ so với tốt nhất"
    assert by["big"]["pareto"] and by["small"]["pareto"] and not by["bad"]["pareto"]
    assert by["big"]["resources"]["vram_delta_mb"] == [2000.0] and by["big"]["resources"]["cold_start_ms"] == 115
    assert by["big"]["resources"]["index_mb"] == pytest.approx(0.2, abs=0.01)
    rec = rep["recommendation"]
    assert rec["status"] == "suggested_for_human_review"
    assert (rec["best_quality"], rec["second_candidate"]) == ("big", "small")
    assert any("60–100" in c for c in rep["checks"])  # 24 mẫu < cỡ dev subset của PLAN
    md = sm.markdown(rep)
    assert "oom-model" in md and "Ứng viên 2: `small`" in md


def test_pareto_keeps_config_that_saves_ram(tmp_path):
    fast = image_run(tmp_path, "fast", [1, 0, 1, 0], p95=10, model_mb=300)
    lean = image_run(tmp_path, "lean", [1, 0, 1, 0], p95=12, model_mb=300)
    run = json.loads((fast / "run.json").read_text(encoding="utf-8"))
    run["resources"]["peak_rss_mb"] = 5000.0  # nhanh hơn nhưng tốn RAM gấp nhiều lần (như TensorRT)
    (fast / "run.json").write_text(json.dumps(run), encoding="utf-8")
    rows = {r["name"]: r for r in sm.summarize([fast, lean])["rows"]}
    assert rows["fast"]["pareto"] and rows["lean"]["pareto"]


def test_summarize_guards(tmp_path):
    a = image_run(tmp_path, "a", [1, 0, 1, 0], 10, 100)
    b = image_run(tmp_path, "b", [1, 1, 1, 0], 10, 100, manifest="x" * 64)
    with pytest.raises(sm.cr.Incomparable, match="manifest"):
        sm.summarize([a, b])
    t1 = image_run(tmp_path, "t1", [1, 0], 10, 100, split="test", status="locked_test")
    t2 = image_run(tmp_path, "t2", [1, 1], 10, 100, split="test", status="locked_test")
    with pytest.raises(sm.cr.Incomparable, match="locked test"):
        sm.summarize([t1, t2])
    smoke = image_run(tmp_path, "s", [1, 0, 1, 0], 10, 100, status="smoke_unreviewed")
    rep = sm.summarize([a, smoke])
    assert rep["status"] == "smoke" and rep["recommendation"] is None
    few = sm.summarize([a, image_run(tmp_path, "c", [1, 1, 1, 1], 10, 50)])  # 2 họ < 5 cụm
    assert few["recommendation"]["status"] == "not_enough_clusters"
    assert sm.main(["summarize", str(a), str(b), "--report-dir", str(tmp_path / "r")]) == 2


def test_resources_reports_rss_and_loaded_model_files(tmp_path):
    from app import ml
    f = tmp_path / "model.onnx"
    f.write_bytes(b"x" * 2**20)
    ml.LOADED_FILES["test/repo@0/model.onnx"] = f
    try:
        res = lp.resources()
    finally:
        del ml.LOADED_FILES["test/repo@0/model.onnx"]
    assert res["peak_rss_mb"] > 0
    assert {"file": "test/repo@0/model.onnx", "mb": 1.0} in res["model_files"]["files"]
    assert res["model_files"]["total_mb"] >= 1.0


def test_openclip_preprocess_maps_to_transformers_convention():
    from app.ml.image import openclip_processor
    cfg = openclip_processor({"size": [224, 224], "mode": "RGB", "mean": [0.1, 0.2, 0.3], "std": [0.4, 0.5, 0.6],
                              "interpolation": "bicubic", "resize_mode": "shortest", "fill_color": 0})
    assert cfg["size"] == {"shortest_edge": 224} and cfg["crop_size"] == {"height": 224, "width": 224}
    assert cfg["resample"] == 3 and cfg["image_mean"] == [0.1, 0.2, 0.3] and cfg["rescale_factor"] == 1 / 255
    for bad in ({"resize_mode": "squash"}, {"interpolation": "bilinear"}, {"size": [224, 256]}):
        base = {"size": [224, 224], "mode": "RGB", "mean": [0] * 3, "std": [1] * 3, "interpolation": "bicubic",
                "resize_mode": "shortest"}
        with pytest.raises(RuntimeError):
            openclip_processor({**base, **bad})
