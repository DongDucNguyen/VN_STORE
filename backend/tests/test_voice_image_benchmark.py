"""Metric và evaluator voice/ảnh trên dữ liệu TỔNG HỢP; không phải kết quả benchmark."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

from tests.media_samples import png, wav

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "scripts" / "benchmark"
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "catalog.fixture.json"
sys.path.insert(0, str(BENCH))


import asr_metrics as am  # noqa: E402
import eval_image as ei  # noqa: E402
import eval_voice as ev  # noqa: E402
import retrieval_metrics as rm  # noqa: E402


# ---------- WER/CER ----------

def test_wer_counts_each_edit_type():
    e = am.word_edits("tìm túi cói dưới ba trăm", "tìm cối dưới ba trăm nghìn")
    assert (e.substitutions, e.deletions, e.insertions, e.reference_length) == (1, 1, 1, 6)
    assert e.rate == pytest.approx(3 / 6)


def test_diacritics_are_errors_case_and_punct_only_in_normalized():
    assert am.wer("túi cói", "tui coi") == 1.0  # bỏ dấu không được tính là đúng
    assert am.cer("túi cói", "tui coi") == pytest.approx(2 / 6)
    assert am.wer("Túi cói, dưới 300k!", "túi cói dưới 300k") == 0.0
    assert am.wer("Túi cói, dưới 300k!", "túi cói dưới 300k", level="raw") == pytest.approx(3 / 4)
    assert am.wer("300k", "ba trăm nghìn") == pytest.approx(3.0)  # không tự đổi cách viết số


def test_nfc_and_empty_reference():
    decomposed = "túi cói"  # dấu sắc tổ hợp
    assert am.wer("túi cói", decomposed) == 0.0
    assert am.word_edits(None, "xin chào").rate is None
    assert am.word_edits("", "").reference_length == 0
    total = am.word_edits("a b", "a") + am.word_edits("c d e", "c d e")
    assert total.rate == pytest.approx(1 / 5)


# ---------- Metric xếp hạng ----------

def test_ndcg_ap_success_and_unjudged():
    labels = {"a": 3, "b": 0, "c": 2, "d": 1}
    assert rm.ndcg_at(["a", "c", "d", "b"], labels) == pytest.approx(1.0)
    assert 0 < rm.ndcg_at(["b", "a", "c", "d"], labels) < 1
    assert rm.ap_at(["a", "b", "c", "d"], labels) == pytest.approx((1 + 2 / 3) / 2)
    assert rm.success_at(["b", "d", "a", "c"], labels, 1) is False
    assert rm.success_at(["b", "a"], labels, 5) is True
    assert rm.ndcg_at(["a", "x"], labels) is None and rm.ap_at(["x"], labels) is None
    assert rm.success_at(["x", "a"], labels, 5) is None
    assert rm.exact_rr_at(["b", "a"], "a") == 0.5 and rm.exact_rr_at(["b"], "a") == 0.0
    assert rm.percentile([5, 1, 3, 4, 2], 0.95) == 5 and rm.percentile([], 0.5) is None


# ---------- eval_voice ----------

def voice_manifest(tmp_path, samples):
    d = tmp_path / "voice"
    (d / "raw").mkdir(parents=True)
    shutil.copy(ROOT / "benchmarks/voice/manifest.schema.json", d / "manifest.schema.json")
    rows = []
    for qid, audio, ref, speaker, split in samples:
        (d / "raw" / f"{qid}.wav").write_bytes(audio)
        rows.append({"qid": qid, "audio_path": f"raw/{qid}.wav", "sha256": hashlib.sha256(audio).hexdigest(),
                     "reference_text": ref, "speaker_id": speaker, "region": "nam", "device": "phone-a",
                     "environment": "quiet", "split": split, "consent": {"status": "unknown", "evidence": None},
                     "transcript_review": None})
    (d / "manifest.json").write_text(json.dumps({"manifest_version": "1.0.0", "samples": rows}, ensure_ascii=False),
                                     encoding="utf-8")
    return d / "manifest.json"


def test_eval_voice_end_to_end(tmp_path, capsys):
    m = voice_manifest(tmp_path, [
        ("v1", wav(1.0), "tìm cho mình cái túi cói dưới ba trăm nghìn", "s1", "dev"),
        ("v2", wav(1.0), "tìm cho mình cái túi cói dưới bốn trăm nghìn", "s2", "dev"),
        ("v3", wav(1.0, amplitude=0.0), None, "s3", "dev"),
        ("v4", wav(1.0), "giỏ mây không lấy nhựa", "s4", "train"),
    ])
    args = ["--adapter", "tests.fakes:FakeASR", "--manifest", str(m), "--catalog", str(FIXTURE),
            "--split", "dev", "--name", "fake-smoke", "--out-root", str(tmp_path / "out")]
    assert ev.main(args) == 1  # nhãn chưa duyệt: phải bật smoke rõ ràng
    assert ev.main(args + ["--allow-unreviewed"]) == 0
    run_dir = next((tmp_path / "out").iterdir())
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    rows = [json.loads(x) for x in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    met = run["metrics"]
    assert run["evaluation_status"] == "smoke_unreviewed" and run["model"]["model_id"] == "test/fake-asr"
    assert met["n_clips"] == 3 and met["n_speech"] == 2 and met["n_silence"] == 1
    assert met["wer_normalized"] == pytest.approx(1 / 20)  # "ba" → "bốn": 1 lỗi / 2×10 âm tiết
    assert met["price_accuracy"] == 0.5 and met["n_price"] == 2
    assert met["silence_hallucination_rate"] == 0.0  # bị chặn trước ASR
    by = {r["qid"]: r for r in rows}
    assert by["v3"]["gate_rejected"] == "audio_silent" and by["v3"]["hallucinated"] is False
    assert by["v1"]["price_ref"] == by["v1"]["price_hyp"] and by["v1"]["wer_normalized"] == 0.0
    assert met["by_group"]["region"]["nam"]["n"] == 2


def test_eval_voice_guards(tmp_path):
    same_speaker = voice_manifest(tmp_path, [("a", wav(1.0), "x", "s1", "dev"), ("b", wav(1.0), "y", "s1", "test")])
    with pytest.raises(ev.ManifestError, match="nhiều split"):
        ev.load_manifest(same_speaker)
    samples = ev.load_manifest(voice_manifest(tmp_path / "2", [("a", wav(1.0), "x", "s1", "test")]))
    with pytest.raises(ev.ManifestError, match="locked test"):
        ev.select(samples, "test", True, False)
    with pytest.raises(ev.ManifestError, match="chưa duyệt"):
        ev.select(samples, "test", True, True)
    m = voice_manifest(tmp_path / "3", [("a", wav(1.0), "x", "s1", "dev")])
    (m.parent / "raw" / "a.wav").write_bytes(wav(2.0))
    with pytest.raises(ev.ManifestError, match="sha256"):
        ev.load_manifest(m)


# ---------- eval_image ----------

def image_manifest(tmp_path, samples):
    d = tmp_path / "image"
    (d / "raw").mkdir(parents=True)
    shutil.copy(ROOT / "benchmarks/image/manifest.schema.json", d / "manifest.schema.json")
    rows = []
    for i, (qid, task, text, judgment) in enumerate(samples):
        data = png(64 + i, 64, (40 * i, 100, 200))
        (d / "raw" / f"{qid}.png").write_bytes(data)
        h = hashlib.sha256(data).hexdigest()
        rows.append({"qid": qid, "task": task, "text_vi": text, "split": "dev", "family_id": f"fam-{qid}",
                     "capture_session_id": f"ses-{qid}", "source_asset_id": f"src-{qid}", "source_asset_sha256": h,
                     "image_path": f"raw/{qid}.png", "sha256": h, "source_url": None,
                     "usage_rights": {"status": "unknown", "evidence": None}, "independence_review": None,
                     "judgment": judgment})
    snap_sha = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    (d / "manifest.json").write_text(json.dumps({"manifest_version": "1.0.0", "catalog_sha256": snap_sha,
                                                 "include_drafts": False, "samples": rows}, ensure_ascii=False),
                                     encoding="utf-8")
    return d / "manifest.json"


def judgment(relevance, exact=None):
    return {"has_answer": any(v >= 2 for v in relevance.values()), "relevance": relevance,
            "exact_product_id": exact, "exact_variant_sku": None, "reviewed_by": "synthetic",
            "reviewed_at": "2026-10-10T16:00:00+07:00"}


def test_eval_image_end_to_end(tmp_path):
    m = image_manifest(tmp_path, [
        ("q-exact", "exact", None, judgment({"fx-gio-may-co-quai": 3}, "fx-gio-may-co-quai")),
        ("q-text", "image_text", "dưới 400k", judgment({"fx-gio-may-co-quai": 3, "fx-gio-tre-khong-quai": 2})),
        ("q-unlabeled", "similar", None, None),
    ])
    out = tmp_path / "out"
    args = ["--adapter", "tests.fakes:ByteHistogramEmbedder", "--manifest", str(m), "--catalog", str(FIXTURE),
            "--split", "dev", "--name", "fake-smoke", "--out-root", str(out), "--allow-unreviewed"]
    assert ei.main(args) == 0, "audit/eval phải chạy được trên manifest tổng hợp"
    run_dir = next(out.iterdir())
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    rows = {r["qid"]: r for r in map(json.loads, (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines())}
    assert run["audit_status"] == "pending_review" and run["evaluation_status"] == "smoke_unreviewed"
    assert run["benchmark_approved"] is False and run["skipped_unjudged_or_unreviewed"] == 1
    assert run["index"] == {"source": "built_in_memory", "entries": 24, "dim": 256}
    assert set(rows) == {"q-exact", "q-text"}
    assert rows["q-text"]["applied_filters"] == ["Giá dưới 400.000đ"]
    assert "fx-khan-lua-do" not in rows["q-text"]["predictions"]
    assert isinstance(rows["q-exact"]["recall_10"], bool) and 0 <= rows["q-exact"]["rr_10"] <= 1
    assert rows["q-text"]["ndcg_10"] is None  # còn sản phẩm chưa chấm trong top 10 → không tính
    assert run["metrics"]["exact"]["n"] == 1 and run["metrics"]["image_text"]["eligible"]["ndcg_10"] == 0


def test_eval_image_refuses_test_without_lock(tmp_path):
    m = image_manifest(tmp_path, [("q", "exact", None, judgment({"fx-gio-may-co-quai": 3}, "fx-gio-may-co-quai"))])
    base = ["--adapter", "tests.fakes:ByteHistogramEmbedder", "--manifest", str(m), "--catalog", str(FIXTURE),
            "--out-root", str(tmp_path / "out")]
    assert ei.main(base + ["--split", "test"]) == 1
    assert ei.main(base + ["--split", "test", "--confirm-locked-test", "--allow-unreviewed"]) == 1
    assert not (tmp_path / "out").exists()


# ---------- import_voice_session ----------

import import_voice_session as ivs  # noqa: E402


def session_zip(path, speaker="s01", split="dev", qids=("p01", "p02"), extra=None):
    import zipfile
    samples, files = [], {}
    for q in qids:
        qid = f"{speaker}-20261010t1700-{q}"
        data = wav(1.0)
        files[f"raw/{qid}.wav"] = data
        samples.append({"qid": qid, "audio_path": f"raw/{qid}.wav", "sha256": hashlib.sha256(data).hexdigest(),
                        "reference_text": "túi cói dưới ba trăm nghìn", "speaker_id": speaker, "region": "bac",
                        "device": "phone-a", "environment": "quiet", "split": split, "tags": ["price"],
                        "consent": {"status": "granted", "evidence": "consent-001"}, "transcript_review": None})
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.json", json.dumps({"manifest_version": "1.0.0", "samples": samples}, ensure_ascii=False))
        for name, data in {**files, **(extra or {})}.items():
            z.writestr(name, data)
    return path


def empty_target(tmp_path):
    d = tmp_path / "voice"
    d.mkdir()
    (d / "manifest.json").write_text('{"manifest_version": "1.0.0", "samples": []}', encoding="utf-8")
    return d / "manifest.json"


def test_import_voice_session_merges_and_guards(tmp_path):
    target = empty_target(tmp_path)
    z = session_zip(tmp_path / "a.zip")
    assert ivs.main([str(z), "--manifest", str(target), "--dry-run"]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["samples"] == []
    assert ivs.main([str(z), "--manifest", str(target)]) == 0
    merged = json.loads(target.read_text(encoding="utf-8"))["samples"]
    assert [s["qid"] for s in merged] == ["s01-20261010t1700-p01", "s01-20261010t1700-p02"]
    assert (target.parent / "raw" / "s01-20261010t1700-p01.wav").is_file()
    assert ivs.main([str(z), "--manifest", str(target)]) == 1  # qid trùng
    other = session_zip(tmp_path / "b.zip", split="test", qids=("p03",))
    assert ivs.main([str(other), "--manifest", str(target)]) == 1  # cùng người nói khác split
    assert len(json.loads(target.read_text(encoding="utf-8"))["samples"]) == 2  # lỗi thì không ghi


@pytest.mark.parametrize("extra", [{"../evil.wav": b"x"}, {"raw/khong-co-trong-manifest.wav": wav(1.0)}],
                         ids=["traversal", "unlisted"])
def test_import_voice_session_rejects_unexpected_files(tmp_path, extra):
    target = empty_target(tmp_path)
    assert ivs.main([str(session_zip(tmp_path / "x.zip", extra=extra)), "--manifest", str(target)]) == 1
    assert not (tmp_path / "evil.wav").exists() and not (target.parent / "raw").exists()


# ---------- import_image_session ----------

import import_image_session as iis  # noqa: E402


def image_session_zip(path, collector="c01", split="dev", n=2, family="fx-gio-may-co-quai", extra=None):
    import zipfile
    samples, files = [], {}
    for i in range(n):
        qid = f"{collector}-20261010t1700-{i:03d}"
        data = png(80 + i + (10 if split == "test" else 0), 64, (10 * i, 90, 160))
        files[f"raw/{qid}.jpg"] = data
        h = hashlib.sha256(data).hexdigest()
        samples.append({"qid": qid, "task": "exact", "text_vi": None, "split": split, "family_id": family,
                        "capture_session_id": f"{collector}-cho", "source_asset_id": f"{qid}-src",
                        "source_asset_sha256": h, "image_path": f"raw/{qid}.jpg", "sha256": h, "source_url": None,
                        "usage_rights": {"status": "owned", "evidence": "rights-001"},
                        "independence_review": None, "judgment": None})
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("samples.json", json.dumps({"samples": samples}))
        for name, data in {**files, **(extra or {})}.items():
            z.writestr(name, data)
    return path


def image_target(tmp_path):
    d = tmp_path / "image"
    d.mkdir()
    sha = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    (d / "manifest.json").write_text(json.dumps({"manifest_version": "1.0.0", "catalog_sha256": sha,
                                                 "include_drafts": False, "samples": []}), encoding="utf-8")
    return d / "manifest.json"


def test_import_image_session(tmp_path):
    target = image_target(tmp_path)
    args = ["--manifest", str(target), "--catalog", str(FIXTURE)]
    z = image_session_zip(tmp_path / "a.zip")
    assert iis.main([str(z), *args, "--dry-run"]) == 0
    assert not list((target.parent / "raw").glob("*")) and len(list(target.parent.iterdir())) == 2  # dọn sạch
    assert iis.main([str(z), *args]) == 0
    assert len(json.loads(target.read_text(encoding="utf-8"))["samples"]) == 2
    assert iis.main([str(z), *args]) == 1  # qid trùng
    # Cùng họ sản phẩm ở split khác: audit chặn rò split, không để lại file.
    leak = image_session_zip(tmp_path / "b.zip", collector="c02", split="test", n=1)
    assert iis.main([str(leak), *args]) == 1
    assert len(json.loads(target.read_text(encoding="utf-8"))["samples"]) == 2
    assert not (target.parent / "raw" / "c02-20261010t1700-000.jpg").exists()


def test_import_image_session_rejects_bad_zip(tmp_path):
    target = image_target(tmp_path)
    args = ["--manifest", str(target), "--catalog", str(FIXTURE)]
    assert iis.main([str(image_session_zip(tmp_path / "x.zip", extra={"../x.jpg": b"1"})), *args]) == 1
    assert iis.main([str(image_session_zip(tmp_path / "y.zip", extra={"raw/la.jpg": b"1"})), *args]) == 1


# ---------- compare_runs (paired cluster bootstrap) ----------

import compare_runs as cr  # noqa: E402


def voice_run(errors_by_speaker, name="a", manifest="m" * 64):
    rows = []
    for spk, errs in errors_by_speaker.items():
        for i, e in enumerate(errs):
            rows.append({"qid": f"{spk}-{i}", "speaker_id": spk, "word_normalized": [e, 0, 0, 10],
                         "char_normalized": [e, 0, 0, 40]})
    return {"name": name, "split": "dev", "manifest_sha256": manifest, "model": {"model_id": name}}, rows


def test_compare_voice_runs_bootstrap_by_speaker():
    speakers = [f"s{i}" for i in range(8)]
    left = voice_run({s: [3, 2] for s in speakers})
    right = voice_run({s: [1, 1] for s in speakers}, "b")
    rep = cr.compare(left, right, samples=500)
    m = rep["metrics"]["wer_normalized"]
    assert rep["cluster"] == "speaker_id" and m["clusters"] == 8
    assert m["left"] == 0.25 and m["right"] == 0.1 and m["delta"] == -0.15
    assert m["ci95"] == [-0.15, -0.15]  # mọi cụm cải thiện như nhau
    mixed = voice_run({s: ([0, 0] if i % 2 else [4, 4]) for i, s in enumerate(speakers)}, "c")
    mm = cr.compare(left, mixed, samples=500)["metrics"]["wer_normalized"]
    # Nửa số người nói tốt hẳn, nửa kém đi: trung bình giảm 0,05 nhưng CI chứa 0.
    assert mm["delta"] == -0.05 and mm["ci95"][0] < 0 < mm["ci95"][1]
    assert cr.compare(left, left, samples=200)["metrics"]["wer_normalized"]["ci95"] == [0.0, 0.0]


def test_compare_refuses_too_few_clusters_and_mismatches():
    few = cr.compare(voice_run({"s1": [3, 3]}), voice_run({"s1": [1, 1]}, "b"), samples=100)
    assert few["metrics"]["wer_normalized"]["ci95"] is None and "1 cụm" in few["metrics"]["wer_normalized"]["ci_note"]
    a = voice_run({f"s{i}": [1] for i in range(6)})
    with pytest.raises(cr.Incomparable, match="manifest"):
        cr.compare(a, voice_run({f"s{i}": [1] for i in range(6)}, manifest="x" * 64))
    with pytest.raises(cr.Incomparable, match="qid"):
        cr.compare(a, voice_run({f"s{i}": [1] for i in range(5)}))


def test_compare_image_runs_pairs_only_judged_queries():
    def run(vals):
        rows = [{"qid": f"q{i}", "family_id": f"f{i % 6}", "ndcg_10": v, "recall_5": v is not None and v > 0.5}
                for i, v in enumerate(vals)]
        return {"name": "x", "split": "dev", "manifest_sha256": "m" * 64, "model": None}, rows
    left = run([0.2, 0.4, None, 0.3, 0.5, 0.1, 0.2, 0.3, 0.4, 0.2, 0.1, 0.3])
    right = run([0.6, 0.8, 0.9, 0.7, 0.9, 0.5, 0.6, None, 0.8, 0.6, 0.5, 0.7])
    m = cr.compare(left, right, samples=300)["metrics"]["ndcg_10"]
    assert m["queries"] == 10 and m["clusters"] == 6  # q2, q7 thiếu ở một bên → loại cả cặp
    assert m["delta"] > 0 and m["ci95"][0] > 0
