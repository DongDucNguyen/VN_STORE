"""Duyệt họ sản phẩm: packet từ đề xuất thật, áp quyết định TỔNG HỢP (không phải quyết định của người duyệt)."""
import hashlib
import json
import sys

import pytest

from app.catalog.store import load_snapshot
from app.catalog.validation import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))
import apply_family_review as afr  # noqa: E402
import prepare_family_review as pfr  # noqa: E402

CAT = "c" * 64


def proposal():
    fam = {"p-a1": "fam-a1", "p-a2": "fam-a1", "p-a3": "fam-a1", "p-b": "fam-b", "p-c": "fam-c", "p-d": "fam-d"}
    return {"status": "proposed_unreviewed", "catalog_sha256": CAT, "product_family": fam,
            "families": [{"family_id": "fam-a1", "products": ["p-a1", "p-a2", "p-a3"], "evidence": []}],
            "visual_candidates": [{"a": "p-b", "b": "p-c", "cosine": 0.94}, {"a": "p-c", "b": "p-d", "cosine": 0.93}],
            "shared_image_clusters": [{"images": ["img-x", "img-y"], "products": ["p-b", "p-c"]}]}


def decisions(**over):
    d = {"kind": "family_review_decisions", "proposal_sha256": "p" * 64, "catalog_sha256": CAT,
         "reviewed_by": "người duyệt tổng hợp", "reviewed_at": "2026-10-11T09:00:00Z",
         "families": {"fam-a1": {"action": "split", "groups": {"p-a1": "A", "p-a2": "A", "p-a3": "B"}}},
         "candidates": {"p-b|p-c": "merge", "p-c|p-d": "separate"}, "shared": {"img-x,img-y": "exclude"}}
    d.update(over)
    return d


def test_apply_splits_merges_and_keeps_shared_decisions():
    r = afr.apply(proposal(), "p" * 64, decisions(), CAT)
    fam = r["product_family"]
    assert fam["p-a1"] == fam["p-a2"] == "fam-a1-a" and fam["p-a3"] == "fam-a1-b"
    assert fam["p-b"] == fam["p-c"] != fam["p-d"]
    assert r["stats"] == {"products": 6, "families": 4, "split": 1, "merged_pairs": 1}
    assert {tuple(f["products"]) for f in r["families"]} == {("p-a1", "p-a2"), ("p-b", "p-c")}
    assert r["shared_image_decisions"] == {"img-x,img-y": "exclude"} and r["status"] == "reviewed"


@pytest.mark.parametrize("over,msg", [
    ({"candidates": {"p-b|p-c": "merge"}}, "chưa quyết định"),
    ({"families": {"fam-a1": {"action": "split", "groups": {"p-a1": "A", "p-a2": "A", "p-a3": "A"}}}}, "ít nhất 2 nhóm"),
    ({"reviewed_by": " "}, "người duyệt"),
    ({"proposal_sha256": "x" * 64}, "đề xuất khác"),
    ({"candidates": {"p-b|p-c": "merge", "p-c|p-d": "maybe"}}, "merge hoặc separate"),
])
def test_apply_rejects_incomplete_or_invalid(over, msg):
    with pytest.raises(afr.ReviewError, match=msg):
        afr.apply(proposal(), "p" * 64, decisions(**over), CAT)


def test_apply_rejects_changed_catalog():
    with pytest.raises(afr.ReviewError, match="đã đổi"):
        afr.apply(proposal(), "p" * 64, decisions(), "d" * 64)


@pytest.mark.parametrize("over,msg", [
    ({"catalog_sha256": "d" * 64}, "catalog khác"),
    ({"reviewed_by": ["name"]}, "người duyệt"),
    ({"reviewed_at": "yesterday"}, "múi giờ"),
    ({"reviewed_at": "2026-10-11T09:00:00"}, "múi giờ"),
    ({"reviewed_at": True}, "múi giờ"),
    ({"families": []}, "JSON object"),
    ({"families": {"fam-a1": None}}, "JSON object"),
    ({"candidates": []}, "JSON object"),
    ({"shared": {"unknown": "exclude"}}, "ảnh dùng chung"),
    ({"shared": {"img-x,img-y": "maybe"}}, "ảnh dùng chung"),
    ({"families": {"fam-a1": {"action": "split", "groups": {"p-a1": "A", "p-a2": "a", "p-a3": " A "}}}}, "sau chuẩn hóa"),
    ({"families": {"fam-a1": {"action": "split", "groups": {"p-a1": [], "p-a2": "A", "p-a3": "B"}}}}, "ít nhất 2 nhóm"),
])
def test_apply_validates_review_metadata_and_shapes(over, msg):
    with pytest.raises(afr.ReviewError, match=msg):
        afr.apply(proposal(), "p" * 64, decisions(**over), CAT)


def test_separate_must_hold_after_transitive_merges():
    p = proposal()
    p["visual_candidates"].append({"a": "p-b", "b": "p-d"})
    d = decisions(candidates={"p-b|p-c": "merge", "p-c|p-d": "merge", "p-b|p-d": "separate"})
    for order in (d["candidates"], dict(reversed(list(d["candidates"].items())))):
        with pytest.raises(afr.ReviewError, match="Mâu thuẫn.*p-b\\|p-d"):
            afr.apply(p, "p" * 64, {**d, "candidates": order}, CAT)


def test_merge_cannot_undo_split_through_another_family():
    p = proposal()
    p["visual_candidates"] += [{"a": "p-a1", "b": "p-b"}, {"a": "p-a3", "b": "p-c"}]
    d = decisions()
    d["candidates"].update({"p-a1|p-b": "merge", "p-a3|p-c": "merge"})
    with pytest.raises(afr.ReviewError, match="đã tách nhưng bị gộp lại"):
        afr.apply(p, "p" * 64, d, CAT)


def test_separate_cannot_disagree_with_confirmed_family():
    p = proposal()
    p["visual_candidates"].append({"a": "p-a1", "b": "p-a2"})
    d = decisions(families={"fam-a1": {"action": "confirm"}})
    d["candidates"]["p-a1|p-a2"] = "separate"
    with pytest.raises(afr.ReviewError, match="chọn khác họ"):
        afr.apply(p, "p" * 64, d, CAT)


def test_split_ids_cannot_collide_with_existing_family():
    p = proposal()
    p["product_family"]["p-b"] = "fam-a1-a"
    with pytest.raises(afr.ReviewError, match="trùng mã họ"):
        afr.apply(p, "p" * 64, decisions(), CAT)


def test_catalog_coverage_and_proposal_members_are_checked():
    p = proposal()
    with pytest.raises(afr.ReviewError, match="bao phủ"):
        afr.apply(p, "p" * 64, decisions(), CAT, set(p["product_family"]) | {"missing"})
    p["families"][0]["products"].remove("p-a3")
    with pytest.raises(afr.ReviewError, match="không khớp product_family"):
        afr.apply(p, "p" * 64, decisions(), CAT)


def test_shared_review_is_optional_and_apply_does_not_mutate_inputs():
    p, d = proposal(), decisions(shared={})
    before = json.dumps([p, d], sort_keys=True)
    assert afr.apply(p, "p" * 64, d, CAT)["shared_image_decisions"] == {}
    assert json.dumps([p, d], sort_keys=True) == before


def test_cli_rejects_conflict_without_overwriting_output(tmp_path):
    p = proposal()
    p["visual_candidates"].append({"a": "p-a1", "b": "p-a2"})
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"products": [{"id": pid} for pid in p["product_family"]]}), encoding="utf-8")
    p["catalog_sha256"] = hashlib.sha256(catalog.read_bytes()).hexdigest()
    source = tmp_path / "proposal.json"
    source.write_text(json.dumps(p), encoding="utf-8")
    d = decisions(catalog_sha256=p["catalog_sha256"], proposal_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    d["candidates"]["p-a1|p-a2"] = "separate"
    review = tmp_path / "decisions.json"
    review.write_text(json.dumps(d), encoding="utf-8")
    out = tmp_path / "families.json"
    out.write_bytes(b"existing review")
    assert afr.main([str(review), "--proposal", str(source), "--catalog", str(catalog), "--out", str(out)]) == 1
    assert out.read_bytes() == b"existing review"


def test_packet_from_current_proposal(tmp_path):
    """Đề xuất trong repo phải khớp catalog hiện tại (đổi DB thì chạy lại propose_families.py)."""
    raw = (REPO_ROOT / "benchmarks/families/proposal.json").read_bytes()
    snap = load_snapshot(REPO_ROOT / "database.json", include_drafts=True)
    out = tmp_path / "packet"
    packet = pfr.make_packet(json.loads(raw), hashlib.sha256(raw).hexdigest(), snap, out)
    assert packet["families"] and packet["candidates"] and packet["shared"]
    for pid, p in packet["products"].items():
        assert p["images"] and all((out / i).resolve().is_file() for i in p["images"]), pid
    assert all((out / i).resolve().is_file() for s in packet["shared"] for i in s["images"])
    stale = {**json.loads(raw), "catalog_sha256": "0" * 64}
    with pytest.raises(ValueError, match="catalog khác"):
        pfr.make_packet(stale, "x", snap, out)
