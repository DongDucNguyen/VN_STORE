import copy
import json
from pathlib import Path
import sys
import shutil

import pytest

from app.catalog.validation import REPO_ROOT, ValidationResult
from conftest import FIXTURE

sys.path.insert(0, str(REPO_ROOT / "scripts/import_raw"))
from apply_images import apply_images, DEFAULT_MANIFEST
from build_drafts import generate
from safe_import import (COLLECTIONS, digest, encoded, execute_import, guarded_write,
                         load_baseline, merge_catalog)


@pytest.fixture()
def catalog():
    return {"catalog_version": "v1", "updated_at": "2026-10-10T00:00:00+07:00",
            **{c: [] for c in COLLECTIONS}, "products": [
                {"id": "p-one", "status": "draft", "reviewed_at": None,
                 "name_vi": "Original", "materials": ["bamboo"],
                 "images": [{"id": "i-one", "usage_rights": {"status": "unknown"}}],
                 "origin": {"country": None, "detail": "old"}}]}


def test_no_baseline_allows_identical_and_additions(catalog):
    incoming = copy.deepcopy(catalog)
    incoming["sources"] = [{"id": "src-new"}]
    out, conflicts = merge_catalog(catalog, incoming)
    assert not conflicts
    assert out["sources"] == incoming["sources"]
    assert catalog["sources"] == []


def test_no_baseline_refuses_to_replace_existing_record(catalog):
    incoming = copy.deepcopy(catalog)
    incoming["products"][0]["name_vi"] = "New"
    out, conflicts = merge_catalog(catalog, incoming)
    assert out == catalog
    assert conflicts[0]["baseline"] == {"present": False}


def test_preserves_local_review_rights_and_source_note(catalog):
    baseline = copy.deepcopy(catalog)
    baseline["sources"] = [{"id": "s", "note": "original"}]
    current = copy.deepcopy(baseline)
    current["products"][0].update(status="published", reviewed_at="2026-10-10T01:00:00+07:00")
    current["products"][0]["images"][0]["usage_rights"] = {"status": "licensed", "note": "Document A"}
    current["sources"][0]["note"] = "Reviewed source"
    out, conflicts = merge_catalog(current, baseline, baseline)
    assert not conflicts and out == current


def test_independent_nested_edits_merge_without_mutating_inputs(catalog):
    current, incoming = copy.deepcopy(catalog), copy.deepcopy(catalog)
    current["products"][0]["origin"]["country"] = "VN"
    incoming["products"][0]["origin"]["detail"] = "New evidence"
    before = copy.deepcopy((catalog, current, incoming))
    out, conflicts = merge_catalog(current, incoming, catalog)
    assert not conflicts
    assert out["products"][0]["origin"] == {"country": "VN", "detail": "New evidence"}
    assert (catalog, current, incoming) == before


@pytest.mark.parametrize("field,local,remote", [
    ("name_vi", "Human title", "Source title"),
    ("materials", ["rattan"], ["wood"]),
    ("images", [{"id": "i-one", "usage_rights": {"status": "licensed"}}], [{"id": "i-two"}]),
])
def test_overlapping_edits_conflict_and_keep_local(catalog, field, local, remote):
    current, incoming = copy.deepcopy(catalog), copy.deepcopy(catalog)
    current["products"][0][field] = local
    incoming["products"][0][field] = remote
    out, conflicts = merge_catalog(current, incoming, catalog)
    assert out == current
    assert conflicts[0]["path"].endswith("." + field)


@pytest.mark.parametrize("status,reviewed", [("published", None), ("archived", None), ("draft", "2026-10-10")])
def test_source_update_cannot_change_reviewed_product(catalog, status, reviewed):
    current, incoming = copy.deepcopy(catalog), copy.deepcopy(catalog)
    current["products"][0].update(status=status, reviewed_at=reviewed)
    incoming["products"][0]["name_vi"] = "Changed source"
    out, conflicts = merge_catalog(current, incoming, catalog)
    assert out == current
    assert any(c["code"] == "reviewed_or_non_draft_product" for c in conflicts)


@pytest.mark.parametrize("referenced", [True, False])
def test_shared_source_updates_require_review_only_when_referenced(catalog, referenced):
    catalog["sources"] = [{"id": "s-one", "title": "Old source"}]
    catalog["products"][0]["source_ids"] = ["s-one"] if referenced else []
    current, incoming = copy.deepcopy(catalog), copy.deepcopy(catalog)
    current["products"][0]["reviewed_at"] = "2026-10-10T01:00:00+07:00"
    incoming["sources"][0]["title"] = "Changed evidence"
    _, conflicts = merge_catalog(current, incoming, catalog)
    assert bool(conflicts) == referenced
    if referenced:
        assert conflicts[0]["code"] == "reviewed_product_reference_changed"


def test_record_omission_never_deletes_and_local_deletion_not_resurrected(catalog):
    empty = copy.deepcopy(catalog)
    empty["products"] = []
    assert merge_catalog(catalog, empty, catalog) == (catalog, [])
    assert merge_catalog(empty, catalog, catalog) == (empty, [])
    incoming = copy.deepcopy(catalog)
    incoming["products"][0]["name_vi"] = "Updated"
    out, conflicts = merge_catalog(empty, incoming, catalog)
    assert out == empty and conflicts


def test_same_edit_both_sides_is_not_conflict(catalog):
    current = copy.deepcopy(catalog)
    current["products"][0]["name_vi"] = "Same title"
    assert merge_catalog(current, current, catalog) == (current, [])


def test_duplicate_ids_are_rejected(catalog):
    incoming = copy.deepcopy(catalog)
    incoming["products"] *= 2
    with pytest.raises(ValueError, match="Duplicate ID"):
        merge_catalog(catalog, incoming, catalog)


def test_stale_catalog_write_rejected_and_temp_cleaned(tmp_path, catalog):
    dest = tmp_path / "database.json"
    original = encoded(catalog)
    dest.write_bytes(b"concurrent editor changed this file")
    with pytest.raises(ValueError, match="Catalog"):
        guarded_write(dest, original, catalog)
    assert dest.read_bytes() == b"concurrent editor changed this file"
    assert list(tmp_path.iterdir()) == [dest]


@pytest.mark.parametrize("dry_run,conflict,status,eligible", [
    (True, False, "preview", False), (False, False, "applied", True),
    (False, True, "blocked", False),
])
def test_commit_records_diff_backup_and_baseline(tmp_path, catalog, dry_run, conflict, status, eligible):
    dest = tmp_path / "database.json"
    original = encoded(catalog)
    dest.write_bytes(original)
    proposed = copy.deepcopy(catalog)
    proposed["products"][0]["name_vi"] = "Changed"
    code, report_path = execute_import(catalog_path=dest, original=original, proposed=proposed,
        generated=proposed, conflicts=[{"code": "test", "path": "$"}] if conflict else [],
        validation=ValidationResult(), dry_run=dry_run, root=tmp_path)
    report = json.loads(report_path.read_bytes())
    run_dir = tmp_path / report["artifacts"]
    assert report["status"] == status and bool(code) == conflict
    assert (run_dir / "catalog.before.json").read_bytes() == original
    assert bool(report["changes"])
    assert dest.read_bytes() == (encoded(proposed) if status == "applied" else original)
    if eligible:
        assert load_baseline(run_dir / "baseline.json") == proposed
    else:
        with pytest.raises(ValueError, match="Baseline"):
            load_baseline(run_dir / "baseline.json")


def test_noop_keeps_original_bytes_and_creates_usable_baseline(tmp_path, catalog):
    dest = tmp_path / "database.json"
    original = json.dumps(catalog).encode()  # Different formatting must remain intact.
    dest.write_bytes(original)
    code, path = execute_import(catalog_path=dest, original=original, proposed=catalog,
        generated=catalog, conflicts=[], validation=ValidationResult(), dry_run=True, root=tmp_path)
    report = json.loads(path.read_bytes())
    assert code == 0 and report["status"] == "no_op" and dest.read_bytes() == original
    baseline_path = tmp_path / report["artifacts"] / "baseline.json"
    assert load_baseline(baseline_path) == catalog
    payload = json.loads(baseline_path.read_bytes())
    payload["generated"]["catalog_version"] = "tampered"
    baseline_path.write_bytes(encoded(payload))
    with pytest.raises(ValueError, match="checksum"):
        load_baseline(baseline_path)


def test_validation_failure_never_writes(tmp_path, catalog):
    dest = tmp_path / "database.json"
    original = encoded(catalog)
    dest.write_bytes(original)
    validation = ValidationResult()
    validation.error("bad_catalog", "$", "Invalid proposal")
    code, path = execute_import(catalog_path=dest, original=original, proposed=catalog,
        generated=catalog, conflicts=[], validation=validation, dry_run=False, root=tmp_path)
    assert code == 1 and dest.read_bytes() == original
    assert json.loads(path.read_bytes())["status"] == "blocked"


@pytest.fixture()
def real():
    return json.loads((REPO_ROOT / "database.json").read_bytes())


def test_real_generator_is_noop_with_safe_merge(real):
    editorial = json.loads((REPO_ROOT / "data_collection/editorial.json").read_bytes())
    generated = generate(editorial)
    # Import timestamps can differ from collection timestamps after a real import.
    out, conflicts = merge_catalog(real, generated, generated)
    assert not conflicts and out == real


def test_import_adds_category_and_moves_product_together(catalog):
    incoming = copy.deepcopy(catalog)
    incoming["categories"] = [{"id": "decor-vase", "name_vi": "Bình trang trí", "parent_id": None}]
    incoming["products"][0]["category_id"] = "decor-vase"
    out, conflicts = merge_catalog(catalog, incoming, catalog)
    assert not conflicts and out["categories"] == incoming["categories"]
    assert out["products"][0]["category_id"] == "decor-vase"


def test_legacy_baseline_without_categories_can_be_loaded(tmp_path, catalog):
    old = copy.deepcopy(catalog)
    del old["categories"]
    path = tmp_path / "baseline.json"
    path.write_bytes(encoded({"format": "vnstore-import-baseline-v1", "eligible": True,
                             "generated": old, "generated_sha256": digest(encoded(old))}))
    assert load_baseline(path) == old
    out, conflicts = merge_catalog(catalog, old, old)
    assert not conflicts and out == catalog


def test_category_change_referenced_by_reviewed_product_is_blocked(catalog):
    catalog["categories"] = [{"id": "decor", "name_vi": "Trang trí"}]
    catalog["products"][0].update(category_id="decor", reviewed_at="2026-10-10T01:00:00+07:00")
    incoming = copy.deepcopy(catalog)
    incoming["categories"][0]["name_vi"] = "Đổi tên"
    _, conflicts = merge_catalog(catalog, incoming, catalog)
    assert conflicts[0]["code"] == "reviewed_product_reference_changed"


def test_image_reimport_preserves_rights_caption_and_new_version(real):
    real["catalog_version"] = "human-reviewed-v2"
    product = real["products"][0]
    product.update(status="published", reviewed_at="2026-10-10T01:00:00+07:00")
    image = product["images"][0]
    image["usage_rights"].update(status="licensed", note="Permission document 123", license="Internal agreement")
    image["alt_vi"] = "Caption corrected by reviewer"
    before = copy.deepcopy(real)
    assert apply_images(real) == before
    assert real == before


def test_image_reimport_does_not_replace_changed_asset(real):
    real["products"][0]["images"][0]["sha256"] = "0" * 64
    before = copy.deepcopy(real)
    with pytest.raises(ValueError, match="differs from manifest"):
        apply_images(real)
    assert real == before


def test_image_manifest_cannot_remove_local_or_licensed_image(real, tmp_path):
    manifest = json.loads(DEFAULT_MANIFEST.read_bytes())
    record = manifest["products"][1]  # A product with at least two accepted images.
    accepted = [a for a in record["images"] if a.get("decision") == "accept"]
    assert len(accepted) >= 2
    accepted[0]["decision"] = "exclude"
    path = tmp_path / "manifest.json"
    path.write_bytes(encoded(manifest))
    with pytest.raises(ValueError, match="would remove"):
        apply_images(real, path)


def test_image_download_does_not_transfer_prior_permission(real):
    image = real["products"][0]["images"][0]
    image["local_path"] = None
    image["usage_rights"]["status"] = "licensed"
    with pytest.raises(ValueError, match="rights already recorded"):
        apply_images(real)


def test_image_caption_note_and_gallery_order_survive_download_and_reimport(real):
    product = next(p for p in real["products"] if len(p["images"]) > 1)
    product["images"].reverse()
    image = product["images"][0]
    image["local_path"] = None
    image["alt_vi"] = "Manual caption before download"
    image["usage_rights"]["note"] = "Manual pending-rights note"
    before = copy.deepcopy(real)
    out = apply_images(real)
    updated = next(p for p in out["products"] if p["id"] == product["id"])
    assert [i["id"] for i in updated["images"]] == [i["id"] for i in product["images"]]
    assert updated["images"][0]["alt_vi"] == image["alt_vi"]
    assert updated["images"][0]["usage_rights"] == image["usage_rights"]
    assert updated["images"][0]["local_path"] is not None
    assert real == before


@pytest.mark.parametrize("new_version,dry_run,expected_code", [(None, False, 1), ("v-next", True, 0), ("v-next", False, 0)])
def test_draft_cli_requires_version_and_honors_preview(tmp_path, monkeypatch, new_version, dry_run, expected_code):
    import build_drafts
    current = json.loads(FIXTURE.read_bytes())
    current["products"][0].update(status="draft", reviewed_at=None)
    original = encoded(current)
    dest = tmp_path / "database.json"
    dest.write_bytes(original)
    shutil.copytree(FIXTURE.parent / "assets", tmp_path / "assets")
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_bytes(encoded({"format": "vnstore-import-baseline-v1", "eligible": True,
                                      "generated": current, "generated_sha256": digest(encoded(current))}))
    incoming = copy.deepcopy(current)
    incoming["products"][0]["name_vi"] = "Source name updated"
    monkeypatch.setattr(build_drafts, "ROOT", tmp_path)
    monkeypatch.setattr(build_drafts, "generate", lambda *_: incoming)
    args = ["build_drafts.py", "--catalog", str(dest), "--baseline", str(baseline_path),
            "--editorial", str(REPO_ROOT / "data_collection/editorial.json")]
    if new_version:
        args.extend(["--catalog-version", new_version])
    if dry_run:
        args.append("--dry-run")
    monkeypatch.setattr(sys, "argv", args)
    assert build_drafts.main() == expected_code
    if not dry_run and expected_code == 0:
        result = json.loads(dest.read_bytes())
        assert result["products"][0]["name_vi"] == "Source name updated"
        assert result["catalog_version"] == "v-next"
    else:
        assert dest.read_bytes() == original


def test_stale_write_is_saved_as_failed_report(tmp_path, catalog):
    dest = tmp_path / "database.json"
    original = encoded(catalog)
    dest.write_bytes(b"Changed concurrently")
    proposal = copy.deepcopy(catalog)
    proposal["catalog_version"] = "v-next"
    code, path = execute_import(catalog_path=dest, original=original, proposed=proposal,
        generated=proposal, conflicts=[], validation=ValidationResult(), dry_run=False, root=tmp_path)
    report = json.loads(path.read_bytes())
    assert code == 1 and report["status"] == "write_failed"
    assert dest.read_bytes() == b"Changed concurrently"
    baseline_path = tmp_path / report["artifacts"] / "baseline.json"
    with pytest.raises(ValueError, match="Baseline"):
        load_baseline(baseline_path)
