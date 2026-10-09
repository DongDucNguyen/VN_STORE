"""Chuyển bản ghi catalog sang dữ liệu hiển thị. Mọi thông tin hiển thị lấy từ snapshot."""
from __future__ import annotations

from typing import Any

from .store import CatalogSnapshot

CLAIM_LABELS = {
    "vn_brand": "Thương hiệu Việt",
    "made_in_vn": "Sản xuất tại Việt Nam",
    "vn_material": "Nguyên liệu Việt",
    "traditional_craft": "Thủ công/truyền thống",
    "craft_village": "Làng nghề",
}
CLAIM_STATUS_LABELS = {
    "manufacturer_declared": "Nhà sản xuất công bố",
    "source_checked": "Đã đối chiếu nguồn",
    "unverified": "Chưa xác minh",
}


def image_url(image_id: str) -> str:
    return f"/images/{image_id}"


def price_summary(p: dict[str, Any]) -> dict[str, Any]:
    known = [v["price_vnd"] for v in p["variants"] if v["price_vnd"] is not None]
    dates = [v["observed_at"] for v in p["variants"] if v.get("observed_at")]
    return {
        "min_vnd": min(known) if known else None,
        "max_vnd": max(known) if known else None,
        "has_unknown": len(known) < len(p["variants"]),
        "observed_at": max(dates) if dates else None,
    }


def _ref(coll: dict[str, dict[str, Any]], key: str | None, name_field: str = "name") -> dict[str, Any] | None:
    if key is None or key not in coll:
        return None
    return {"id": key, "name": coll[key][name_field]}


def _place(snap: CatalogSnapshot, pid: str | None) -> dict[str, Any] | None:
    if pid is None or pid not in snap.places:
        return None
    pl = snap.places[pid]
    return {"id": pid, "name": pl["name_normalized"], "name_as_sourced": pl["name_as_sourced"],
            "place_type": pl["place_type"]}


def origin_badges(p: dict[str, Any]) -> list[dict[str, Any]]:
    """Chỉ claim value=true có nguồn mới thành nhãn. Không tính điểm tổng hợp."""
    out, seen = [], set()
    for c in p["origin_claims"]:
        if c["value"] is True and c["source_ids"] and c["claim_type"] not in seen:
            seen.add(c["claim_type"])
            out.append({"claim_type": c["claim_type"], "label": CLAIM_LABELS[c["claim_type"]],
                        "status": c["status"], "status_label": CLAIM_STATUS_LABELS[c["status"]]})
    return out


def _local_images(p: dict[str, Any]) -> list[dict[str, Any]]:
    """Chỉ ảnh đã có file mới được phục vụ; ảnh chỉ có source_url (chưa có quyền) không hotlink."""
    return [i for i in p["images"] if i["local_path"] is not None]


def product_summary(snap: CatalogSnapshot, p: dict[str, Any]) -> dict[str, Any]:
    cat = snap.categories.get(p["category_id"])
    local = _local_images(p)
    img = local[0] if local else None
    return {
        "id": p["id"],
        "slug": p["slug"],
        "name_vi": p["name_vi"],
        "status": p["status"],
        "category": {"id": p["category_id"], "name_vi": cat["name_vi"] if cat else p["category_id"]},
        "brand": _ref(snap.brands, p["brand_id"]),
        "maker": _ref(snap.makers, p["maker_id"]),
        "craft_village": _place(snap, p["origin"]["craft_village_id"]),
        "price": price_summary(p),
        "image": {"id": img["id"], "url": image_url(img["id"]), "alt_vi": img["alt_vi"]} if img else None,
        "materials": p.get("materials", []),
        "colors": p.get("colors", []),
        "origin_badges": origin_badges(p),
    }


def _source(snap: CatalogSnapshot, sid: str) -> dict[str, Any]:
    s = snap.sources[sid]
    return {"id": sid, "url": s["url"], "title": s.get("title"), "publisher": s["publisher"],
            "source_type": s["source_type"], "retrieved_at": s["retrieved_at"]}


def product_detail(snap: CatalogSnapshot, p: dict[str, Any]) -> dict[str, Any]:
    used_sources: list[str] = list(p["source_ids"])

    def collect(ids: list[str]) -> None:
        for s in ids:
            if s not in used_sources:
                used_sources.append(s)

    claims = []
    for c in p["origin_claims"]:
        collect(c["source_ids"])
        claims.append({
            **c,
            "label": CLAIM_LABELS[c["claim_type"]],
            "status_label": CLAIM_STATUS_LABELS[c["status"]],
            "places": [x for x in (_place(snap, pid) for pid in c.get("place_ids", [])) if x],
        })
    for v in p["variants"]:
        if v.get("price_source_id"):
            collect([v["price_source_id"]])
    for cert in p.get("certifications", []):
        collect(cert["source_ids"])

    return {
        **product_summary(snap, p),
        "category_path": snap.category_path(p["category_id"]),
        "short_description_vi": p["short_description_vi"],
        "description_vi": p.get("description_vi", ""),
        "aliases": p.get("aliases", []),
        "tags": p.get("tags", []),
        "intended_uses": p.get("intended_uses", []),
        "dimensions": p.get("dimensions", {}),
        "craft_techniques": p.get("craft_techniques", []),
        "motifs": p.get("motifs", []),
        "variants": p["variants"],
        "origin": {
            **p["origin"],
            "places": [x for x in (_place(snap, pid) for pid in p["origin"]["place_ids"]) if x],
        },
        "origin_claims": claims,
        "certifications": p.get("certifications", []),
        "images": [{"id": i["id"], "url": image_url(i["id"]), "alt_vi": i["alt_vi"], "view_type": i["view_type"],
                    "variant_sku": i.get("variant_sku"), "usage_rights": i["usage_rights"]} for i in _local_images(p)],
        # Tách rõ: ảnh chưa tải file và ảnh đã có file nhưng chưa rõ quyền dùng.
        "images_missing_file": len(p["images"]) - len(_local_images(p)),
        "images_pending_rights": sum(1 for i in p["images"] if i["usage_rights"]["status"] == "unknown"),
        "sources": [_source(snap, s) for s in used_sources if s in snap.sources],
        "updated_at": p["updated_at"],
        "reviewed_at": p["reviewed_at"],
    }
