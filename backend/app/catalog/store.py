"""Snapshot catalog bất biến, dựng từ database.json đã validate (PLAN.md mục 3.3)."""
from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .validation import Issue, validate_catalog


class CatalogError(Exception):
    def __init__(self, message: str, issues: list[Issue] | None = None):
        super().__init__(message)
        self.issues = issues or []


@dataclass
class CatalogSnapshot:
    data: dict[str, Any]
    path: Path
    sha256: str
    loaded_at: str
    include_drafts: bool
    products: dict[str, dict[str, Any]] = field(default_factory=dict)  # chỉ sản phẩm hiển thị
    categories: dict[str, dict[str, Any]] = field(default_factory=dict)
    category_children: dict[str, list[str]] = field(default_factory=dict)
    brands: dict[str, dict[str, Any]] = field(default_factory=dict)
    makers: dict[str, dict[str, Any]] = field(default_factory=dict)
    places: dict[str, dict[str, Any]] = field(default_factory=dict)
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    images: dict[str, tuple[str, dict[str, Any]]] = field(default_factory=dict)  # image_id → (product_id, image)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def base_dir(self) -> Path:
        return self.path.parent

    @property
    def version(self) -> str:
        return self.data["catalog_version"]

    def category_subtree(self, category_id: str) -> set[str]:
        out, stack = set(), [category_id]
        while stack:
            c = stack.pop()
            if c in out:
                continue
            out.add(c)
            stack.extend(self.category_children.get(c, []))
        return out

    def category_path(self, category_id: str) -> list[dict[str, str]]:
        path, cur, seen = [], category_id, set()
        while cur and cur in self.categories and cur not in seen:
            seen.add(cur)
            c = self.categories[cur]
            path.append({"id": c["id"], "name_vi": c["name_vi"]})
            cur = c["parent_id"]
        return list(reversed(path))

    def image_path(self, image_id: str) -> Path | None:
        hit = self.images.get(image_id)
        if not hit or hit[1]["local_path"] is None:
            return None
        try:
            relative = Path(hit[1]["local_path"])
            root = self.base_dir.resolve()
            fp = (root / relative).resolve()
            if relative.is_absolute() or root not in fp.parents:
                return None
            info = fp.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
                return None
            return fp
        except (OSError, ValueError, RuntimeError):
            # Files can disappear or become inaccessible after the snapshot loads.
            return None


def load_snapshot(path: Path, include_drafts: bool = False) -> CatalogSnapshot:
    path = path.resolve()
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise CatalogError(f"Không đọc được catalog {path}: {e}") from e

    result = validate_catalog(data, path.parent)
    if not result.ok:
        raise CatalogError(f"Catalog {path.name} có {len(result.errors)} lỗi", result.errors)

    visible = ("published", "draft") if include_drafts else ("published",)
    snap = CatalogSnapshot(
        data=data,
        path=path,
        sha256=hashlib.sha256(raw).hexdigest(),
        loaded_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        include_drafts=include_drafts,
        warnings=result.warnings,
    )
    snap.products = {p["id"]: p for p in data["products"] if p["status"] in visible}
    snap.categories = {c["id"]: c for c in data["categories"]}
    for c in data["categories"]:
        if c["parent_id"]:
            snap.category_children.setdefault(c["parent_id"], []).append(c["id"])
    snap.brands = {b["id"]: b for b in data["brands"]}
    snap.makers = {m["id"]: m for m in data["makers"]}
    snap.places = {p["id"]: p for p in data["places"]}
    snap.sources = {s["id"]: s for s in data["sources"]}
    for p in snap.products.values():
        for img in p["images"]:
            snap.images[img["id"]] = (p["id"], img)
    return snap
