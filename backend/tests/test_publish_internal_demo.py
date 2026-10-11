"""Publishing reviewed drafts and the explicit internal-demo image-rights policy (fixture catalog only)."""
import copy
import json
import sys
from pathlib import Path

import pytest

from app.catalog.validation import validate_catalog
from tests.conftest import FIXTURE

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/import_raw"))
import publish_reviewed as pr  # noqa: E402

POLICY = {"mode": "internal_demo", "allow_unverified_image_rights": True,
          "decided_at": "2026-10-11T14:00:00+07:00", "decided_by": None, "note": "synthetic"}


def catalog_with_unknown_rights():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    product = next(p for p in data["products"] if p["status"] == "published" and p["images"])
    for image in product["images"]:
        image["usage_rights"] = {**image["usage_rights"], "status": "unknown"}
    return data


def codes(result, level):
    return [i.code for i in result.issues if i.level == level]


def test_unknown_rights_block_publish_unless_internal_demo():
    data = catalog_with_unknown_rights()
    strict = validate_catalog(data, FIXTURE.parent, check_files=False)
    assert "image_rights" in codes(strict, "error")
    demo = validate_catalog({**data, "publication_policy": POLICY}, FIXTURE.parent, check_files=False)
    assert "image_rights" not in codes(demo, "error") and "published_no_image" not in codes(demo, "error")
    assert codes(demo, "warning").count("image_rights_unverified_demo") == 1  # one catalog-level note


@pytest.mark.parametrize("bad", [{"allow_unverified_image_rights": False}, {"mode": "public"}, {"note": ""}])
def test_policy_must_be_explicit(bad):
    data = {**catalog_with_unknown_rights(), "publication_policy": {**POLICY, **bad}}
    assert "schema" in codes(validate_catalog(data, FIXTURE.parent, check_files=False), "error")


def test_publish_sets_review_fields_and_keeps_excluded_drafts():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    drafts = [p["id"] for p in data["products"] if p["status"] == "draft"]
    assert drafts, "fixture needs a draft product"
    out, changed = pr.publish(data, exclude={drafts[0]}, stamp="2026-10-11T14:00:00+07:00", note="n",
                              internal_demo=True, decided_by=None)
    by = {p["id"]: p for p in out["products"]}
    assert by[drafts[0]]["status"] == "draft" and set(changed) == set(drafts[1:])
    assert all(by[i]["reviewed_at"] == "2026-10-11T14:00:00+07:00" for i in changed)
    assert out["publication_policy"]["decided_by"] is None
    assert data == json.loads(FIXTURE.read_text(encoding="utf-8"))  # input untouched
    with pytest.raises(ValueError, match="không có"):
        pr.publish(copy.deepcopy(data), exclude={"p-missing"}, stamp="x", note="n", internal_demo=False, decided_by=None)
