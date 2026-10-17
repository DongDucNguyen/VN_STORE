"""Dịch vụ trợ lý: nạp model theo biến môi trường, giới hạn đồng thời/tần suất, lưu phiên theo mức đồng ý.

    VNSTORE_ASSISTANT=off                 tắt hẳn trợ lý (API trả 503)
    VNSTORE_LLM_ADAPTER=module:Class      model (vd. app.ml.llm:Qwen3_4B_Instruct). Không đặt → chế độ cơ bản: hiểu yêu cầu
                                          bằng luật, gợi ý từ kết quả tìm kiếm, không có câu chữ do model viết.
    VNSTORE_LLM_PRELOAD=1                 nạp model lúc khởi động API
    VNSTORE_ASSISTANT_DB                  đường dẫn SQLite (mặc định var/assistant/assistant.db)
    VNSTORE_ASSISTANT_SLOTS               số lượt chạy cùng lúc (mặc định 1)
    VNSTORE_ASSISTANT_TURN_TIMEOUT        giây cho một lượt (mặc định 60)
"""
from __future__ import annotations

import os
import copy
import threading
import time
import uuid
from collections import OrderedDict, deque
from typing import Any, Protocol, runtime_checkable

from ..adapters import Gate
from ..modalities import Status, adapter_from_env
from . import memory, prompts
from .store import CONSENT_TEXT_VERSION, Store

RATE_LIMIT = (20, 600)       # 20 tin nhắn / 10 phút / khách
MAX_TURNS = 40               # lượt khách mỗi phiên
IDLE_MINUTES = 30
TRANSIENT_SESSIONS = 500


@runtime_checkable
class LLMAdapter(Protocol):
    model_id: str
    revision: str

    def generate(self, messages, max_new_tokens=512, on_text=None, deadline_s=None):
        ...


class RateLimited(Exception):
    pass


class AssistantService:
    def __init__(self, llm: Any | None, status: Status, store: Store, slots: int = 1, enabled: bool = True):
        self.llm, self.status, self.store, self.enabled = llm, status, store, enabled
        self.gate = Gate(slots)
        self._rate: dict[str, deque[float]] = {}
        self._rate_lock = threading.Lock()
        # Mức "không lưu": lịch sử chỉ nằm trong RAM của tiến trình, mất khi phiên kết thúc/hết hạn.
        self.transient: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        self._transient_lock = threading.RLock()
        self.transient_state: dict[str, dict[str, Any]] = {}
        # Serialize short persistence/consent operations, never model inference.
        self.session_lock = threading.RLock()
        self._last_purge = 0.0

    @classmethod
    def from_env(cls, store: Store | None = None) -> "AssistantService":
        enabled = os.environ.get("VNSTORE_ASSISTANT", "on").strip().lower() not in ("off", "0", "false")
        store = store or Store()
        llm, status = (adapter_from_env("VNSTORE_LLM_ADAPTER", LLMAdapter) if enabled
                       else (None, Status("unavailable", detail="VNSTORE_ASSISTANT=off")))
        slots = int(os.environ.get("VNSTORE_ASSISTANT_SLOTS", "1") or 1)
        return cls(llm, status, store, slots, enabled)

    @property
    def mode(self) -> str:
        """ok: có model; basic: chạy không model; off: tắt."""
        if not self.enabled:
            return "off"
        return "ok" if self.llm is not None and self.status.ok else "basic"

    def public_status(self) -> dict[str, Any]:
        return {"state": self.mode, "model": self.status.public(), "prompt_version": prompts.current_version()}

    def preload(self) -> None:
        warm = getattr(self.llm, "warmup", None)
        if callable(warm):
            try:
                warm()
            except Exception as e:  # noqa: BLE001 — model hỏng: chuyển chế độ cơ bản, API vẫn chạy
                self.status = Status("error", self.status.model_id, self.status.revision, f"{type(e).__name__}: {e}")
                self.llm = None

    # ---------- giới hạn ----------

    def check_rate(self, cid: str) -> None:
        limit, window = RATE_LIMIT
        t = time.monotonic()
        with self._rate_lock:
            # Expire abandoned clients instead of retaining a deque forever.
            for key in [key for key, values in self._rate.items() if not values or t - values[-1] > window]:
                del self._rate[key]
            q = self._rate.setdefault(cid, deque())
            while q and t - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                raise RateLimited()
            q.append(t)

    # ---------- phiên ----------

    @staticmethod
    def consent_needed(cust) -> bool:
        """Chưa từng chọn (consent_at còn bằng lúc tạo) hoặc văn bản thông báo đã đổi."""
        return cust["consent_text_version"] != CONSENT_TEXT_VERSION or cust["consent_at"] == cust["created_at"]

    def new_session(self, cid: str, entry_point: str | None) -> str:
        self.maintenance()
        cust = self.store.ensure_customer(cid)
        for s in self.store.q("SELECT id FROM sessions WHERE customer_id = ? AND ended_at IS NULL", (cid,)):
            self.end_session(s["id"])
        sid = uuid.uuid4().hex
        model = self.llm if self.mode == "ok" else None
        self.store.create_session(sid, cid, entry_point, getattr(model, "model_id", None),
                                  getattr(model, "revision", None), prompts.current_version(),
                                  persisted=cust["consent_level"] != "none")
        return sid

    def history(self, sid: str) -> list[dict[str, Any]]:
        s = self.store.session(sid)
        if s is None:
            return []
        if s["persisted"]:
            return [{"role": m["role"], "content": m["content"]} for m in self.store.messages(sid)]
        with self._transient_lock:
            return list(self.transient.get(sid, []))

    def append_transient(self, sid: str, role: str, content: str) -> None:
        with self._transient_lock:
            self.transient.setdefault(sid, []).append({"role": role, "content": content})
            self.transient.move_to_end(sid)
            while len(self.transient) > TRANSIENT_SESSIONS:
                old, _ = self.transient.popitem(last=False)
                self.transient_state.pop(old, None)

    def forget_transient(self, sid: str) -> None:
        with self._transient_lock:
            self.transient.pop(sid, None)
            self.transient_state.pop(sid, None)

    def session_state(self, sid: str) -> dict[str, Any]:
        s = self.store.session(sid)
        if s is None:
            return {}
        if s["persisted"]:
            return self.store.session_state(sid)
        with self._transient_lock:
            return copy.deepcopy(self.transient_state.get(sid, {}))

    def save_session_state(self, sid: str, state: dict[str, Any]) -> None:
        s = self.store.session(sid)
        if s is None or s["ended_at"]:
            return
        if s["persisted"]:
            self.store.save_session_state(sid, state)
        else:
            with self._transient_lock:
                self.transient_state[sid] = copy.deepcopy(state)
            from .store import iso, now
            self.store.x("UPDATE sessions SET state_json = '{}', last_active_at = ? WHERE id = ?", (iso(now()), sid))

    def set_consent(self, cid: str, level: str) -> None:
        with self.session_lock:
            self.store.set_consent(cid, level)
            for s in self.store.q("SELECT id FROM sessions WHERE customer_id = ? AND ended_at IS NULL", (cid,)):
                # A new consent applies prospectively; old private context is not promoted to disk.
                self.forget_transient(s["id"])
                self.store.x("UPDATE sessions SET persisted = ? WHERE id = ?", (int(level != "none"), s["id"]))

    def end_session(self, sid: str) -> None:
        with self.session_lock:
            self._end_session(sid)

    def _end_session(self, sid: str) -> None:
        s = self.store.session(sid)
        if s is None or s["ended_at"]:
            return
        cust = self.store.customer(s["customer_id"])
        level = cust["consent_level"] if cust else "none"
        if level == "memory":
            users = [m["content"] for m in self.store.messages(sid) if m["role"] == "user"]
            recs = self.store.session_recommendations(sid)
            catalog = self.catalog_provider()
            facts = memory.extract(catalog.engine, users) if users and catalog else []
            memory.remember(self.store, s["customer_id"], sid, facts)

            def names(ids: list[str]) -> list[str]:
                out = []
                for pid in dict.fromkeys(ids):
                    p = catalog.product(pid) if catalog else None
                    out.append(p["name_vi"] if p else pid)
                return out
            self.store.end_session(sid, memory.session_summary(
                users, names([r["product_id"] for r in recs]), names([r["product_id"] for r in recs
                                                                      if r["clicked_at"]])))
        elif level == "history":
            self.store.end_session(sid, None)
        else:
            self.forget_transient(sid)
            self.store.x("DELETE FROM sessions WHERE id = ?", (sid,))

    def catalog_provider(self):
        """Catalog của snapshot hiện tại; main.py thay hàm này khi gắn router (dịch vụ không giữ snapshot cũ)."""
        return None

    def maintenance(self) -> None:
        t = time.monotonic()
        if t - self._last_purge < 600:
            return
        self._last_purge = t
        for s in self.store.idle_sessions(IDLE_MINUTES):
            self.end_session(s["id"])
        self.store.purge_expired()
