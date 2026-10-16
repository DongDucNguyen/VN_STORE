"""Kho SQLite của trợ lý: khách (ẩn danh), phiên, tin nhắn, gợi ý, bộ nhớ, đánh giá sản phẩm.

Mặc định ở `var/assistant/assistant.db` (VNSTORE_ASSISTANT_DB; ":memory:" cho test). Dùng sqlite3 của thư viện chuẩn,
WAL, một khóa tiến trình cho mọi lệnh ghi. Lưu mã băm của cookie khách, không lưu cookie gốc. Xóa khách xóa dây chuyền
mọi dữ liệu liên quan (ON DELETE CASCADE) và chỉ để lại một dòng nhật ký xóa không có nội dung.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CONSENT_LEVELS = ("none", "history", "memory")
CONSENT_TEXT_VERSION = "2026-10-15.v1"
HISTORY_DAYS = 90
REVIEW_ORIGINS = ("vnstore_customer", "imported_source", "internal_test")

MIGRATIONS: list[str] = [
    """
    CREATE TABLE customers (
      id TEXT PRIMARY KEY,
      account_id TEXT,
      consent_level TEXT NOT NULL CHECK (consent_level IN ('none','history','memory')),
      consent_text_version TEXT NOT NULL,
      consent_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      last_seen_at TEXT NOT NULL
    );
    CREATE TABLE sessions (
      id TEXT PRIMARY KEY,
      customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
      started_at TEXT NOT NULL,
      last_active_at TEXT NOT NULL,
      ended_at TEXT,
      entry_point TEXT,
      model_id TEXT, model_revision TEXT, prompt_version TEXT,
      state_json TEXT NOT NULL DEFAULT '{}',
      summary_vi TEXT, summary_at TEXT,
      persisted INTEGER NOT NULL DEFAULT 1,
      expires_at TEXT NOT NULL
    );
    CREATE INDEX sessions_customer ON sessions(customer_id, started_at);
    CREATE TABLE messages (
      id INTEGER PRIMARY KEY,
      session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
      role TEXT NOT NULL CHECK (role IN ('user','assistant')),
      content TEXT NOT NULL,
      payload_json TEXT,
      input_mode TEXT,
      catalog_version TEXT, catalog_sha256 TEXT,
      usage_json TEXT, latency_ms INTEGER,
      created_at TEXT NOT NULL
    );
    CREATE INDEX messages_session ON messages(session_id, id);
    CREATE TABLE recommendations (
      id INTEGER PRIMARY KEY,
      message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
      product_id TEXT NOT NULL,
      rank INTEGER NOT NULL,
      reason_vi TEXT,
      clicked_at TEXT, favorited_at TEXT,
      feedback INTEGER CHECK (feedback IN (-1, 0, 1))
    );
    CREATE TABLE memory_facts (
      id INTEGER PRIMARY KEY,
      customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
      kind TEXT NOT NULL,
      value TEXT NOT NULL,
      label_vi TEXT NOT NULL,
      polarity INTEGER NOT NULL DEFAULT 1,
      origin TEXT NOT NULL CHECK (origin IN ('explicit','inferred','user_edited')),
      confidence REAL NOT NULL,
      source_session_id TEXT,
      created_at TEXT NOT NULL,
      last_confirmed_at TEXT NOT NULL,
      expires_at TEXT,
      UNIQUE (customer_id, kind, value)
    );
    CREATE TABLE grounding_events (
      id INTEGER PRIMARY KEY,
      session_id TEXT,
      check_name TEXT NOT NULL,
      action TEXT NOT NULL,
      detail TEXT,
      created_at TEXT NOT NULL
    );
    CREATE TABLE turn_metrics (
      id INTEGER PRIMARY KEY,
      model_id TEXT, intent TEXT, ok INTEGER NOT NULL, fallback INTEGER NOT NULL,
      latency_ms INTEGER, prompt_tokens INTEGER, output_tokens INTEGER, created_at TEXT NOT NULL
    );
    CREATE TABLE deletion_log (
      id INTEGER PRIMARY KEY,
      customer_hash TEXT NOT NULL,
      scope TEXT NOT NULL,
      deleted_at TEXT NOT NULL
    );
    CREATE TABLE reviews (
      id TEXT PRIMARY KEY,
      product_id TEXT NOT NULL,
      variant_sku TEXT,
      origin TEXT NOT NULL CHECK (origin IN ('vnstore_customer','imported_source','internal_test')),
      source_id TEXT,
      source_url TEXT,
      author_hash TEXT,
      author_display TEXT,
      rating INTEGER CHECK (rating BETWEEN 1 AND 5),
      title_vi TEXT,
      body_vi TEXT NOT NULL,
      verified_purchase INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')),
      moderation_note TEXT,
      created_at TEXT NOT NULL,
      moderated_at TEXT,
      content_sha256 TEXT NOT NULL UNIQUE,
      CHECK (origin != 'imported_source' OR source_id IS NOT NULL)
    );
    CREATE INDEX reviews_product ON reviews(product_id, status);
    """,
]


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def customer_hash(raw_cookie: str) -> str:
    return hashlib.sha256(("vnstore-cid:" + raw_cookie).encode("utf-8")).hexdigest()


def default_path() -> str:
    return os.environ.get("VNSTORE_ASSISTANT_DB", str(ROOT / "var" / "assistant" / "assistant.db"))


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or default_path()
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._db.execute("PRAGMA foreign_keys = ON")
            if self.path != ":memory:":
                self._db.execute("PRAGMA journal_mode = WAL")
            self._migrate()

    # ---------- hạ tầng ----------

    def _migrate(self) -> None:
        self._db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT)")
        done = {r[0] for r in self._db.execute("SELECT version FROM schema_migrations")}
        for v, sql in enumerate(MIGRATIONS, start=1):
            if v in done:
                continue
            self._db.execute("BEGIN")
            try:
                for stmt in [s for s in sql.split(";") if s.strip()]:
                    self._db.execute(stmt)
                self._db.execute("INSERT INTO schema_migrations VALUES (?, ?)", (v, iso(now())))
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def q(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._db.execute(sql, args))

    def x(self, sql: str, args: tuple = ()) -> int:
        with self._lock:
            cur = self._db.execute(sql, args)
            return cur.lastrowid or cur.rowcount

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # ---------- khách và đồng ý ----------

    def ensure_customer(self, cid: str) -> sqlite3.Row:
        t = iso(now())
        with self._lock:
            self._db.execute("INSERT OR IGNORE INTO customers (id, consent_level, consent_text_version, consent_at, "
                             "created_at, last_seen_at) VALUES (?, 'none', ?, ?, ?, ?)",
                             (cid, CONSENT_TEXT_VERSION, t, t, t))
            self._db.execute("UPDATE customers SET last_seen_at = ? WHERE id = ?", (t, cid))
            return self._db.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()

    def customer(self, cid: str) -> sqlite3.Row | None:
        rows = self.q("SELECT * FROM customers WHERE id = ?", (cid,))
        return rows[0] if rows else None

    def set_consent(self, cid: str, level: str) -> None:
        if level not in CONSENT_LEVELS:
            raise ValueError(level)
        old = self.ensure_customer(cid)["consent_level"]
        t = iso(now())
        with self._lock:
            self._db.execute("BEGIN")
            self._db.execute("UPDATE customers SET consent_level = ?, consent_text_version = ?, consent_at = ? "
                             "WHERE id = ?", (level, CONSENT_TEXT_VERSION, t, cid))
            # Hạ mức thì xóa ngay phần vượt mức mới.
            if CONSENT_LEVELS.index(level) < CONSENT_LEVELS.index("memory"):
                self._db.execute("DELETE FROM memory_facts WHERE customer_id = ?", (cid,))
                self._db.execute("UPDATE sessions SET summary_vi = NULL, summary_at = NULL WHERE customer_id = ?",
                                 (cid,))
            if level == "none":
                self._db.execute("DELETE FROM sessions WHERE customer_id = ? AND ended_at IS NOT NULL", (cid,))
                self._db.execute("DELETE FROM messages WHERE session_id IN (SELECT id FROM sessions "
                                 "WHERE customer_id = ?)", (cid,))
                self._db.execute("UPDATE sessions SET persisted = 0 WHERE customer_id = ?", (cid,))
            self._db.execute("COMMIT")
        if old != level:
            self.x("INSERT INTO deletion_log (customer_hash, scope, deleted_at) VALUES (?, ?, ?)",
                   (cid, f"consent:{old}->{level}", t))

    def delete_customer(self, cid: str) -> None:
        with self._lock:
            self._db.execute("BEGIN")
            self._db.execute("DELETE FROM grounding_events WHERE session_id IN (SELECT id FROM sessions "
                             "WHERE customer_id = ?)", (cid,))
            self._db.execute("DELETE FROM customers WHERE id = ?", (cid,))
            self._db.execute("UPDATE reviews SET author_hash = NULL WHERE author_hash = ?", (cid,))
            self._db.execute("INSERT INTO deletion_log (customer_hash, scope, deleted_at) VALUES (?, 'all', ?)",
                             (cid, iso(now())))
            self._db.execute("COMMIT")

    # ---------- phiên ----------

    def create_session(self, sid: str, cid: str, entry_point: str | None, model_id: str | None,
                       revision: str | None, prompt_version: str, persisted: bool) -> None:
        t = now()
        self.x("INSERT INTO sessions (id, customer_id, started_at, last_active_at, entry_point, model_id, "
               "model_revision, prompt_version, persisted, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
               (sid, cid, iso(t), iso(t), entry_point, model_id, revision, prompt_version, int(persisted),
                iso(t + timedelta(days=HISTORY_DAYS))))

    def session(self, sid: str) -> sqlite3.Row | None:
        rows = self.q("SELECT * FROM sessions WHERE id = ?", (sid,))
        return rows[0] if rows else None

    def session_state(self, sid: str) -> dict[str, Any]:
        s = self.session(sid)
        return json.loads(s["state_json"]) if s else {}

    def save_session_state(self, sid: str, state: dict[str, Any]) -> None:
        self.x("UPDATE sessions SET state_json = ?, last_active_at = ? WHERE id = ?",
               (json.dumps(state, ensure_ascii=False), iso(now()), sid))

    def end_session(self, sid: str, summary: str | None) -> None:
        self.x("UPDATE sessions SET ended_at = COALESCE(ended_at, ?), summary_vi = COALESCE(?, summary_vi), "
               "summary_at = CASE WHEN ? IS NULL THEN summary_at ELSE ? END WHERE id = ?",
               (iso(now()), summary, summary, iso(now()), sid))

    def sessions_for(self, cid: str, limit: int = 20) -> list[sqlite3.Row]:
        return self.q("SELECT * FROM sessions WHERE customer_id = ? AND persisted = 1 ORDER BY started_at DESC "
                      "LIMIT ?", (cid, limit))

    def delete_session(self, sid: str, cid: str) -> bool:
        n = self.x("DELETE FROM sessions WHERE id = ? AND customer_id = ?", (sid, cid))
        if n:
            self.x("INSERT INTO deletion_log (customer_hash, scope, deleted_at) VALUES (?, ?, ?)",
                   (cid, "session", iso(now())))
        return bool(n)

    def idle_sessions(self, idle_minutes: int) -> list[sqlite3.Row]:
        cutoff = iso(now() - timedelta(minutes=idle_minutes))
        return self.q("SELECT * FROM sessions WHERE ended_at IS NULL AND last_active_at < ?", (cutoff,))

    # ---------- tin nhắn ----------

    def add_message(self, sid: str, role: str, content: str, payload: dict | None = None, input_mode: str | None = None,
                    catalog: tuple[str, str] | None = None, usage: dict | None = None,
                    latency_ms: int | None = None) -> int:
        return self.x("INSERT INTO messages (session_id, role, content, payload_json, input_mode, catalog_version, "
                      "catalog_sha256, usage_json, latency_ms, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (sid, role, content, json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                       input_mode, catalog[0] if catalog else None, catalog[1] if catalog else None,
                       json.dumps(usage) if usage else None, latency_ms, iso(now())))

    def messages(self, sid: str) -> list[sqlite3.Row]:
        return self.q("SELECT * FROM messages WHERE session_id = ? ORDER BY id", (sid,))

    def add_recommendations(self, message_id: int, recs: list[tuple[str, str]]) -> list[int]:
        return [self.x("INSERT INTO recommendations (message_id, product_id, rank, reason_vi) VALUES (?,?,?,?)",
                       (message_id, pid, i + 1, reason)) for i, (pid, reason) in enumerate(recs)]

    def recommendation_owner(self, rec_id: int) -> str | None:
        rows = self.q("SELECT s.customer_id FROM recommendations r JOIN messages m ON m.id = r.message_id "
                      "JOIN sessions s ON s.id = m.session_id WHERE r.id = ?", (rec_id,))
        return rows[0][0] if rows else None

    def recommendation_event(self, rec_id: int, event: str, value: int | None = None) -> None:
        if event == "feedback":
            self.x("UPDATE recommendations SET feedback = ? WHERE id = ?", (value, rec_id))
        elif event in ("clicked", "favorited"):
            self.x(f"UPDATE recommendations SET {event}_at = COALESCE({event}_at, ?) WHERE id = ?",
                   (iso(now()), rec_id))
        else:
            raise ValueError(event)

    def session_recommendations(self, sid: str) -> list[sqlite3.Row]:
        return self.q("SELECT r.* FROM recommendations r JOIN messages m ON m.id = r.message_id "
                      "WHERE m.session_id = ? ORDER BY r.id", (sid,))

    # ---------- bộ nhớ ----------

    def facts(self, cid: str, include_expired: bool = False) -> list[sqlite3.Row]:
        if include_expired:
            return self.q("SELECT * FROM memory_facts WHERE customer_id = ? ORDER BY last_confirmed_at DESC", (cid,))
        return self.q("SELECT * FROM memory_facts WHERE customer_id = ? AND (expires_at IS NULL OR expires_at > ?) "
                      "ORDER BY last_confirmed_at DESC", (cid, iso(now())))

    def upsert_fact(self, cid: str, kind: str, value: str, label: str, polarity: int, origin: str,
                    confidence: float, session_id: str | None, ttl_days: int | None) -> None:
        t = now()
        expires = iso(t + timedelta(days=ttl_days)) if ttl_days else None
        with self._lock:
            row = self._db.execute("SELECT * FROM memory_facts WHERE customer_id = ? AND kind = ? AND value = ?",
                                   (cid, kind, value)).fetchone()
            if row is None:
                self._db.execute("INSERT INTO memory_facts (customer_id, kind, value, label_vi, polarity, origin, "
                                 "confidence, source_session_id, created_at, last_confirmed_at, expires_at) "
                                 "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                 (cid, kind, value, label, polarity, origin, confidence, session_id, iso(t), iso(t),
                                  expires))
            elif row["origin"] != "user_edited":
                self._db.execute("UPDATE memory_facts SET label_vi = ?, polarity = ?, confidence = MIN(1.0, "
                                 "MAX(confidence, ?) + 0.1), last_confirmed_at = ?, expires_at = ?, "
                                 "source_session_id = ? WHERE id = ?",
                                 (label, polarity, confidence, iso(t), expires, session_id, row["id"]))

    def delete_fact(self, cid: str, fact_id: int) -> bool:
        return bool(self.x("DELETE FROM memory_facts WHERE id = ? AND customer_id = ?", (fact_id, cid)))

    def edit_fact(self, cid: str, fact_id: int, label: str) -> bool:
        return bool(self.x("UPDATE memory_facts SET label_vi = ?, origin = 'user_edited', last_confirmed_at = ? "
                           "WHERE id = ? AND customer_id = ?", (label, iso(now()), fact_id, cid)))

    def delete_fact_kind(self, cid: str, kind: str, value: str) -> None:
        self.x("DELETE FROM memory_facts WHERE customer_id = ? AND kind = ? AND value = ?", (cid, kind, value))

    # ---------- số đo ẩn danh ----------

    def grounding_event(self, sid: str | None, check: str, action: str, detail: str = "") -> None:
        self.x("INSERT INTO grounding_events (session_id, check_name, action, detail, created_at) VALUES (?,?,?,?,?)",
               (sid, check, action, detail[:300], iso(now())))

    def turn_metric(self, model_id: str | None, intent: str, ok: bool, fallback: bool, latency_ms: int,
                    prompt_tokens: int, output_tokens: int) -> None:
        self.x("INSERT INTO turn_metrics (model_id, intent, ok, fallback, latency_ms, prompt_tokens, output_tokens, "
               "created_at) VALUES (?,?,?,?,?,?,?,?)",
               (model_id, intent, int(ok), int(fallback), latency_ms, prompt_tokens, output_tokens, iso(now())))

    # ---------- dọn dẹp ----------

    def purge_expired(self) -> dict[str, int]:
        t = iso(now())
        out = {"sessions": self.x("DELETE FROM sessions WHERE expires_at < ?", (t,)),
               "facts": self.x("DELETE FROM memory_facts WHERE expires_at IS NOT NULL AND expires_at < ?", (t,)),
               "events": self.x("DELETE FROM grounding_events WHERE created_at < ?",
                                (iso(now() - timedelta(days=HISTORY_DAYS)),))}
        return out

    def export(self, cid: str) -> dict[str, Any]:
        cust = self.customer(cid)
        sessions = []
        for s in self.sessions_for(cid, 1000):
            sessions.append({"id": s["id"], "started_at": s["started_at"], "ended_at": s["ended_at"],
                             "summary_vi": s["summary_vi"],
                             "messages": [{"role": m["role"], "content": m["content"], "created_at": m["created_at"]}
                                          for m in self.messages(s["id"])]})
        return {"customer": {"consent_level": cust["consent_level"], "consent_at": cust["consent_at"],
                             "created_at": cust["created_at"]} if cust else None,
                "memory": [{"kind": f["kind"], "label_vi": f["label_vi"], "origin": f["origin"],
                            "last_confirmed_at": f["last_confirmed_at"]} for f in self.facts(cid)],
                "sessions": sessions}

    # ---------- đánh giá ----------

    def add_review(self, review: dict[str, Any]) -> bool:
        body = review["body_vi"].strip()
        # Chống gửi trùng của cùng một người/nguồn; hai khách khác nhau viết giống nhau vẫn được.
        who = review.get("author_hash") or review.get("source_url") or review.get("source_id") or ""
        sha = hashlib.sha256(f"{review['product_id']}\n{who}\n{review.get('rating')}\n{body}".encode("utf-8")).hexdigest()
        rid = review.get("id") or "rv-" + sha[:16]
        try:
            self.x("INSERT INTO reviews (id, product_id, variant_sku, origin, source_id, source_url, author_hash, "
                   "author_display, rating, title_vi, body_vi, verified_purchase, status, moderation_note, created_at, "
                   "moderated_at, content_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (rid, review["product_id"], review.get("variant_sku"), review["origin"], review.get("source_id"),
                    review.get("source_url"), review.get("author_hash"), review.get("author_display"),
                    review.get("rating"), review.get("title_vi"), body, int(bool(review.get("verified_purchase"))),
                    review.get("status", "pending"), review.get("moderation_note"),
                    review.get("created_at") or iso(now()), review.get("moderated_at"), sha))
        except sqlite3.IntegrityError:
            return False
        return True

    def reviews(self, product_id: str, origins: tuple[str, ...], limit: int = 50) -> list[sqlite3.Row]:
        marks = ",".join("?" * len(origins)) or "''"
        return self.q(f"SELECT * FROM reviews WHERE product_id = ? AND status = 'approved' AND origin IN ({marks}) "
                      "ORDER BY created_at DESC LIMIT ?", (product_id, *origins, limit))

    def review_counts(self, origins: tuple[str, ...]) -> dict[str, tuple[int, float]]:
        marks = ",".join("?" * len(origins)) or "''"
        return {r[0]: (r[1], r[2]) for r in self.q(
            f"SELECT product_id, COUNT(*), AVG(rating) FROM reviews WHERE status = 'approved' AND origin IN ({marks}) "
            "GROUP BY product_id", origins)}

    def moderate_review(self, review_id: str, status: str, note: str | None = None) -> bool:
        return bool(self.x("UPDATE reviews SET status = ?, moderation_note = ?, moderated_at = ? WHERE id = ?",
                           (status, note, iso(now()), review_id)))
