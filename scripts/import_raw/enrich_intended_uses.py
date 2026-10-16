"""Bổ sung `intended_uses` (công dụng/dịp dùng) còn trống theo loại sản phẩm, qua execute_import.

    .venv/Scripts/python -X utf8 scripts/import_raw/enrich_intended_uses.py --catalog-version <mới> [--dry-run]

Mục đích: trợ lý và tìm kiếm gợi ý được theo nhu cầu ("đựng trang sức", "cắm hoa", "quà tặng"). Trước đợt này 0/330
sản phẩm có trường này.

Quy tắc: chỉ ĐIỀN trường đang rỗng; giá trị suy từ LOẠI sản phẩm (từ khóa trong tên, rồi danh mục) theo bảng có kiểm
soát bên dưới — không suy công dụng sức khỏe, chất lượng hay nguồn gốc. Mỗi sản phẩm được thêm một dòng editor_note ghi
giá trị và quy tắc đã khớp. Đây là nhãn BIÊN TẬP suy từ loại sản phẩm, không trích từ trang nguồn; được duyệt tự động
theo ủy quyền của chủ dự án ngày 15/10/2026 (docs/ke-hoach-tro-ly-ai.md §8.4).
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPROVAL = "duyệt tự động theo ủy quyền của chủ dự án ngày 15/10/2026"

# (mẫu trong tên, danh mục áp dụng hoặc None = mọi danh mục, công dụng). Khớp mẫu đầu tiên; mẫu so trên tên viết thường.
NAME_RULES: list[tuple[str, tuple[str, ...] | None, list[str]]] = [
    (r"chụp đèn|\bđèn\b", None, ["chiếu sáng", "trang trí nội thất"]),
    (r"nhà cho thú cưng", None, ["chỗ nằm cho thú cưng"]),
    (r"\bbàn\b", ("may-tre-coi-noi-that",), ["đồ nội thất", "trang trí nội thất"]),
    (r"hộp trang sức", None, ["đựng trang sức", "quà tặng"]),
    (r"hộp trà", None, ["đựng trà", "quà tặng"]),
    (r"hộp đựng giấy|hộp giấy", None, ["đựng khăn giấy", "trang trí bàn"]),
    (r"cigar|xì gà", None, ["đựng xì gà", "quà tặng"]),
    (r"hộp đồng hồ", None, ["đựng đồng hồ", "quà tặng"]),
    (r"chặn sách", None, ["trang trí kệ sách"]),
    (r"cờ tướng|bộ cờ", None, ["giải trí", "quà tặng"]),
    (r"giá đỡ điện thoại", None, ["để bàn làm việc"]),
    (r"\btranh\b", None, ["treo tường", "trang trí nhà cửa"]),
    (r"\bkhay\b", None, ["bày đồ ăn, bánh kẹo", "trang trí"]),
    (r"\bhộp\b", None, ["đựng đồ", "trang trí"]),
    (r"bình hoa|lọ hoa|bình cắm|bình\b|\blọ\b", ("gom-su-binh-lo",), ["cắm hoa", "trang trí nhà cửa", "quà tặng"]),
    (r"bình hoa|bình\b|\blọ\b", ("go-son-mai-binh-lo", "go-son-mai"), ["trang trí nhà cửa", "quà tặng"]),
    (r"\bbát\b|\btô\b", ("go-son-mai", "may-tre-coi-gio", "may-tre-coi"), ["đựng trái cây, đồ khô", "trang trí"]),
    (r"\bgiỏ\b|\brổ\b", None, ["đựng đồ", "trang trí"]),
    (r"\btúi\b", None, ["xách tay", "đi chơi"]),
    (r"khăn tay|handkerchief|handk", None, ["khăn tay", "phụ kiện thời trang"]),
    (r"\bkhăn\b|scarf", None, ["quàng cổ", "phụ kiện thời trang", "quà tặng"]),
    (r"vòng cổ|\bvòng\b", ("det-may-thoi-trang",), ["phụ kiện thời trang"]),
    (r"\báo\b|\bváy\b|\bquần\b|jumpsuit|kaftan|dress|coat", ("det-may-thoi-trang",), ["trang phục"]),
    (r"\bấm\b|bộ trà|\btách\b|chén trà", None, ["pha trà", "tiếp khách"]),
    (r"\bcốc\b|\bly\b|\bmug\b", None, ["uống trà, cà phê"]),
    (r"ironbar|protein|energy bar", ("thuc-pham-banh-keo",), ["ăn nhẹ", "bổ sung năng lượng khi vận động"]),
]
CATEGORY_DEFAULTS = {
    "gom-su-binh-lo": ["cắm hoa", "trang trí nhà cửa", "quà tặng"],
    "gom-su-bat-dia": ["dùng bữa hằng ngày", "bày món ăn"],
    "gom-su-am-chen": ["pha trà", "tiếp khách", "quà tặng"],
    "gom-su-coc-ly": ["uống trà, cà phê"],
    "may-tre-coi": ["đựng đồ", "trang trí"],
    "may-tre-coi-gio": ["đựng đồ", "trang trí"],
    "may-tre-coi-tui": ["xách tay", "đi chơi"],
    "may-tre-coi-noi-that": ["trang trí nội thất"],
    "det-may-khan": ["quàng cổ", "phụ kiện thời trang", "quà tặng"],
    "det-may-thoi-trang": ["trang phục"],
    "det-may-vai-lua": ["may trang phục"],
    "go-son-mai": ["trang trí", "quà tặng"],
    "go-son-mai-binh-lo": ["trang trí nhà cửa", "quà tặng"],
    "thuc-pham-banh-keo": ["ăn vặt", "quà tặng"],
}
GIFT_WORDS = r"set quà|quà tặng|quà biếu|gift"
GIFT_CATEGORIES = {"thuc-pham-banh-keo", "det-may-khan", "go-son-mai", "go-son-mai-binh-lo", "gom-su-binh-lo",
                   "gom-su-am-chen"}


def uses_for(p: dict) -> tuple[list[str], str] | None:
    name = unicodedata.normalize("NFC", p["name_vi"]).lower()
    found = None
    for pattern, cats, values in NAME_RULES:
        if (cats is None or p["category_id"] in cats) and re.search(pattern, name):
            found = (list(values), f"tên khớp “{pattern}”")
            break
    if found is None and p["category_id"] in CATEGORY_DEFAULTS:
        found = (list(CATEGORY_DEFAULTS[p["category_id"]]), f"danh mục {p['category_id']}")
    if found is None:
        return None
    values, rule = found
    # "quà tặng" là nhãn cộng thêm: tên ghi rõ là quà/set quà, hoặc nhóm hàng hay được mua làm quà.
    if "quà tặng" not in values and (re.search(GIFT_WORDS, name) or p["category_id"] in GIFT_CATEGORIES):
        values.append("quà tặng")
    return values, rule


def enrich(current: dict, stamp: str) -> tuple[dict, list[dict]]:
    out = copy.deepcopy(current)
    log = []
    for p in out["products"]:
        if p.get("intended_uses"):
            continue
        found = uses_for(p)
        if not found:
            continue
        values, rule = found
        p["intended_uses"] = values
        note = (f"Bổ sung tự động {stamp[:10]}: intended_uses={values} — suy từ loại sản phẩm ({rule}), "
                f"không trích từ nguồn; {APPROVAL}.")
        p["editor_note"] = ((p.get("editor_note") or "").rstrip() + "\n" if p.get("editor_note") else "") + note
        p["updated_at"] = stamp
        log.append({"product_id": p["id"], "name_vi": p["name_vi"], "values": values, "rule": rule})
    return out, log


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
    out, log = enrich(current, stamp)
    conflicts = []
    if out != current:
        if args.catalog_version == current["catalog_version"]:
            conflicts.append({"code": "catalog_version_required", "path": "$.catalog_version"})
        out["catalog_version"] = args.catalog_version
        out["updated_at"] = stamp
    result = validate_catalog(out, dest.parent)
    code, report = execute_import(catalog_path=dest, original=original, proposed=out, generated={},
                                  conflicts=conflicts, validation=result, dry_run=args.dry_run, root=ROOT,
                                  inputs={"rules_sha256": digest(Path(__file__).read_bytes())}, kind="enrich")
    evidence = report.with_name(report.stem + "-intended-uses.json")
    evidence.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [p["id"] for p in out["products"] if not p.get("intended_uses")]
    print(f"Bổ sung intended_uses cho {len(log)} sản phẩm; còn trống {len(missing)}; {len(result.errors)} lỗi, "
          f"{len(conflicts)} xung đột. Báo cáo: {report}; chi tiết: {evidence}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
