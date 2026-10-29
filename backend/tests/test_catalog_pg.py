"""Catalog trong PostgreSQL: nhập fixture, đọc lại không mất dữ liệu, API phục vụ từ DB. Cần VNSTORE_TEST_DATABASE_URL."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.catalog.pg import import_catalog, read_catalog
from app.catalog.store import CatalogError, load_snapshot_from_db
from app.db import connect
from tests.conftest import BACKEND, FIXTURE, reset_pg


@pytest.fixture()
def pg_catalog():
    url = reset_pg("catalog")
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with connect(url) as conn:
        import_catalog(conn, data, FIXTURE.name)
    return url, data


def test_round_trip_is_lossless(pg_catalog):
    url, data = pg_catalog
    with connect(url) as conn:
        assert read_catalog(conn) == data
        # Nhập lại thay toàn bộ, không nhân đôi.
        import_catalog(conn, data)
        assert conn.execute("SELECT count(*) FROM catalog.products").fetchone()[0] == len(data["products"])


def test_snapshot_from_db_matches_file(pg_catalog, snap):
    url, _ = pg_catalog
    db = load_snapshot_from_db(url, FIXTURE.parent)
    assert db.source == "postgresql" and db.data == snap.data
    assert db.products.keys() == snap.products.keys()
    assert all(db.image_path(i) == snap.image_path(i) for i in snap.images)


def test_empty_database_is_catalog_error():
    url = reset_pg("catalog")
    with pytest.raises(CatalogError, match="import_json"):
        load_snapshot_from_db(url, BACKEND)


def test_api_reads_catalog_from_db(pg_catalog, monkeypatch):
    url, data = pg_catalog
    monkeypatch.delenv("VNSTORE_CATALOG")
    monkeypatch.setenv("VNSTORE_DATABASE_URL", url)
    monkeypatch.setenv("VNSTORE_ASSETS_DIR", str(FIXTURE.parent))
    monkeypatch.setenv("VNSTORE_ASSISTANT_DB", ":memory:")
    with connect(url) as conn, conn.transaction():
        # Sửa trong DB phải hiện ra ở API, chứng tỏ API không còn đọc file.
        conn.execute("UPDATE catalog.products SET name_vi = 'Tên sửa trong DB' WHERE id = %s",
                     (data["products"][0]["id"],))
    from app.main import app
    with TestClient(app) as c:
        h = c.get("/health").json()
        assert h["status"] == "ok" and h["catalog"]["source"] == "postgresql"
        p = c.get(f"/products/{data['products'][0]['id']}")
        assert p.status_code == 200 and p.json()["name_vi"] == "Tên sửa trong DB"
        assert c.post("/search", json={"query": "Tên sửa trong DB"}).json()["results"]
