"""Bổ sung chất liệu/màu còn trống cho sản phẩm từ bản lưu trang nguồn (đợt 002), qua execute_import.

    .venv/Scripts/python scripts/import_raw/enrich_from_archive.py --catalog-version <mới> [--dry-run]

Chỉ ĐIỀN trường đang rỗng, không sửa giá trị đã có, không đụng giá. Mỗi sản phẩm được bổ sung có thêm một dòng
editor_note ghi trường, giá trị và căn cứ (trích từ trang lưu hoặc tên sản phẩm của nguồn). Quy tắc căn cứ:
- "Màu sắc: …" / "Color: …" / "Material: …" trên trang sản phẩm lưu trong product_pages.zip;
- màu nêu tường minh trong tên sản phẩm của nguồn (vd. "Trắng Ngà", "Màu Cam", "nền xanh ngọc");
- Minh Long: "sứ" theo trang chủ nguồn ("gốm sứ Minh Long") khi trang sản phẩm không ghi — có ghi chú riêng;
- Marou: "cacao" cho sản phẩm sô cô la (tên nguồn) khi trang không có thành phần.
Không có căn cứ thì để trống. Giá không được suy ra (Vietcraft bán sỉ không niêm yết; Kilomet109 niêm yết USD).
"""
from __future__ import annotations

import argparse
import copy
import html
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "data_collection/batches/2026-10-10_dot-002"

# Explicit colour words as they appear in source titles/fields → catalog colour value. Longest first.
COLOR_WORDS = [
    ("trắng ngà", "trắng ngà"), ("tím than", "tím than"), ("xanh da trời", "xanh da trời"), ("xanh ngọc", "xanh ngọc"), ("xanh non", "xanh non"), ("xanh lá", "xanh lá"),
    ("xanh dương", "xanh dương"), ("xanh lam", "xanh lam"), ("cobalt", "xanh cobalt"), ("nhiều màu", "nhiều màu"),
    ("trắng", "trắng"), ("vàng", "vàng"), ("cam", "cam"), ("đỏ", "đỏ"), ("hồng", "hồng"), ("đen", "đen"),
    ("nâu", "nâu"), ("tím", "tím"), ("xanh", "xanh"),
]
EN_COLORS = [("matte black", "đen"), ("black", "đen"), ("natural", "màu tự nhiên"), ("dark brown", "nâu sẫm"),
             ("brown", "nâu"), ("white", "trắng"), ("red", "đỏ")]
EN_MATERIALS = [("rattan", "mây"), ("bamboo", "tre"), ("seagrass", "seagrass"), ("water hyacinth", "lục bình"),
                ("ceramic", "gốm"), ("mother of pearl", "xà cừ")]
VI_MATERIALS = [("tơ tằm", "lụa tơ tằm"), ("đũi", "lụa tơ tằm"), ("lụa", "lụa tơ tằm"), ("cotton", "cotton")]


def text_of(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def words(text: str, table) -> list[str]:
    found, rest = [], f" {text.lower()} "
    for key, value in table:
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", rest):
            if value not in found:
                found.append(value)
            rest = re.sub(rf"(?<!\w){re.escape(key)}(?!\w)", " ", rest)
    return found


def title_colors(title: str) -> list[str]:
    """Colour only from an explicit colour segment of the source title (after ' - ', 'Màu', 'nền', parentheses)."""
    segments = re.findall(r"(?:màu|nền)\s+([^-–|()]+)|\(([^)]+)\)|[-–]\s*([^-–|()]+)$", title, flags=re.I)
    text = " ".join(x for seg in segments for x in seg if x)
    text = re.sub(r"hoa hồng", " ", text, flags=re.I)  # flower name, not a colour
    return words(text, COLOR_WORDS)


def evidence_for(product: dict, page_text: str, record_text: str) -> dict:
    """Return {field: (values, quote)} for empty fields only."""
    found = {}
    brand = product["brand_id"] or ""
    title = product["name_vi"]
    if not product["colors"]:
        m = re.search(r"Màu sắc\s*[:：]\s*(.{1,60}?)(?=\s+(?:Khổ|Kích|Chất|Size|Họa tiết|Sản xuất|Quý khách|Khách hàng|Xuất xứ|"
                      r"[A-ZĐ]{3,})|[.|;:]|$)", page_text)
        if m and words(m.group(1), COLOR_WORDS):
            found["colors"] = (words(m.group(1), COLOR_WORDS), m.group(0).strip())
        else:
            m = re.search(r"Colou?r\s*[:：]\s*([^.;|]{1,40})", page_text + " " + record_text, re.I)
            if m and words(m.group(1), EN_COLORS):
                found["colors"] = (words(m.group(1), EN_COLORS), m.group(0).strip())
            elif brand in ("brand-minh-long",) and title_colors(title):
                found["colors"] = (title_colors(title), f"tên nguồn: {title}")
    if not product["materials"]:
        m = re.search(r"Materials?\s*[:：]\s*([^.;|]{1,60})", page_text + " " + record_text, re.I)
        if m and words(m.group(1), EN_MATERIALS):
            found["materials"] = (words(m.group(1), EN_MATERIALS), m.group(0).strip())
        elif brand == "brand-hanhsilk" and words(title, VI_MATERIALS):
            found["materials"] = (words(title, VI_MATERIALS)[:1], f"tên nguồn: {title}")
        elif brand == "brand-minh-long":
            found["materials"] = (["sứ"], "trang chủ nguồn: 'gốm sứ Minh Long' (trang sản phẩm không ghi chất liệu)")
        elif brand == "brand-marou" and re.search(r"chocolate|sô cô la", title, re.I):
            found["materials"] = (["cacao"], f"tên nguồn là sản phẩm sô cô la: {title}")
    return found


def enrich(current: dict, pages: dict[str, str], records: dict[str, str], stamp: str) -> tuple[dict, list[dict]]:
    out = copy.deepcopy(current)
    log = []
    for product in out["products"]:
        found = evidence_for(product, pages.get(product["id"], ""), records.get(product["id"], ""))
        if not found:
            continue
        notes = []
        for field, (values, quote) in found.items():
            product[field] = values
            notes.append(f"{field}={values} — căn cứ: {quote[:120]}")
            log.append({"product_id": product["id"], "field": field, "values": values, "evidence": quote[:200]})
        product["editor_note"] = ((product.get("editor_note") or "").rstrip() + "\n" if product.get("editor_note") else "") + \
            f"Bổ sung tự động {stamp[:10]} từ trang nguồn lưu trữ (chưa người duyệt lại): " + "; ".join(notes)
        product["updated_at"] = stamp
    return out, log


def load_archive() -> tuple[dict[str, str], dict[str, str]]:
    id_map = json.loads((BATCH / "id_map.json").read_text(encoding="utf-8"))["products"]
    staging = {(v if isinstance(v, str) else v["id"]): k for k, v in id_map.items()}
    pages, records = {}, {}
    with zipfile.ZipFile(BATCH / "product_pages.zip") as zf:
        names = set(zf.namelist())
        for pid, sid in staging.items():
            name = f"product_pages/{sid}.html"
            if name in names:
                pages[pid] = text_of(zf.read(name).decode("utf-8", "replace"))
            rec = BATCH / "records" / f"{sid}.json"
            if rec.exists():
                records[pid] = text_of(rec.read_text(encoding="utf-8"))
    return pages, records


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--catalog-version", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(ROOT / "backend"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app.catalog.validation import validate_catalog
    from safe_import import digest, execute_import

    dest = args.catalog.resolve()
    original = dest.read_bytes()
    current = json.loads(original)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    pages, records = load_archive()
    out, log = enrich(current, pages, records, stamp)
    conflicts = []
    if out != current:
        if args.catalog_version == current["catalog_version"]:
            conflicts.append({"code": "catalog_version_required", "path": "$.catalog_version"})
        out["catalog_version"] = args.catalog_version
        out["updated_at"] = stamp
    result = validate_catalog(out, dest.parent)
    code, report = execute_import(catalog_path=dest, original=original, proposed=out, generated={},
                                 conflicts=conflicts, validation=result, dry_run=args.dry_run, root=ROOT,
                                 inputs={"product_pages.zip": digest((BATCH / "product_pages.zip").read_bytes())},
                                 kind="enrich")
    evidence = report.with_name(report.stem + "-evidence.json")
    evidence.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    by = {}
    for row in log:
        by.setdefault(row["field"], set()).add(row["product_id"])
    print(f"Bổ sung: " + ", ".join(f"{k} {len(v)} sản phẩm" for k, v in by.items()) +
          f"; {len(result.errors)} lỗi, {len(conflicts)} xung đột. Báo cáo: {report}; căn cứ: {evidence}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
