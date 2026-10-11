"""Packet chấm query ảnh và áp judgment trên dữ liệu TỔNG HỢP; nhãn trong test là giả lập người chấm."""
import json
import sys
from pathlib import Path

from tests.image_review_demo import FIXTURE, ROOT, build

sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))

import apply_image_judgments as aij  # noqa: E402
from audit_image_queries import audit  # noqa: E402

PUBLISHED = 12  # catalog fixture: 12 published + 1 draft
WHO, AT = "người chấm tổng hợp", "2026-10-11T09:00:00+07:00"


def packet_of(path: Path) -> dict:
    return json.loads((path / "packet.json").read_text(encoding="utf-8"))


def export(packet: dict, items: list[dict]) -> dict:
    return {"kind": "image_judgment_export", "packet_id": packet["packet_id"], "catalog_sha256": packet["catalog_sha256"],
            "manifest_sha256": packet["manifest_sha256"], "exported_at": AT, "items": items}


def item(packet, qid, relevance, exact=None, sku=None, independent=True):
    q = next(q for q in packet["queries"] if q["qid"] == qid)
    return {"qid": qid, "sha256": q["sha256"],
            "judgment": {"has_answer": any(v >= 2 for v in relevance.values()), "relevance": relevance,
                         "exact_product_id": exact, "exact_variant_sku": sku, "reviewed_by": WHO, "reviewed_at": AT},
            "independence_review": {"independent": independent, "reviewed_by": WHO, "reviewed_at": AT,
                                    "note": "Đối chiếu với gallery fixture"}}


def write(tmp_path, data, name="judgments.json"):
    p = tmp_path / name
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_packet_pools_are_blind_complete_and_deterministic(tmp_path):
    manifest, out = build(tmp_path / "a")
    packet = packet_of(out)
    assert packet["verified"] is False and len(packet["products"]) == PUBLISHED
    assert {q["qid"] for q in packet["queries"]} == {"q-exact", "q-nomatch", "q-text"}
    for q in packet["queries"]:
        assert sorted(q["pool"] + q["rest"]) == sorted(p["id"] for p in packet["products"])  # không trùng, không sót
        assert not set(q["pool"]) & set(q["rest"]) and set(q["pool"]) == set(q["pool_sources"])
        sources = [s.split("@")[0] for v in q["pool_sources"].values() for s in v]
        assert sources.count("random") == 2 and "byte-histogram:visual" in sources
        assert q["existing"] == {"judgment": None, "independence_review": None, "family_review": None}
        assert (out / q["image"]).resolve() == (manifest.parent / "raw" / f"{q['qid']}.png").resolve()
    text = next(q for q in packet["queries"] if q["qid"] == "q-text")
    assert any(s.startswith("bm25:text_vi") for v in text["pool_sources"].values() for s in v)
    assert all((out / src).is_file() for p in packet["products"] for src in p["images"])
    html = (out / "index.html").read_text(encoding="utf-8")
    assert packet["packet_id"] in html and "__PACKET_JSON__" not in html
    # Cùng manifest/seed → cùng pool và cùng thứ tự.
    _, again = build(tmp_path / "b")
    assert [q["pool"] for q in packet_of(again)["queries"]] == [q["pool"] for q in packet["queries"]]


def test_apply_judgments_reaches_recorded_checks(tmp_path):
    manifest, out = build(tmp_path)
    packet = packet_of(out)
    every = {p["id"]: 0 for p in packet["products"]}
    items = [item(packet, "q-exact", {"fx-gio-may-co-quai": 3, "fx-gio-tre-khong-quai": 1}, exact="fx-gio-may-co-quai"),
             item(packet, "q-nomatch", every),
             item(packet, "q-text", {"fx-gio-may-co-quai": 2, "fx-tui-coi-tron": 0})]
    data = write(tmp_path, export(packet, items))
    before = manifest.read_bytes()
    assert aij.main([str(data), "--manifest", str(manifest), "--catalog", str(FIXTURE), "--dry-run"]) == 0
    assert manifest.read_bytes() == before and not list(manifest.parent.glob(".manifest.*"))
    assert aij.main([str(data), "--manifest", str(manifest), "--catalog", str(FIXTURE)]) == 0
    rows = {s["qid"]: s for s in json.loads(manifest.read_text(encoding="utf-8"))["samples"]}
    assert rows["q-exact"]["judgment"]["exact_product_id"] == "fx-gio-may-co-quai"
    assert rows["q-nomatch"]["judgment"]["has_answer"] is False
    assert audit(manifest, FIXTURE)["status"] == "recorded_checks_passed"
    # Lần hai: không đổi gì; lượt chấm khác cần --replace-judged.
    assert aij.main([str(data), "--manifest", str(manifest), "--catalog", str(FIXTURE)]) == 0
    other = write(tmp_path, export(packet, [item(packet, "q-text", {"fx-gio-may-co-quai": 3})]), "b.json")
    assert aij.main([str(other), "--manifest", str(manifest), "--catalog", str(FIXTURE)]) == 1
    assert aij.main([str(other), "--manifest", str(manifest), "--catalog", str(FIXTURE), "--replace-judged"]) == 0


def test_packet_family_review_applies_canonical_and_external_ids(tmp_path):
    manifest, out = build(tmp_path, with_families=True)
    packet = packet_of(out)
    registry = packet["family_registry"]
    assert registry["product_family"]["fx-tui-coi-tron"] == "fam-fx-tui-coi-tron"
    q = next(q for q in packet["queries"] if q["qid"] == "q-text")
    entry = {"qid": q["qid"], "sha256": q["sha256"], "source_family_id": q["family_id"],
             "family_id": "fam-fx-tui-coi-tron", "family_review": {"product_id": "fx-tui-coi-tron",
             "reviewed_by": WHO, "reviewed_at": AT, "note": "Synthetic identity"}}
    data = {**export(packet, [entry]), "family_registry_sha256": registry["sha256"]}
    source = write(tmp_path, data)
    args = [str(source), "--manifest", str(manifest), "--catalog", str(FIXTURE)]
    before = manifest.read_bytes()
    assert aij.main(args) == 1  # registry required
    assert manifest.read_bytes() == before
    args += ["--families", str(tmp_path / "families.json")]
    assert aij.main(args + ["--dry-run"]) == 0 and manifest.read_bytes() == before
    assert aij.main(args) == 0
    assert aij.main(args) == 0  # idempotent despite source_family_id now being old
    rows = json.loads(manifest.read_bytes())["samples"]
    actual = next(s for s in rows if s["qid"] == "q-text")
    assert actual["family_id"] == "fam-fx-tui-coi-tron" and actual["judgment"] is None
    data["items"][0].update(source_family_id=actual["family_id"], family_id="external-object-1")
    data["items"][0]["family_review"]["product_id"] = None
    write(tmp_path, data)
    assert aij.main(args) == 1  # previously reviewed identity requires explicit replace
    assert aij.main(args + ["--replace-judged"]) == 0


def test_family_export_cannot_change_registry_or_bypass_audit(tmp_path):
    manifest, out = build(tmp_path, with_families=True)
    packet = packet_of(out)
    q = packet["queries"][1]
    entry = {"qid": q["qid"], "sha256": q["sha256"], "source_family_id": q["family_id"],
             "family_id": "wrong-family", "family_review": {"product_id": "fx-tui-coi-tron",
             "reviewed_by": WHO, "reviewed_at": AT, "note": "Synthetic"}}
    data = {**export(packet, [entry]), "family_registry_sha256": packet["family_registry"]["sha256"]}
    source = write(tmp_path, data)
    args = [str(source), "--manifest", str(manifest), "--catalog", str(FIXTURE),
            "--families", str(tmp_path / "families.json")]
    before = manifest.read_bytes()
    assert aij.main(args) == 1
    data["items"][0]["family_id"] = "fam-fx-tui-coi-tron"
    data["items"][0]["source_family_id"] = "stale-family"
    write(tmp_path, data)
    assert aij.main(args) == 1
    data["items"][0]["source_family_id"] = q["family_id"]
    data["family_registry_sha256"] = "b" * 64
    write(tmp_path, data)
    assert aij.main(args) == 1
    assert manifest.read_bytes() == before


def test_apply_judgments_rejects_inconsistent_input(tmp_path):
    manifest, out = build(tmp_path)
    packet = packet_of(out)
    before = manifest.read_bytes()
    args = ["--manifest", str(manifest), "--catalog", str(FIXTURE)]
    bad_cases = {
        "nomatch-partial": export(packet, [item(packet, "q-nomatch", {"fx-khan-lua-do": 0})]),  # audit invalid
        "exact-unlabeled": export(packet, [item(packet, "q-exact", {"fx-khan-lua-do": 2}, exact="fx-gio-nhua-dan")]),
        "sha-changed": export(packet, [{**item(packet, "q-text", {"fx-gio-may-co-quai": 2}), "sha256": "0" * 64}]),
        "unknown-qid": export(packet, [{**item(packet, "q-text", {"fx-gio-may-co-quai": 2}), "qid": "q-khac"}]),
        "catalog": {**export(packet, [item(packet, "q-text", {"fx-gio-may-co-quai": 2})]), "catalog_sha256": "1" * 64},
        "hidden-product": export(packet, [item(packet, "q-text", {"fx-ban-nhap": 3})]),
        "kind": {"items": []},
    }
    for name, data in bad_cases.items():
        assert aij.main([str(write(tmp_path, data, f"{name}.json")), *args]) == 1, name
    assert manifest.read_bytes() == before and not list(manifest.parent.glob(".manifest.*"))
