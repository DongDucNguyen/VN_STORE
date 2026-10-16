"""Công cụ catalog của trợ lý: tìm, chi tiết, so sánh, tương tự. Chạy trên snapshot/SearchEngine hiện tại.

Hai dạng đầu ra: bản rút gọn đưa cho model (ít token, không có editor_note, quyền ảnh, nguồn đầy đủ) và dữ kiện có cấu
trúc để backend tự dựng phần "thông tin từ catalog" — phần này không đi qua model nên không thể bị bịa.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..catalog.present import CLAIM_LABELS, CLAIM_STATUS_LABELS, origin_badges, price_summary, product_summary
from ..catalog.store import CatalogSnapshot
from ..search.engine import SearchEngine, SearchFilters, fmt_vnd
from .reviews import ReviewSummary, summarize
from .store import Store

DIM_LABELS = {"length_mm": ("Dài", "mm"), "width_mm": ("Rộng", "mm"), "height_mm": ("Cao", "mm"),
              "diameter_mm": ("Đường kính", "mm"), "volume_ml": ("Dung tích", "ml"), "weight_g": ("Khối lượng", "g")}
DESC_CHARS = 220


def price_label(p: dict[str, Any]) -> str:
    ps = price_summary(p)
    if ps["min_vnd"] is None:
        return "chưa có giá"
    if ps["min_vnd"] == ps["max_vnd"]:
        return fmt_vnd(ps["min_vnd"])
    return f"{fmt_vnd(ps['min_vnd'])}–{fmt_vnd(ps['max_vnd'])}"


def origin_labels(p: dict[str, Any]) -> list[str]:
    return [f"{b['label']} ({b['status_label'].lower()})" for b in origin_badges(p)]


@dataclass
class Catalog:
    snap: CatalogSnapshot
    engine: SearchEngine
    store: Store | None = None

    def product(self, pid: str) -> dict[str, Any] | None:
        return self.snap.products.get(pid)

    def review(self, pid: str) -> ReviewSummary:
        return summarize(self.store, pid)

    def compact(self, p: dict[str, Any], with_desc: bool = True) -> dict[str, Any]:
        cat = self.snap.categories.get(p["category_id"])
        brand = self.snap.brands.get(p["brand_id"]) if p["brand_id"] else None
        out = {"id": p["id"], "name": p["name_vi"], "category": cat["name_vi"] if cat else p["category_id"],
               "brand": brand["name"] if brand else None, "materials": p.get("materials", []),
               "colors": p.get("colors", []), "price": price_label(p), "origin": origin_labels(p),
               "reviews": self.review(p["id"]).label()}
        if p.get("intended_uses"):
            out["uses"] = p["intended_uses"]
        if with_desc:
            desc = p.get("description_vi") or p["short_description_vi"]
            out["desc"] = desc[:DESC_CHARS]
        return {k: v for k, v in out.items() if v not in (None, [], "")}

    def search(self, query: str, filters: SearchFilters | None = None, limit: int = 8) -> dict[str, Any]:
        res = self.engine.search(query, filters or SearchFilters(), limit=limit)
        return {"ids": [r["id"] for r in res["results"]], "total": res["total"],
                "interpreted": res["interpreted_query"], "applied_filters": res["applied_filters"],
                "relaxations": res["relaxations"], "warnings": res["warnings"]}

    def similar(self, pid: str, limit: int = 4) -> list[str]:
        p = self.product(pid)
        if p is None:
            return []
        root = (self.snap.category_path(p["category_id"]) or [{"id": None}])[0]["id"]
        mats = set(p.get("materials", []))
        scored = []
        for q in self.snap.products.values():
            if q["id"] == pid:
                continue
            score = 3.0 if q["category_id"] == p["category_id"] else (
                1.0 if root and (self.snap.category_path(q["category_id"]) or [{"id": None}])[0]["id"] == root else 0)
            score += len(mats & set(q.get("materials", [])))
            if score > 0:
                scored.append((score, q["name_vi"], q["id"]))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [x[2] for x in scored[:limit]]

    def facts(self, pid: str) -> dict[str, Any]:
        """Dữ kiện cho phần nhận xét khách quan (§6.4), dựng từ catalog, kèm danh sách thông tin còn thiếu."""
        p = self.snap.products[pid]
        rows: list[dict[str, str]] = []
        missing: list[str] = []

        def add(label: str, value: str | None, field: str) -> None:
            if value:
                rows.append({"label": label, "value": value, "field": field})
            else:
                missing.append(label.lower())

        cat = self.snap.category_path(p["category_id"])
        add("Danh mục", " › ".join(c["name_vi"] for c in cat), "category")
        brand = self.snap.brands.get(p["brand_id"]) if p["brand_id"] else None
        maker = self.snap.makers.get(p["maker_id"]) if p["maker_id"] else None
        add("Thương hiệu", brand["name"] if brand else None, "brand")
        if maker and (not brand or maker["name"] != brand["name"]):
            rows.append({"label": "Nhà sản xuất", "value": maker["name"], "field": "maker"})
        add("Chất liệu", ", ".join(p.get("materials", [])), "materials")
        add("Màu sắc", ", ".join(p.get("colors", [])), "colors")
        dims = [f"{DIM_LABELS[k][0]} {v:g} {DIM_LABELS[k][1]}" for k, v in (p.get("dimensions") or {}).items()
                if k in DIM_LABELS and isinstance(v, (int, float))]
        add("Kích thước", "; ".join(dims), "dimensions")
        if p.get("craft_techniques"):
            rows.append({"label": "Kỹ thuật", "value": ", ".join(p["craft_techniques"]), "field": "craft_techniques"})
        if p.get("intended_uses"):
            rows.append({"label": "Công dụng", "value": ", ".join(p["intended_uses"]), "field": "intended_uses"})
        ps = price_summary(p)
        if ps["min_vnd"] is None:
            missing.append("giá")
        else:
            rows.append({"label": "Giá", "value": price_label(p) + (f" (ghi nhận {ps['observed_at']})"
                                                                     if ps["observed_at"] else ""),
                         "field": "price"})
        avail = {v.get("availability") for v in p["variants"]}
        if avail == {"in_stock"}:
            rows.append({"label": "Tình trạng", "value": "còn hàng (theo nguồn)", "field": "availability"})
        origin = []
        for c in p["origin_claims"]:
            if c["value"] is True and c["source_ids"]:
                origin.append({"label": CLAIM_LABELS[c["claim_type"]], "status": CLAIM_STATUS_LABELS[c["status"]],
                               "detail": c.get("detail_vi")})
            elif c["value"] == "unknown":
                origin.append({"label": CLAIM_LABELS[c["claim_type"]], "status": "Chưa rõ", "detail": None})
        desc = p.get("description_vi") or p["short_description_vi"]
        return {"product_id": pid, "rows": rows, "origin": origin, "missing": missing, "description": desc,
                "reviews": self.review(pid).public()}

    def card(self, pid: str) -> dict[str, Any]:
        p = self.snap.products[pid]
        out = product_summary(self.snap, p)
        out["review_stats"] = {k: v for k, v in self.review(pid).public().items()
                               if k in ("count", "average")}
        return out
