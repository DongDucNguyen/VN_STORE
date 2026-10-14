"""Transfer unchanged keyword annotation pairs into an UNCONFIRMED draft.

Both packet.json files and the source draft backup are required. Never edits
packets, catalog or reviewed labels. The output is imported with 'Nạp bản nháp'
on the destination review page; all queries must be confirmed again by a person.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ANNOTATION_FIELDS = {"relevance", "has_answer", "labeled_by", "verified", "reviewed_at",
                     "catalog_sha256", "label_scope", "assist"}
SHA256 = re.compile(r"[a-f0-9]{64}")


def content_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def packet_key(packet: dict) -> str:
    suffix = ":assisted" if packet.get("suggestions") else ""
    return f"vnstore-review:{packet['catalog_sha256']}:{packet['queries_sha256']}{suffix}"


def objects(items, name: str) -> dict:
    if not isinstance(items, list) or not items:
        raise ValueError(f"Packet thiếu danh sách {name}")
    key = "qid" if name == "queries" else "id"
    out = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key]:
            raise ValueError(f"{name}: ID không hợp lệ")
        if item[key] in out:
            raise ValueError(f"{name}: ID trùng {item[key]}")
        out[item[key]] = item
    return out


def inspect_packet(packet: dict):
    if not isinstance(packet, dict) or packet.get("kind", "keyword_review") != "keyword_review":
        raise ValueError("Không phải packet keyword")
    for field in ("catalog_sha256", "queries_sha256"):
        if not isinstance(packet.get(field), str) or not packet[field]:
            raise ValueError(f"Packet thiếu {field}")
    if packet.get("review_content_version", 1) != 1:
        raise ValueError("Phiên bản nội dung packet chưa được hỗ trợ")
    queries, products = objects(packet.get("queries"), "queries"), objects(packet.get("products"), "products")
    for qid, q in queries.items():
        if not isinstance(q.get("query"), str) or not q["query"].strip() or q.get("split") not in {"train", "dev", "test"}:
            raise ValueError(f"{qid}: query/split không hợp lệ")
        ids = packet.get("candidate_order", {}).get(qid)
        if not isinstance(ids, list) or len(ids) != len(products) or set(ids) != set(products):
            raise ValueError(f"{qid}: candidate_order không phủ đúng sản phẩm")
    return queries, products


def product_content(product: dict) -> str | None:
    image_hash = product.get("image_sha256")
    if product.get("image") and (not isinstance(image_hash, str) or not SHA256.fullmatch(image_hash)):
        # Legacy packets recorded only a path; reading the path now cannot recover
        # what the reviewer actually saw before the file changed.
        return None
    content = {k: v for k, v in product.items() if k not in {"image", "image_sha256"}}
    content["image_sha256"] = image_hash if product.get("image") else None
    return content_hash(content)


def query_content(query: dict) -> str:
    # Exact query text, split, group and intent must agree. Machine draft grades
    # and old verification metadata are not evidence of unchanged intent.
    return content_hash({k: v for k, v in query.items() if k not in ANNOTATION_FIELDS})


def validate_state(state, queries, products) -> None:
    if not isinstance(state, dict) or not isinstance(state.get("reviewer"), str):
        raise ValueError("Bản nháp thiếu reviewer hợp lệ")
    for field in ("labels", "confirmed", "groups", "assisted"):
        mapping = state.get(field, {} if field == "assisted" else None)
        if not isinstance(mapping, dict) or set(mapping) - set(queries):
            raise ValueError(f"Bản nháp có {field} không hợp lệ")
        for qid, value in mapping.items():
            if field in {"labels", "assisted"}:
                if (not isinstance(value, dict) or set(value) - set(products) or
                        any(type(score) is not int or not 0 <= score <= 3 for score in value.values())):
                    raise ValueError(f"{qid}: {field} cần điểm nguyên 0..3 của sản phẩm trong packet cũ")
            elif (field == "confirmed" and type(value) is not bool) or (field == "groups" and not isinstance(value, str)):
                raise ValueError(f"{qid}: {field} không hợp lệ")


def migrate(old: dict, new: dict, draft: dict) -> dict:
    old_queries, old_products = inspect_packet(old)
    queries, products = inspect_packet(new)
    if not isinstance(draft, dict) or draft.get("key") != packet_key(old):
        raise ValueError("Bản nháp không thuộc packet nguồn")
    state = draft.get("state")
    validate_state(state, old_queries, old_products)
    assisted = bool(old.get("suggestions"))
    if assisted != bool(new.get("suggestions")):
        raise ValueError("Không chuyển giữa packet có gợi ý máy và packet chấm độc lập")
    if assisted and (not old.get("suggestions_sha256") or
                     old.get("suggestions_sha256") != new.get("suggestions_sha256")):
        raise ValueError("Gợi ý máy đã đổi; cần chấm lại để giữ đúng nguồn hỗ trợ")
    if not assisted and any(state.get("assisted", {}).values()):
        raise ValueError("Bản nháp chấm độc lập chứa điểm đã áp gợi ý máy")

    unchanged = {qid for qid in queries if qid in old_queries and
                 query_content(queries[qid]) == query_content(old_queries[qid])}
    old_hashes = {pid: product_content(p) for pid, p in old_products.items()}
    hashes = {pid: product_content(p) for pid, p in products.items()}
    result = {"reviewer": state["reviewer"], "labels": {}, "confirmed": {qid: False for qid in queries},
              "groups": {qid: value for qid, value in state["groups"].items() if qid in unchanged}, "assisted": {}}
    skipped = []
    kept = 0
    for qid, labels in state["labels"].items():
        for pid, score in labels.items():
            reason = None
            if qid not in unchanged:
                reason = "query_changed_or_removed"
            elif pid not in products:
                reason = "product_removed"
            elif old_hashes[pid] is None or hashes[pid] is None:
                reason = "image_history_unavailable"
            elif old_hashes[pid] != hashes[pid]:
                reason = "product_content_changed"
            if reason:
                skipped.append({"qid": qid, "product_id": pid, "reason": reason})
                continue
            result["labels"].setdefault(qid, {})[pid] = score
            if pid in state.get("assisted", {}).get(qid, {}):
                result["assisted"].setdefault(qid, {})[pid] = state["assisted"][qid][pid]
            kept += 1
    result["migration"] = {"source_key": packet_key(old), "destination_key": packet_key(new),
                           "source_packet_sha256": content_hash(old), "destination_packet_sha256": content_hash(new),
                           "source_draft_sha256": content_hash(draft), "copied_pairs": kept,
                           "skipped_pairs": skipped, "requires_confirmation": True}
    return {"key": packet_key(new), "state": result}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--old-packet", type=Path, required=True)
    ap.add_argument("--new-packet", type=Path, required=True)
    ap.add_argument("--draft", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        old, new, draft = [json.loads(p.read_text(encoding="utf-8"))
                           for p in (args.old_packet, args.new_packet, args.draft)]
        output = migrate(old, new, draft)
        # Exclusive creation keeps the source backup and any existing result intact.
        with args.out.open("x", encoding="utf-8") as f:
            f.write(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        ap.error(str(exc))
    summary = output["state"]["migration"]
    print(json.dumps({"copied_pairs": summary["copied_pairs"],
                      "skipped": dict(Counter(p["reason"] for p in summary["skipped_pairs"])),
                      "confirmed_queries": 0, "out": str(args.out)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
