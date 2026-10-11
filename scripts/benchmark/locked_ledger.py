"""Append-only, hash-chained ledger for GĐ6 locked-test openings.

Every test-split evaluation must belong to a session opened by `locked_test.py open`
(env VNSTORE_LOCKED_TEST_ID). Evaluators record their run here, so any opening of test
data leaves a trace. This is tamper-evident bookkeeping, not access control: whoever can
read the manifests can still look at test files; the ledger makes reruns visible.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "reports/acceptance/locked_test_ledger.jsonl"
EVENTS = {"opened", "run_recorded", "closed", "report_written", "signoff"}
MODALITIES = ("keyword", "voice", "image")


class LedgerError(ValueError):
    pass


def path() -> Path:
    value = os.environ.get("VNSTORE_LOCKED_TEST_LEDGER")
    return Path(value) if value else DEFAULT


def now() -> str:
    return datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")


def _line_hash(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def read(ledger: Path | None = None) -> list[dict]:
    """Return events after checking the hash chain; any edit or deletion is rejected."""
    ledger = ledger or path()
    if not ledger.exists():
        return []
    events, prev = [], None
    for no, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LedgerError(f"ledger line {no}: invalid JSON") from exc
        if event.get("prev_sha256") != prev or event.get("event") not in EVENTS:
            raise LedgerError(f"ledger line {no}: hash chain broken or unknown event; do not edit the ledger")
        events.append(event)
        prev = _line_hash(line)
    return events


def append(event: dict, ledger: Path | None = None) -> dict:
    ledger = ledger or path()
    events = read(ledger)
    if event.get("event") not in EVENTS:
        raise LedgerError("unknown ledger event")
    prev = None
    if events:
        lines = [x for x in ledger.read_text(encoding="utf-8").splitlines() if x.strip()]
        prev = _line_hash(lines[-1])
    record = {**event, "at": now(), "prev_sha256": prev}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def sessions(events: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for e in events:
        if e["event"] == "opened":
            out[e["id"]] = {"opened": e, "runs": {}, "closed": None, "reports": [], "signoffs": []}
            continue
        s = out.get(e.get("id"))
        if s is None:
            raise LedgerError(f"ledger event for unknown session {e.get('id')!r}")
        if e["event"] == "run_recorded":
            s["runs"][e["modality"]] = e
        elif e["event"] == "closed":
            s["closed"] = e
        elif e["event"] == "report_written":
            s["reports"].append(e)
        else:
            s["signoffs"].append(e)
    return out


def require_open(modality: str) -> str:
    """Called by evaluators before touching test data. Returns the open session id."""
    if modality not in MODALITIES:
        raise LedgerError("unknown modality")
    sid = os.environ.get("VNSTORE_LOCKED_TEST_ID", "")
    if not sid:
        raise LedgerError("split test only runs inside a session opened by scripts/benchmark/locked_test.py open")
    s = sessions(read()).get(sid)
    if s is None or s["closed"] is not None:
        raise LedgerError(f"locked-test session {sid!r} is not open")
    if modality not in s["opened"]["modalities"]:
        raise LedgerError(f"{modality} is not part of locked-test session {sid}")
    if modality in s["runs"]:
        raise LedgerError(f"{modality} already ran in locked-test session {sid}; open a new attempt with a reason")
    return sid


def record_run(sid: str, modality: str, run_dir: Path) -> dict:
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    full = run_dir.resolve()
    shown = full.relative_to(ROOT).as_posix() if full.is_relative_to(ROOT) else str(full)
    return append({"event": "run_recorded", "id": sid, "modality": modality, "run_dir": shown,
                   "run_sha256": digest(run_dir / "run.json"),
                   "predictions_sha256": digest(run_dir / "predictions.jsonl")})
