"""Collection audit fixtures are synthetic bytes/metadata, never benchmark data."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from conftest import FIXTURE

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("image_query_audit", ROOT / "scripts/benchmark/audit_image_queries.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
STAMP = "2026-10-10T15:00:00+07:00"


@pytest.fixture()
def collection(tmp_path):
    gallery = tmp_path / "gallery"
    shutil.copytree(FIXTURE.parent, gallery)
    catalog = gallery / FIXTURE.name
    data = json.loads(catalog.read_bytes())
    pid = data["products"][0]["id"]
    folder = tmp_path / "queries"; (folder / "raw").mkdir(parents=True)
    raw = b"SYNTHETIC query bytes; byte audit intentionally does not decode images"
    (folder / "raw/q1.jpg").write_bytes(raw)
    row = {"qid": "q1", "task": "similar", "text_vi": None, "split": "dev", "family_id": "family1",
           "capture_session_id": "session1", "source_asset_id": "original1", "source_asset_sha256": audit.digest(raw),
           "image_path": "raw/q1.jpg", "sha256": audit.digest(raw), "source_url": None,
           "usage_rights": {"status": "owned", "evidence": "SYNTHETIC consent reference"},
           "independence_review": {"independent": True, "reviewed_by": "fixture", "reviewed_at": STAMP, "note": "SYNTHETIC"},
           "judgment": {"has_answer": True, "relevance": {pid: 3}, "exact_product_id": None,
                        "exact_variant_sku": None, "reviewed_by": "fixture", "reviewed_at": STAMP}}
    manifest = {"manifest_version": "1.0.0", "catalog_sha256": audit.digest(catalog.read_bytes()),
                "include_drafts": False, "samples": [row]}
    return folder / "manifest.json", catalog, manifest


def run(collection):
    path, catalog, data = collection
    path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes(), catalog.read_bytes()
    report = audit.audit(path, catalog)
    assert before == (path.read_bytes(), catalog.read_bytes())
    return report


def codes(report):
    return {i["code"] for i in report["issues"]}


def second_sample(collection):
    path, _, data = collection
    row = copy.deepcopy(data["samples"][0]); row.update(qid="q2", image_path="raw/q2.jpg",
        family_id="family2", capture_session_id="session2", source_asset_id="original2", split="train")
    raw = b"SYNTHETIC different query bytes"
    (path.parent / row["image_path"]).write_bytes(raw)
    row["sha256"] = row["source_asset_sha256"] = audit.digest(raw)
    data["samples"].append(row)
    return row


def test_recorded_checks_do_not_approve_benchmark_or_decode(collection):
    report = run(collection)
    assert report["status"] == "recorded_checks_passed"
    assert report["benchmark_approved"] is False
    assert report["summary"]["hash_verified_files"] == 1


def test_empty_manifest_is_pending_collection(collection):
    collection[2]["samples"] = []
    report = run(collection)
    assert report["status"] == "pending_collection"
    assert report["summary"]["queries"] == 0


def test_missing_rights_and_reviews_are_explicit_pending(collection):
    row = collection[2]["samples"][0]
    row.update(judgment=None, independence_review=None)
    row["usage_rights"] = {"status": "unknown", "evidence": None}
    report = run(collection)
    assert report["status"] == "pending_review"
    assert report["summary"]["pending"] == {"judgment": 1, "rights": 1, "independence_review": 1}


@pytest.mark.parametrize("field", ["family_id", "capture_session_id", "source_asset_id", "source_asset_sha256", "sha256"])
def test_group_leakage_across_splits(collection, field):
    first = collection[2]["samples"][0]
    second_sample(collection)[field] = first[field]
    report = run(collection)
    assert report["status"] == "invalid" and "split_leakage" in codes(report)


def test_exact_product_cannot_cross_split_under_renamed_family(collection):
    second_sample(collection)
    for row in collection[2]["samples"]:
        row["task"] = "exact"
        row["judgment"]["exact_product_id"] = next(iter(row["judgment"]["relevance"]))
    assert "split_leakage" in codes(run(collection))


def test_same_image_text_ablations_within_one_split_are_warned(collection):
    row = copy.deepcopy(collection[2]["samples"][0])
    row.update(qid="q2", task="image_text", text_vi="synthetic text")
    collection[2]["samples"].append(row)
    report = run(collection)
    assert report["status"] == "recorded_checks_passed"
    assert "duplicate_query_bytes" in codes(report)
    assert report["summary"]["unique_query_hashes"] == 1


def test_duplicate_bytes_cannot_claim_different_provenance(collection):
    row = copy.deepcopy(collection[2]["samples"][0]); row.update(qid="q2", family_id="other")
    collection[2]["samples"].append(row)
    assert "duplicate_provenance" in codes(run(collection))


def test_original_hash_of_gallery_blocks_crops(collection):
    path, catalog, data = collection
    product = json.loads(catalog.read_bytes())["products"][0]
    data["samples"][0]["source_asset_sha256"] = audit.digest((catalog.parent / product["images"][0]["local_path"]).read_bytes())
    assert "gallery_original" in codes(run(collection))


def test_copied_gallery_image_is_rejected_even_if_original_id_changed(collection):
    path, catalog, data = collection
    product = json.loads(catalog.read_bytes())["products"][0]
    raw = (catalog.parent / product["images"][0]["local_path"]).read_bytes()
    (path.parent / "raw/q1.jpg").write_bytes(raw)
    data["samples"][0]["sha256"] = audit.digest(raw)
    assert "gallery_duplicate" in codes(run(collection))


@pytest.mark.parametrize("value", ["raw/../../outside.jpg", "raw/../q.jpg", "raw/x:stream", "raw/..\\outside.jpg"])
def test_path_escape_is_rejected(collection, value):
    collection[2]["samples"][0]["image_path"] = value
    assert "outside_raw" in codes(run(collection))


@pytest.mark.parametrize("mode,code", [("missing", "missing_file"), ("directory", "missing_file"),
                                     ("empty", "file_size"), ("changed", "checksum"), ("large", "file_size")])
def test_bad_local_files(collection, monkeypatch, mode, code):
    target = collection[0].parent / "raw/q1.jpg"
    if mode == "missing": target.unlink()
    elif mode == "directory": target.unlink(); target.mkdir()
    elif mode == "empty": target.write_bytes(b"")
    elif mode == "changed": target.write_bytes(b"changed")
    elif mode == "large": monkeypatch.setattr(audit, "MAX_BYTES", 2)
    assert code in codes(run(collection))


def test_catalog_hash_change_requires_review(collection):
    collection[2]["catalog_sha256"] = "0" * 64
    assert "catalog_changed" in codes(run(collection))


def test_rights_need_evidence(collection):
    collection[2]["samples"][0]["usage_rights"]["evidence"] = None
    assert "rights_evidence" in codes(run(collection))


def test_explicit_gallery_related_review_is_rejected(collection):
    collection[2]["samples"][0]["independence_review"]["independent"] = False
    assert "not_independent" in codes(run(collection))


def test_no_match_requires_full_gallery_judgments(collection):
    row = collection[2]["samples"][0]
    row["judgment"].update(has_answer=False, relevance={})
    assert "incomplete_no_match" in codes(run(collection))
    catalog = json.loads(collection[1].read_bytes())
    row["judgment"]["relevance"] = {p["id"]: 0 for p in catalog["products"] if p["status"] == "published"}
    assert run(collection)["status"] == "recorded_checks_passed"


@pytest.mark.parametrize("mode,code", [("hidden", "unknown_product"), ("bool", "schema"),
    ("float", "invalid_grade"), ("mismatch", "has_answer_mismatch"), ("sku", "exact_sku"),
    ("unexpected", "unexpected_exact_target"), ("missing_target", "exact_target"),
    ("text", "text_task"), ("timezone", "review_timestamp"), ("duplicate_qid", "duplicate_qid")])
def test_invalid_annotations(collection, mode, code):
    row = collection[2]["samples"][0]; j = row["judgment"]; pid = next(iter(j["relevance"]))
    if mode == "hidden": j["relevance"] = {"fx-ban-nhap": 3}
    elif mode == "bool": j["relevance"][pid] = True
    elif mode == "float": j["relevance"][pid] = 3.0
    elif mode == "mismatch": j["has_answer"] = False
    elif mode == "sku": row["task"] = "exact"; j.update(exact_product_id=pid, exact_variant_sku="wrong")
    elif mode == "unexpected": j["exact_product_id"] = pid
    elif mode == "missing_target": row["task"] = "exact"
    elif mode == "text": row["task"] = "image_text"
    elif mode == "timezone": j["reviewed_at"] = "2026-10-10T15:00:00"
    elif mode == "duplicate_qid": collection[2]["samples"].append(copy.deepcopy(row))
    assert code in codes(run(collection))


@pytest.mark.parametrize("stamp", ["2026-02-30T15:00:00+07:00", "not-a-date", "2026-10-10"])
def test_independence_review_timestamp_is_validated(collection, stamp):
    collection[2]["samples"][0]["independence_review"]["reviewed_at"] = stamp
    report = run(collection)
    assert report["status"] == "invalid"
    assert codes(report) & {"schema", "review_timestamp"}


def test_raw_directory_resolving_outside_manifest_is_rejected(collection, monkeypatch):
    # Portable simulation: creating real symlinks requires privileges on Windows.
    raw = collection[0].parent / "raw"
    original = Path.resolve
    def outside(path, *args, **kwargs):
        if path == raw:
            return collection[1].parent
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "resolve", outside)
    assert "outside_raw" in codes(run(collection))


def test_cli_persists_invalid_input_without_mutation(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"; path.write_text("{", encoding="utf-8")
    folder = tmp_path / "reports"
    monkeypatch.setattr("sys.argv", ["audit_image_queries.py", "--manifest", str(path), "--report-dir", str(folder)])
    assert audit.main() == 1
    reports = list(folder.glob("*.json")); assert len(reports) == 1
    assert reports[0].with_suffix(".md").exists()
    assert json.loads(reports[0].read_bytes())["status"] == "invalid"
    assert path.read_text(encoding="utf-8") == "{"
