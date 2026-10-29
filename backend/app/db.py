"""Kết nối PostgreSQL dùng chung cho catalog và trợ lý.

VNSTORE_DATABASE_URL, ví dụ postgresql://vnstore:matkhau@127.0.0.1:5432/vnstore. Không đặt → catalog đọc
database.json và trợ lý dùng SQLite như trước. psycopg chỉ được nạp khi thật sự dùng PostgreSQL.
"""
from __future__ import annotations

import os
from typing import Any


def database_url() -> str | None:
    return os.environ.get("VNSTORE_DATABASE_URL") or None


def is_postgres_url(value: str | None) -> bool:
    return bool(value) and value.split(":", 1)[0] in ("postgresql", "postgres")


def connect(url: str, **kwargs: Any):
    try:
        import psycopg
    except ImportError as e:  # pragma: no cover — chỉ khi thiếu gói
        raise RuntimeError("Thiếu psycopg; cài: pip install -r backend/requirements.txt") from e
    return psycopg.connect(url, **kwargs)
