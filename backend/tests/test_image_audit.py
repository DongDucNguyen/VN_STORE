import copy
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

from app.catalog.validation import REPO_ROOT
from conftest import FIXTURE

sys.path.insert(0, str(REPO_ROOT / "scripts/validate_catalog"))
from audit_images import audit_catalog, render_gallery


@pytest.fixture()
def catalog_file(tmp_path):
    shutil.copytree(FIXTURE.parent / "assets", tmp_path / "assets")
    path = tmp_path / "database.json"
    path.write_bytes(FIXTURE.read_bytes())
    return path


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_mixed_status_and_source_only_images(catalog_file):
    data = json.loads(catalog_file.read_bytes())
    data["products"][0]["status"] = "archived"
    draft = next(p for p in data["products"] if p["status"] == "draft")
    image = copy.deepcopy(data["products"][1]["images"][0])
    image.update(id="img-url-only", local_path=None, source_url="https://example.com/photo.png", sha256=None)
    image["usage_rights"]["status"] = "unknown"
    draft["images"] = [image]
    save(catalog_file, data)
    before = catalog_file.read_bytes()
    report = audit_catalog(catalog_file)
    assert report["status"] == "passed", report["failures"]
    assert report["api_modes"]["published_only"]["listed_products"] == 11
    assert report["api_modes"]["include_drafts"]["listed_products"] == 12
    assert report["quality"]["image_files"]["by_status"]["no_local_path"] == 1
    assert report["import_check"]["status"] == "skipped"
    assert catalog_file.read_bytes() == before


def test_pagination_beyond_one_hundred(catalog_file):
    data = json.loads(catalog_file.read_bytes())
    template = data["products"][0]
    products = []
    for index in range(101):
        p = copy.deepcopy(template)
        p["id"] = f"p-many-{index}"
        p["slug"] = f"product-many-{index}"
        for v in p["variants"]:
            v["sku"] += f"-{index}"
        for image in p["images"]:
            image["id"] += f"-{index}"
            image["variant_sku"] = None
        products.append(p)
    data["products"] = products
    save(catalog_file, data)
    report = audit_catalog(catalog_file)
    assert report["status"] == "passed", report["failures"]
    assert report["api_modes"]["published_only"]["pages"] == 2
    assert report["api_modes"]["include_drafts"]["listed_products"] == 101
    assert report["hash_verified_api_images"] == sum(len(p["images"]) for p in products)


def test_empty_catalog(catalog_file):
    data = json.loads(catalog_file.read_bytes())
    data["products"] = []
    save(catalog_file, data)
    report = audit_catalog(catalog_file)
    assert report["status"] == "passed"
    assert report["hash_verified_api_images"] == 0
    assert report["api_modes"]["published_only"]["listed_products"] == 0


def test_missing_draft_file_is_warning_and_not_verified(catalog_file):
    data = json.loads(catalog_file.read_bytes())
    draft = data["products"][0]
    draft.update(status="draft", reviewed_at=None)
    draft["images"][0]["local_path"] = "assets/missing.svg"
    save(catalog_file, data)
    report = audit_catalog(catalog_file)
    assert report["status"] == "passed"
    assert any(i["code"] == "missing_image_file" for i in report["validation_issues"])
    assert report["quality"]["image_files"]["by_status"]["missing"] == 1


def test_invalid_checksum_stops_before_api(catalog_file):
    data = json.loads(catalog_file.read_bytes())
    data["products"][0]["images"][0]["sha256"] = "0" * 64
    save(catalog_file, data)
    report = audit_catalog(catalog_file)
    assert report["status"] == "failed"
    assert "api_modes" not in report
    assert any(i["code"] == "image_checksum" for i in report["validation_issues"])


def test_restores_environment_and_api_state(catalog_file, monkeypatch):
    import app.main as api
    sentinel = object()
    monkeypatch.setattr(api.state, "bundle", sentinel)
    monkeypatch.setenv("VNSTORE_CATALOG", "original.json")
    monkeypatch.delenv("VNSTORE_INCLUDE_DRAFTS", raising=False)
    audit_catalog(catalog_file)
    assert api.state.bundle is sentinel
    assert os.environ["VNSTORE_CATALOG"] == "original.json"
    assert "VNSTORE_INCLUDE_DRAFTS" not in os.environ


def test_restores_state_when_testclient_fails(catalog_file, monkeypatch):
    import app.main as api
    import fastapi.testclient
    before = api.state.bundle
    monkeypatch.setenv("VNSTORE_INCLUDE_DRAFTS", "before-audit")

    def broken(*args, **kwargs):
        raise ValueError("Simulated client failure")
    monkeypatch.setattr(fastapi.testclient, "TestClient", broken)
    with pytest.raises(ValueError, match="Simulated"):
        audit_catalog(catalog_file)
    assert api.state.bundle is before
    assert os.environ["VNSTORE_INCLUDE_DRAFTS"] == "before-audit"


def test_optional_manifest_not_dependent_on_product_order(tmp_path):
    manifest = json.loads((REPO_ROOT / "data_collection/images/2026-10-10/manifest.json").read_bytes())
    manifest["products"].reverse()
    path = tmp_path / "manifest.json"
    save(path, manifest)
    report = audit_catalog(REPO_ROOT / "database.json", manifests=[path])
    assert report["status"] == "passed"
    assert report["manifest_checks"][0]["idempotent"] is True


def test_bad_optional_manifest_is_reported(catalog_file, tmp_path):
    report = audit_catalog(catalog_file, manifests=[tmp_path / "not-there.json"])
    assert report["status"] == "failed"
    assert report["manifest_checks"][0]["status"] == "failed"


def test_gallery_escapes_text_and_links_existing_files(catalog_file, tmp_path):
    data = json.loads(catalog_file.read_bytes())
    data["products"][0]["name_vi"] = '<script>alert("bad")</script>'
    data["products"][0]["images"][0]["source_url"] = "javascript:alert(1)"
    page = render_gallery(data, catalog_file.parent, tmp_path / "review")
    assert '<script>' not in page and 'javascript:' not in page
    assert '&lt;script&gt;' in page
    assert 'src="../assets/' in page


def test_cli_saves_failed_report_for_invalid_json(tmp_path, monkeypatch):
    import audit_images
    catalog = tmp_path / "bad.json"
    catalog.write_text("not JSON", encoding="utf-8")
    report_dir = tmp_path / "reports"
    monkeypatch.setattr(sys, "argv", ["audit_images.py", "--catalog", str(catalog), "--report-dir", str(report_dir)])
    assert audit_images.main() == 1
    reports = list(report_dir.glob("*.json"))
    assert len(reports) == 1
    assert json.loads(reports[0].read_bytes())["status"] == "failed"


def test_gallery_output_refuses_existing_directory(tmp_path, monkeypatch):
    import audit_images
    monkeypatch.setattr(sys, "argv", ["audit_images.py", "--review-out", str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        audit_images.main()
    assert error.value.code == 2
