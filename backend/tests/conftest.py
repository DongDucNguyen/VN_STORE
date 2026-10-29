import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FIXTURE = BACKEND / "tests" / "fixtures" / "catalog.fixture.json"
sys.path.insert(0, str(BACKEND))
os.environ["VNSTORE_CATALOG"] = str(FIXTURE)
os.environ.setdefault("VNSTORE_ASSISTANT_DB", ":memory:")
os.environ.pop("VNSTORE_DATABASE_URL", None)
# PostgreSQL RIÊNG cho test (test xóa và dựng lại schema catalog/assistant); không đặt → bỏ qua các test PostgreSQL.
PG_TEST_URL = os.environ.get("VNSTORE_TEST_DATABASE_URL")

from app.catalog.store import load_snapshot  # noqa: E402
from app.search.engine import SearchEngine  # noqa: E402


@pytest.fixture(scope="session")
def snap():
    return load_snapshot(FIXTURE)


@pytest.fixture(scope="session")
def engine(snap):
    return SearchEngine(snap)


def reset_pg(*schemas: str) -> str:
    """URL PostgreSQL test với các schema đã xóa sạch; skip nếu chưa cấu hình."""
    if not PG_TEST_URL:
        pytest.skip("đặt VNSTORE_TEST_DATABASE_URL để chạy test PostgreSQL")
    import psycopg
    with psycopg.connect(PG_TEST_URL, autocommit=True) as conn:
        for schema in schemas:
            conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    return PG_TEST_URL


def store_path(backend: str) -> str:
    return ":memory:" if backend == "sqlite" else reset_pg("assistant")
