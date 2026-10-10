"""VNStore API (PLAN.md mục 4).

Chạy: cd backend && ../.venv/Scripts/uvicorn app.main:app --reload
Biến môi trường:
    VNSTORE_CATALOG         đường dẫn catalog (mặc định ../database.json)
    VNSTORE_INCLUDE_DRAFTS  1 = hiển thị cả sản phẩm draft (chỉ dùng khi phát triển)
    VNSTORE_CORS_ORIGINS    danh sách origin, phân tách bằng dấu phẩy
    VNSTORE_ASR_ADAPTER     adapter ASR dạng module:thuộc_tính (mặc định: chưa có → 503)
    VNSTORE_IMAGE_ADAPTER   adapter embedding ảnh dạng module:thuộc_tính (mặc định: chưa có → 503)
    VNSTORE_IMAGE_INDEX_DIR thư mục chỉ mục ảnh (mặc định ../artifacts/indexes/image)
    VNSTORE_IMAGE_INDEX_AUTOBUILD  1 = tự dựng chỉ mục ảnh trong bộ nhớ khi thiếu/cũ (chỉ khi phát triển)
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from .adapters import Busy, ImageEmbedder
from .catalog.present import product_detail, product_summary
from .catalog.store import CatalogError, CatalogSnapshot, load_snapshot
from .media import MAX_AUDIO_BYTES, MAX_IMAGE_BYTES, MediaError
from .modalities import STATE_MESSAGES, ImageService, Status, VoiceService, adapter_from_env
from .search.engine import SearchEngine, SearchFilters

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Bundle:
    """Catalog và chỉ mục cùng phiên bản; thay nguyên khối, không ghép lẫn."""
    snap: CatalogSnapshot
    engine: SearchEngine
    images: ImageService | None = None  # chỉ mục ảnh đã kiểm tra khớp đúng snapshot này


class AppState:
    bundle: Bundle | None = None
    error: CatalogError | None = None
    voice: VoiceService = VoiceService(None, Status("unavailable"))
    image_embedder: ImageEmbedder | None = None
    image_status: Status = Status("unavailable")


state = AppState()


def catalog_path() -> Path:
    return Path(os.environ.get("VNSTORE_CATALOG", REPO_ROOT / "database.json"))


def reload_catalog(path: Path | None = None) -> None:
    """Dựng snapshot mới; chỉ thay khi thành công, giữ bản cũ nếu lỗi."""
    try:
        snap = load_snapshot(path or catalog_path(), include_drafts=os.environ.get("VNSTORE_INCLUDE_DRAFTS") == "1")
        old = state.bundle.images if isinstance(state.bundle, Bundle) else None
        images = ImageService.for_snapshot(snap, state.image_embedder, state.image_status,
                                           old.gate if old else None)
        state.bundle = Bundle(snap, SearchEngine(snap), images)
        state.error = None
    except CatalogError as e:
        state.error = e
        if state.bundle is None:
            return
        raise


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Adapter khởi tạo rẻ (chưa nạp trọng số); trọng số nạp ở lần dùng đầu.
    state.voice = VoiceService.from_env()
    state.image_embedder, state.image_status = adapter_from_env("VNSTORE_IMAGE_ADAPTER", ImageEmbedder)
    reload_catalog()
    yield


app = FastAPI(title="VNStore API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("VNSTORE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def bundle() -> Bundle:
    if state.bundle is None:
        detail = {"code": "catalog_unavailable", "message": "Catalog chưa nạp được"}
        if state.error:
            detail["errors"] = [str(i) for i in state.error.issues[:20]] or [str(state.error)]
        raise HTTPException(503, detail)
    return state.bundle


def _product_or_404(snap: CatalogSnapshot, key: str) -> dict[str, Any]:
    p = snap.products.get(key)
    if p is None:
        p = next((x for x in snap.products.values() if x["slug"] == key), None)
    if p is None:
        raise HTTPException(404, {"code": "not_found", "message": "Không tìm thấy sản phẩm"})
    return p


@app.get("/health")
def health() -> dict[str, Any]:
    if state.bundle is None:
        return {"status": "error", "catalog": None,
                "errors": [str(i) for i in state.error.issues[:20]] if state.error else []}
    s = state.bundle.snap
    return {
        "status": "ok",
        "catalog": {
            "path": s.path.name,
            "version": s.version,
            "sha256": s.sha256,
            "loaded_at": s.loaded_at,
            "products_visible": len(s.products),
            "products_total": len(s.data["products"]),
            "include_drafts": s.include_drafts,
            "warnings": len(s.warnings),
        },
        "search": {"keyword": "ok", "index_build_ms": state.bundle.engine.build_ms,
                   "voice": state.voice.status.state, "image": _image_status().state,
                   "models": {"voice": state.voice.status.public(), "image": _image_status().public()}},
    }


@app.get("/products")
def list_products(
    category_id: str | None = None,
    brand_id: str | None = None,
    maker_id: str | None = None,
    place_id: str | None = None,
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    b = bundle()
    s = b.snap
    items = list(s.products.values())
    if category_id:
        sub = s.category_subtree(category_id)
        items = [p for p in items if p["category_id"] in sub]
    if brand_id:
        items = [p for p in items if p["brand_id"] == brand_id]
    if maker_id:
        items = [p for p in items if p["maker_id"] == maker_id]
    if place_id:
        items = [p for p in items if place_id == p["origin"]["craft_village_id"] or place_id in p["origin"]["place_ids"]]
    items.sort(key=lambda p: p["name_vi"])
    return {
        "total": len(items),
        "results": [product_summary(s, p) for p in items[offset:offset + limit]],
        "facets": b.engine.facets([p["id"] for p in items]),
    }


@app.get("/products/{key}")
def get_product(key: str) -> dict[str, Any]:
    s = bundle().snap
    return product_detail(s, _product_or_404(s, key))


@app.get("/products/{key}/similar")
def similar_products(key: str, limit: int = Query(8, ge=1, le=24)) -> dict[str, Any]:
    """Tương tự theo thuộc tính có nguồn (danh mục, chất liệu, làng nghề, kỹ thuật)."""
    s = bundle().snap
    p = _product_or_404(s, key)
    root = (s.category_path(p["category_id"]) or [{"id": None}])[0]["id"]
    mats, techs = set(p.get("materials", [])), set(p.get("craft_techniques", []))
    scored = []
    for q in s.products.values():
        if q["id"] == p["id"]:
            continue
        score = 0.0
        if q["category_id"] == p["category_id"]:
            score += 3
        elif root and (s.category_path(q["category_id"]) or [{"id": None}])[0]["id"] == root:
            score += 1
        score += len(mats & set(q.get("materials", [])))
        score += 0.5 * len(techs & set(q.get("craft_techniques", [])))
        if p["origin"]["craft_village_id"] and q["origin"]["craft_village_id"] == p["origin"]["craft_village_id"]:
            score += 1
        if score > 0:
            scored.append((score, q))
    scored.sort(key=lambda x: (-x[0], x[1]["name_vi"]))
    return {"results": [product_summary(s, q) for _, q in scored[:limit]]}


@app.get("/categories")
def categories() -> list[dict[str, Any]]:
    s = bundle().snap
    counts: dict[str, int] = {}
    for p in s.products.values():
        for c in s.category_path(p["category_id"]):
            counts[c["id"]] = counts.get(c["id"], 0) + 1

    def node(c: dict[str, Any]) -> dict[str, Any]:
        return {"id": c["id"], "name_vi": c["name_vi"], "count": counts.get(c["id"], 0),
                "children": [node(s.categories[x]) for x in s.category_children.get(c["id"], [])]}

    return [node(c) for c in s.categories.values() if c["parent_id"] is None]


def _count_by(s: CatalogSnapshot, key) -> dict[str, int]:
    out: dict[str, int] = {}
    for p in s.products.values():
        for k in key(p):
            if k:
                out[k] = out.get(k, 0) + 1
    return out


@app.get("/brands")
def brands() -> list[dict[str, Any]]:
    s = bundle().snap
    counts = _count_by(s, lambda p: [p["brand_id"]])
    return sorted(({"id": b["id"], "name": b["name"], "official_url": b.get("official_url"),
                    "origin_country": b.get("origin_country"), "count": counts.get(b["id"], 0)}
                   for b in s.brands.values()), key=lambda x: x["name"])


@app.get("/makers")
def makers() -> list[dict[str, Any]]:
    s = bundle().snap
    counts = _count_by(s, lambda p: [p["maker_id"]])
    return sorted(({"id": m["id"], "name": m["name"], "maker_type": m["maker_type"],
                    "official_url": m.get("official_url"), "count": counts.get(m["id"], 0)}
                   for m in s.makers.values()), key=lambda x: x["name"])


@app.get("/places")
def places(place_type: str | None = None) -> list[dict[str, Any]]:
    s = bundle().snap
    counts = _count_by(s, lambda p: {p["origin"]["craft_village_id"], *p["origin"]["place_ids"]})
    return sorted(({"id": pl["id"], "name": pl["name_normalized"], "name_as_sourced": pl["name_as_sourced"],
                    "place_type": pl["place_type"], "count": counts.get(pl["id"], 0)}
                   for pl in s.places.values() if place_type is None or pl["place_type"] == place_type),
                  key=lambda x: x["name"])


@app.get("/facets")
def facets() -> dict[str, Any]:
    return bundle().engine.facets()


@app.get("/suggest")
def suggest(q: str = Query("", max_length=200), limit: int = Query(8, ge=1, le=20)) -> list[dict[str, Any]]:
    return bundle().engine.suggest(q, limit)


class FiltersIn(BaseModel):
    category_ids: list[str] = Field(default_factory=list)
    brand_ids: list[str] = Field(default_factory=list)
    maker_ids: list[str] = Field(default_factory=list)
    place_ids: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    claim_types: list[str] = Field(default_factory=list)
    price_min: int | None = Field(None, ge=0)
    price_max: int | None = Field(None, ge=0)


class SearchIn(BaseModel):
    query: str = Field("", max_length=300)
    filters: FiltersIn = Field(default_factory=FiltersIn)
    limit: int = Field(24, ge=1, le=100)
    offset: int = Field(0, ge=0)


@app.post("/search")
def search(body: SearchIn) -> dict[str, Any]:
    return bundle().engine.search(body.query, SearchFilters(**body.filters.model_dump()), body.limit, body.offset)


def _image_status() -> Status:
    b = state.bundle
    return b.images.status if b and b.images else state.image_status


def _error(status: int, code: str, message: str, **extra: Any) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": {"code": code, "message": message, **extra}})


def _model_unavailable(kind: str, st: Status) -> JSONResponse:
    reason = STATE_MESSAGES.get(st.state, st.state)
    return _error(503, "model_unavailable", f"Tìm bằng {kind} chưa sẵn sàng: {reason}. Bạn vẫn có thể tìm bằng chữ.",
                  state=st.state)


async def _read_body(request: Request, limit: int) -> bytes:
    """Đọc body có giới hạn; không tin Content-Length, dừng ngay khi vượt."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise MediaError("too_large", f"File vượt {limit // (1024 * 1024)} MB.", 413)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise MediaError("too_large", f"File vượt {limit // (1024 * 1024)} MB.", 413)
        chunks.append(chunk)
    return b"".join(chunks)


BUSY_MESSAGE = "Máy chủ đang xử lý yêu cầu khác. Thử lại sau vài giây."


@app.post("/search/voice")
async def search_voice(request: Request, limit: int = Query(24, ge=1, le=100)) -> Any:
    """Body: WAV PCM 16-bit (trình duyệt tự mã hóa). Trả bản chép lời + kết quả tìm theo bản chép lời."""
    voice = state.voice
    if not voice.status.ok:
        return _model_unavailable("giọng nói", voice.status)
    b = bundle()
    t0 = time.perf_counter()
    try:
        data = await _read_body(request, MAX_AUDIO_BYTES)
        text, clip, timings = await run_in_threadpool(voice.transcribe, data)
    except MediaError as e:
        return _error(e.status, e.code, e.message)
    except Busy:
        return _error(429, "busy", BUSY_MESSAGE)
    except Exception as e:  # noqa: BLE001 — lỗi model không làm sập API
        return _error(503, "model_error", f"Model giọng nói gặp lỗi ({type(e).__name__}). Thử lại hoặc gõ chữ.")
    out = b.engine.search(text, limit=limit)
    out["mode"] = "voice"
    out["transcript"] = {"text": text, "model_id": voice.status.model_id, "revision": voice.status.revision,
                         "duration_s": round(clip.duration_s, 2), "editable": True}
    out["timings_ms"] = {**out["timings_ms"], **timings, "total": round((time.perf_counter() - t0) * 1000, 2)}
    return out


@app.post("/search/image")
async def search_image(request: Request, text: str = Query("", max_length=300),
                       filters: str = Query("", max_length=4000), limit: int = Query(24, ge=1, le=100)) -> Any:
    """Body: ảnh JPEG/PNG/WebP (giao diện cắt vùng và bỏ metadata trước khi gửi). Tham số text là yêu cầu
    bổ sung tiếng Việt, ví dụ "có quai, dưới 400k": giá/phủ định là bộ lọc cứng như tìm bằng chữ.
    filters là JSON cùng dạng với bộ lọc của POST /search (body đã dành cho ảnh nên đi qua query)."""
    try:
        chosen = SearchFilters(**FiltersIn.model_validate_json(filters or "{}").model_dump())
    except ValidationError:
        return _error(422, "invalid_filters", "Bộ lọc không hợp lệ.")
    b = bundle()
    images = b.images
    if images is None or not images.status.ok:
        return _model_unavailable("ảnh", _image_status())
    t0 = time.perf_counter()
    try:
        data = await _read_body(request, MAX_IMAGE_BYTES)
        hits, timings = await run_in_threadpool(images.query, data, set(b.snap.products))
    except MediaError as e:
        return _error(e.status, e.code, e.message)
    except Busy:
        return _error(429, "busy", BUSY_MESSAGE)
    except Exception as e:  # noqa: BLE001
        return _error(503, "model_error", f"Model ảnh gặp lỗi ({type(e).__name__}). Thử lại hoặc gõ chữ.")
    out = b.engine.search_visual(hits, text, chosen, limit=limit)
    out["mode"] = "image"
    out["visual"] = {"model_id": images.status.model_id, "revision": images.status.revision,
                     "top_similarity": hits[0].similarity if hits else None, "match_label": "similar"}
    out["warnings"].append("Kết quả là mẫu giống về hình ảnh, không khẳng định đúng sản phẩm; "
                           "nhãn nguồn gốc lấy từ catalog, không suy ra từ ảnh.")
    out["timings_ms"] = {**out["timings_ms"], **timings, "total": round((time.perf_counter() - t0) * 1000, 2)}
    return out


@app.get("/images/{image_id}")
def image(image_id: str) -> FileResponse:
    fp = bundle().snap.image_path(image_id)
    if fp is None:
        raise HTTPException(404, {"code": "not_found", "message": "Không tìm thấy ảnh"})
    return FileResponse(fp, headers={"Cache-Control": "public, max-age=3600"})
