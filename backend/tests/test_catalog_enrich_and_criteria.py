"""Archive enrichment (fill-only, evidence-backed) and criteria machine labels — synthetic products only."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/import_raw"))
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
import criteria_labels as cl  # noqa: E402
import enrich_from_archive as ea  # noqa: E402


def product(**over):
    p = {"id": "p1", "name_vi": "Dĩa lót 15.5 cm - Tulip Ngà - Màu Cam", "brand_id": "brand-minh-long",
         "materials": [], "colors": [], "aliases": [], "short_description_vi": "", "category_id": "bowl",
         "variants": [{"price_vnd": 90000}]}
    p.update(over)
    return p


def test_enrich_fills_only_empty_fields_from_explicit_evidence():
    found = ea.evidence_for(product(), "", "")
    assert found["colors"][0] == ["cam"] and found["materials"][0] == ["sứ"]
    assert "colors" not in ea.evidence_for(product(colors=["xanh"]), "", "")  # never overwrite
    assert "colors" not in ea.evidence_for(product(name_vi="Bình hoa 41 cm - Bình Hoa - Hoa Hồng"), "", "")
    silk = product(brand_id="brand-sensilk", name_vi="Khăn lụa", materials=["lụa tơ tằm"])
    assert ea.evidence_for(silk, "Màu sắc: Tím than Họa tiết: hoa", "")["colors"][0] == ["tím than"]
    assert ea.evidence_for(product(brand_id=None, materials=["mây"]), "", "") == {}  # no evidence → nothing


def test_enrich_records_note_and_log():
    catalog = {"products": [product()]}
    out, log = ea.enrich(catalog, {}, {}, "2026-10-11T15:00:00+07:00")
    assert catalog["products"][0]["colors"] == []  # input untouched
    assert "chưa người duyệt lại" in out["products"][0]["editor_note"] and {r["field"] for r in log} == {"colors", "materials"}


def view(**over):
    return cl.product_view(product(**over), {"bowl": "Bát, đĩa, chén ăn", "vase": "Bình, lọ"})


@pytest.mark.parametrize("spec,over,expected", [
    ({"cat": ["bowl"], "item": r"^(chén|bát)"}, {}, 0),                          # category name never matches the item
    ({"brand": "brand-hanoia"}, {}, 0),                                          # brand-only query, other brand
    ({"cat": ["bowl"], "brand": "brand-lys"}, {}, 1),                             # same item type, other brand
    ({"mat": ["gỗ óc chó"]}, {}, 0),                                              # attribute-only query, unrelated
    ({"cat": ["bowl"], "color": ["cam"]}, {}, 3),
    ({"cat": ["bowl"], "color": ["trắng"]}, {"colors": ["cam"]}, 1),              # contradicted colour
    ({"cat": ["bowl"], "price": (0, 50000)}, {}, 0),                              # over budget
    ({"cat": ["bowl"], "price": (0, 50000)}, {"variants": [{"price_vnd": None}]}, 1),  # no price
    ({"cat": ["bowl"], "not_color": ["cam"]}, {"colors": ["cam"]}, 0),
    ({"cat": ["bowl"], "soft": r"nhà hàng"}, {}, 2),
    ({"nomatch": True, "related": r"tulip"}, {}, 1),
])
def test_criteria_grades_follow_rubric(spec, over, expected):
    assert cl.grade(spec, view(**over))[0] == expected


def test_test_split_gets_no_machine_labels():
    catalog = {"categories": [{"id": "bowl", "name_vi": "Bát"}], "products": [product()]}
    groups = [{"group_id": "x", "split": "test", "intent": "a", "queries": ["dĩa cam"], "spec": {"cat": ["bowl"]}},
              {"group_id": "y", "split": "dev", "intent": "a", "queries": ["dĩa màu cam"], "spec": {"cat": ["bowl"]}}]
    out = cl.build(groups, catalog, set(), "sha")
    assert out["test"][0]["relevance"] == {} and out["test"][0]["needs_human_labels"] is True
    assert out["dev"][0]["label_source"] == "machine" and out["dev"][0]["verified"] is False
    with pytest.raises(ValueError, match="duplicate"):
        cl.build(groups, catalog, {"dĩa cam"}, "sha")
