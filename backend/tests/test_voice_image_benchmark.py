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


def session_zip(path, speaker="s01", split="dev", qids=("p01", "p02"), extra=None,
                text="túi cói dưới ba trăm nghìn"):
    import zipfile
    samples, files = [], {}
    for q in qids:
        qid = f"{speaker}-20261010t1700-{q}"
        data = wav(1.0)
        files[f"raw/{qid}.wav"] = data
        samples.append({"qid": qid, "audio_path": f"raw/{qid}.wav", "sha256": hashlib.sha256(data).hexdigest(),
                        "reference_text": text, "speaker_id": speaker, "region": "bac",
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


def test_same_sentence_cannot_span_splits(tmp_path):
    """Bộ câu mỗi split tách riêng: câu dev xuất hiện lại ở test bị chặn khi nhập, khi áp duyệt và khi nạp."""
    target = empty_target(tmp_path)
    shutil.copy(ROOT / "benchmarks/voice/manifest.schema.json", target.parent / "manifest.schema.json")
    assert ivs.main([str(session_zip(tmp_path / "a.zip")), "--manifest", str(target)]) == 0
    same = session_zip(tmp_path / "b.zip", speaker="s02", split="test", qids=("te01",),
                       text="Túi cói, dưới ba trăm nghìn!")  # khác hoa/dấu câu vẫn là cùng câu
    before = target.read_bytes()
    assert ivs.main([str(same), "--manifest", str(target)]) == 1
    assert target.read_bytes() == before
    other = session_zip(tmp_path / "c.zip", speaker="s02", split="test", qids=("te01",), text="khăn lụa thêu hoa sen")
    assert ivs.main([str(other), "--manifest", str(target)]) == 0
    assert len(ev.load_manifest(target)) == 3
    # Người duyệt sửa câu dev thành đúng câu của test → từ chối, manifest giữ nguyên.
    z = reviewed_zip(tmp_path / "a.zip", tmp_path / "r.zip", {"s01-20261010t1700-p01": {
        "reference_text": "khăn lụa thêu hoa sen", "transcript_review": REVIEW}})
    before = target.read_bytes()
    assert avr.main([str(z), "--manifest", str(target)]) == 1
    assert target.read_bytes() == before
    with pytest.raises(ev.ManifestError, match="đã có ở split dev"):
        ev.check_text_splits([{"qid": "a", "split": "dev", "reference_text": "Ly sứ"},
                              {"qid": "s", "split": "dev", "reference_text": None},
                              {"qid": "b", "split": "test", "reference_text": "ly  sứ."}])


# ---------- apply_voice_review ----------

import apply_voice_review as avr  # noqa: E402


def reviewed_zip(src, dest, edits):
    """Giả lập zip do người duyệt xuất từ #/review/voice: sửa reference_text/transcript_review theo qid."""
    import zipfile
    with zipfile.ZipFile(src) as z:
        files = {i.filename: z.read(i) for i in z.infolist()}
    manifest = json.loads(files["manifest.json"])
    for s in manifest["samples"]:
        s.update(edits.get(s["qid"], {}))
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False).encode()
    with zipfile.ZipFile(dest, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return dest


def imported_target(tmp_path):
    target = empty_target(tmp_path)
    shutil.copy(ROOT / "benchmarks/voice/manifest.schema.json", target.parent / "manifest.schema.json")
    src = session_zip(tmp_path / "s.zip")
    assert ivs.main([str(src), "--manifest", str(target)]) == 0
    return target, src


REVIEW = {"reviewed_by": "người duyệt A", "reviewed_at": "2026-10-11T09:00:00Z"}


def test_apply_voice_review_updates_only_review_fields(tmp_path):
    target, src = imported_target(tmp_path)
    q1, q2 = "s01-20261010t1700-p01", "s01-20261010t1700-p02"
    z = reviewed_zip(src, tmp_path / "r.zip", {q1: {"reference_text": "tìm túi cói dưới ba trăm",
                                                    "transcript_review": REVIEW}})
    before = target.read_bytes()
    assert avr.main([str(z), "--manifest", str(target), "--dry-run"]) == 0
    assert target.read_bytes() == before
    assert avr.main([str(z), "--manifest", str(target)]) == 0
    rows = {s["qid"]: s for s in json.loads(target.read_text(encoding="utf-8"))["samples"]}
    assert rows[q1]["reference_text"] == "tìm túi cói dưới ba trăm" and rows[q1]["transcript_review"] == REVIEW
    assert rows[q2]["transcript_review"] is None  # clip chưa xác nhận giữ nguyên
    assert rows[q2]["reference_text"] == "túi cói dưới ba trăm nghìn"
    assert ev.load_manifest(target)  # vẫn đúng schema, file, hash

    # Đã duyệt: lượt duyệt khác chỉ được ghi đè khi yêu cầu rõ.
    again = reviewed_zip(src, tmp_path / "r2.zip", {q1: {"reference_text": None, "transcript_review": {
        "reviewed_by": "người duyệt B", "reviewed_at": "2026-10-12T09:00:00Z"}}})
    assert avr.main([str(again), "--manifest", str(target)]) == 1
    assert avr.main([str(again), "--manifest", str(target), "--replace-reviewed"]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["samples"][0]["reference_text"] is None


@pytest.mark.parametrize("edit", [{"split": "test"}, {"consent": {"status": "unknown", "evidence": None}}],
                         ids=["split", "consent"])
def test_apply_voice_review_rejects_changed_metadata(tmp_path, edit):
    target, src = imported_target(tmp_path)
    before = target.read_bytes()
    z = reviewed_zip(src, tmp_path / "r.zip", {"s01-20261010t1700-p01": {**edit, "transcript_review": REVIEW}})
    assert avr.main([str(z), "--manifest", str(target)]) == 1
    assert target.read_bytes() == before


def test_apply_voice_review_requires_imported_session(tmp_path):
    target, _ = imported_target(tmp_path)
    other = session_zip(tmp_path / "o.zip", speaker="s02")
    z = reviewed_zip(other, tmp_path / "r.zip", {"s02-20261010t1700-p01": {"transcript_review": REVIEW}})
    assert avr.main([str(z), "--manifest", str(target)]) == 1


def test_reviewed_zip_imports_directly(tmp_path):
    target = empty_target(tmp_path)
    z = reviewed_zip(session_zip(tmp_path / "s.zip"), tmp_path / "r.zip",
                     {"s01-20261010t1700-p01": {"transcript_review": REVIEW}})
    assert ivs.main([str(z), "--manifest", str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["samples"][0]["transcript_review"] == REVIEW


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


# ---------- latency_protocol ----------

import latency_protocol as lp  # noqa: E402


def test_rounds_summary_reports_spread():
    s = lp.rounds_summary([[10, 20, 30, 40], [12, 22, 32, 44]])
    assert s["n_rounds"] == 2 and [r["p95"] for r in s["rounds"]] == [40, 44]
    assert s["p95_spread_pct"] == pytest.approx(10.0) and s["p95"] == 44 and s["p50"] == 22
    assert lp.rounds_summary([[5]])["p95_spread_pct"] is None


def test_idle_check_warns_when_gpu_busy(monkeypatch):
    busy = [{"name": "g", "driver_version": "1", "memory_total_mb": 16000, "memory_used_mb": 9000,
             "utilization_pct": 80}]
    monkeypatch.setattr(lp, "gpu_status", lambda: busy)
    report = lp.idle_check(samples=2, interval_s=0)
    assert report["checked"] and len(report["warnings"]) == 2
    monkeypatch.setattr(lp, "gpu_status", lambda: None)
    assert lp.idle_check(samples=2, interval_s=0) == {"checked": False, "warnings": []}


def test_vram_peak_without_nvidia_smi(monkeypatch):
    monkeypatch.setattr(lp, "_nvidia_smi", lambda: None)
    with lp.VramPeak() as v:
        pass
    assert v.peak is None


def test_eval_voice_records_latency_protocol(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, "gpu_status", lambda: None)
    monkeypatch.setattr(lp, "_nvidia_smi", lambda: None)
    m = voice_manifest(tmp_path, [("v1", wav(1.0), "giỏ mây", "s1", "dev"), ("v2", wav(1.0), "túi cói", "s2", "dev")])
    out = tmp_path / "out"
    assert ev.main(["--adapter", "tests.fakes:FakeASR", "--manifest", str(m), "--catalog", str(FIXTURE), "--split",
                    "dev", "--out-root", str(out), "--allow-unreviewed", "--latency-rounds", "3"]) == 0
    run = json.loads((next(out.iterdir()) / "run.json").read_text(encoding="utf-8"))
    lat = run["metrics"]["latency"]
    assert lat["asr_ms"]["n_rounds"] == 3 and lat["cold_first_call_ms"] >= 0 and lat["adapter_load_ms"] >= 0
    assert lat["peak_vram_mb"] is None and lat["machine_busy_warnings"] == []
    assert run["latency_protocol"]["rounds"] == 3 and "gpus" in run["environment"]
    with pytest.raises(SystemExit):
        ev.main(["--adapter", "tests.fakes:FakeASR", "--manifest", str(m), "--split", "dev", "--latency-rounds", "0"])


# ---------- compare_reviews (hai người duyệt độc lập) ----------

import compare_reviews as crv  # noqa: E402


def test_compare_voice_reviews(tmp_path):
    src = session_zip(tmp_path / "s.zip")
    q1, q2 = "s01-20261010t1700-p01", "s01-20261010t1700-p02"
    a = reviewed_zip(src, tmp_path / "a.zip", {q1: {"transcript_review": REVIEW},
                                               q2: {"reference_text": "túi cói dưới ba trăm", "transcript_review": REVIEW}})
    rb = {**REVIEW, "reviewed_by": "người duyệt B"}
    b = reviewed_zip(src, tmp_path / "b.zip", {q1: {"transcript_review": rb},
                                               q2: {"reference_text": "túi cói dưới  ba trăm nghìn", "transcript_review": rb}})
    out = tmp_path / "rep"
    assert crv.main(["voice", str(a), str(b), "--report-dir", str(out)]) == 2
    r = json.loads(next(out.glob("*.json")).read_text(encoding="utf-8"))
    assert r["compared"] == 2 and r["agreement"] == 0.5 and [d["qid"] for d in r["disagreements"]] == [q2]
    assert r["disagreements"][0]["cer_between"] > 0
    assert crv.main(["voice", str(a), str(a), "--report-dir", str(out)]) == 1  # cùng người duyệt
    other = reviewed_zip(session_zip(tmp_path / "o.zip", speaker="s02"), tmp_path / "o2.zip", {})
    assert crv.main(["voice", str(a), str(other), "--report-dir", str(out)]) == 1  # khác phiên


def image_export(who, items, packet_id="p" * 64):
    def j(rel, exact=None):
        return {"has_answer": any(v >= 2 for v in rel.values()), "relevance": rel, "exact_product_id": exact,
                "exact_variant_sku": None, "reviewed_by": who, "reviewed_at": "2026-10-11T09:00:00+07:00"}
    return {"kind": "image_judgment_export", "packet_id": packet_id, "catalog_sha256": "c" * 64,
            "items": [{"qid": q, "sha256": "s" * 64, "judgment": j(rel, ex)} for q, rel, ex in items]}


def test_compare_image_judgments(tmp_path):
    a = image_export("A", [("q1", {"x": 3, "y": 0}, "x"), ("q2", {"x": 0, "y": 1}, None)])
    b = image_export("B", [("q1", {"x": 3, "y": 2, "z": 0}, "y"), ("q2", {"x": 0, "y": 1}, None)])
    r = crv.compare_image(a, b)
    assert r["pairs_compared"] == 4 and r["exact_grade_agreement"] == 0.75
    assert r["grades_disagreements"][0]["crosses_relevant_threshold"] is True
    assert r["exact_disagreements"] == [{"qid": "q1", "left": ["x", None], "right": ["y", None]}]
    assert r["coverage_differences"] == [{"qid": "q1", "labeled_by_one_reviewer": ["z"]}]
    assert r["requires_adjudication"] is True
    assert crv.compare_image(a, image_export("B", [("q1", {"x": 3, "y": 0}, "x"), ("q2", {"x": 0, "y": 1}, None)])
                             )["requires_adjudication"] is False
    with pytest.raises(crv.CompareError, match="packet"):
        crv.compare_image(a, image_export("B", [], packet_id="q" * 64))
    with pytest.raises(crv.CompareError, match="cùng người"):
        crv.compare_image(a, image_export("a", [("q1", {"x": 3}, "x")]))


def test_prompt_sets_are_disjoint_between_splits():
    """frontend/src/collect/prompts.ts: mỗi split một bộ câu, không câu nào (sau chuẩn hóa) lặp lại ở bộ khác."""
    import re
    src = (ROOT / "frontend/src/collect/prompts.ts").read_text(encoding="utf-8")
    body = src[src.index("PROMPT_SETS"):]
    starts = {m.group(1): m.end() for m in re.finditer(r"^  (train|dev|test): \[", body, re.M)}
    assert sorted(starts) == ["dev", "test", "train"]
    ids, texts = set(), {}
    for split, pos in starts.items():
        rows = re.findall(r'\{ id: "([^"]+)", text: "([^"]+)"', body[pos:body.index("\n  ],", pos)])
        assert len(rows) >= 15, split  # ≥15 clip/người (600 clip / 40 người)
        for pid, text in rows:
            assert re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,19}", pid) and pid not in ids, pid
            ids.add(pid)
            key = am.normalize(text)
            assert key and key not in texts, f"{text!r} lặp lại (đã có ở {texts.get(key)})"
            texts[key] = split
    ev.check_text_splits([{"qid": t, "split": s, "reference_text": t} for t, s in texts.items()])
