"""Bộ ảnh thử khám phá: nạp/kiểm dữ liệu, tóm tắt không cần nhãn, báo cáo, trang duyệt vùng cắt (13/10/2026).

Không cần Pillow/model: dữ liệu và kết quả tìm kiếm là tổng hợp. Phần chuẩn bị ảnh (Pillow) nằm ở
scripts/benchmark/tests/test_image_exploratory_prepare.py.
"""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.media_samples import png

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))

import prepare_crop_review as pcr  # noqa: E402
import run_image_exploratory as rie  # noqa: E402


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def dataset(tmp_path):
    """Hai ảnh: một ảnh tương tự (có ca crop) và một ảnh đối chứng gallery."""
    ds = tmp_path / "ds"
    images = []
    for iid, role, group in (("web-1", "similar_candidate", "may-tre-coi"), ("control-1", "gallery_control", "gom-su")):
        rel = f"raw/images/{role}/{group}/{iid}.png"
        (ds / rel).parent.mkdir(parents=True)
        data = png(64, 48)
        (ds / rel).write_bytes(data)
        images.append({"id": iid, "role": role, "group": group, "topic": None, "title": f"File:{iid}.png",
                       "image_path": rel, "sha256": hashlib.sha256(data).hexdigest(),
                       "expected_product_id": "p-1" if role == "gallery_control" else None})
    write_json(ds / "manifest.json", {"dataset_version": "t-1", "catalog_sha256": "0" * 64, "images": images})
    write_json(ds / "test_cases.json", {"cases": [
        {"case_id": "web-1-image", "image_path": images[0]["image_path"], "task": "similar_candidate", "text_vi": ""},
        {"case_id": "web-1-crop", "image_id": "web-1", "image_path": images[0]["image_path"],
         "task": "manual_crop_comparison", "text_vi": "", "crop_instruction_vi": "Chọn giỏ."},
        {"case_id": "control-1-image", "image_path": images[1]["image_path"], "task": "gallery_control", "text_vi": ""},
    ]})
    write_json(ds / "crops.json", {"format": "xyxy", "chosen_by": "test", "crops": {"web-1-crop": [0.1, 0.1, 0.9, 0.9]}})
    return ds


# --- nạp dữ liệu ---

def test_load_dataset_accepts_consistent_set(dataset):
    manifest, cases, crops = rie.load_dataset(dataset)
    assert len(manifest["images"]) == 2 and len(cases) == 3 and crops == {"web-1-crop": [0.1, 0.1, 0.9, 0.9]}


def test_load_dataset_rejects_changed_image(dataset):
    (dataset / "raw/images/similar_candidate/may-tre-coi/web-1.png").write_bytes(png(40, 40))
    with pytest.raises(SystemExit, match="sha256"):
        rie.load_dataset(dataset)


@pytest.mark.parametrize("crops,match", [
    ({"web-1-image": [0, 0, 1, 1]}, "không phải ca cắt vùng"),
    ({"web-1-crop": [0.9, 0.1, 0.1, 0.9]}, "không hợp lệ"),
    ({"web-1-crop": [0, 0, 1.5, 1]}, "không hợp lệ"),
    ({"web-1-crop": [0, 0, 1]}, "không hợp lệ"),
])
def test_load_dataset_rejects_bad_crops(dataset, tmp_path, crops, match):
    f = tmp_path / "crops.bad.json"
    write_json(f, {"crops": crops})
    with pytest.raises(SystemExit, match=match):
        rie.load_dataset(dataset, f)


def test_crops_meta_distinguishes_reviewed_export(dataset, tmp_path):
    assert rie.crops_meta(dataset / "crops.json")["reviewed"] is False
    f = tmp_path / "crops.reviewed.json"
    write_json(f, {"kind": "vnstore_crop_review", "reviewed_by": "r1", "reviewed_at": "2026-10-13T10:00:00+07:00",
                   "complete": True, "crops": {"web-1-crop": [0, 0, 1, 1]}})
    meta = rie.crops_meta(f)
    assert meta["reviewed"] and meta["reviewed_by"] == "r1" and meta["complete"] and meta["n"] == 1
    assert rie.crops_meta(tmp_path / "missing.json") == {"file": None, "reviewed": False}


# --- tóm tắt không cần nhãn ---

def result(pid, group, sim, cov=None):
    x = {"product_id": pid, "group": group, "category_id": group, "similarity": sim, "score": 0.01}
    if cov is not None:
        x["text_coverage"] = cov
    return x


def row(case_id, image_id, task, role, group, results, **extra):
    return {"case_id": case_id, "image_id": image_id, "task": task, "role": role, "group": group, "topic": None,
            "text_vi": extra.pop("text_vi", ""), "status": "ok", "total": len(results), "results": results,
            "top_similarity": results[0]["similarity"] if results else None, "applied_filters": [],
            "timings_ms": {"embed": extra.pop("embed", 10.0), "total": extra.pop("total", 30.0)}, **extra}


def test_summarize_label_free_checks():
    rows = [
        row("c-image", "c", "gallery_control", "gallery_control", "gom-su",
            [result("p-1", "gom-su", 0.99), result("p-2", "gom-su", 0.8)], expected_product_id="p-1",
            embed=900.0, total=1000.0),
        row("c-text-0", "c", "image_text", "gallery_control", "gom-su",
            [result("p-2", "gom-su", 0.8, 1.0), result("p-1", "gom-su", 0.99, 1.0)], expected_product_id="p-1",
            text_vi="bình gốm", applied_filters=[{"key": "price"}], price={"max_vnd": 1}, price_violations=["p-2"]),
        row("w-image", "w", "similar_candidate", "similar_candidate", "may-tre-coi",
            [result("p-3", "may-tre-coi", 0.7)] + [result(f"p-{i}", "gom-su", 0.6) for i in range(4, 8)]),
        row("w-crop", "w", "manual_crop_comparison", "similar_candidate", "may-tre-coi",
            [result("p-3", "may-tre-coi", 0.75), result("p-8", "may-tre-coi", 0.7)], crop=[0, 0, 1, 1]),
        row("n-image", "n", "negative_candidate", "negative_candidate", "ngoai-catalog", [result("p-9", "gom-su", 0.5)]),
        {"case_id": "x-crop", "status": "skipped_no_crop"},
        {"case_id": "y-image", "status": "error"},
    ]
    s = rie.summarize(rows)
    assert (s["cases"], s["ok"], s["errors"], s["skipped"]) == (7, 5, ["y-image"], ["x-crop"])
    assert s["gallery_control"]["rank1"] == 1 and s["gallery_control"]["items"][0]["rank"] == 1
    ct = s["image_text"]["gallery_control_with_text"]
    assert ct == [{"case_id": "c-text-0", "text_vi": "bình gốm", "expected": "p-1", "rank": 2, "filters": ["price"]}]
    assert s["image_text"]["price_violations"] == {"c-text-0": ["p-2"]}
    assert s["image_text"]["text_coverage_top5"] == {"n": 1, "mean": 1.0}
    # Proxy chỉ tính ảnh ngoài gallery có nhóm catalog: 1/5 kết quả cùng nhóm, top 1 đúng nhóm.
    assert s["group_proxy"]["all"] == {"n": 1, "top1_same_group": 1, "top5_same_group": 0.2}
    assert s["crop_vs_full"]["items"][0]["top5_overlap"] == 1
    assert s["crop_vs_full"]["group_proxy_better"] == 1
    assert s["top_similarity_by_role"]["negative_candidate"]["median"] == 0.5
    # Ca đầu (khởi động) không nằm trong p95 ấm.
    assert s["latency_ms"]["first_case_total"] == 1000.0 and s["latency_ms"]["api_total_p95"] == 30.0


def test_report_survives_missing_similarity(tmp_path):
    rows = [row("c-image", "c", "gallery_control", "gallery_control", "gom-su", [], expected_product_id="p-1"),
            row("w-image", "w", "similar_candidate", "similar_candidate", "gom-su", [result("p-1", "gom-su", None)]),
            row("w-crop", "w", "manual_crop_comparison", "similar_candidate", "gom-su", [result("p-1", "gom-su", None)])]
    rows[1]["top_similarity"] = rows[2]["top_similarity"] = None
    s = rie.summarize(rows)
    args = SimpleNamespace(adapter="x:Y", top_k=10, dataset=tmp_path, crops=None)
    res = {"rows": rows, "manifest": {"dataset_version": "t-1"}, "catalog_sha256": "a" * 64, "load_s": 1.0,
           "search_config": {"visual_text_rank": "coverage"}}
    rie.write_report("t", args, res, s, tmp_path / "run", tmp_path / "report", rie.crops_meta(tmp_path / "none.json"))
    text = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "| c | p-1 | — | — |" in text and "— → —" in text and "visual_text_rank=coverage" in text
    assert "chưa được người duyệt xác nhận" in text


def test_engine_text_coverage(engine):
    cov = engine.text_coverage("túi cói", ["fx-tui-coi-tron", "fx-binh-gom-men-lam"])
    assert cov["fx-tui-coi-tron"] == 1.0 and cov["fx-binh-gom-men-lam"] == 0.0
    assert engine.text_coverage("dưới 500k", ["fx-tui-coi-tron"]) is None


# --- trang duyệt vùng cắt ---

def test_prepare_crop_review_builds_packet_and_page(dataset):
    packet = pcr.build(dataset)
    assert [c["case_id"] for c in packet["cases"]] == ["web-1-crop"]
    c = packet["cases"][0]
    assert c["proposed"] == [0.1, 0.1, 0.9, 0.9] and c["title"] == "web-1.png" and c["instruction"] == "Chọn giỏ."
    assert packet["source_crops_sha256"] == hashlib.sha256((dataset / "crops.json").read_bytes()).hexdigest()


def test_prepare_crop_review_rejects_inconsistent_inputs(dataset):
    crops = json.loads((dataset / "crops.json").read_text(encoding="utf-8"))
    write_json(dataset / "crops.json", {**crops, "crops": {}})
    with pytest.raises(SystemExit, match="chưa có vùng"):
        pcr.build(dataset)
    write_json(dataset / "crops.json", {**crops, "crops": {**crops["crops"], "ghost-crop": [0, 0, 1, 1]}})
    with pytest.raises(SystemExit, match="không thuộc test_cases"):
        pcr.build(dataset)
    write_json(dataset / "crops.json", {**crops, "crops": {"web-1-crop": [0.5, 0, 0.4, 1]}})
    with pytest.raises(SystemExit, match="không hợp lệ"):
        pcr.build(dataset)
    write_json(dataset / "crops.json", crops)
    (dataset / "raw/images/similar_candidate/may-tre-coi/web-1.png").unlink()
    with pytest.raises(SystemExit, match="thiếu file"):
        pcr.build(dataset)


def test_prepare_crop_review_escapes_html_in_packet(dataset):
    cases = json.loads((dataset / "test_cases.json").read_text(encoding="utf-8"))
    cases["cases"][1]["crop_instruction_vi"] = "</script><script>alert(1)</script>"
    write_json(dataset / "test_cases.json", cases)
    out = dataset / "crop_review.html"
    sys.argv = ["prepare_crop_review.py", "--dataset", str(dataset)]
    assert pcr.main() == 0
    html = out.read_text(encoding="utf-8")
    assert "</script><script>alert(1)" not in html
