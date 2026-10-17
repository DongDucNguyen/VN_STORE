"""Persistence/privacy and lifecycle regressions found while integrating demo_version."""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.assistant.service import AssistantService
from app.assistant.store import Store
from app.modalities import Status
from tests.test_assistant_api import client, chat  # noqa: F401 — shared API fixture


def test_none_context_stays_in_ram_and_is_removed_on_end(client):
    from app.main import state
    svc = state.assistant
    sid = client.post("/assistant/sessions", json={}).json()["session_id"]
    chat(client, sid, "tìm giỏ mây dưới 400k")
    assert svc.session_state(sid).get("last_recommended")
    assert svc.store.session_state(sid) == {}
    assert not svc.store.messages(sid)
    assert not svc.store.q("SELECT detail FROM grounding_events WHERE detail != ''")
    client.post(f"/assistant/sessions/{sid}/end")
    assert sid not in svc.transient and sid not in svc.transient_state


def test_consent_is_recorded_even_within_creation_second(client):
    client.post("/assistant/sessions", json={})
    client.put("/assistant/me/consent", json={"level": "none"})
    assert client.get("/assistant/me").json()["consent_needed"] is False


def test_downgrade_erases_stored_context_and_grounding_details(client):
    from app.main import state
    svc = state.assistant
    client.put("/assistant/me/consent", json={"level": "memory"})
    sid = client.post("/assistant/sessions", json={}).json()["session_id"]
    chat(client, sid, "quà cho mẹ, giỏ dưới 400k")
    svc.store.grounding_event(sid, "test", "blocked", "private context")
    assert svc.store.session_state(sid)
    client.put("/assistant/me/consent", json={"level": "none"})
    assert svc.store.session_state(sid) == {}
    assert svc.session_state(sid) == {}
    assert not svc.store.messages(sid)
    assert not svc.store.q("SELECT * FROM grounding_events WHERE session_id = ?", (sid,))


def test_private_context_not_retroactively_promoted(client):
    from app.main import state
    sid = client.post("/assistant/sessions", json={}).json()["session_id"]
    chat(client, sid, "tìm giỏ mây")
    client.put("/assistant/me/consent", json={"level": "history"})
    assert state.assistant.history(sid) == []
    assert state.assistant.session_state(sid) == {}
    assert sid not in state.assistant.transient_state


def test_deleted_session_is_not_recreated_by_inflight_turn(client, monkeypatch):
    from app.assistant.orchestrator import Turn
    from app.main import state
    sid = client.post("/assistant/sessions", json={}).json()["session_id"]
    started, release = threading.Event(), threading.Event()
    original = Turn.run

    def delayed(self, *args):
        result = original(self, *args)
        started.set()
        assert release.wait(5)
        return result

    monkeypatch.setattr(Turn, "run", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(chat, client, sid, "tìm giỏ")
        try:
            assert started.wait(5)
            assert client.delete(f"/assistant/sessions/{sid}").json()["deleted"]
        finally:
            release.set()
        events = task.result(timeout=5)
    assert "error" not in [kind for kind, _ in events]
    assert state.assistant.store.session(sid) is None
    assert sid not in state.assistant.transient
    assert sid not in state.assistant.transient_state


def test_missing_fact_mutation_returns_404_after_prior_insert(client):
    client.post("/assistant/sessions", json={})
    assert client.delete("/assistant/me/facts/999999").status_code == 404
    assert client.patch("/assistant/me/facts/999999", json={"label_vi": "new"}).status_code == 404


def test_consent_change_during_generation_does_not_persist_private_turn(client, monkeypatch):
    from app.assistant.orchestrator import Turn
    from app.main import state
    sid = client.post("/assistant/sessions", json={}).json()["session_id"]
    started, release = threading.Event(), threading.Event()
    original = Turn.run

    def delayed(self, *args):
        result = original(self, *args)
        started.set()
        assert release.wait(5)
        return result

    monkeypatch.setattr(Turn, "run", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(chat, client, sid, "tìm giỏ cho mẹ")
        try:
            assert started.wait(5)
            client.put("/assistant/me/consent", json={"level": "history"})
        finally:
            release.set()
        events = task.result(timeout=5)
    assert any(k == "error" and d["code"] == "consent_changed" for k, d in events)
    assert not state.assistant.store.messages(sid)
    assert state.assistant.store.session_state(sid) == {}


def test_whitespace_message_rejected(client):
    sid = client.post("/assistant/sessions", json={}).json()["session_id"]
    assert client.post(f"/assistant/sessions/{sid}/messages", json={"text": "  \n  "}).status_code == 422


def test_rate_tracking_expires_abandoned_customers(monkeypatch):
    import app.assistant.service as module
    t = [1000.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: t[0])
    store = Store(":memory:")
    try:
        svc = AssistantService(None, Status("unavailable"), store)
        svc.check_rate("old")
        t[0] += 601
        svc.check_rate("new")
        assert set(svc._rate) == {"new"}
    finally:
        store.close()


def test_review_statistics_cover_all_rows_not_only_excerpt_window():
    from app.assistant.reviews import summarize
    store = Store(":memory:")
    try:
        for i in range(60):
            store.add_review({"product_id": "product", "origin": "vnstore_customer", "author_hash": str(i),
                              "rating": 1 if i < 30 else 5, "body_vi": f"Sản phẩm đẹp {i}", "status": "approved",
                              "verified_purchase": i < 30})
        summary = summarize(store, "product")
        assert summary.count == 60 and summary.average == 3
        assert summary.distribution[1] == summary.distribution[5] == 30
        assert summary.verified_share == .5 and len(summary.excerpts) == 8
        assert summarize(store, "product", origins=()).count == 0
    finally:
        store.close()
