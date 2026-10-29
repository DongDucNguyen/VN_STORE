"""Đưa dữ liệu vào PostgreSQL: catalog từ database.json, và (tùy chọn) dữ liệu trợ lý cũ từ SQLite.

    set VNSTORE_DATABASE_URL=postgresql://vnstore:matkhau@127.0.0.1:5432/vnstore
    .venv/Scripts/python -X utf8 scripts/db/import_json.py                      # catalog
    .venv/Scripts/python -X utf8 scripts/db/import_json.py --assistant-sqlite var/assistant/assistant.db
    .venv/Scripts/python -X utf8 scripts/db/import_json.py --export out.json    # DB → JSON cho script offline

Catalog được validate như khi API nạp file; có lỗi thì không ghi gì. Nhập lại thay toàn bộ catalog trong một giao dịch,
rồi đọc ngược từ DB và so với file để chắc chắn không mất dữ liệu. Dữ liệu trợ lý chỉ thêm dòng chưa có (giữ id cũ),
chạy lại không nhân đôi. Mã thoát 1 nếu lỗi.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.assistant.store import SERIAL_TABLES, Store  # noqa: E402
from app.catalog.pg import content_sha256, import_catalog, read_catalog  # noqa: E402
from app.catalog.validation import validate_catalog  # noqa: E402
from app.db import connect, database_url, is_postgres_url  # noqa: E402

# Cha trước con để khóa ngoại hợp lệ.
ASSISTANT_TABLES = ("customers", "sessions", "messages", "recommendations", "memory_facts", "grounding_events",
                    "turn_metrics", "deletion_log", "reviews")


def import_catalog_file(url: str, path: Path) -> int:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    result = validate_catalog(data, path.resolve().parent)
    if not result.ok:
        print(f"Catalog {path} có {len(result.errors)} lỗi, không nhập:")
        for issue in result.errors[:20]:
            print("  ", issue)
        return 1
    with connect(url) as conn:
        counts = import_catalog(conn, data, path.name, hashlib.sha256(raw).hexdigest())
        back = read_catalog(conn)
    if back != data:
        print("LỖI: dữ liệu đọc lại từ DB khác file; catalog đã ghi nhưng cần kiểm tra lại pg.py")
        return 1
    print(f"Catalog {data['catalog_version']} → PostgreSQL ({len(result.warnings)} cảnh báo validate). "
          f"Đọc lại khớp file, sha256 nội dung {content_sha256(data)[:12]}.")
    for table, n in counts.items():
        print(f"  catalog.{table:<22} {n}")
    return 0


def import_assistant_sqlite(url: str, path: Path) -> int:
    if not path.is_file():
        print(f"Không thấy {path}")
        return 1
    Store(url).close()  # dựng schema assistant nếu chưa có
    src = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    with connect(url) as conn, conn.transaction():
        for table in ASSISTANT_TABLES:
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
            if rows:
                cols = rows[0].keys()
                with conn.cursor() as cur:
                    cur.executemany(f"INSERT INTO assistant.{table} ({', '.join(cols)}) VALUES "
                                    f"({', '.join(['%s'] * len(cols))}) ON CONFLICT DO NOTHING",
                                    [tuple(r) for r in rows])
                    added = cur.rowcount
            else:
                added = 0
            if table in SERIAL_TABLES:
                # Id giữ từ SQLite; dời bộ đếm để dòng mới không trùng.
                conn.execute(f"SELECT setval(pg_get_serial_sequence('assistant.{table}', 'id'), "
                             f"COALESCE((SELECT MAX(id) FROM assistant.{table}), 0) + 1, false)")
            print(f"  assistant.{table:<18} {len(rows)} dòng trong SQLite, thêm {max(added, 0)}")
    src.close()
    return 0


def export_catalog(url: str, out: Path) -> int:
    with connect(url) as conn:
        data = read_catalog(conn)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã ghi {out} ({len(data['products'])} sản phẩm, catalog {data['catalog_version']})")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=database_url(), help="mặc định VNSTORE_DATABASE_URL")
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--skip-catalog", action="store_true", help="không nhập catalog")
    ap.add_argument("--assistant-sqlite", type=Path, help="chuyển dữ liệu trợ lý từ file SQLite này")
    ap.add_argument("--export", type=Path, help="ghi catalog trong DB ra file JSON rồi thoát")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if not is_postgres_url(args.url):
        print("Cần URL PostgreSQL: --url hoặc VNSTORE_DATABASE_URL (postgresql://user:pass@host:5432/db)")
        return 1
    if args.export:
        return export_catalog(args.url, args.export)
    code = 0 if args.skip_catalog else import_catalog_file(args.url, args.catalog)
    if code == 0 and args.assistant_sqlite:
        print(f"Dữ liệu trợ lý từ {args.assistant_sqlite}:")
        code = import_assistant_sqlite(args.url, args.assistant_sqlite)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
