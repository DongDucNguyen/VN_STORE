"""P1.15: truy vấn nháp từ bản chép lời đã duyệt và gắn keyword_qid. Nhãn trong test là TỔNG HỢP."""
import json
import sys
from pathlib import Path

import pytest

from app.catalog.store import load_snapshot
from tests.media_samples import wav
from tests.test_voice_image_benchmark import FIXTURE, voice_manifest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/benchmark"))
import eval_voice as ev  # noqa: E402
import prepare_voice_queries as pvq  # noqa: E402
import voice_retrieval as vr  # noqa: E402

REVIEW = {"reviewed_by": "người duyệt tổng hợp", "reviewed_at": "2026-10-11T10:00:00+07:00"}
CONSENT = {"status": "granted", "evidence": "consent-synthetic"}


def manifest(tmp_path):
    clips = [("s01-20261011t0900-p01", "túi cói dưới ba trăm nghìn", "s01"),
             ("s02-20261011t0910-p01", "Túi cói, dưới ba trăm nghìn.", "s02"),  # cùng câu sau chuẩn hóa
             ("s03-20261011t0920-p01", "túi cói dưới ba trăm", "s03"),  # đọc khác câu mẫu → cùng nhóm
             ("s01-20261011t0900-p24", "nồi cơm điện giá rẻ", "s01"),
             ("s01-20261011t0900-p02", "bình gốm bát tràng", "s01"),  # chưa duyệt
             ("s01-20261011t0900-im-lang", None, "s01")]
    path = voice_manifest(tmp_path, [(q, wav(1), text, spk, "dev") for q, text, spk in clips])
    data = json.loads(path.read_text(encoding="utf-8"))
    for s in data["samples"]:
        s["consent"] = CONSENT
        if not s["qid"].endswith("-p02"):
            s["transcript_review"] = REVIEW
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def run_draft(tmp_path, path, *extra):
    out = tmp_path / "draft"
    code = pvq.main(["--manifest", str(path), "--catalog", str(FIXTURE), "draft", "--split", "dev",
                     "--out", str(out), *extra])
    return code, out


def labels(out, snap, verified=True):
    """Giả lập file nhãn sau chấm và phân xử: truy vấn túi cói có đáp án, nồi cơm điện là no-match đủ catalog."""
    rows = []
    for q in map(json.loads, (out / "queries.jsonl").read_text(encoding="utf-8").splitlines()):
        coi = "túi cói" in q["query"].casefold()
        rel = {p: (3 if coi and p == "fx-tui-coi-tron" else 0) for p in snap.products}
        rows.append({**q, "relevance": rel, "has_answer": coi, "verified": verified,
                     "labeled_by": "người chấm tổng hợp", "reviewed_at": "2026-10-11T11:00:00+07:00",
                     "catalog_sha256": snap.sha256})
    path = out / "labels.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path, rows


def apply(path, out, label_path, *extra):
    return pvq.main(["--manifest", str(path), "--catalog", str(FIXTURE), "apply", str(out / "links.json"),
                     str(label_path), *extra])


def test_draft_groups_by_prompt_and_skips_unready(tmp_path):
    path = manifest(tmp_path)
    before = path.read_bytes()
    code, out = run_draft(tmp_path, path)
    assert code == 0 and path.read_bytes() == before
    rows = [json.loads(line) for line in (out / "queries.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 3  # hai clip cùng câu chung một truy vấn
    by_text = {r["query"]: r for r in rows}
    assert by_text["túi cói dưới ba trăm nghìn"]["voice_clips"] == ["s01-20261011t0900-p01", "s02-20261011t0910-p01"]
    assert by_text["túi cói dưới ba trăm"]["group_id"] == by_text["túi cói dưới ba trăm nghìn"]["group_id"] == "vg-p01"
    assert by_text["nồi cơm điện giá rẻ"]["group_id"] == "vg-p24"
    assert all(r["relevance"] == {} and r["verified"] is False and r["has_answer"] is False for r in rows)
    links = json.loads((out / "links.json").read_text(encoding="utf-8"))
    assert links["summary"]["skipped"] == {"unreviewed": 1, "silence": 1, "no_consent": 0, "already_linked": 0}
    assert links["catalog_sha256"] == load_snapshot(FIXTURE, include_drafts=True).sha256
    assert set(links["links"]) == {r for q in rows for r in q["voice_clips"]}
    with pytest.raises(SystemExit):  # thư mục đầu ra đã tồn tại
        run_draft(tmp_path, path)


def test_apply_links_verified_labels_then_eval_accepts(tmp_path):
    path = manifest(tmp_path)
    _, out = run_draft(tmp_path, path)
    snap = load_snapshot(FIXTURE, include_drafts=True)
    label_path, _ = labels(out, snap)
    before = path.read_bytes()
    assert apply(path, out, label_path, "--dry-run") == 0 and path.read_bytes() == before
    assert apply(path, out, label_path) == 0
    samples = ev.load_manifest(path)
    linked = {s["qid"]: s.get("keyword_qid") for s in samples}
    assert linked["s01-20261011t0900-p01"] == linked["s02-20261011t0910-p01"]
    assert linked["s01-20261011t0900-p02"] is None and linked["s01-20261011t0900-im-lang"] is None
    assert apply(path, out, label_path) == 0  # chạy lại: không đổi gì
    # evaluator voice nhận liên kết vừa gắn (clip đã duyệt; clip chưa duyệt bị loại khỏi lượt chọn)
    chosen = [s for s in samples if s["transcript_review"] is not None]
    got, meta = vr.load_links(label_path, samples, chosen, snap, allow_unreviewed=False)
    assert meta["linked_speech"] == 4 and meta["unreviewed_queries"] == 0


@pytest.mark.parametrize("case", ["unverified", "transcript_changed", "other_link", "catalog_changed",
                                  "query_text", "partial_no_match", "missing_label"])
def test_apply_guards_write_nothing(tmp_path, case):
    path = manifest(tmp_path)
    _, out = run_draft(tmp_path, path)
    snap = load_snapshot(FIXTURE, include_drafts=True)
    label_path, rows = labels(out, snap, verified=case != "unverified")
    if case in ("transcript_changed", "other_link"):
        data = json.loads(path.read_text(encoding="utf-8"))
        s = data["samples"][0]
        if case == "transcript_changed":
            s["reference_text"] = "túi cói dưới hai trăm nghìn"
        else:
            s["keyword_qid"] = "kw-khac"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if case == "catalog_changed":
        links = json.loads((out / "links.json").read_text(encoding="utf-8"))
        (out / "links.json").write_text(json.dumps({**links, "catalog_sha256": "0" * 64}), encoding="utf-8")
    if case in ("query_text", "partial_no_match", "missing_label"):
        nm = next(r for r in rows if not r["has_answer"])
        if case == "query_text":
            nm["query"] = "nồi cơm điện"
        elif case == "partial_no_match":
            nm["relevance"] = {"fx-tui-coi-tron": 0}
        else:
            rows.remove(nm)
        label_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    before = path.read_bytes()
    assert apply(path, out, label_path) == 1
    assert path.read_bytes() == before


def test_draft_refuses_text_in_other_keyword_split(tmp_path):
    path = manifest(tmp_path)
    kw = tmp_path / "kw.jsonl"
    kw.write_text(json.dumps({"qid": "kw-test-1", "query": "Nồi cơm điện giá rẻ", "split": "test"},
                             ensure_ascii=False) + "\n", encoding="utf-8")
    assert run_draft(tmp_path, path, "--keyword-file", str(kw))[0] == 1
    kw.write_text(json.dumps({"qid": "kw-dev-9", "query": "nồi cơm điện giá rẻ", "split": "dev"},
                             ensure_ascii=False) + "\n", encoding="utf-8")
    code, out = run_draft(tmp_path, path, "--keyword-file", str(kw))
    assert code == 0
    overlap = json.loads((out / "links.json").read_text(encoding="utf-8"))["summary"]["keyword_overlap_same_split"]
    assert overlap == [{"clip": "s01-20261011t0900-p24", "keyword_qid": "kw-dev-9", "file": kw.as_posix()}]
