"""Validate reviewed catalog families and resolve query grouping without using relevance as identity."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import re

ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,119}")
HASH = re.compile(r"[0-9a-f]{64}")


def validate_registry(data: dict, catalog_sha: str, product_ids: set[str]) -> dict[str, str]:
    if not isinstance(data, dict) or data.get("status") != "reviewed":
        raise ValueError("Family registry must have status reviewed; proposal is not a registry.")
    if data.get("catalog_sha256") != catalog_sha:
        raise ValueError("Family registry belongs to another catalog; re-review, do not just change the hash.")
    if not isinstance(data.get("proposal_sha256"), str) or not HASH.fullmatch(data["proposal_sha256"]):
        raise ValueError("Family registry needs proposal_sha256.")
    who = data.get("reviewed_by")
    if not isinstance(who, str) or not who.strip():
        raise ValueError("Family registry needs reviewed_by.")
    try:
        stamp = datetime.fromisoformat(data["reviewed_at"].replace("Z", "+00:00"))
        if stamp.utcoffset() is None:
            raise ValueError()
    except (KeyError, AttributeError, TypeError, ValueError):
        raise ValueError("Family registry needs reviewed_at with timezone.") from None
    mapping = data.get("product_family")
    if not isinstance(mapping, dict) or set(mapping) != product_ids:
        raise ValueError("Family registry must cover exactly all catalog product IDs.")
    if any(not isinstance(f, str) or not ID.fullmatch(f) or f.startswith("external-") for f in mapping.values()):
        raise ValueError("Invalid catalog family ID (external- is reserved for objects outside catalog).")
    groups = defaultdict(set)
    for pid, fid in mapping.items():
        groups[fid].add(pid)
    listed = {}
    rows = data.get("families")
    if not isinstance(rows, list):
        raise ValueError("Family registry needs a families list.")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("family_id"), str) or not isinstance(row.get("products"), list):
            raise ValueError("Invalid family members.")
        fid, pids = row["family_id"], row["products"]
        if not all(isinstance(p, str) for p in pids) or fid in listed or len(pids) < 2 or len(set(pids)) != len(pids):
            raise ValueError("Duplicate or incomplete family members.")
        listed[fid] = set(pids)
    if listed != {f: p for f, p in groups.items() if len(p) > 1}:
        raise ValueError("Family members do not match product_family.")
    return mapping


def resolve_family(row: dict, mapping: dict[str, str]) -> tuple[str | None, str | None]:
    """Return canonical family and error. None/None means a human family review is still needed.

    Exact answers use the judged target. Other tasks use a reviewed identity of the
    photographed object; relevance can span unrelated families and is never used here.
    """
    judgment, review = row["judgment"], row.get("family_review")
    exact = row["task"] == "exact" and judgment and judgment["has_answer"]
    target = judgment["exact_product_id"] if exact else review["product_id"] if review else None
    if exact and review and review["product_id"] != target:
        return None, "Family review disagrees with the exact target."
    if not exact and not review:
        return None, None
    if target is not None:
        if target not in mapping:
            return None, "Reviewed object product_id is not in the catalog registry."
        canonical = mapping[target]
        if row["family_id"] != canonical:
            return canonical, f"family_id must be {canonical} for product {target}."
        return canonical, None
    if not row["family_id"].startswith("external-") or row["family_id"] == "external-":
        return None, "Objects reviewed as outside catalog require an external-<stable-id> family."
    return row["family_id"], None
