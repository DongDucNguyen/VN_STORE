"""API trợ lý (docs/ke-hoach-tro-ly-ai.md §9). Gắn vào app bằng build_router(get_service, get_catalog).

Định danh khách: cookie `vnstore_cid` ngẫu nhiên, HttpOnly; DB chỉ lưu mã băm. Câu trả lời trả về dạng SSE
(text/event-stream) với các sự kiện: session, status, delta, cards, clarify, evaluation, assessment, comparison,
saved, warning, error, done.
"""
from __future__ import annotations

import json
import queue
import secrets
import threading
import time
from collections.abc import Callable, AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from . import memory, moderation, prompts
from .orchestrator import Turn, turn_timeout
from .privacy import redact
from .reviews import summarize
from .service import MAX_TURNS, AssistantService, RateLimited
from .store import CONSENT_TEXT_VERSION, customer_hash, iso, now
from .tools import Catalog

COOKIE = "vnstore_cid"
COOKIE_MAX_AGE = 180 * 24 * 3600
CONSENT_TEXT_VI = {
    "none": "Không lưu: lịch sử chỉ giữ trong phiên này và bị xóa khi bạn đóng trò chuyện.",
    "history": "Lưu lịch sử 90 ngày để bạn xem lại; không ghi nhớ sở thích.",
    "memory": ("Lưu lịch sử và ghi nhớ sở thích mua sắm (ngân sách, chất liệu, người nhận quà, dịp) để gợi ý tốt hơn "
               "ở lần sau. Không ghi nhớ thông tin nhạy cảm. Bạn xem, sửa, xóa được bất cứ lúc nào."),
}


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": {"code": code, "message": message}})


class SessionIn(BaseModel):
    entry_point: str | None = Field(None, max_length=120)
    product_id: str | None = Field(None, max_length=200)


class MessageIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    input_mode: Literal["text", "voice"] = "text"
    context_product_id: str | None = Field(None, max_length=200)


class ConsentIn(BaseModel):
    level: Literal["none", "history", "memory"]


class FactEditIn(BaseModel):
    label_vi: str = Field(..., min_length=1, max_length=120)


class RecEventIn(BaseModel):
    event: Literal["clicked", "favorited", "feedback"]
    value: int | None = Field(None, ge=-1, le=1)


class ReviewIn(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    body_vi: str = Field(..., min_length=10, max_length=2000)
    title_vi: str | None = Field(None, max_length=120)
    author_display: str | None = Field(None, max_length=60)


def _sse(kind: str, data: dict[str, Any]) -> str:
    return f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_router(get_service: Callable[[], AssistantService], get_catalog: Callable[[], Catalog]) -> APIRouter:
    r = APIRouter()

    def service() -> AssistantService:
        svc = get_service()
        if svc is None or not svc.enabled:
            raise HTTPException(503, {"code": "assistant_unavailable",
                                      "message": "Trợ lý đang tắt. Bạn vẫn có thể tìm bằng chữ, giọng nói hoặc ảnh."})
        return svc

    def customer(request: Request, response: Response | None = None, create: bool = True) -> str | None:
        raw = request.cookies.get(COOKIE)
        if not raw and not create:
            return None
        if not raw or len(raw) < 20:
            raw = secrets.token_urlsafe(24)
            if response is not None:
                response.set_cookie(COOKIE, raw, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax",
                                    secure=request.url.scheme == "https")
        request.state.cid_raw = raw
        return customer_hash(raw)

    def own_session(svc: AssistantService, sid: str, cid: str | None):
        s = svc.store.session(sid)
        if s is None or cid is None or s["customer_id"] != cid:
            raise HTTPException(404, {"code": "session_not_found", "message": "Không tìm thấy phiên trò chuyện"})
        return s

    @r.post("/assistant/sessions")
    def create_session(body: SessionIn, request: Request, response: Response) -> dict[str, Any]:
        svc = service()
        cid = customer(request, response)
        sid = svc.new_session(cid, body.entry_point or (f"product:{body.product_id}" if body.product_id else None))
        cust = svc.store.customer(cid)
        return {"session_id": sid, "consent_level": cust["consent_level"],
                "consent_needed": svc.consent_needed(cust), "consent_options": CONSENT_TEXT_VI,
                "consent_text_version": CONSENT_TEXT_VERSION, "greeting_vi": prompts.GREETING_VI,
                "assistant": svc.public_status()}

    @r.get("/assistant/sessions/{sid}")
    def get_session(sid: str, request: Request) -> dict[str, Any]:
        svc = service()
        s = own_session(svc, sid, customer(request, create=False))
        msgs = []
        if s["persisted"]:
            for m in svc.store.messages(sid):
                msgs.append({"role": m["role"], "content": m["content"], "created_at": m["created_at"],
                             "payload": json.loads(m["payload_json"]) if m["payload_json"] else None})
        else:
            msgs = svc.history(sid)
        return {"session_id": sid, "started_at": s["started_at"], "ended_at": s["ended_at"], "messages": msgs}

    @r.post("/assistant/sessions/{sid}/messages")
    def post_message(sid: str, body: MessageIn, request: Request) -> Any:
        svc = service()
        cid = customer(request, create=False)
        s = own_session(svc, sid, cid)
        if s["ended_at"]:
            return _error(409, "session_ended", "Phiên đã kết thúc, hãy mở phiên mới.")
        try:
            svc.check_rate(cid)
        except RateLimited:
            return _error(429, "rate_limited", "Bạn gửi hơi nhanh, đợi một chút rồi thử lại nhé.")
        history = svc.history(sid)
        if sum(1 for m in history if m["role"] == "user") >= MAX_TURNS:
            return _error(409, "session_full", "Phiên này đã dài, hãy mở phiên mới để tiếp tục.")
        catalog = get_catalog()
        text = redact(" ".join(body.text.split()))
        if not text:
            return _error(422, "empty_message", "Bạn hãy nhập nội dung tin nhắn.")
        state = svc.session_state(sid)
        cust = svc.store.customer(cid)
        level = cust["consent_level"]
        profile = memory.profile_block(svc.store, cid, exclude_session=sid) if level == "memory" else ""
        context_pid = body.context_product_id if body.context_product_id in catalog.snap.products else None
        events: queue.Queue = queue.Queue()
        cancelled = threading.Event()

        def emit(kind: str, data: dict[str, Any]) -> None:
            if cancelled.is_set():
                raise RuntimeError("client_disconnected")
            events.put((kind, data))

        llm = svc.llm if svc.mode == "ok" else None

        def work() -> None:
            t0 = time.perf_counter()
            try:
                res = Turn(catalog, llm, emit, turn_timeout()).run(text, history, state, profile, context_pid)
                latency = int((time.perf_counter() - t0) * 1000)
                cat = (catalog.snap.version, catalog.snap.sha256)
                rec_ids: list[int] = []
                with svc.session_lock:
                    current = svc.store.session(sid)
                    if cancelled.is_set() or current is None or current["ended_at"]:
                        return
                    latest_customer = svc.store.customer(cid)
                    if latest_customer is None or latest_customer["consent_at"] != cust["consent_at"]:
                        events.put(("error", {"code": "consent_changed",
                                             "message": "Lựa chọn lưu đã thay đổi. Bạn gửi lại tin nhắn nhé."}))
                        return
                    persisted = bool(current["persisted"])
                    if persisted:
                        svc.store.add_message(sid, "user", text, None, body.input_mode, cat)
                        mid = svc.store.add_message(sid, "assistant", res.message, res.payload(), None, cat,
                                                   {"prompt_tokens": res.prompt_tokens,
                                                    "output_tokens": res.output_tokens}, latency)
                        rec_ids = svc.store.add_recommendations(mid, res.recommendations) if res.intent in (
                            "recommend", "compare") else []
                    else:
                        svc.append_transient(sid, "user", text)
                        svc.append_transient(sid, "assistant", res.message)
                    svc.save_session_state(sid, res.state)
                    for check, action, detail in res.events:
                        # Details may contain generated text; private sessions leave only counters.
                        svc.store.grounding_event(sid if persisted else None, check, action, detail if persisted else "")
                svc.store.turn_metric(getattr(llm, "model_id", None), res.intent, not res.fallback, res.fallback,
                                      latency, res.prompt_tokens, res.output_tokens)
                if rec_ids:
                    events.put(("saved", {"recommendation_ids": rec_ids}))
                events.put(("done", {"intent": res.intent, "message": res.message, "fallback": res.fallback,
                                     "mode": svc.mode, "catalog_version": catalog.snap.version,
                                     "timings_ms": {**res.timings_ms, "total": latency},
                                     "usage": {"prompt_tokens": res.prompt_tokens,
                                               "output_tokens": res.output_tokens}}))
            except Exception as e:  # noqa: BLE001
                if not cancelled.is_set():
                    events.put(("error", {"code": "assistant_error",
                                          "message": f"Trợ lý gặp lỗi ({type(e).__name__}). Bạn thử lại hoặc tìm "
                                                     "bằng ô tìm kiếm nhé."}))
            finally:
                slot.__exit__(None, None, None)
                events.put(None)

        # Giữ chỗ ngay trước khi chạy: mọi lỗi phía trên trả về mà không chiếm chỗ; work() luôn trả chỗ trong finally.
        slot = svc.gate.slot()
        try:
            slot.__enter__()
        except Exception:  # noqa: BLE001 — Busy
            return _error(429, "busy", "Trợ lý đang trả lời người khác. Thử lại sau vài giây.")
        try:
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            slot.__exit__(None, None, None)
            raise

        async def stream() -> AsyncIterator[str]:
            try:
                yield _sse("session", {"session_id": sid, "mode": svc.mode})
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        item = await run_in_threadpool(events.get, True, 0.5)
                    except queue.Empty:
                        continue
                    if item is None:
                        break
                    yield _sse(*item)
            finally:
                cancelled.set()

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @r.post("/assistant/sessions/{sid}/end")
    def end_session(sid: str, request: Request) -> dict[str, Any]:
        svc = service()
        own_session(svc, sid, customer(request, create=False))
        svc.end_session(sid)
        return {"ended": True}

    @r.delete("/assistant/sessions/{sid}")
    def delete_session(sid: str, request: Request) -> dict[str, Any]:
        svc = service()
        cid = customer(request, create=False)
        own_session(svc, sid, cid)
        with svc.session_lock:
            svc.forget_transient(sid)
            return {"deleted": svc.store.delete_session(sid, cid)}

    @r.post("/assistant/recommendations/{rid}/event")
    def rec_event(rid: int, body: RecEventIn, request: Request) -> dict[str, Any]:
        svc = service()
        cid = customer(request, create=False)
        if cid is None or svc.store.recommendation_owner(rid) != cid:
            raise HTTPException(404, {"code": "not_found", "message": "Không tìm thấy gợi ý"})
        svc.store.recommendation_event(rid, body.event, body.value)
        return {"ok": True}

    @r.get("/assistant/me")
    def me(request: Request, response: Response) -> dict[str, Any]:
        svc = service()
        cid = customer(request, response)
        cust = svc.store.ensure_customer(cid)
        sessions = [{"id": s["id"], "started_at": s["started_at"], "ended_at": s["ended_at"],
                     "summary_vi": s["summary_vi"],
                     "first_message": next((m["content"][:120] for m in svc.store.messages(s["id"])
                                            if m["role"] == "user"), None)}
                    for s in svc.store.sessions_for(cid)]
        return {"consent_level": cust["consent_level"], "consent_needed": svc.consent_needed(cust),
                "consent_options": CONSENT_TEXT_VI, "facts": memory.public_facts(svc.store, cid),
                "sessions": sessions, "assistant": svc.public_status()}

    @r.put("/assistant/me/consent")
    def set_consent(body: ConsentIn, request: Request, response: Response) -> dict[str, Any]:
        svc = service()
        cid = customer(request, response)
        svc.set_consent(cid, body.level)
        return {"consent_level": body.level}

    @r.patch("/assistant/me/facts/{fid}")
    def edit_fact(fid: int, body: FactEditIn, request: Request) -> dict[str, Any]:
        svc = service()
        if not svc.store.edit_fact(customer(request, create=False) or "", fid, body.label_vi.strip()):
            raise HTTPException(404, {"code": "not_found", "message": "Không tìm thấy mục ghi nhớ"})
        return {"ok": True}

    @r.delete("/assistant/me/facts/{fid}")
    def delete_fact(fid: int, request: Request) -> dict[str, Any]:
        svc = service()
        if not svc.store.delete_fact(customer(request, create=False) or "", fid):
            raise HTTPException(404, {"code": "not_found", "message": "Không tìm thấy mục ghi nhớ"})
        return {"ok": True}

    @r.delete("/assistant/me")
    def delete_me(request: Request, response: Response) -> dict[str, Any]:
        svc = service()
        cid = customer(request, create=False)
        if cid:
            with svc.session_lock:
                for s in svc.store.q("SELECT id FROM sessions WHERE customer_id = ?", (cid,)):
                    svc.forget_transient(s["id"])
                svc.store.delete_customer(cid)
        response.delete_cookie(COOKIE)
        return {"deleted": True}

    @r.get("/assistant/me/export")
    def export_me(request: Request) -> dict[str, Any]:
        svc = service()
        cid = customer(request, create=False)
        return svc.store.export(cid) if cid else {"customer": None, "memory": [], "sessions": []}

    # ---------- đánh giá sản phẩm ----------

    @r.get("/products/{pid}/reviews")
    def product_reviews(pid: str) -> dict[str, Any]:
        catalog = get_catalog()
        if pid not in catalog.snap.products:
            raise HTTPException(404, {"code": "not_found", "message": "Không tìm thấy sản phẩm"})
        svc = get_service()
        return summarize(svc.store if svc else None, pid).public()

    @r.post("/products/{pid}/reviews")
    def add_review(pid: str, body: ReviewIn, request: Request, response: Response) -> Any:
        catalog = get_catalog()
        if pid not in catalog.snap.products:
            raise HTTPException(404, {"code": "not_found", "message": "Không tìm thấy sản phẩm"})
        svc = service()
        cid = customer(request, response)
        try:
            svc.check_rate(cid)
        except RateLimited:
            return _error(429, "rate_limited", "Bạn gửi hơi nhanh, đợi một chút rồi thử lại nhé.")
        text = redact(body.body_vi)
        passed, reason = moderation.check(text)
        status = "approved" if passed and moderation.auto_approve_enabled() else "pending"
        ok = svc.store.add_review({"product_id": pid, "origin": "vnstore_customer", "author_hash": cid,
                                   "author_display": (body.author_display or "").strip() or None,
                                   "rating": body.rating, "title_vi": body.title_vi, "body_vi": text,
                                   "status": status, "moderation_note": "tự động: " + reason,
                                   "moderated_at": iso(now()) if status == "approved" else None})
        if not ok:
            return _error(409, "duplicate", "Đánh giá này đã được gửi.")
        if status == "approved":
            return {"status": status, "message": "Cảm ơn bạn. Đánh giá đã được đăng."}
        return {"status": status, "message": "Cảm ơn bạn. Đánh giá sẽ hiển thị sau khi được duyệt."}

    return r
