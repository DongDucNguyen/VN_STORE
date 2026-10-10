"""Đề xuất họ sản phẩm (family) để chia split benchmark không rò rỉ (PLAN.md mục 8.1). Chỉ là đề xuất.

    .venv-ml/Scripts/python scripts/benchmark/propose_families.py [--index-dir artifacts/indexes/image/<model>]

Họ = các SKU/record là biến thể của cùng một món (size, dung tích, màu, hộp quà/edition). Hai nguồn bằng chứng:
- Tên: cùng nguồn và cùng khóa tên sau khi bỏ kích thước/dung tích/khối lượng, size S/M/L, mã sản phẩm, đoạn
  biến thể màu cuối tên, "edition", ngoặc đơn. Khóa chỉ gồm từ chung chung (loại hàng, chất liệu, từ trong tên
  danh mục…) không được dùng, vì nhiều món khác nhau có tên kiểu "Khay mây — <mã>".
- Ảnh: cùng nguồn và cosine lớn nhất giữa các ảnh ≥ --visual-threshold (mặc định 0,96) trên chỉ mục ảnh đã dựng.
  Ảnh gần như đồng nhất (cosine ≥ 0,99) xuất hiện ở ≥3 sản phẩm là ảnh minh họa dùng chung: không dùng để gom họ,
  được báo riêng để người duyệt quyết định giữ/loại khỏi gallery.
Hai liên kết được gộp bằng union-find. Báo thêm, không gộp: cặp ảnh giống trong khoảng [--candidate-threshold,
ngưỡng) và "dòng thiết kế" (từ đặc trưng chung của ≥2 sản phẩm cùng nguồn, ví dụ Exotic, Camellia).
Ngưỡng chưa được hiệu chỉnh trên dữ liệu có nhãn. Kết quả ghi benchmarks/families/proposal.json
(status proposed_unreviewed) và báo cáo Markdown/JSON trong reports/benchmark/. Không sửa catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.catalog.store import load_snapshot  # noqa: E402

DEFAULT_INDEX = ROOT / "artifacts/indexes/image/google_siglip2-base-patch16-224_ba1f3b0843f24bc5417d38e19c37b287d719b2f4"
OUT = ROOT / "benchmarks" / "families" / "proposal.json"
TZ = timezone(timedelta(hours=7))
COLORS = set("do xanh duong lam la vang kim trang nga den nau tim hong cam bac xam kem ngoc co vit cobalt navy "
             "ruou mau nhieu bien reu".split())
# Từ chung chung bổ sung ngoài tên danh mục/chất liệu: loại hàng, hình dáng, công dụng, từ marketing.
GENERIC_EXTRA = set("gio khay hop ban ghe den chup tha treo bat dia chen to ly coc tach binh lo hoa am tra bo set "
                    "tui ro thung ke ngan dan tay thu cong tron vuong chu nhat oval bau duc hinh co quai nap de "
                    "trang tri dung do va voi cho cua bang tu tai lam kieu mau moi cao cap handmade wholesale "
                    "made in vietnam from viet nam natural woven handwoven basket tray bowl box lamp lampshade "
                    "pendant light storage decor vase plate pot the and of with for chocolate bar bars dark milk "
                    "white gift single origin silk scarf scarves shawl handkerchief square print printed painted hand "
                    "collection flavors flavor vietnamese limited luxury premium mulberry pure qua tang hoa tiet theu "
                    "ve in nghe thuat doc ban doanh nghiep su kien thoi trang".split())
CODE = re.compile(r"^(?=.*\d)[a-z0-9_]+$")  # vh24062, klvi05, af26ex08, 1071550827, 3d
MEASURE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:x\s*\d+(?:[.,]\d+)?\s*)?(?:cm|mm|m|l|ml|g|gr|kg)\b"
                     r"|\b\d+\s*x\s*\d+\s*g?\b|\bsize\s+[a-z]{1,2}\b|\bset of \d+\b|\b\d+\s*mieng\b")


def plain(text: str) -> str:
    s = unicodedata.normalize("NFD", text.lower().replace("đ", "d").replace("Đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def generic_vocabulary(snap) -> set[str]:
    words = set(GENERIC_EXTRA)
    for c in snap.categories.values():
        words.update(re.findall(r"[a-z0-9]+", plain(c["name_vi"])))
    for p in snap.products.values():
        for m in p["materials"]:
            words.update(re.findall(r"[a-z0-9]+", plain(m)))
    return words


def name_key(name: str, brand_words: set[str]) -> str:
    """Khóa tên của một món, bỏ phần chỉ biến thể. brand_words: tên thương hiệu cần bỏ (marou, sensilk…)."""
    s = plain(name)
    s = re.sub(r"\([^)]*\)", " ", s)
    s = s.split(" | ")[0]                                   # "… | SenSilk", "… | Quà Tặng Đối Tác"
    s = re.sub(r"^so co la marou\s*[—-]\s*", "", s)
    s = MEASURE.sub(" ", s)
    segs = [g.strip() for g in re.split(r"\s+[—–-]\s+", s) if g.strip()]
    kept = []
    for i, g in enumerate(segs):
        toks = re.findall(r"[a-z0-9]+", g)
        if not toks or "edition" in toks:
            continue
        if i > 0 and (toks[0] == "mau" or all(t in COLORS for t in toks)):  # biến thể màu ở đoạn sau
            continue
        kept.append(g)
    toks = [t for t in re.findall(r"[a-z0-9]+", " ".join(kept))
            if not CODE.match(t) and t not in brand_words and t not in ("mini", "nho", "lon", "vua", "thap", "cao")]
    return " ".join(toks)


class UnionFind:
    def __init__(self, items):
        self.parent = {x: x for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def source_of(pid: str) -> str:
    return pid.split("-")[1]


def image_similarity(vectors: dict[str, list[tuple[str, list[float]]]]) -> dict[tuple[str, str], float]:
    """Cosine lớn nhất giữa ảnh của hai sản phẩm cùng nguồn; vectors: product_id → [(image_id, vector)]."""
    out: dict[tuple[str, str], float] = {}
    by_src = defaultdict(list)
    for pid in sorted(vectors):
        by_src[source_of(pid)].append(pid)
    try:
        import numpy as np
    except ImportError:
        np = None
    for pids in by_src.values():
        rows = [(pid, img, v) for pid in pids for img, v in vectors[pid]]
        if not rows:
            continue
        if np is not None:
            m = np.array([r[2] for r in rows], dtype=np.float32)
            m /= np.linalg.norm(m, axis=1, keepdims=True)
            sims = (m @ m.T).tolist()
        else:
            norm = [[x / math.sqrt(sum(y * y for y in r[2])) for x in r[2]] for r in rows]
            sims = [[sum(a * b for a, b in zip(u, w)) for w in norm] for u in norm]
        for i, (pa, _, _) in enumerate(rows):
            for j in range(i + 1, len(rows)):
                pb = rows[j][0]
                if pa != pb:
                    key = (min(pa, pb), max(pa, pb))
                    out[key] = max(out.get(key, -1.0), sims[i][j])
    return out


def shared_image_clusters(vectors, threshold: float = 0.99) -> list[dict]:
    """Cụm ảnh gần như đồng nhất thuộc các sản phẩm khác nhau (cùng nguồn)."""
    flat = [(pid, img, v) for pid in sorted(vectors) for img, v in vectors[pid]]
    uf = UnionFind([img for _, img, _ in flat])
    owner = {img: pid for pid, img, _ in flat}
    norm = {img: [x / math.sqrt(sum(y * y for y in v)) for x in v] for _, img, v in flat}
    try:
        import numpy as np
        ids = [img for _, img, _ in flat]
        m = np.array([norm[i] for i in ids], dtype=np.float32)
        s = m @ m.T
        hits = [(ids[a], ids[b]) for a, b in zip(*np.where(np.triu(s, 1) >= threshold))]
    except ImportError:
        ids = [img for _, img, _ in flat]
        hits = [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]
                if sum(x * y for x, y in zip(norm[a], norm[b])) >= threshold]
    for a, b in hits:
        if owner[a] != owner[b] and source_of(owner[a]) == source_of(owner[b]):
            uf.union(a, b)
    groups = defaultdict(list)
    for img in owner:
        groups[uf.find(img)].append(img)
    return [{"images": sorted(g), "products": sorted({owner[i] for i in g})}
            for g in groups.values() if len({owner[i] for i in g}) > 1]


def propose(snap, vectors=None, visual_threshold: float = 0.96, candidate_threshold: float = 0.93) -> dict:
    products = snap.products
    generic = generic_vocabulary(snap)
    brand_words = ({w for b in snap.brands.values() for w in re.findall(r"[a-z0-9]+", plain(b["name"]))}
                   | {source_of(pid) for pid in products} | {"marou"})
    uf = UnionFind(sorted(products))
    evidence = defaultdict(list)
    keys = {pid: name_key(p["name_vi"], brand_words) for pid, p in products.items()}
    by_key = defaultdict(list)
    for pid, k in keys.items():
        if k and not set(k.split()) <= generic:
            by_key[(source_of(pid), k)].append(pid)
    for (src, k), pids in by_key.items():
        for pid in pids[1:]:
            uf.union(pids[0], pid)
        if len(pids) > 1:
            evidence["name"].append({"source": src, "key": k, "products": sorted(pids)})
    shared, candidates = [], []
    if vectors:
        shared = shared_image_clusters(vectors)
        generic_imgs = {i for c in shared if len(c["products"]) >= 3 for i in c["images"]}
        usable = {pid: [(i, v) for i, v in imgs if i not in generic_imgs] for pid, imgs in vectors.items()}
        for (a, b), s in sorted(image_similarity(usable).items()):
            if s >= visual_threshold:
                uf.union(a, b)
                evidence["visual"].append({"a": a, "b": b, "cosine": round(s, 4)})
            elif s >= candidate_threshold:
                candidates.append({"a": a, "b": b, "cosine": round(s, 4)})
    members = defaultdict(list)
    for pid in products:
        members[uf.find(pid)].append(pid)
    families, product_family = [], {}
    for root_id, pids in sorted(members.items()):
        pids = sorted(pids)
        fid = "fam-" + pids[0].removeprefix("p-")
        for pid in pids:
            product_family[pid] = fid
        if len(pids) > 1:
            inside = set(pids)
            why = [{"type": "name", "key": e["key"]} for e in evidence["name"] if set(e["products"]) <= inside]
            why += [{"type": "visual", **e} for e in evidence["visual"] if e["a"] in inside]
            families.append({"family_id": fid, "products": pids, "names": [products[p]["name_vi"] for p in pids],
                             "evidence": why})
    # Dòng thiết kế: từ không chung chung, không phải mã/màu, xuất hiện ở ≥2 sản phẩm cùng nguồn (không gộp).
    terms = defaultdict(set)
    for pid, k in keys.items():
        for t in set(k.split()) - generic - COLORS:
            if len(t) >= 4:
                terms[(source_of(pid), t)].add(pid)
    lines = [{"source": s, "term": t, "products": sorted(p)} for (s, t), p in sorted(terms.items())
             if len(p) >= 2 and len({product_family[x] for x in p}) >= 2]
    return {"families": families, "product_family": product_family, "evidence": evidence,
            "visual_candidates": sorted(candidates, key=lambda c: -c["cosine"]),
            "shared_image_clusters": shared, "design_lines": lines,
            "params": {"visual_threshold": visual_threshold, "candidate_threshold": candidate_threshold,
                       "shared_image_threshold": 0.99, "visual_used": bool(vectors)}}


def load_vectors(index_dir: Path, snap) -> tuple[dict | None, str]:
    from app.image.index import ImageIndex, IndexUnavailable
    try:
        idx = ImageIndex.load(index_dir)
    except IndexUnavailable as e:
        return None, f"không dùng ảnh: {e}"
    if idx.meta.get("catalog_sha256") != snap.sha256:
        return None, "không dùng ảnh: chỉ mục dựng cho catalog khác, hãy dựng lại"
    out = defaultdict(list)
    for e, v in zip(idx.entries, idx.vectors):
        if e.product_id in snap.products:
            out[e.product_id].append((e.image_id, list(v)))
    return dict(out), f"{idx.model_id}@{idx.revision[:12]}"


def markdown(r: dict, snap) -> str:
    name = lambda p: snap.products[p]["name_vi"]  # noqa: E731
    n_multi = sum(len(f["products"]) for f in r["families"])
    lines = ["# Đề xuất họ sản phẩm (chưa duyệt)", "",
             f"- Catalog `{snap.version}` (`{snap.sha256[:12]}…`), {len(snap.products)} sản phẩm; ảnh: {r['visual_source']}",
             f"- **{len(r['families'])} họ nhiều thành viên** gồm {n_multi} sản phẩm; "
             f"{len(snap.products) - n_multi} sản phẩm đứng riêng → {len(set(r['product_family'].values()))} họ",
             f"- Liên kết theo tên: {len(r['evidence'].get('name', []))} nhóm; theo ảnh (cosine ≥ {r['params']['visual_threshold']}): "
             f"{len(r['evidence'].get('visual', []))} cặp; ứng viên ảnh chưa gộp: {len(r['visual_candidates'])}",
             f"- Cụm ảnh gần như đồng nhất giữa sản phẩm khác nhau: {len(r['shared_image_clusters'])}", "",
             "Ngưỡng chưa hiệu chỉnh. Người duyệt xác nhận/tách/gộp trước khi dùng `family_id` cho split.", "",
             "## Họ nhiều thành viên", ""]
    for f in sorted(r["families"], key=lambda f: -len(f["products"])):
        why = ", ".join(f"tên “{e['key']}”" if e["type"] == "name" else f"ảnh {e['cosine']}" for e in f["evidence"][:4])
        lines.append(f"- `{f['family_id']}` ({len(f['products'])}): " + "; ".join(n[:50] for n in f["names"][:8])
                     + (" …" if len(f["names"]) > 8 else "") + f" — *{why}*")
    lines += ["", "## Ảnh dùng chung (cần quyết định giữ/loại khỏi gallery)", ""]
    for c in sorted(r["shared_image_clusters"], key=lambda c: -len(c["products"])):
        tag = "ảnh minh họa chung, không dùng để gom họ" if len(c["products"]) >= 3 else "dùng để gom họ"
        lines.append(f"- {len(c['images'])} ảnh / {len(c['products'])} sản phẩm ({tag}): "
                     + "; ".join(name(p)[:40] for p in c["products"]) + f" — `{', '.join(c['images'][:3])}`")
    lines += ["", "## Ứng viên ảnh chưa gộp (30 cặp đầu)", "", "| cosine | A | B |", "|---|---|---|"]
    lines += [f"| {c['cosine']} | {name(c['a'])[:45]} | {name(c['b'])[:45]} |" for c in r["visual_candidates"][:30]]
    lines += ["", "## Dòng thiết kế gợi ý (không gộp; cân nhắc giữ cùng split)", ""]
    lines += [f"- {d['source']} · **{d['term']}**: {len(d['products'])} sản phẩm" for d in
              sorted(r["design_lines"], key=lambda d: -len(d["products"]))[:40]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--visual-threshold", type=float, default=0.96)
    ap.add_argument("--candidate-threshold", type=float, default=0.93)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports" / "benchmark")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    snap = load_snapshot(args.catalog, include_drafts=True)
    vectors, visual_source = load_vectors(args.index_dir, snap)
    r = propose(snap, vectors, args.visual_threshold, args.candidate_threshold)
    now = datetime.now(TZ)
    r = {"status": "proposed_unreviewed", "catalog_version": snap.version, "catalog_sha256": snap.sha256,
         "generated_at": now.isoformat(timespec="seconds"), "visual_source": visual_source,
         "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), **r}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    args.report_dir.mkdir(parents=True, exist_ok=True)
    rep = args.report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_family-proposal.md"
    rep.write_text(markdown(r, snap), encoding="utf-8")
    print(f"{len(r['families'])} họ nhiều thành viên, {len(set(r['product_family'].values()))} họ tổng; "
          f"ảnh: {visual_source}. Ghi {args.out} và {rep}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
