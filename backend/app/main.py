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
    VNSTORE_TEXT_ADAPTER    adapter embedding văn bản cho nhánh ngữ nghĩa (vd. app.ml.text:BGEM3); chỉ có tác dụng khi
                            VNSTORE_SEARCH_CONFIG đặt semantic_weight > 0. Lỗi/thiếu chỉ mục → tìm bằng chữ dùng BM25
    VNSTORE_TEXT_INDEX_DIR  thư mục chỉ mục văn bản (mặc định ../artifacts/indexes/text)
    VNSTORE_LLM_ADAPTER     model của trợ lý tư vấn (vd. app.ml.llm:Qwen3_4B_Instruct); không đặt → trợ lý chế độ cơ bản.
                            Các biến khác của trợ lý: xem app/assistant/service.py
"""
from __future__ import annotations

import os
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from .adapters import Busy, ImageEmbedder
from .assistant.router import build_router as build_assistant_router
from .assistant.service import AssistantService
from .assistant.tools import Catalog
from .catalog.present import product_detail, product_summary
from .catalog.store import CatalogError, CatalogSnapshot, load_snapshot
from .media import MAX_AUDIO_BYTES, MAX_IMAGE_BYTES, MediaError
from .modalities import STATE_MESSAGES, ImageService, Status, VoiceService, adapter_from_env
from .search.engine import SearchEngine, SearchFilters
from .search.semantic import SemanticSearch, TextEmbedder, TextIndexUnavailable
from .voice.suggestions import PhraseSuggester

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Bundle:
    """Catalog và chỉ mục cùng phiên bản; thay nguyên khối, không ghép lẫn."""
    snap: CatalogSnapshot
    engine: SearchEngine
    images: ImageService | None = None  # chỉ mục ảnh đã kiểm tra khớp đúng snapshot này
    voice_suggestions: PhraseSuggester | None = None


class AppState:
    bundle: Bundle | None = None
    error: CatalogError | None = None
    voice: VoiceService = VoiceService(None, Status("unavailable"))
    image_embedder: ImageEmbedder | None = None
    image_status: Status = Status("unavailable")
    text_embedder: TextEmbedder | None = None
    text_status: Status = Status("unavailable")
    assistant: AssistantService | None = None


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
        state.bundle = Bundle(snap, SearchEngine(snap, semantic=_semantic_for(snap)), images, PhraseSuggester(snap))
        state.error = None
    except CatalogError as e:
        state.error = e
        if state.bundle is None:
            return
        raise


def _semantic_for(snap: CatalogSnapshot) -> SemanticSearch | None:
    """Nhánh ngữ nghĩa khớp snapshot, hoặc None (BM25) khi chưa cấu hình/lỗi model/chỉ mục thiếu hay cũ."""
    emb = state.text_embedder
    if emb is None:
        return None
    try:
        semantic = SemanticSearch.for_snapshot(snap, emb)
    except TextIndexUnavailable as e:
        state.text_status = Status(e.code, emb.model_id, emb.revision, str(e))
        return None
    except Exception as e:  # noqa: BLE001 — lỗi model khi dựng chỉ mục chỉ tắt nhánh ngữ nghĩa
        state.text_status = Status("error", emb.model_id, emb.revision, f"{type(e).__name__}: {e}")
        return None
    state.text_status = Status("ok", emb.model_id, emb.revision)
    return semantic


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Adapter khởi tạo rẻ; GPU demo có thể nạp trước English để giảm độ trễ yêu cầu đầu.
    state.voice = VoiceService.from_env()
    state.image_embedder, state.image_status = adapter_from_env("VNSTORE_IMAGE_ADAPTER", ImageEmbedder)
    state.text_embedder, state.text_status = adapter_from_env("VNSTORE_TEXT_ADAPTER", TextEmbedder)
    reload_catalog()
    state.assistant = AssistantService.from_env()
    state.assistant.catalog_provider = _assistant_catalog
    if os.environ.get("VNSTORE_LLM_PRELOAD") == "1":
        await run_in_threadpool(state.assistant.preload)
    if os.environ.get("VNSTORE_ASR_PRELOAD_ENGLISH") == "1" and state.voice.adapter is not None:
        preload = getattr(state.voice.adapter, "preload_english", None)
        if callable(preload):
            await run_in_threadpool(preload)
    yield
    if state.assistant is not None:
        state.assistant.store.close()


app = FastAPI(title="VNStore API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("VNSTORE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,  # cookie khách ẩn danh của trợ lý
)


def bundle() -> Bundle:
    if state.bundle is None:
        detail = {"code": "catalog_unavailable", "message": "Catalog chưa nạp được"}
        if state.error:
            detail["errors"] = [str(i) for i in state.error.issues[:20]] or [str(state.error)]
        raise HTTPException(503, detail)
    return state.bundle


def _assistant_catalog() -> Catalog | None:
    b = state.bundle
    return Catalog(b.snap, b.engine, state.assistant.store if state.assistant else None) if b else None


def _assistant_catalog_or_503() -> Catalog:
    b = bundle()
    return Catalog(b.snap, b.engine, state.assistant.store if state.assistant else None)


app.include_router(build_assistant_router(lambda: state.assistant, _assistant_catalog_or_503))


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
            "publication_mode": (s.data.get("publication_policy") or {}).get("mode", "standard"),
            "warnings": len(s.warnings),
        },
        "search": {"keyword": "ok", "index_build_ms": state.bundle.engine.build_ms,
                   "voice": state.voice.status.state, "image": _image_status().state,
                   "semantic": state.text_status.state if state.bundle.engine.config.semantic_weight else "off",
                   "assistant": state.assistant.mode if state.assistant else "off",
                   "models": {"voice": state.voice.status.public(), "image": _image_status().public(),
                              "text": state.text_status.public(),
                              "assistant": state.assistant.status.public() if state.assistant else None}},
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
async def search_voice(request: Request, limit: int = Query(24, ge=1, le=100),
                       language: Literal["vi", "en", "auto"] | None = None, review: bool = False) -> Any:
    """Body: WAV PCM 16-bit (trình duyệt tự mã hóa). Trả bản chép lời + kết quả tìm theo bản chép lời."""
    voice = state.voice
    if not voice.status.ok:
        return _model_unavailable("giọng nói", voice.status)
    b = bundle()
    t0 = time.perf_counter()
    try:
        data = await _read_body(request, MAX_AUDIO_BYTES)
        body_ms = (time.perf_counter() - t0) * 1000
        recognition, clip, quality, timings = await run_in_threadpool(voice.transcribe_detailed, data, language)
    except MediaError as e:
        return _error(e.status, e.code, e.message)
    except Busy:
        return _error(429, "busy", BUSY_MESSAGE)
    except Exception as e:  # noqa: BLE001 — lỗi model không làm sập API
        logging.getLogger(__name__).exception("Voice inference failed (language=%s)", language)
        return _error(503, "model_error", f"Model giọng nói gặp lỗi ({type(e).__name__}). Thử lại hoặc gõ chữ.")
    text = " ".join(recognition.text.split())
    warnings = []
    if quality["low_volume"]:
        warnings.append("Âm lượng nhỏ. Hãy kiểm tra bản chép lời hoặc nói gần micro hơn và ghi lại.")
    if quality["clipped_fraction"] > 0.01:
        warnings.append("Âm thanh bị vỡ. Hãy giảm mức micro hoặc nói xa micro hơn rồi ghi lại.")
    if recognition.truncated:
        warnings.append("Bản chép lời có thể bị cắt. Hãy nói câu ngắn hơn hoặc sửa trước khi tìm.")
    if recognition.language_probability is not None and recognition.language_probability < 0.8:
        warnings.append("Chưa chắc ngôn ngữ của đoạn nói. Hãy kiểm tra bản chép lời hoặc chọn ngôn ngữ rồi ghi lại.")
    suggestions = (b.voice_suggestions.suggest(text)
                   if b.voice_suggestions and recognition.language in {None, "vi"} else [])
    # Review requests do not execute retrieval until the user confirms a query.
    out = {"warnings": [], "timings_ms": {}} if review else b.engine.search(text, limit=limit)
    out["warnings"].extend(warnings)
    out["mode"] = "voice"
    out["transcript"] = {"text": text, "raw_text": recognition.text,
                         "model_id": recognition.model_id or voice.status.model_id,
                         "revision": recognition.revision or voice.status.revision,
                         "duration_s": round(clip.duration_s, 2), "editable": True,
                         "language": recognition.language, "requested_language": language,
                         "language_probability": recognition.language_probability,
                         "truncated": recognition.truncated, "suggestions": suggestions,
                         "quality": quality, "requires_confirmation": True}
    out["timings_ms"] = {**out["timings_ms"], **timings, "body_read": round(body_ms, 2),
                         "total": round((time.perf_counter() - t0) * 1000, 2)}
    return out


@app.post("/search/image")
async def search_image(request: Request, text: str = Query("", max_length=300),
                       filters: str = Query("", max_length=4000), limit: int = Query(24, ge=1, le=100),
                       reuse: bool = Query(False)) -> Any:
    """Body: ảnh JPEG/PNG/WebP (giao diện cắt vùng và bỏ metadata trước khi gửi). Tham số text là yêu cầu
    bổ sung tiếng Việt, ví dụ "có quai, dưới 400k": giá/phủ định là bộ lọc cứng như tìm bằng chữ.
    filters là JSON cùng dạng với bộ lọc của POST /search (body đã dành cho ảnh nên đi qua query).
    reuse=1 khi gửi lại đúng ảnh vừa tìm để đổi bộ lọc: dùng lại embedding/OCR trong bộ nhớ nếu còn."""
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
        body_ms = (time.perf_counter() - t0) * 1000
        out, diagnostics = await run_in_threadpool(images.search, data, b.engine, text, chosen, limit, reuse)
    except MediaError as e:
        return _error(e.status, e.code, e.message)
    except Busy:
        return _error(429, "busy", BUSY_MESSAGE)
    except Exception as e:  # noqa: BLE001
        return _error(503, "model_error", f"Model ảnh gặp lỗi ({type(e).__name__}). Thử lại hoặc gõ chữ.")
    timings = {k: diagnostics[k + "_ms"] for k in ("validate", "embed", "retrieve", "ocr")}
    out["mode"] = "image"
    out["visual"] = {"model_id": images.status.model_id, "revision": images.status.revision,
                       "top_similarity": diagnostics["top_similarity"], "match_label": "similar",
                       "query_cache": diagnostics["query_cache"]}
    out["warnings"].append("Kết quả là mẫu giống về hình ảnh, không khẳng định đúng sản phẩm; "
                           "nhãn nguồn gốc lấy từ catalog, không suy ra từ ảnh.")
    out["timings_ms"] = {**out["timings_ms"], **timings, "body_read": round(body_ms, 2),
                         "total": round((time.perf_counter() - t0) * 1000, 2)}
    return out


@app.get("/images/{image_id}")
def image(image_id: str) -> FileResponse:
    fp = bundle().snap.image_path(image_id)
    if fp is None:
        raise HTTPException(404, {"code": "not_found", "message": "Không tìm thấy ảnh"})
    media_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                  ".webp": "image/webp"}.get(fp.suffix.lower())
    return FileResponse(fp, media_type=media_type,
                        headers={"Cache-Control": "public, max-age=3600"})
