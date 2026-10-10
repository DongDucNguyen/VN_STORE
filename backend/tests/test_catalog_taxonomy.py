"""Real-data regression for category semantics; no retrieval benchmark labels."""
import json

import pytest

from app.catalog.store import load_snapshot
from app.catalog.validation import REPO_ROOT
from app.search.engine import SearchEngine, SearchFilters

VASES = {"p-hanoia-binh-hoa-mystery-a18mt01", "p-hanoia-binh-hoa-vita-pc26vt01"}
CATEGORY = "go-son-mai-binh-lo"


@pytest.fixture(scope="module")
def real():
    return load_snapshot(REPO_ROOT / "database.json", include_drafts=True)


def test_decorative_vases_have_own_category_consistent_with_editorial(real):
    editorial = json.loads((REPO_ROOT / "data_collection/editorial.json").read_bytes())
    products = {p["id"]: p for p in editorial["products"]}
    assert real.categories[CATEGORY]["parent_id"] == "go-son-mai"
    for pid in VASES:
        assert real.products[pid]["category_id"] == products[pid]["category_id"] == CATEGORY
        assert "resin" in real.products[pid]["materials"]
    # A navigation category must not create a material/technique claim.
    assert real.products["p-hanoia-binh-hoa-vita-pc26vt01"]["craft_techniques"] == []


def test_vase_filter_excludes_ceramics_and_paintings(real):
    engine = SearchEngine(real)
    results = engine.search("", SearchFilters(category_ids=[CATEGORY]), limit=100)["results"]
    assert {p["id"] for p in results} == VASES
    for category in ("go-son-mai-tranh", "gom-su"):
        results = engine.search("", SearchFilters(category_ids=[category]), limit=100)["results"]
        assert not VASES.intersection(p["id"] for p in results)


def test_budget_filter_keeps_vita_and_excludes_mystery(real):
    results = SearchEngine(real).search("bình hoa dưới 5 triệu", SearchFilters(category_ids=[CATEGORY]))["results"]
    assert [p["id"] for p in results] == ["p-hanoia-binh-hoa-vita-pc26vt01"]
