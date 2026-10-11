"""Synthetic registry/query reviews only; never writes reviewed project data."""
import copy
import hashlib
import json
import zipfile

import pytest

from test_image_query_audit import collection, second_sample, codes, audit, STAMP
from test_voice_image_benchmark import image_manifest, judgment
from conftest import FIXTURE
import family_registry as fr
import eval_image as ei
import import_image_session as importer
import apply_image_judgments as apply_judgments
import compare_runs as compare


def registry(catalog, path):
    products = json.loads(catalog.read_bytes())["products"]
    mapping = {p["id"]: "fam-" + p["id"] for p in products}
    siblings = [p["id"] for p in products[:2]]
    mapping[siblings[1]] = mapping[siblings[0]]
    data = {"status": "reviewed", "catalog_sha256": hashlib.sha256(catalog.read_bytes()).hexdigest(),
            "proposal_sha256": "a" * 64, "reviewed_by": "SYNTHETIC", "reviewed_at": STAMP,
            "product_family": mapping, "families": [{"family_id": mapping[siblings[0]], "products": siblings}]}
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def family_review(product_id):
    return {"product_id": product_id, "reviewed_by": "SYNTHETIC", "reviewed_at": STAMP,
            "note": "Synthetic object identity, not relevance inference"}


@pytest.fixture()
def reviewed(collection):
    manifest, catalog, data = collection
    path = manifest.parent / "families.json"
    reg = registry(catalog, path)
    row = data["samples"][0]
    pid = next(iter(reg["product_family"]))
    row["family_id"] = reg["product_family"][pid]
    row["family_review"] = family_review(pid)
    return collection, path, reg


def run(reviewed):
    (manifest, catalog, data), path, _ = reviewed
    manifest.write_text(json.dumps(data), encoding="utf-8")
    return audit.audit(manifest, catalog, path, require_families=True)


def test_reviewed_registry_is_hashed_and_inputs_unchanged(reviewed):
    before = reviewed[1].read_bytes()
    report = run(reviewed)
    assert report["status"] == "recorded_checks_passed"
    assert report["family_registry"]["sha256"] == hashlib.sha256(before).hexdigest()
    assert not report["benchmark_approved"]
    assert reviewed[1].read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("status", "proposed_unreviewed"), ("catalog_sha256", "f" * 64),
    ("proposal_sha256", "invalid"), ("reviewed_by", " "), ("reviewed_by", []),
    ("reviewed_at", "2026-10-11T12:00:00"), ("reviewed_at", True),
    ("product_family", {}), ("families", []), ("families", [None]),
])
def test_invalid_registry_rejected(reviewed, field, value):
    reviewed[2][field] = value
    reviewed[1].write_text(json.dumps(reviewed[2]), encoding="utf-8")
    assert "family_registry_invalid" in codes(run(reviewed))


def test_registry_rejects_external_namespace_and_extra_product(reviewed):
    reg = reviewed[2]
    pid = next(iter(reg["product_family"]))
    for mapping in ({**reg["product_family"], pid: "external-x"}, {**reg["product_family"], "unknown": "fam-x"}):
        with pytest.raises(ValueError):
            fr.validate_registry({**reg, "product_family": mapping}, reg["catalog_sha256"], set(reg["product_family"]))


def test_sibling_skus_cannot_cross_split_with_renamed_family(reviewed):
    coll, _, reg = reviewed
    other = second_sample(coll)
    siblings = reg["families"][0]["products"]
    for row, pid in zip(coll[2]["samples"], siblings):
        row.update(task="exact", family_id="renamed-" + row["qid"])
        row.pop("family_review", None)
        row["judgment"] = judgment({pid: 3}, pid)
    report = run(reviewed)
    assert {"family_mismatch", "split_leakage"} <= codes(report)
    assert any("registry_family" in i["message"] for i in report["issues"])
    # Correct spelling still cannot put the same canonical family in two splits.
    for row in coll[2]["samples"]:
        row["family_id"] = reg["product_family"][siblings[0]]
    assert "split_leakage" in codes(run(reviewed))
    other["split"] = "dev"
    assert run(reviewed)["status"] == "recorded_checks_passed"


def test_exact_target_and_family_review_must_agree(reviewed):
    row = reviewed[0][2]["samples"][0]
    row["task"] = "exact"
    row["judgment"]["exact_product_id"] = next(iter(row["judgment"]["relevance"]))
    row["family_review"]["product_id"] = reviewed[2]["families"][0]["products"][1]
    assert "family_mismatch" in codes(run(reviewed))


@pytest.mark.parametrize("task", ["similar", "image_text"])
def test_relevance_is_not_used_to_guess_object_family(reviewed, task):
    row = reviewed[0][2]["samples"][0]
    row.update(task=task, text_vi="synthetic" if task == "image_text" else None)
    row.pop("family_review")
    report = run(reviewed)
    assert report["status"] == "pending_review"
    assert report["family_registry"]["pending_qids"] == ["q1"]
    # No changes to identity based on the positive relevance label.
    row["family_review"] = family_review(None)
    row["family_id"] = "external-basket-1"
    assert run(reviewed)["status"] == "recorded_checks_passed"


def test_no_match_can_depict_catalog_object_excluded_by_text(reviewed):
    row = reviewed[0][2]["samples"][0]
    row.update(task="image_text", text_vi="unavailable color")
    products = json.loads(reviewed[0][1].read_bytes())["products"]
    row["judgment"] = judgment({p["id"]: 0 for p in products if p["status"] == "published"})
    assert run(reviewed)["status"] == "recorded_checks_passed"
    row["family_review"] = family_review(None)
    assert "family_mismatch" in codes(run(reviewed))
    row["family_id"] = "external-object-1"
    assert run(reviewed)["status"] == "recorded_checks_passed"


def test_explicit_registry_requirement_and_missing_path(reviewed):
    run(reviewed)
    manifest, catalog, data = reviewed[0]
    assert "family_registry_required" in codes(audit.audit(manifest, catalog, require_families=True))
    assert audit.audit(manifest, catalog, manifest.parent / "missing.json")["status"] == "invalid"
    data["samples"] = []
    manifest.write_text(json.dumps(data), encoding="utf-8")
    assert audit.audit(manifest, catalog, require_families=True)["status"] == "pending_collection"


def test_import_rolls_back_on_family_mismatch(reviewed, tmp_path):
    (manifest, catalog, data), families, reg = reviewed
    row = copy.deepcopy(data["samples"][0])
    row.update(qid="new", image_path="raw/new.jpg", family_id="wrong-family")
    source = manifest.parent / "raw/q1.jpg"
    archive = tmp_path / "session.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("samples.json", json.dumps({"samples": [row]}))
        z.writestr(row["image_path"], source.read_bytes())
    data["samples"] = []
    manifest.write_text(json.dumps(data), encoding="utf-8")
    before = manifest.read_bytes()
    assert importer.main([str(archive), "--manifest", str(manifest), "--catalog", str(catalog),
                          "--families", str(families)]) == 1
    assert manifest.read_bytes() == before
    assert not (manifest.parent / row["image_path"]).exists()


def test_apply_family_review_preserves_other_fields_and_rejects_mismatch(reviewed, tmp_path):
    run(reviewed)
    (manifest, catalog, data), families, _ = reviewed
    row = data["samples"][0]
    export = {"kind": "image_judgment_export", "catalog_sha256": data["catalog_sha256"],
              "items": [{"qid": row["qid"], "sha256": row["sha256"], "family_review": family_review(None)}]}
    source = tmp_path / "review.json"
    source.write_text(json.dumps(export), encoding="utf-8")
    before = manifest.read_bytes()
    assert apply_judgments.main([str(source), "--manifest", str(manifest), "--catalog", str(catalog),
                                "--families", str(families), "--replace-judged"]) == 1
    assert manifest.read_bytes() == before


def test_evaluator_requires_registry_before_loading_model(reviewed, tmp_path, monkeypatch):
    run(reviewed)
    manifest, catalog, _ = reviewed[0]
    monkeypatch.setattr(ei, "load_adapter", lambda *a: pytest.fail("must not load model"))
    args = ["--adapter", "tests.fakes:ByteHistogramEmbedder", "--manifest", str(manifest),
            "--catalog", str(catalog), "--split", "dev", "--out-root", str(tmp_path / "runs")]
    assert ei.main(args) == 1
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("split,expected", [("dev", 0), ("test", 1)])
def test_pending_family_review_is_not_evaluated(reviewed, tmp_path, monkeypatch, split, expected):
    (manifest, catalog, data), families, _ = reviewed
    row = data["samples"][0]
    row.pop("family_review")
    row["split"] = split
    run(reviewed)
    monkeypatch.setattr(ei, "load_adapter", lambda *a: pytest.fail("must not load model"))
    out = tmp_path / "runs"
    assert ei.main(["--adapter", "tests.fakes:ByteHistogramEmbedder", "--manifest", str(manifest),
                    "--catalog", str(catalog), "--split", split, "--families", str(families),
                    "--out-root", str(out), "--confirm-locked-test"]) == expected
    assert not out.exists()


def test_apply_new_family_review_to_existing_manifest(reviewed, tmp_path):
    (manifest, catalog, data), families, _ = reviewed
    row = data["samples"][0]
    review = row.pop("family_review")
    run(reviewed)
    source = tmp_path / "review.json"
    source.write_text(json.dumps({"kind": "image_judgment_export", "catalog_sha256": data["catalog_sha256"],
        "items": [{"qid": row["qid"], "sha256": row["sha256"], "family_review": review}]}), encoding="utf-8")
    assert apply_judgments.main([str(source), "--manifest", str(manifest), "--catalog", str(catalog),
                                "--families", str(families)]) == 0
    actual = json.loads(manifest.read_bytes())["samples"][0]
    assert actual.pop("family_review") == review and actual == row


@pytest.mark.parametrize("mutation", [None, "change", "delete"])
def test_formal_fake_run_records_registry_hash(tmp_path, monkeypatch, mutation):
    pid = "fx-gio-may-co-quai"
    manifest = image_manifest(tmp_path, [("exact", "exact", None, judgment({pid: 3}, pid))])
    families = tmp_path / "families.json"
    reg = registry(FIXTURE, families)
    data = json.loads(manifest.read_bytes())
    row = data["samples"][0]
    row.update(family_id=reg["product_family"][pid],
               usage_rights={"status": "owned", "evidence": "SYNTHETIC"},
               independence_review={"independent": True, "reviewed_by": "SYNTHETIC", "reviewed_at": STAMP, "note": "SYNTHETIC"})
    manifest.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(ei.lp, "gpu_status", lambda: None)
    monkeypatch.setattr(ei.lp, "_nvidia_smi", lambda: None)
    if mutation:
        original = ei.evaluate
        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            if mutation == "delete":
                families.unlink()
            else:
                families.write_text("{}", encoding="utf-8")
            return result
        monkeypatch.setattr(ei, "evaluate", mutate)
    out = tmp_path / "runs"
    code = ei.main(["--adapter", "tests.fakes:ByteHistogramEmbedder", "--manifest", str(manifest),
                    "--catalog", str(FIXTURE), "--split", "dev", "--families", str(families),
                    "--out-root", str(out), "--latency-rounds", "1"])
    if mutation:
        assert code == 1 and not out.exists()
        return
    assert code == 0
    result = json.loads(next(out.glob("*/run.json")).read_bytes())
    assert result["family_registry_sha256"] == hashlib.sha256(families.read_bytes()).hexdigest()
    assert result["evaluation_status"] == "dev" and result["benchmark_approved"] is False


@pytest.mark.parametrize("key", ["family_registry_sha256", "family_grouping_policy"])
def test_compare_rejects_different_registry_or_policy(key):
    meta = {"manifest_sha256": "same", "split": "dev", key: "left"}
    rows = [{"qid": "q", "family_id": "fam-a", "recall_1": 1}]
    with pytest.raises(compare.Incomparable, match=key):
        compare.compare((meta, rows), ({**meta, key: "right"}, rows))
