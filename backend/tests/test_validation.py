import copy
import json

import pytest

from app.catalog.validation import REPO_ROOT, quality_report, validate_catalog
from conftest import FIXTURE


@pytest.fixture()
def data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def codes(result):
    return {i.code for i in result.errors}


def test_fixture_is_valid(data):
    r = validate_catalog(data, FIXTURE.parent)
    assert r.ok, [str(i) for i in r.errors]


def test_seed_database_is_valid():
    path = REPO_ROOT / "database.json"
    r = validate_catalog(json.loads(path.read_text(encoding="utf-8")), path.parent)
    assert r.ok, [str(i) for i in r.errors]


def test_duplicate_ids_and_skus(data):
    d = copy.deepcopy(data)
    dup = copy.deepcopy(d["products"][0])
    d["products"].append(dup)
    c = codes(validate_catalog(d, FIXTURE.parent))
    assert {"duplicate_id", "duplicate_sku", "duplicate_slug", "duplicate_image_id"} <= c


def test_broken_references(data):
    d = copy.deepcopy(data)
    d["products"][0]["category_id"] = "khong-ton-tai"
    d["products"][0]["origin_claims"][0]["source_ids"] = ["src-khong-co"]
    assert "broken_ref" in codes(validate_catalog(d, FIXTURE.parent))


def test_zero_price_rejected(data):
    d = copy.deepcopy(data)
    d["products"][0]["variants"][0]["price_vnd"] = 0
    assert "schema" in codes(validate_catalog(d, FIXTURE.parent))


def test_known_price_needs_source_and_date(data):
    d = copy.deepcopy(data)
    v = d["products"][0]["variants"][0]
    v["price_source_id"] = None
    assert "schema" in codes(validate_catalog(d, FIXTURE.parent))


def test_true_claim_needs_source(data):
    d = copy.deepcopy(data)
    d["products"][0]["origin_claims"][0]["source_ids"] = []
    assert "schema" in codes(validate_catalog(d, FIXTURE.parent))


def test_unknown_claim_without_source_is_allowed(data):
    d = copy.deepcopy(data)
    d["products"][0]["origin_claims"].append(
        {"claim_type": "vn_material", "value": "unknown", "status": "unverified", "source_ids": [], "checked_at": None})
    assert validate_catalog(d, FIXTURE.parent).ok


def test_published_rules(data):
    d = copy.deepcopy(data)
    p = d["products"][0]
    p["images"][0]["local_path"] = "assets/khong-co.svg"
    p["images"][1]["usage_rights"]["status"] = "unknown"
    p["origin_claims"] = [{"claim_type": "made_in_vn", "value": "unknown", "status": "unverified",
                           "source_ids": [], "checked_at": None}]
    c = codes(validate_catalog(d, FIXTURE.parent))
    assert {"missing_image_file", "image_rights", "published_no_image", "published_no_vn_claim"} <= c


def test_draft_missing_image_is_only_warning(data):
    d = copy.deepcopy(data)
    draft = next(p for p in d["products"] if p["status"] == "draft")
    draft["images"] = [{"id": "img-draft", "local_path": "assets/khong-co.svg", "alt_vi": "x",
                        "view_type": "front", "usage_rights": {"status": "unknown"}}]
    r = validate_catalog(d, FIXTURE.parent)
    assert r.ok and any(i.code == "missing_image_file" for i in r.warnings)


def test_category_cycle(data):
    d = copy.deepcopy(data)
    d["categories"][0]["parent_id"] = "gom-su-binh-lo"
    assert "category_cycle" in codes(validate_catalog(d, FIXTURE.parent))


def test_quality_report(data):
    rep = quality_report(data, FIXTURE.parent)
    assert rep["counts"]["products"] == len(data["products"])
    assert rep["missing"]["khong_co_gia_bien_the"]["count"] == 1
    assert rep["status"] == {"published": 12, "draft": 1}
