"""Draft transfer must never turn old judgments into new confirmations."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
import migrate_keyword_draft as migration
import prepare_review


def packet():
    return {"catalog_sha256": "old-catalog", "queries_sha256": "old-queries", "queries": [
        {"qid": "q1", "query": "giỏ tre", "split": "dev", "group_id": "basket", "relevance": {},
         "has_answer": False, "verified": False, "labeled_by": "draft"}],
        "products": [{"id": pid, "name": pid, "description": "tre", "variants": [{"price_vnd": 100}],
                      "image": "../images/" + pid + ".png", "image_sha256": "a" * 64} for pid in ("a", "b")],
        "candidate_order": {"q1": ["a", "b"]}, "pool": {"q1": ["a"]}}


def draft(p):
    return {"key": migration.packet_key(p), "state": {"reviewer": "synthetic-reviewer",
            "labels": {"q1": {"a": 3, "b": 0}}, "groups": {"q1": "basket"}, "confirmed": {"q1": True}}}


def test_keeps_unchanged_pairs_across_catalog_and_path_changes_but_requires_confirmation():
    old = packet()
    new = copy.deepcopy(old)
    new.update(catalog_sha256="new-catalog", queries_sha256="new-queries")
    for p in new["products"]:
        p["image"] = "../../images/" + p["id"] + ".png"
    new["pool"]["q1"] = ["a", "b"]
    source = draft(old)
    before = copy.deepcopy(source)
    result = migration.migrate(old, new, source)
    assert result["key"] == migration.packet_key(new)
    assert result["state"]["labels"] == source["state"]["labels"]
    assert result["state"]["confirmed"] == {"q1": False}
    assert result["state"]["migration"]["copied_pairs"] == 2
    assert source == before


@pytest.mark.parametrize("field,value", [("name", "Khác"), ("description", "nhựa"),
    ("variants", [{"price_vnd": 200}]), ("image_sha256", "b" * 64), ("image", None),
    ("claims", [{"value": True}]), ("sources", [{"url": "https://example.com/new"}])])
def test_changed_product_requires_regrading(field, value):
    old = packet()
    new = copy.deepcopy(old)
    new["products"][0][field] = value
    result = migration.migrate(old, new, draft(old))["state"]
    assert result["labels"] == {"q1": {"b": 0}}
    assert result["migration"]["skipped_pairs"][0]["reason"] == "product_content_changed"


@pytest.mark.parametrize("field,value", [("query", "giỏ nhựa"), ("split", "train"),
                                        ("group_id", "new-group"), ("intent", "new intent")])
def test_changed_query_split_or_intent_never_carries_labels(field, value):
    old = packet()
    new = copy.deepcopy(old)
    new["queries"][0][field] = value
    result = migration.migrate(old, new, draft(old))["state"]
    assert result["labels"] == result["groups"] == {}
    assert result["confirmed"] == {"q1": False}


def test_added_products_are_ungraded_even_if_old_query_was_no_match():
    old = packet()
    source = draft(old)
    source["state"]["labels"]["q1"]["a"] = 0
    new = copy.deepcopy(old)
    new["products"].append({**new["products"][0], "id": "c"})
    new["candidate_order"]["q1"].append("c")
    new["pool"]["q1"].append("c")
    result = migration.migrate(old, new, source)["state"]
    assert result["labels"] == {"q1": {"a": 0, "b": 0}}
    assert result["confirmed"]["q1"] is False


def test_legacy_image_without_historical_checksum_is_not_trusted():
    old = packet()
    new = copy.deepcopy(old)
    del old["products"][0]["image_sha256"]
    result = migration.migrate(old, new, draft(old))["state"]
    assert result["labels"] == {"q1": {"b": 0}}
    assert result["migration"]["skipped_pairs"][0]["reason"] == "image_history_unavailable"


def test_removed_products_and_queries_are_counted():
    old = packet()
    new = copy.deepcopy(old)
    new["products"] = new["products"][:1]
    new["candidate_order"]["q1"] = ["a"]
    result = migration.migrate(old, new, draft(old))["state"]
    assert result["labels"] == {"q1": {"a": 3}}
    assert result["migration"]["skipped_pairs"][0]["reason"] == "product_removed"
    new["queries"][0]["qid"] = "q2"
    new["candidate_order"] = {"q2": ["a"]}
    assert migration.migrate(old, new, draft(old))["state"]["labels"] == {}


@pytest.mark.parametrize("score", [True, -1, 4, "3", 2.5])
def test_invalid_scores_rejected(score):
    p = packet()
    source = draft(p)
    source["state"]["labels"]["q1"]["a"] = score
    with pytest.raises(ValueError, match="0..3"):
        migration.migrate(p, p, source)


def test_unknown_ids_and_wrong_backup_rejected():
    p = packet()
    source = draft(p)
    source["key"] = "wrong"
    with pytest.raises(ValueError, match="packet nguồn"):
        migration.migrate(p, p, source)
    source = draft(p)
    source["state"]["labels"]["q1"]["unknown"] = 3
    with pytest.raises(ValueError):
        migration.migrate(p, p, source)


def test_assisted_draft_keeps_attribution_and_cannot_become_independent():
    old = packet()
    old.update(suggestions={"version": "v1"}, suggestions_sha256="c" * 64)
    source = draft(old)
    source["state"]["assisted"] = {"q1": {"a": 2}}
    result = migration.migrate(old, old, source)["state"]
    assert result["assisted"] == {"q1": {"a": 2}}
    with pytest.raises(ValueError, match="độc lập"):
        migration.migrate(old, packet(), source)
    with pytest.raises(ValueError, match="Gợi ý máy đã đổi"):
        migration.migrate(old, {**old, "suggestions_sha256": "d" * 64}, source)


def test_packet_records_actual_displayed_image_digest(snap, tmp_path):
    query = packet()["queries"][0]
    result = prepare_review.make_packet([query], snap, tmp_path)
    assert result["review_content_version"] == 1
    for product in result["products"]:
        if product["image"]:
            assert product["image_sha256"] == hashlib.sha256((tmp_path / product["image"]).read_bytes()).hexdigest()


def test_cli_writes_importable_draft_without_overwriting_source(tmp_path):
    p = packet()
    for name, value in (("old", p), ("new", {**p, "catalog_sha256": "new"}), ("draft", draft(p))):
        (tmp_path / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
    out = tmp_path / "converted.json"
    args = ["--old-packet", str(tmp_path / "old.json"), "--new-packet", str(tmp_path / "new.json"),
            "--draft", str(tmp_path / "draft.json"), "--out", str(out)]
    assert migration.main(args) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["state"]["confirmed"] == {"q1": False}
    with pytest.raises(SystemExit) as exc:
        migration.main(args)
    assert exc.value.code == 2
