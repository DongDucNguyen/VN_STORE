"""Criteria-based MACHINE labels for keyword queries over the whole catalog (never human-verified).

    .venv/Scripts/python scripts/benchmark/criteria_labels.py --spec benchmarks/keyword/expansion/claude_criteria_v1.py \
        --out-dir benchmarks/keyword/expansion

Each intent group in the spec states what a shopper asks for: item type (regex on name/aliases/category), brand,
materials, colours, price range, negations, soft wishes. Every product in the catalog is graded with the project
rubric (review_protocol.md):
  3  item type and every stated constraint evidenced in catalog fields;
  2  type and hard constraints met, a soft wish (usage, style, size) not evidenced;
  1  type met but a hard attribute missing/contradicted or brand differs (P2/P4), price unknown (P3),
     or the product is only related (spec "related");
  0  otherwise; price outside the range or a negated attribute present (P3).
train/dev rows get machine labels (label_source=machine, verified=false). test rows are written WITHOUT labels:
the locked test needs human judgments.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = "claude-criteria-v1"


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").lower()


def product_view(p: dict, categories: dict) -> dict:
    # Item type and hard wishes match the product's own name/aliases only: category names ("Bát, đĩa, chén ăn")
    # and free descriptions ("vườn dừa", "nhiệt độ cao") would otherwise match unrelated products.
    title = " ".join([p["name_vi"], *p.get("aliases", [])])
    text = " ".join([title, p.get("short_description_vi") or ""])
    prices = [v["price_vnd"] for v in p["variants"] if v["price_vnd"] is not None]
    return {"id": p["id"], "title": nfc(title), "text": nfc(text), "name": nfc(p["name_vi"]), "brand": p["brand_id"],
            "category": p["category_id"], "materials": [nfc(m) for m in p["materials"]],
            "colors": [nfc(c) for c in p["colors"]], "price": min(prices) if prices else None}


def has(pattern: str | None, text: str) -> bool:
    return bool(pattern) and re.search(pattern, text, re.I) is not None


def attribute(values: list[str] | None, field: list[str], text: str) -> str:
    """satisfied | missing | contradicted for an any-of attribute (field first, then text)."""
    if not values:
        return "satisfied"
    wanted = [nfc(v) for v in values]
    if any(w == f or f.startswith(w + " ") or w in f.split(", ") for w in wanted for f in field):
        return "satisfied"
    if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in wanted):
        return "satisfied"
    return "contradicted" if field else "missing"


def grade(spec: dict, p: dict) -> tuple[int, str]:
    if spec.get("nomatch"):
        return (1, "liên quan nhưng không đáp ứng") if has(spec.get("related"), p["title"]) else (0, "không có sản phẩm phù hợp")
    type_ok = (not spec.get("cat") or p["category"] in spec["cat"]) and (not spec.get("item") or has(spec["item"], p["title"]))
    if not type_ok:
        return (1, "liên quan, khác loại hàng") if has(spec.get("related"), p["title"]) else (0, "khác loại hàng")
    typed = bool(spec.get("cat") or spec.get("item") or spec.get("brand"))
    for key, field in (("not_mat", p["materials"]), ("not_color", p["colors"])):
        if spec.get(key) and attribute(spec[key], field, p["name"]) == "satisfied":
            return 0, "có thuộc tính bị loại trừ"
    if spec.get("not_text") and has(spec["not_text"], p["text"]):
        return 0, "có thuộc tính bị loại trừ"
    if spec.get("price"):
        lo, hi = spec["price"]
        if p["price"] is None:
            return 1, "chưa có giá (P3)"
        if not (lo or 0) <= p["price"] <= (hi or float("inf")):
            return 0, "ngoài khoảng giá (P3)"
    if spec.get("brand") and p["brand"] != spec["brand"]:
        if not (spec.get("cat") or spec.get("item")):
            return 0, "khác thương hiệu"  # brand-only query: other brands are not the same item type
        return 1, "đúng loại hàng, khác thương hiệu (P4)"
    for key, field in (("mat", p["materials"]), ("color", p["colors"])):
        state = attribute(spec.get(key), field, p["text"])
        if state != "satisfied":
            if not typed:
                return 0, "không có thuộc tính được hỏi"  # attribute-only query: unrelated products stay 0
            return 1, f"{'chất liệu' if key == 'mat' else 'màu'} {('chưa có căn cứ' if state == 'missing' else 'khác yêu cầu')} (P2)"
    if spec.get("need") and not has(spec["need"], p["title"]):
        return (1, "thiếu đặc điểm bắt buộc (P2)") if typed else (0, "không có đặc điểm được hỏi")
    if spec.get("soft") and not has(spec["soft"], p["title"]):
        return 2, "đúng hàng; mong muốn phụ chưa có căn cứ"
    return 3, "đáp ứng loại hàng và mọi ràng buộc"


def load_spec(path: Path):
    spec = importlib.util.spec_from_file_location("criteria_spec", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GROUPS


def build(groups: list[dict], catalog: dict, existing_texts: set[str], sha: str) -> dict[str, list[dict]]:
    categories = {c["id"]: c["name_vi"] for c in catalog["categories"]}
    products = [product_view(p, categories) for p in catalog["products"]]
    seen, out = set(existing_texts), {"train": [], "dev": [], "test": []}
    ids = set()
    for g in groups:
        if g["split"] not in out:
            raise ValueError(f"{g['group_id']}: bad split")
        for i, text in enumerate(g["queries"], 1):
            key = " ".join(nfc(text).split())
            if key in seen:
                raise ValueError(f"duplicate query text: {text!r}")
            seen.add(key)
            qid = f"kw-{g['split']}-{g['group_id']}-{i}"
            if qid in ids:
                raise ValueError(f"duplicate qid {qid}")
            ids.add(qid)
            row = {"qid": qid, "query": text, "split": g["split"], "group_id": f"g-x-{g['group_id']}",
                   "intent": g["intent"]}
            if g["split"] == "test":
                row.update(has_answer=False, relevance={}, labeled_by="chưa chấm (cần người duyệt)", verified=False,
                           label_source="none", needs_human_labels=True)
            else:
                labels = {p["id"]: grade(g["spec"], p) for p in products}
                relevance = {pid: s for pid, (s, _) in labels.items()}
                row.update(has_answer=any(s >= 2 for s in relevance.values()), relevance=relevance,
                           labeled_by=f"{VERSION} (máy)", verified=False, label_source="machine",
                           label_scope="full_catalog", catalog_sha256=sha,
                           criteria=g["spec"], reasons={pid: r for pid, (s, r) in labels.items() if s > 0})
            out[g["split"]].append(row)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--existing", type=Path, action="append", default=[], help="file truy vấn đã có (chặn trùng câu)")
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    raw = args.catalog.read_bytes()
    catalog = json.loads(raw)
    existing = {" ".join(nfc(json.loads(l)["query"]).split()) for f in args.existing
                for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}
    try:
        out = build(load_spec(args.spec), catalog, existing, hashlib.sha256(raw).hexdigest())
    except (ValueError, KeyError) as exc:
        ap.error(str(exc))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for split, rows in out.items():
        name = f"{split}_{'unlabeled' if split == 'test' else 'machine'}.jsonl"
        (args.out_dir / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        answered = sum(r["has_answer"] for r in rows if split != "test")
        print(f"{split}: {len(rows)} truy vấn" + ("" if split == "test" else f", {answered} có đáp án") + f" → {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
