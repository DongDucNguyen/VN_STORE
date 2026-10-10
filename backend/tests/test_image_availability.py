import json
from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

import app.main as api
from app.catalog.present import product_detail, product_summary
from app.catalog.store import load_snapshot
from app.catalog.validation import REPO_ROOT
from conftest import FIXTURE


@pytest.fixture()
def local_catalog(tmp_path):
    shutil.copytree(FIXTURE.parent / "assets", tmp_path / "assets")
    path = tmp_path / "database.json"
    path.write_bytes(FIXTURE.read_bytes())
    return path


def test_missing_cover_uses_next_file_without_mutating_snapshot(local_catalog):
    snap = load_snapshot(local_catalog)
    p = next(iter(snap.products.values()))
    before = json.dumps(snap.data, ensure_ascii=False)
    (snap.base_dir / p["images"][0]["local_path"]).unlink()
    summary = product_summary(snap, p)
    detail = product_detail(snap, p)
    assert summary["image"]["id"] == p["images"][1]["id"]
    assert [im["id"] for im in detail["images"]] == [p["images"][1]["id"]]
    assert detail["images_missing_file"] == 1
    assert json.dumps(snap.data, ensure_ascii=False) == before


def test_all_files_disappear_then_restore(local_catalog):
    snap = load_snapshot(local_catalog)
    p = next(iter(snap.products.values()))
    files = [(snap.base_dir / im["local_path"]) for im in p["images"]]
    original = files[0].read_bytes()
    for path in files:
        path.unlink()
    detail = product_detail(snap, p)
    assert detail["image"] is None and detail["images"] == []
    assert detail["images_missing_file"] == len(files)
    files[0].write_bytes(original)
    assert product_summary(snap, p)["image"]["id"] == p["images"][0]["id"]


def test_file_becomes_empty_is_not_listed(local_catalog):
    snap = load_snapshot(local_catalog)
    p = next(iter(snap.products.values()))
    (snap.base_dir / p["images"][0]["local_path"]).write_bytes(b"")
    assert snap.image_path(p["images"][0]["id"]) is None
    assert product_detail(snap, p)["images_missing_file"] == 1


def test_file_replaced_by_directory_is_not_listed(local_catalog):
    snap = load_snapshot(local_catalog)
    p = next(iter(snap.products.values()))
    target = snap.base_dir / p["images"][0]["local_path"]
    target.unlink()
    target.mkdir()
    assert snap.image_path(p["images"][0]["id"]) is None
    assert product_summary(snap, p)["image"]["id"] == p["images"][1]["id"]


def test_file_stat_denied_does_not_break_product(local_catalog, monkeypatch):
    snap = load_snapshot(local_catalog)
    p = next(iter(snap.products.values()))
    target = (snap.base_dir / p["images"][0]["local_path"]).resolve()
    original = Path.stat

    def denied(path, *args, **kwargs):
        if path == target:
            raise PermissionError("Simulated access denial")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", denied)
    assert product_summary(snap, p)["image"]["id"] == p["images"][1]["id"]


@pytest.mark.parametrize("replacement", ["../outside.svg", "/outside.svg"])
def test_runtime_path_escape_stays_hidden(local_catalog, replacement):
    snap = load_snapshot(local_catalog)
    p = next(iter(snap.products.values()))
    p["images"][0]["local_path"] = replacement
    assert snap.image_path(p["images"][0]["id"]) is None


def test_draft_missing_and_url_only_images_count_separately_from_rights(local_catalog):
    data = json.loads(local_catalog.read_bytes())
    p = data["products"][0]
    p.update(status="draft", reviewed_at=None)
    p["images"][0].update(local_path="assets/absent.svg")
    p["images"][1].update(local_path=None, source_url="https://example.com/image.png")
    p["images"][1]["usage_rights"]["status"] = "unknown"
    local_catalog.write_text(json.dumps(data), encoding="utf-8")
    snap = load_snapshot(local_catalog, include_drafts=True)
    detail = product_detail(snap, snap.products[p["id"]])
    assert detail["image"] is None and detail["images"] == []
    assert detail["images_missing_file"] == 2
    assert detail["images_pending_rights"] == 1


def test_api_uses_fallback_after_snapshot_load(local_catalog, monkeypatch):
    monkeypatch.setenv("VNSTORE_CATALOG", str(local_catalog))
    monkeypatch.setattr(api.state, "bundle", None)
    monkeypatch.setattr(api.state, "error", None)
    with TestClient(api.app) as client:
        p = next(iter(api.state.bundle.snap.products.values()))
        image = p["images"][0]
        (local_catalog.parent / image["local_path"]).unlink()
        response = client.get("/products/" + p["id"])
        assert response.status_code == 200
        assert response.json()["image"]["id"] == p["images"][1]["id"]
        assert client.get("/images/" + image["id"]).status_code == 404
        listed = client.get("/products").json()["results"]
        assert next(row for row in listed if row["id"] == p["id"])["image"]["id"] == p["images"][1]["id"]


def test_review_packet_uses_existing_alternative(local_catalog, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO_ROOT / "scripts/benchmark"))
    from prepare_review import make_packet
    snap = load_snapshot(local_catalog)
    p = next(iter(snap.products.values()))
    (snap.base_dir / p["images"][0]["local_path"]).unlink()
    queries = [{"qid": "q1", "query": "test", "split": "dev", "has_answer": False,
                "verified": False, "labeled_by": "synthetic", "relevance": {}}]
    packet = make_packet(queries, snap, tmp_path)
    row = next(item for item in packet["products"] if item["id"] == p["id"])
    assert row["image"].endswith(Path(p["images"][1]["local_path"]).name)
