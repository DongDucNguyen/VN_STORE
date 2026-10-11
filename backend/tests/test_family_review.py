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


def test_carry_drafts_only_from_identical_proposal_content(tmp_path):
    """Catalog đổi nhưng đề xuất giữ nguyên: trang mới nhận bản nháp cũ; nội dung khác thì từ chối."""
    raw = (REPO_ROOT / "benchmarks/families/proposal.json").read_bytes()
    snap = load_snapshot(REPO_ROOT / "database.json", include_drafts=True)
    new = pfr.make_packet(json.loads(raw), "n" * 64, snap, tmp_path / "new")
    old = {**json.loads(json.dumps(new)), "proposal_sha256": "o" * 64, "catalog_sha256": "0" * 64,
           "catalog_version": "cu", "compatible_proposal_sha256": ["q" * 64, "n" * 64]}
    old["products"] = {pid: {**p, "images": ["../khac/" + i for i in p["images"]]} for pid, p in old["products"].items()}
    old_path = tmp_path / "old.json"
    old_path.write_text(json.dumps(old), encoding="utf-8")
    pfr.carry_drafts(new, [old_path, old_path])
    assert new["compatible_proposal_sha256"] == ["o" * 64, "q" * 64]

    changed = json.loads(json.dumps(old))
    pid = next(iter(changed["products"]))
    changed["products"][pid]["family"] = "fam-khac"
    changed_path = tmp_path / "changed.json"
    changed_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="nội dung đề xuất khác"):
        pfr.carry_drafts(new, [changed_path])
    changed_path.write_text(json.dumps({**old, "kind": "keyword_review"}), encoding="utf-8")
    with pytest.raises(ValueError, match="không phải packet duyệt họ"):
        pfr.carry_drafts(new, [changed_path])


# ---------- gợi ý máy (build_family_suggestions.py) ----------
import build_family_suggestions as bfs  # noqa: E402
from types import SimpleNamespace  # noqa: E402


def fam_packet():
    p = proposal()
    return {"kind": "family_review", "proposal_sha256": "p" * 64, "catalog_sha256": CAT, "families": p["families"],
            "candidates": [{**c, "key": f"{c['a']}|{c['b']}"} for c in p["visual_candidates"]],
            "shared": [{"key": "img-x,img-y", "products": ["p-b", "p-c"]}], "compatible_proposal_sha256": []}


def suggestion(F=None, C=None, S=None):
    return SimpleNamespace(F=F or {0: ("split", ["A", "A", "B"], "lý do")},
                           C=C or {0: ("merge", "lý do"), 1: ("separate", "lý do")}, S=S or {0: ("keep", "lý do")})


def test_family_suggestions_are_checked_with_apply_rules():
    out = bfs.build(suggestion(), fam_packet(), proposal(), "p" * 64)
    assert out["families"]["fam-a1"]["groups"] == {"p-a1": "A", "p-a2": "A", "p-a3": "B"}
    assert out["if_all_accepted"]["merge"] == 1 and "không phải quyết định" in out["author"]
    with pytest.raises(afr.ReviewError, match="Mâu thuẫn"):
        _contradiction()
    with pytest.raises(ValueError, match="cover"):
        bfs.build(suggestion(C={0: ("merge", "x")}), fam_packet(), proposal(), "p" * 64)
    with pytest.raises(ValueError, match="reason"):
        bfs.build(suggestion(S={0: ("keep", " ")}), fam_packet(), proposal(), "p" * 64)


def _contradiction():
    # Splitting a1|a3 while a merge candidate joins them again must be rejected like a human export.
    p, pk = proposal(), fam_packet()
    p["visual_candidates"].append({"a": "p-a1", "b": "p-a3", "cosine": 0.95})
    pk["candidates"].append({"a": "p-a1", "b": "p-a3", "key": "p-a1|p-a3"})
    bfs.build(suggestion(C={0: ("merge", "x"), 1: ("separate", "x"), 2: ("merge", "x")}), pk, p, "p" * 64)


def test_family_suggestions_attach_only_to_matching_page():
    raw = json.dumps(bfs.build(suggestion(), fam_packet(), proposal(), "p" * 64)).encode()
    page = fam_packet()
    pfr.attach_suggestions(page, raw)
    assert page["suggestions_sha256"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):
        pfr.attach_suggestions({**fam_packet(), "proposal_sha256": "q" * 64}, raw)


def test_apply_keeps_valid_assist_and_rejects_malformed():
    p, sha = proposal(), "p" * 64
    assist = {"version": "v1", "suggestions_sha256": "s", "applied": 3, "kept_unchanged": 2, "changed": 1}
    assert afr.apply(p, sha, decisions(assist=assist), CAT)["assist"] == assist
    with pytest.raises(afr.ReviewError, match="assist"):
        afr.apply(p, sha, decisions(assist={"applied": -1}), CAT)


def test_project_family_suggestions_are_consistent():
    path = REPO_ROOT / "benchmarks/families/suggestions/claude_assist_v1.json"
    packet = REPO_ROOT / "artifacts/family_review/2026-10-11_seed-006/packet.json"
    if not packet.exists():
        pytest.skip("review packet not present")
    raw = (REPO_ROOT / "benchmarks/families/proposal.json").read_bytes()
    module = bfs.load(REPO_ROOT / "benchmarks/families/suggestions/claude_assist_v1_decisions.py")
    rebuilt = bfs.build(module, json.loads(packet.read_text(encoding="utf-8")), json.loads(raw),
                        hashlib.sha256(raw).hexdigest())
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert {k: saved[k] for k in ("families", "candidates", "shared")} == \
        {k: rebuilt[k] for k in ("families", "candidates", "shared")}
