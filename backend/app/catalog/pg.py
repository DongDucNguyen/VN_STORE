"""Catalog trong PostgreSQL (schema `catalog`): nhập từ database.json và dựng lại đúng dạng dict đó để validate/snapshot.

Mỗi thực thể một bảng, danh sách giữ thứ tự bằng cột `position`. Đối tượng con nhỏ, thưa (kích thước, quyền ảnh,
thuộc tính biến thể...) để ở JSONB. Cột `omitted` ghi các khóa mà bản ghi gốc không có, để phân biệt "không có khóa"
với "có khóa, giá trị null" khi dựng lại. Thời điểm lưu timestamptz, xuất lại theo giờ Việt Nam (+07:00) như file gốc.
Catalog là dữ liệu nhập: mỗi lần nhập dựng lại cả schema `catalog` trong một giao dịch.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta, timezone
from typing import Any

VN_TZ = timezone(timedelta(hours=7))

SCHEMA_SQL = """
CREATE SCHEMA catalog;

CREATE TABLE catalog.meta (
  id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  schema_version text NOT NULL,
  catalog_version text NOT NULL,
  locale text NOT NULL,
  currency text NOT NULL,
  updated_at timestamptz NOT NULL,
  publication_policy jsonb,
  imported_from text,
  imported_sha256 text,
  imported_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE catalog.categories (
  id text PRIMARY KEY,
  position integer NOT NULL,
  name_vi text NOT NULL,
  parent_id text REFERENCES catalog.categories(id) DEFERRABLE INITIALLY DEFERRED,
  aliases text[],
  description_vi text,
  omitted text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE catalog.sources (
  id text PRIMARY KEY,
  position integer NOT NULL,
  url text,
  title text,
  publisher text NOT NULL,
  source_type text NOT NULL,
  retrieved_at timestamptz NOT NULL,
  usage_rights_note text,
  supports text[],
  archived_copy_path text,
  omitted text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE catalog.places (
  id text PRIMARY KEY,
  position integer NOT NULL,
  place_type text NOT NULL,
  name_as_sourced text NOT NULL,
  name_normalized text NOT NULL,
  aliases text[],
  parent_id text REFERENCES catalog.places(id) DEFERRABLE INITIALLY DEFERRED,
  admin_code text,
  admin_code_scheme text,
  historical_names jsonb,
  verified_at date,
  source_ids text[] NOT NULL,
  omitted text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE catalog.brands (
  id text PRIMARY KEY,
  position integer NOT NULL,
  name text NOT NULL,
  aliases jsonb,
  official_url text,
  origin_country text,
  origin_source_ids text[],
  place_ids text[],
  source_ids text[] NOT NULL,
  omitted text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE catalog.makers (
  id text PRIMARY KEY,
  position integer NOT NULL,
  name text NOT NULL,
  maker_type text NOT NULL,
  aliases jsonb,
  brand_ids text[],
  place_ids text[],
  official_url text,
  source_ids text[] NOT NULL,
  omitted text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE catalog.products (
  id text PRIMARY KEY,
  position integer NOT NULL,
  slug text NOT NULL UNIQUE,
  name_vi text NOT NULL,
  status text NOT NULL CHECK (status IN ('draft', 'published', 'archived')),
  category_id text NOT NULL REFERENCES catalog.categories(id),
  brand_id text REFERENCES catalog.brands(id),
  maker_id text REFERENCES catalog.makers(id),
  short_description_vi text NOT NULL,
  description_vi text,
  aliases text[],
  tags text[],
  intended_uses text[],
  materials text[],
  colors text[],
  dimensions jsonb,
  craft_techniques text[],
  motifs text[],
  brand_origin_country text,
  manufacturing_country text,
  material_origins jsonb NOT NULL,
  origin_place_ids text[] NOT NULL,
  craft_village_id text REFERENCES catalog.places(id),
  certifications jsonb,
  source_ids text[] NOT NULL,
  editor_note text,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  reviewed_at timestamptz,
  omitted text[] NOT NULL DEFAULT '{}'
);
CREATE INDEX products_status ON catalog.products(status);
CREATE INDEX products_category ON catalog.products(category_id);

CREATE TABLE catalog.product_variants (
  product_id text NOT NULL REFERENCES catalog.products(id) ON DELETE CASCADE,
  position integer NOT NULL,
  sku text NOT NULL,
  name_vi text,
  attributes jsonb,
  price_vnd bigint CHECK (price_vnd > 0),
  original_price_vnd bigint CHECK (original_price_vnd > 0),
  price_source_id text,
  observed_at date,
  availability text NOT NULL CHECK (availability IN ('in_stock', 'out_of_stock', 'unknown')),
  omitted text[] NOT NULL DEFAULT '{}',
  PRIMARY KEY (product_id, sku)
);

CREATE TABLE catalog.product_images (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES catalog.products(id) ON DELETE CASCADE,
  position integer NOT NULL,
  local_path text,
  source_url text,
  alt_vi text NOT NULL,
  view_type text NOT NULL,
  variant_sku text,
  sha256 text,
  usage_rights jsonb NOT NULL,
  width integer,
  height integer,
  omitted text[] NOT NULL DEFAULT '{}'
);
CREATE INDEX product_images_product ON catalog.product_images(product_id, position);

CREATE TABLE catalog.product_origin_claims (
  product_id text NOT NULL REFERENCES catalog.products(id) ON DELETE CASCADE,
  position integer NOT NULL,
  claim_type text NOT NULL,
  value text NOT NULL CHECK (value IN ('true', 'false', 'unknown')),
  detail_vi text,
  place_ids text[],
  status text NOT NULL,
  source_ids text[] NOT NULL,
  checked_at date,
  note text,
  omitted text[] NOT NULL DEFAULT '{}',
  PRIMARY KEY (product_id, position)
);

CREATE TABLE catalog.term_relations (
  id text PRIMARY KEY,
  section text NOT NULL CHECK (section IN ('synonyms', 'regional_terms')),
  position integer NOT NULL,
  relation text NOT NULL,
  terms text[] NOT NULL,
  head text,
  category_ids text[],
  regions text[],
  note text,
  omitted text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE catalog.brand_aliases (
  position integer PRIMARY KEY,
  brand_id text NOT NULL,
  alias text NOT NULL,
  source_ids text[],
  omitted text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE catalog.unit_aliases (
  position integer PRIMARY KEY,
  unit text NOT NULL,
  aliases text[] NOT NULL,
  factor double precision,
  omitted text[] NOT NULL DEFAULT '{}'
);
"""

TABLES = ("meta", "categories", "sources", "places", "brands", "makers", "products", "product_variants",
          "product_images", "product_origin_claims", "term_relations", "brand_aliases", "unit_aliases")

# (khóa JSON, kiểu); cột trùng tên khóa. Kiểu: text | json | date | ts | tri (true/false/"unknown").
CATEGORY = [("id", "text"), ("name_vi", "text"), ("parent_id", "text"), ("aliases", "text"), ("description_vi", "text")]
SOURCE = [("id", "text"), ("url", "text"), ("title", "text"), ("publisher", "text"), ("source_type", "text"),
          ("retrieved_at", "ts"), ("usage_rights_note", "text"), ("supports", "text"), ("archived_copy_path", "text")]
PLACE = [("id", "text"), ("place_type", "text"), ("name_as_sourced", "text"), ("name_normalized", "text"),
         ("aliases", "text"), ("parent_id", "text"), ("admin_code", "text"), ("admin_code_scheme", "text"),
         ("historical_names", "json"), ("verified_at", "date"), ("source_ids", "text")]
BRAND = [("aliases", "json"), ("id", "text"), ("name", "text"), ("official_url", "text"), ("origin_country", "text"),
         ("origin_source_ids", "text"), ("place_ids", "text"), ("source_ids", "text")]
MAKER = [("aliases", "json"), ("id", "text"), ("name", "text"), ("maker_type", "text"), ("brand_ids", "text"),
         ("place_ids", "text"), ("official_url", "text"), ("source_ids", "text")]
PRODUCT_HEAD = [("id", "text"), ("slug", "text"), ("name_vi", "text"), ("status", "text"), ("category_id", "text"),
                ("brand_id", "text"), ("maker_id", "text"), ("short_description_vi", "text"),
                ("description_vi", "text"), ("aliases", "text"), ("tags", "text"), ("intended_uses", "text"),
                ("materials", "text"), ("colors", "text"), ("dimensions", "json"), ("craft_techniques", "text"),
                ("motifs", "text")]
PRODUCT_TAIL = [("certifications", "json"), ("source_ids", "text"), ("editor_note", "text"), ("created_at", "ts"),
                ("updated_at", "ts"), ("reviewed_at", "ts")]
# Khóa của product.origin (schema bắt buộc đủ) → cột.
ORIGIN = [("brand_origin_country", "brand_origin_country"), ("manufacturing_country", "manufacturing_country"),
          ("material_origins", "material_origins"), ("place_ids", "origin_place_ids"),
          ("craft_village_id", "craft_village_id")]
VARIANT = [("sku", "text"), ("name_vi", "text"), ("attributes", "json"), ("price_vnd", "text"),
           ("original_price_vnd", "text"), ("price_source_id", "text"), ("observed_at", "date"),
           ("availability", "text")]
CLAIM = [("claim_type", "text"), ("value", "tri"), ("detail_vi", "text"), ("place_ids", "text"), ("status", "text"),
         ("source_ids", "text"), ("checked_at", "date"), ("note", "text")]
IMAGE = [("id", "text"), ("local_path", "text"), ("source_url", "text"), ("alt_vi", "text"), ("view_type", "text"),
         ("variant_sku", "text"), ("sha256", "text"), ("usage_rights", "json"), ("width", "text"), ("height", "text")]
TERM = [("id", "text"), ("relation", "text"), ("terms", "text"), ("head", "text"), ("category_ids", "text"),
        ("regions", "text"), ("note", "text")]
BRAND_ALIAS = [("brand_id", "text"), ("alias", "text"), ("source_ids", "text")]
UNIT_ALIAS = [("unit", "text"), ("aliases", "text"), ("factor", "text")]


def content_sha256(data: dict[str, Any]) -> str:
    """Mã băm theo nội dung (không phụ thuộc định dạng file) để ghi phiên bản catalog vào tin nhắn/chỉ mục."""
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------- ghi ----------

def _to_db(value: Any, kind: str) -> Any:
    from psycopg.types.json import Jsonb

    if value is None:
        return None
    if kind == "json":
        return Jsonb(value)
    if kind == "tri":
        return value if isinstance(value, str) else ("true" if value else "false")
    return value


def _values(item: dict[str, Any], fields: list[tuple[str, str]]) -> list[Any]:
    return [_to_db(item.get(k), kind) for k, kind in fields]


def _omitted(item: dict[str, Any], *field_lists: list[tuple[str, str]]) -> list[str]:
    return [k for fields in field_lists for k, _ in fields if k not in item]


def _insert(cur, table: str, fields: list[tuple[str, str]], items: list[dict[str, Any]], **extra: Any) -> None:
    """Thêm các bản ghi theo thứ tự (cột position); extra là cột cố định cho cả lô, vd. product_id."""
    if not items:
        return
    cols = [*extra, "position", *(k for k, _ in fields), "omitted"]
    cur.executemany(f"INSERT INTO catalog.{table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                    [[*extra.values(), i, *_values(it, fields), _omitted(it, fields)] for i, it in enumerate(items)])


def import_catalog(conn, data: dict[str, Any], imported_from: str | None = None,
                   imported_sha256: str | None = None) -> dict[str, int]:
    """Thay toàn bộ catalog trong DB bằng `data` (đã validate) trong một giao dịch; trả số dòng mỗi bảng."""
    from psycopg.types.json import Jsonb

    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS catalog CASCADE")
        cur.execute(SCHEMA_SQL)
        cur.execute("INSERT INTO catalog.meta (schema_version, catalog_version, locale, currency, updated_at, "
                    "publication_policy, imported_from, imported_sha256) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (data["schema_version"], data["catalog_version"], data["locale"], data["currency"],
                     data["updated_at"],
                     Jsonb(data["publication_policy"]) if "publication_policy" in data else None,
                     imported_from, imported_sha256))
        _insert(cur, "categories", CATEGORY, data["categories"])
        _insert(cur, "sources", SOURCE, data["sources"])
        _insert(cur, "places", PLACE, data["places"])
        _insert(cur, "brands", BRAND, data["brands"])
        _insert(cur, "makers", MAKER, data["makers"])

        cols = ["position", *(k for k, _ in PRODUCT_HEAD), *(c for _, c in ORIGIN), *(k for k, _ in PRODUCT_TAIL),
                "omitted"]
        cur.executemany(
            f"INSERT INTO catalog.products ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
            [[i, *_values(p, PRODUCT_HEAD),
              *(Jsonb(p["origin"][k]) if k == "material_origins" else p["origin"][k] for k, _ in ORIGIN),
              *_values(p, PRODUCT_TAIL), _omitted(p, PRODUCT_HEAD, PRODUCT_TAIL)]
             for i, p in enumerate(data["products"])])
        for p in data["products"]:
            _insert(cur, "product_variants", VARIANT, p["variants"], product_id=p["id"])
            _insert(cur, "product_images", IMAGE, p["images"], product_id=p["id"])
            _insert(cur, "product_origin_claims", CLAIM, p["origin_claims"], product_id=p["id"])

        d = data["search_dictionary"]
        _insert(cur, "term_relations", TERM, d["synonyms"], section="synonyms")
        _insert(cur, "term_relations", TERM, d["regional_terms"], section="regional_terms")
        _insert(cur, "brand_aliases", BRAND_ALIAS, d["brand_aliases"])
        _insert(cur, "unit_aliases", UNIT_ALIAS, d["unit_aliases"])
        counts = {}
        for t in TABLES:
            cur.execute(f"SELECT count(*) FROM catalog.{t}")
            counts[t] = cur.fetchone()[0]
    return counts


# ---------- đọc ----------

def _from_db(value: Any, kind: str) -> Any:
    if value is None:
        return None
    if kind == "ts":
        return value.astimezone(VN_TZ).isoformat()
    if kind == "date":
        return value.isoformat() if isinstance(value, date) else value
    if kind == "tri":
        return {"true": True, "false": False}.get(value, value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _item(row: dict[str, Any], fields: list[tuple[str, str]]) -> dict[str, Any]:
    omitted = set(row["omitted"])
    return {k: _from_db(row[k], kind) for k, kind in fields if k not in omitted}


def _select(cur, table: str, order: str = "position") -> list[dict[str, Any]]:
    cur.execute(f"SELECT * FROM catalog.{table} ORDER BY {order}")
    return cur.fetchall()


def read_catalog(conn) -> dict[str, Any]:
    """Dựng lại dict catalog cùng cấu trúc database.json. LookupError nếu DB chưa có catalog."""
    from psycopg.rows import dict_row

    with conn.transaction(), conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT to_regclass('catalog.meta') AS t")
        if cur.fetchone()["t"] is None:
            raise LookupError("Chưa có schema catalog trong PostgreSQL; chạy scripts/db/import_json.py")
        cur.execute("SELECT * FROM catalog.meta")
        meta = cur.fetchone()
        if meta is None:
            raise LookupError("Bảng catalog.meta trống; chạy scripts/db/import_json.py")
        children: dict[str, dict[str, list]] = {"variants": {}, "images": {}, "origin_claims": {}}
        for key, table, fields in (("variants", "product_variants", VARIANT), ("images", "product_images", IMAGE),
                                   ("origin_claims", "product_origin_claims", CLAIM)):
            for r in _select(cur, table, "product_id, position"):
                children[key].setdefault(r["product_id"], []).append(_item(r, fields))
        products = []
        for r in _select(cur, "products"):
            p = _item(r, PRODUCT_HEAD)
            p["variants"] = children["variants"].get(r["id"], [])
            p["origin"] = {k: r[c] for k, c in ORIGIN}
            p["origin_claims"] = children["origin_claims"].get(r["id"], [])
            tail = _item(r, PRODUCT_TAIL)
            if "certifications" in tail:
                p["certifications"] = tail.pop("certifications")
            p["images"] = children["images"].get(r["id"], [])
            p.update(tail)
            products.append(p)
        terms = _select(cur, "term_relations", "section, position")
        data = {
            "schema_version": meta["schema_version"],
            "catalog_version": meta["catalog_version"],
            "locale": meta["locale"],
            "currency": meta["currency"],
            "updated_at": _from_db(meta["updated_at"], "ts"),
            "categories": [_item(r, CATEGORY) for r in _select(cur, "categories")],
            "brands": [_item(r, BRAND) for r in _select(cur, "brands")],
            "makers": [_item(r, MAKER) for r in _select(cur, "makers")],
            "places": [_item(r, PLACE) for r in _select(cur, "places")],
            "sources": [_item(r, SOURCE) for r in _select(cur, "sources")],
            "products": products,
            "search_dictionary": {
                "synonyms": [_item(r, TERM) for r in terms if r["section"] == "synonyms"],
                "regional_terms": [_item(r, TERM) for r in terms if r["section"] == "regional_terms"],
                "brand_aliases": [_item(r, BRAND_ALIAS) for r in _select(cur, "brand_aliases")],
                "unit_aliases": [_item(r, UNIT_ALIAS) for r in _select(cur, "unit_aliases")],
            },
        }
        if meta["publication_policy"] is not None:
            data["publication_policy"] = meta["publication_policy"]
    return data
