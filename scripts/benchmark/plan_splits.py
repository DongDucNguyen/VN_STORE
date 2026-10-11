"""Kế hoạch chia họ sản phẩm vào train/dev/test cho benchmark ảnh, rồi khóa (PLAN.md mục 8.1, 8.3 bước 1).

    .venv/Scripts/python scripts/benchmark/plan_splits.py propose --families benchmarks/families/families.json
    .venv/Scripts/python scripts/benchmark/plan_splits.py propose --preview          # từ proposal.json, không khóa được
    .venv/Scripts/python scripts/benchmark/plan_splits.py lock benchmarks/splits/image_families.json --locked-by <tên>

Đơn vị chia là họ trong families.json đã duyệt, gộp thêm (ưu tiên gộp dư hơn rò rỉ):
- các họ có ảnh gallery gần như đồng nhất (shared_image_clusters của proposal),
- các "dòng thiết kế" được chọn bằng --design-lines (mặc định none; all = mọi dòng của proposal, hoặc danh sách
  nguồn:từ như hanoia:moonbow,minhlong:camellia). Proposal phát hiện dòng bằng từ chung nên có cả âm tiết phổ thông
  ("chim", "hằng"): gộp tất cả nối chuỗi 24 họ bát đĩa Minh Long vào một split. Chỉ chọn dòng có cùng hoa văn thật.
Mỗi đơn vị xếp vào một tầng theo danh mục chiếm đa số; trong tầng, đơn vị lớn trước rồi theo hash(seed, mã đơn vị),
mỗi đơn vị vào split còn thiếu nhiều nhất so với tỉ lệ (mặc định 60/20/20 theo số họ). Kết quả cố định theo seed.
Kế hoạch chỉ phân họ catalog; vật thể ngoài catalog (external-…) tùy phiên thu.

Trạng thái: preview_unreviewed (từ proposal, để xem cân bằng) → proposed (từ registry đã duyệt) → locked (người phụ
trách khóa bằng lệnh lock, ghi tên do người đó cung cấp). Lệnh lock kiểm tra catalog, proposal, registry chưa đổi.
Không ghi đè file đã có: mỗi lần đề xuất dùng --out mới nếu file đích tồn tại. audit_image_queries.py --split-plan
từ chối query của họ nằm khác split trong kế hoạch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from family_registry import validate_registry  # noqa: E402

TZ = timezone(timedelta(hours=7))
SPLITS = ("train", "dev", "test")
PROPOSAL = ROOT / "benchmarks" / "families" / "proposal.json"
OUT = ROOT / "benchmarks" / "splits" / "image_families.json"
POLICY = "image-family-split-v1: units = reviewed families ∪ shared gallery images ∪ design lines; " \
         "stratum = majority category; largest deficit by family count; ties by hash(seed, unit)"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def select_lines(proposal: dict, spec: str) -> list[dict]:
    lines = proposal["design_lines"]
    if spec in ("none", ""):
        return []
    if spec == "all":
        return lines
    wanted = {x.strip() for x in spec.split(",") if x.strip()}
    known = {f"{d['source']}:{d['term']}" for d in lines}
    if wanted - known:
        raise ValueError(f"Dòng thiết kế không có trong proposal: {sorted(wanted - known)}")
    return [d for d in lines if f"{d['source']}:{d['term']}" in wanted]


def build_units(product_family: dict[str, str], proposal: dict, design_lines: list[dict]) -> list[dict]:
    parent: dict[str, str] = {}
    reasons: dict[str, set[str]] = defaultdict(set)

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(products: list[str], reason: str) -> None:
        fams = sorted({product_family[p] for p in products if p in product_family})
        for f in fams[1:]:
            a, b = find(fams[0]), find(f)
            if a != b:
                parent[max(a, b)] = min(a, b)
        if len(fams) > 1:
            reasons[find(fams[0])].add(reason)

    for f in product_family.values():
        find(f)
    for c in proposal["shared_image_clusters"]:
        join(c["products"], "shared_image")
    for d in design_lines:
        join(d["products"], f"design_line:{d['source']}:{d['term']}")
    members: dict[str, set[str]] = defaultdict(set)
    for f in set(product_family.values()):
        members[find(f)].add(f)
    merged_reasons: dict[str, set[str]] = defaultdict(set)
    for root, rs in reasons.items():
        merged_reasons[find(root)] |= rs
    products: dict[str, list[str]] = defaultdict(list)
    for pid, f in product_family.items():
        products[find(f)].append(pid)
    return [{"unit_id": root, "families": sorted(fams), "products": sorted(products[root]),
             "reasons": sorted(merged_reasons[root])} for root, fams in members.items()]


def assign(units: list[dict], categories: dict[str, str], ratios: dict[str, float], seed: str) -> None:
    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for u in units:
        votes = Counter(categories[p] for p in u["products"])
        u["category"] = min(votes, key=lambda c: (-votes[c], c))
        by_stratum[u["category"]].append(u)
    total: Counter = Counter()
    for stratum in sorted(by_stratum):
        local: Counter = Counter()
        rows = sorted(by_stratum[stratum], key=lambda u: (-len(u["families"]),
                      sha(f"{seed}\0{u['unit_id']}".encode())))
        for u in rows:
            size = len(u["families"])
            # Split còn thiếu nhiều nhất trong tầng; hòa thì xét toàn bộ, rồi theo thứ tự train/dev/test.
            u["split"] = min(SPLITS, key=lambda s: ((local[s] + size) / ratios[s], (total[s] + size) / ratios[s],
                                                     SPLITS.index(s)))
            local[u["split"]] += size
            total[u["split"]] += size


def propose(catalog: dict, catalog_sha: str, proposal: dict, proposal_sha: str, registry: dict | None,
            registry_sha: str | None, ratios: dict[str, float], seed: str, design_lines: str = "none") -> dict:
    if proposal.get("catalog_sha256") != catalog_sha:
        raise ValueError("proposal.json dựng cho catalog khác; chạy lại propose_families.py")
    product_ids = {p["id"] for p in catalog["products"]}
    if registry is not None:
        mapping = validate_registry(registry, catalog_sha, product_ids)
        if registry["proposal_sha256"] != proposal_sha:
            raise ValueError("families.json được duyệt trên proposal khác; dùng đúng proposal của lượt duyệt")
        status, source = "proposed", {"kind": "family_registry", "sha256": registry_sha,
                                      "reviewed_by": registry["reviewed_by"], "reviewed_at": registry["reviewed_at"]}
    else:
        mapping = proposal["product_family"]
        if set(mapping) != product_ids:
            raise ValueError("proposal.json không phủ đúng sản phẩm catalog")
        status, source = "preview_unreviewed", {"kind": "proposal_unreviewed", "sha256": None}
    lines = select_lines(proposal, design_lines)
    units = build_units(mapping, proposal, lines)
    assign(units, {p["id"]: p["category_id"] for p in catalog["products"]}, ratios, seed)
    family_split = {f: u["split"] for u in units for f in u["families"]}
    counts = {s: {"units": sum(u["split"] == s for u in units),
                  "families": sum(len(u["families"]) for u in units if u["split"] == s),
                  "products": sum(len(u["products"]) for u in units if u["split"] == s)} for s in SPLITS}
    n_fam = len(family_split)
    by_category = defaultdict(lambda: Counter())
    for u in units:
        by_category[u["category"]][u["split"]] += len(u["families"])
    return {"kind": "image_family_split_plan", "status": status, "policy": POLICY,
            "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "catalog_sha256": catalog_sha, "catalog_version": catalog.get("catalog_version"),
            "proposal_sha256": proposal_sha, "source": source,
            "params": {"ratios": ratios, "seed": seed, "design_lines": sorted(f"{d['source']}:{d['term']}" for d in lines)},
            "counts": counts,
            "family_share": {s: round(counts[s]["families"] / n_fam, 4) for s in SPLITS},
            "largest_unit": max(len(u["families"]) for u in units),
            "by_category": {c: dict(v) for c, v in sorted(by_category.items())},
            "family_split": dict(sorted(family_split.items())),
            "units": sorted(units, key=lambda u: (u["split"], u["category"], u["unit_id"])),
            "locked_by": None, "locked_at": None}


def validate_plan(plan: dict, catalog_sha: str, registry_sha: str | None = None,
                  allow_proposed: bool = False) -> dict[str, str]:
    """Trả về family_id → split của kế hoạch dùng được cho audit/thu query."""
    if not isinstance(plan, dict) or plan.get("kind") != "image_family_split_plan":
        raise ValueError("Không phải kế hoạch split ảnh")
    allowed = ("locked", "proposed") if allow_proposed else ("locked",)
    if plan.get("status") not in allowed:
        raise ValueError(f"Kế hoạch split ở trạng thái {plan.get('status')}; cần {' hoặc '.join(allowed)}")
    if plan.get("catalog_sha256") != catalog_sha:
        raise ValueError("Kế hoạch split thuộc catalog khác; lập và khóa lại theo registry mới")
    if registry_sha is not None and plan["source"].get("sha256") != registry_sha:
        raise ValueError("Kế hoạch split dựng từ families.json khác registry đang dùng")
    mapping = plan.get("family_split")
    if not isinstance(mapping, dict) or not mapping or any(v not in SPLITS for v in mapping.values()):
        raise ValueError("family_split không hợp lệ")
    if plan["status"] == "locked" and not (isinstance(plan.get("locked_by"), str) and plan["locked_by"].strip()):
        raise ValueError("Kế hoạch đã khóa cần locked_by")
    return mapping


def lock(plan: dict, who: str, catalog_sha: str, proposal_sha: str, registry_sha: str) -> dict:
    if plan.get("status") != "proposed":
        raise ValueError("Chỉ khóa kế hoạch proposed dựng từ families.json đã duyệt (preview không khóa được)")
    if not who.strip():
        raise ValueError("Cần --locked-by")
    if plan["catalog_sha256"] != catalog_sha or plan["proposal_sha256"] != proposal_sha \
            or plan["source"]["sha256"] != registry_sha:
        raise ValueError("Catalog, proposal hoặc families.json đã đổi kể từ khi lập kế hoạch; lập lại")
    return {**plan, "status": "locked", "locked_by": who.strip(),
            "locked_at": datetime.now(TZ).isoformat(timespec="seconds")}


def markdown(plan: dict) -> str:
    lines = [f"# Kế hoạch split ảnh theo họ — {plan['status']}", "",
             f"- Catalog: `{plan['catalog_version']}` (`{plan['catalog_sha256'][:16]}…`)",
             f"- Nguồn họ: {plan['source']['kind']}; tạo lúc {plan['generated_at']}",
             f"- Tỉ lệ mục tiêu {plan['params']['ratios']}, seed `{plan['params']['seed']}`, "
             f"dòng thiết kế giữ cùng split: {', '.join(plan['params']['design_lines']) or 'không'}; "
             f"đơn vị lớn nhất {plan['largest_unit']} họ", "",
             "| Split | Đơn vị | Họ | Sản phẩm | Tỉ lệ họ |", "|---|---|---|---|---|"]
    for s in SPLITS:
        c = plan["counts"][s]
        lines.append(f"| {s} | {c['units']} | {c['families']} | {c['products']} | {plan['family_share'][s]:.1%} |")
    lines += ["", "| Danh mục | train | dev | test |", "|---|---|---|---|"]
    for cat, v in plan["by_category"].items():
        lines.append(f"| {cat} | {v.get('train', 0)} | {v.get('dev', 0)} | {v.get('test', 0)} |")
    if plan["status"] == "preview_unreviewed":
        lines += ["", "**Chỉ để xem cân bằng**: dựng từ proposal chưa duyệt, không dùng để thu hoặc chấm query."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--proposal", type=Path, default=PROPOSAL)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("propose")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--families", type=Path, help="families.json đã duyệt")
    src.add_argument("--preview", action="store_true", help="dùng proposal chưa duyệt; kết quả không khóa được")
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--ratios", default="0.6,0.2,0.2", help="train,dev,test theo số họ")
    p.add_argument("--seed", default="vnstore-image-split-1")
    p.add_argument("--design-lines", default="none", help="none | all | nguồn:từ,nguồn:từ (xem design_lines của proposal)")
    k = sub.add_parser("lock")
    k.add_argument("plan", type=Path)
    k.add_argument("--families", type=Path, default=ROOT / "benchmarks" / "families" / "families.json")
    k.add_argument("--locked-by", required=True)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        catalog_raw, proposal_raw = args.catalog.read_bytes(), args.proposal.read_bytes()
        catalog_sha, proposal_sha = sha(catalog_raw), sha(proposal_raw)
        if args.command == "propose":
            if args.out.exists():
                raise ValueError(f"{args.out} đã tồn tại; chọn --out mới để giữ kế hoạch cũ")
            values = [float(x) for x in args.ratios.split(",")]
            if len(values) != 3 or any(v <= 0 for v in values):
                raise ValueError("--ratios cần 3 số dương")
            ratios = {s: v / sum(values) for s, v in zip(SPLITS, values)}
            registry_raw = args.families.read_bytes() if args.families else None
            plan = propose(json.loads(catalog_raw), catalog_sha, json.loads(proposal_raw), proposal_sha,
                           json.loads(registry_raw) if registry_raw else None,
                           sha(registry_raw) if registry_raw else None, ratios, args.seed, args.design_lines)
            target = args.out
        else:
            registry_raw = args.families.read_bytes()
            validate_registry(json.loads(registry_raw), catalog_sha,
                              {p["id"] for p in json.loads(catalog_raw)["products"]})
            plan = lock(json.loads(args.plan.read_text(encoding="utf-8")), args.locked_by, catalog_sha,
                        proposal_sha, sha(registry_raw))
            target = args.plan
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    target.with_suffix(".md").write_text(markdown(plan), encoding="utf-8")
    print(f"{plan['status']}: {json.dumps(plan['counts'], ensure_ascii=False)} → {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
