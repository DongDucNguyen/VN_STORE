import copy
import hashlib
import json
from pathlib import Path

import pytest

from app.catalog import validation
from app.catalog.readiness import publication_readiness
from app.catalog.validation import inspect_image_file, quality_report, validate_catalog
from conftest import FIXTURE


@pytest.fixture()
def data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", ["../outside.svg", "/outside.svg", "."])
@pytest.mark.parametrize("check_files", [True, False])
def test_outside_path_never_hashed(path, check_files, monkeypatch):
    def forbidden(_):
        pytest.fail("Must not read files outside the catalog root")
    monkeypatch.setattr(validation, "sha256_file", forbidden)
    assert inspect_image_file({"local_path": path}, FIXTURE.parent, check_files).status == "outside_root"


def test_resolved_symlink_escape_never_hashed(monkeypatch):
    root = FIXTURE.parent.resolve()
    original = Path.resolve

    def resolve(path, *args, **kwargs):
        if path.name == "escape.svg":
            return root.parent / "external.svg"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    monkeypatch.setattr(validation, "sha256_file", lambda _: pytest.fail("External file read"))
    assert inspect_image_file({"local_path": "escape.svg"}, root).status == "outside_root"


def test_checksum_error_is_not_usable_for_publication(data):
    p = data["products"][0]
    p["images"] = p["images"][:1]
    p["images"][0]["sha256"] = "0" * 64
    result = validate_catalog(data, FIXTURE.parent)
    assert {"image_checksum", "published_no_image"} <= {i.code for i in result.errors}
    quality = quality_report(data, FIXTURE.parent)
    assert quality["image_files"]["by_status"]["checksum_mismatch"] == 1


def test_path_escape_is_rejected_even_without_file_checks(data):
    data["products"][0]["images"][0]["local_path"] = "../outside.svg"
    result = validate_catalog(data, FIXTURE.parent, check_files=False)
    assert "image_path_outside_root" in {i.code for i in result.errors}


def test_file_states_and_checksum(tmp_path):
    path = tmp_path / "photo.bin"
    image = {"local_path": path.name}
    assert inspect_image_file(image, tmp_path).status == "missing"
    path.write_bytes(b"")
    assert inspect_image_file(image, tmp_path).status == "empty_file"
    path.write_bytes(b"image fixture bytes")
    image["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = inspect_image_file(image, tmp_path)
    assert result.status == "valid" and result.sha256 == image["sha256"]
    assert inspect_image_file(image, tmp_path, False).status == "unchecked"
    assert inspect_image_file({"local_path": None}, tmp_path).status == "no_local_path"


def test_unreadable_file_report_does_not_crash(data, monkeypatch):
    def denied(_):
        raise PermissionError("Denied by OS")
    monkeypatch.setattr(validation, "sha256_file", denied)
    result = validate_catalog(data, FIXTURE.parent)
    assert "image_file_invalid" in {i.code for i in result.errors}
    report = quality_report(data, FIXTURE.parent)
    assert report["image_files"]["by_status"]["unreadable"] > 0
    assert report["image_files"]["with_usable_rights_and_valid_file"] == 0
    assert report["duplicate_images_sha256"] == {}


def test_quality_distinguishes_missing_file_from_image_record(data):
    data["products"] = data["products"][:1]
    data["products"][0]["images"] = data["products"][0]["images"][:1]
    data["products"][0]["images"][0]["local_path"] = "assets/absent.svg"
    report = quality_report(data, FIXTURE.parent)
    assert report["missing"]["khong_co_anh"]["count"] == 0
    assert report["missing"]["khong_co_file_anh_hop_le"]["count"] == 1
    assert report["image_files"]["by_status"] == {"missing": 1}


def test_readiness_is_read_only_and_review_separate(data):
    p = data["products"][0]
    p["status"] = "draft"
    p["reviewed_at"] = None
    before = copy.deepcopy(data)
    report = publication_readiness(data, FIXTURE.parent)
    assert data == before
    row = report["products"][0]
    assert row["technical_ready"] is True
    assert row["review_recorded"] is False
    assert row["passes_recorded_checks"] is False
    assert {i["code"] for i in row["warnings"]} == {"published_not_reviewed"}


def test_readiness_counts_products_not_number_of_image_errors(data):
    p = data["products"][0]
    p["status"] = "draft"
    for image in p["images"]:
        image["usage_rights"]["status"] = "unknown"
    report = publication_readiness(data, FIXTURE.parent)
    row = report["products"][0]
    assert row["blocker_codes"] == ["image_rights", "published_no_image"]
    assert sum(i["code"] == "image_rights" for i in row["blockers"]) == 2
    assert report["summary"]["products_by_blocker_code"]["image_rights"] == 1


def test_schema_failure_is_reported_without_assessing_products(data):
    del data["products"][0]["images"]
    report = publication_readiness(data, FIXTURE.parent)
    assert not report["assessment_complete"]
    assert not report["current_validation"]["ok"]
    assert report["products"] == []


def test_global_reference_errors_block_all_products(data):
    data["brands"][0]["source_ids"] = ["src-missing"]
    report = publication_readiness(data, FIXTURE.parent)
    assert report["summary"]["global_errors"] > 0
    assert not any(p["technical_ready"] for p in report["products"])


def test_real_catalog_readiness_matches_known_blockers():
    path = validation.REPO_ROOT / "database.json"
    report = publication_readiness(json.loads(path.read_text(encoding="utf-8")), path.parent)
    # Assert invariants, not fixed seed counts: future approved data can still pass.
    assert report["current_validation"]["ok"]
    assert len(report["products"]) == report["quality"]["counts"]["products"]
    for p in report["products"]:
        if "image_rights" in p["blocker_codes"]:
            assert not p["technical_ready"]
