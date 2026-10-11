"""Kế hoạch split theo họ (plan_splits.py): dữ liệu TỔNG HỢP, không ghi kế hoạch thật của dự án."""
import hashlib
import json

import pytest

from app.catalog.validation import REPO_ROOT
from test_family_registry import reviewed, registry  # noqa: F401  (fixture)
from test_image_query_audit import collection, codes, audit  # noqa: F401  (fixture)
import plan_splits as ps

RATIOS = {"train": 0.6, "dev": 0.2, "test": 0.2}


def synthetic(n_per_cat=10):
    products, mapping = [], {}
    for cat in ("cat-a", "cat-b"):
        for i in range(n_per_cat):
            pid = f"p-{cat}-{i}"
            products.append({"id": pid, "category_id": cat})
            mapping[pid] = f"fam-{cat}-{i // 2}"  # mỗi họ hai SKU
    catalog = {"catalog_version": "synthetic", "products": products}
    proposal = {"catalog_sha256": "c" * 64, "product_family": mapping,
                "shared_image_clusters": [{"images": ["x"], "products": ["p-cat-a-0", "p-cat-a-9"]}],
                "design_lines": [{"source": "s", "term": "moonbow", "products": ["p-cat-b-0", "p-cat-b-2", "p-cat-b-4"]}]}
    reg = {"status": "reviewed", "catalog_sha256": "c" * 64, "proposal_sha256": "b" * 64,
           "reviewed_by": "SYNTHETIC", "reviewed_at": "2026-10-11T09:00:00+07:00", "product_family": mapping,
           "families": [{"family_id": f, "products": sorted(p for p, x in mapping.items() if x == f)}
                        for f in sorted(set(mapping.values()))]}
    return catalog, proposal, reg


def plan(design_lines="all", registry_doc=None, proposal_sha="b" * 64, seed="s1"):
    catalog, proposal, reg = synthetic()
    return ps.propose(catalog, "c" * 64, proposal, proposal_sha, registry_doc if registry_doc is not None else reg,
                      "e" * 64, RATIOS, seed, design_lines)


def test_units_keep_shared_images_and_design_lines_together():
    p = plan()
    fs = p["family_split"]
    assert fs["fam-cat-a-0"] == fs["fam-cat-a-4"]  # ảnh gallery dùng chung
    assert fs["fam-cat-b-0"] == fs["fam-cat-b-1"] == fs["fam-cat-b-2"]  # cùng dòng thiết kế
    assert len(fs) == 10 and set(fs.values()) == {"train", "dev", "test"}
    assert p["status"] == "proposed" and p["source"]["sha256"] == "e" * 64 and p["locked_by"] is None
    assert sum(c["families"] for c in p["counts"].values()) == 10
    loose = plan(design_lines="none")
    assert loose["largest_unit"] == 2 and p["largest_unit"] == 3
    assert plan()["family_split"] == fs  # cố định theo seed
    assert any("design_line:s:moonbow" in u["reasons"] for u in p["units"])
    assert plan(design_lines="s:moonbow")["family_split"] == fs and plan()["params"]["design_lines"] == ["s:moonbow"]
    with pytest.raises(ValueError, match="không có trong proposal"):
        plan(design_lines="s:khong-co")


def test_balance_by_family_count_per_category():
    catalog = {"catalog_version": "x", "products": [{"id": f"p{i}", "category_id": "c"} for i in range(100)]}
    proposal = {"catalog_sha256": "c" * 64, "product_family": {f"p{i}": f"f{i}" for i in range(100)},
                "shared_image_clusters": [], "design_lines": []}
    p = ps.propose(catalog, "c" * 64, proposal, "b" * 64, None, None, RATIOS, "s")
    assert p["status"] == "preview_unreviewed"
    assert {s: c["families"] for s, c in p["counts"].items()} == {"train": 60, "dev": 20, "test": 20}


def test_registry_must_match_proposal_and_catalog():
    catalog, proposal, reg = synthetic()
    with pytest.raises(ValueError, match="proposal khác"):
        plan(proposal_sha="f" * 64)
    with pytest.raises(ValueError, match="catalog khác"):
        ps.propose(catalog, "d" * 64, proposal, "b" * 64, reg, "e" * 64, RATIOS, "s", "all")
    with pytest.raises(ValueError):
        plan(registry_doc={**reg, "status": "proposed_unreviewed"})


def test_lock_only_reviewed_unchanged_plans():
    p = plan()
    with pytest.raises(ValueError, match="preview"):
        ps.lock({**p, "status": "preview_unreviewed"}, "Người khóa", "c" * 64, "b" * 64, "e" * 64)
    with pytest.raises(ValueError, match="đã đổi"):
        ps.lock(p, "Người khóa", "c" * 64, "b" * 64, "9" * 64)
    with pytest.raises(ValueError, match="locked-by"):
        ps.lock(p, "  ", "c" * 64, "b" * 64, "e" * 64)
    locked = ps.lock(p, " Người khóa ", "c" * 64, "b" * 64, "e" * 64)
    assert locked["status"] == "locked" and locked["locked_by"] == "Người khóa" and locked["locked_at"]
    assert ps.validate_plan(locked, "c" * 64, "e" * 64) == p["family_split"]
    with pytest.raises(ValueError, match="trạng thái proposed"):
        ps.validate_plan(p, "c" * 64)
    assert ps.validate_plan(p, "c" * 64, allow_proposed=True)
    for bad, msg in (({**locked, "catalog_sha256": "d" * 64}, "catalog khác"),
                     ({**locked, "locked_by": None}, "locked_by"),
                     ({**locked, "family_split": {"f": "val"}}, "family_split")):
        with pytest.raises(ValueError, match=msg):
            ps.validate_plan(bad, "c" * 64)
    with pytest.raises(ValueError, match="families.json khác"):
        ps.validate_plan(locked, "c" * 64, "8" * 64)


def write_plan(reviewed, status, split_for_row):  # noqa: F811
    (manifest, catalog, data), reg_path, reg = reviewed
    fam = data["samples"][0]["family_id"]
    split_map = {f: "train" for f in set(reg["product_family"].values())}
    split_map[fam] = split_for_row
    doc = {"kind": "image_family_split_plan", "status": status, "catalog_sha256": reg["catalog_sha256"],
           "source": {"kind": "family_registry", "sha256": hashlib.sha256(reg_path.read_bytes()).hexdigest()},
           "family_split": split_map, "locked_by": "SYNTHETIC" if status == "locked" else None}
    path = manifest.parent / "split_plan.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    manifest.write_text(json.dumps(data), encoding="utf-8")
    return manifest, catalog, reg_path, path


def test_audit_enforces_planned_split(reviewed):  # noqa: F811
    manifest, catalog, reg_path, plan_path = write_plan(reviewed, "locked", "dev")
    report = audit.audit(manifest, catalog, reg_path, True, plan_path)
    assert report["status"] == "recorded_checks_passed"
    assert report["split_plan"]["status"] == "locked" and report["split_plan"]["sha256"]
    manifest, catalog, reg_path, plan_path = write_plan(reviewed, "locked", "test")
    assert "split_plan_mismatch" in codes(audit.audit(manifest, catalog, reg_path, True, plan_path))
    manifest, catalog, reg_path, plan_path = write_plan(reviewed, "proposed", "dev")
    report = audit.audit(manifest, catalog, reg_path, True, plan_path)
    assert report["status"] == "recorded_checks_passed" and "split_plan_not_locked" in codes(report)
    manifest, catalog, reg_path, plan_path = write_plan(reviewed, "preview_unreviewed", "dev")
    assert "split_plan_invalid" in codes(audit.audit(manifest, catalog, reg_path, True, plan_path))
    assert "split_plan_needs_registry" in codes(audit.audit(manifest, catalog, None, False, plan_path))


def test_cli_preview_from_repo_proposal_does_not_overwrite(tmp_path):
    out = tmp_path / "plan.json"
    assert ps.main(["propose", "--preview", "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    proposal = json.loads((REPO_ROOT / "benchmarks/families/proposal.json").read_text(encoding="utf-8"))
    assert doc["status"] == "preview_unreviewed" and set(doc["family_split"]) == set(proposal["product_family"].values())
    assert out.with_suffix(".md").is_file()
    before = out.read_bytes()
    assert ps.main(["propose", "--preview", "--out", str(out)]) == 1
    assert out.read_bytes() == before
    assert ps.main(["lock", str(out), "--locked-by", "x", "--families", str(tmp_path / "khong-co.json")]) == 1
