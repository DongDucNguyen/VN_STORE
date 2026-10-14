"""Dựng chỉ mục vector văn bản sản phẩm cho nhánh ngữ nghĩa của tìm bằng chữ (PLAN.md mục 5 bước 7).

    .venv-ml/Scripts/python scripts/build_indexes/build_text_index.py --adapter app.ml.text:BGEM3

Mặc định ghi vào artifacts/indexes/text/<model@revision>/, đúng nơi API tìm khi bật VNSTORE_TEXT_ADAPTER. Chỉ mục
là dữ liệu dẫn xuất, dựng lại được từ database.json. Mặc định gồm cả draft để dùng chung cho chế độ phát triển; API
chỉ trả sản phẩm đang hiển thị.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.adapters import AdapterError, load_adapter  # noqa: E402
from app.catalog.store import CatalogError, load_snapshot  # noqa: E402
from app.image.index import model_dir_name  # noqa: E402
from app.search.semantic import TextEmbedder, TextIndex, TextIndexUnavailable  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", default=os.environ.get("VNSTORE_TEXT_ADAPTER"),
                    help="module:thuộc_tính (mặc định lấy VNSTORE_TEXT_ADAPTER)")
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--out", type=Path, default=None, help="thư mục gốc chỉ mục (mặc định artifacts/indexes/text)")
    ap.add_argument("--published-only", action="store_true")
    ap.add_argument("--batch-size", type=int, default=16)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if not args.adapter:
        print("Cần --adapter hoặc VNSTORE_TEXT_ADAPTER", file=sys.stderr)
        return 2
    try:
        embedder = load_adapter(args.adapter, TextEmbedder)
        snap = load_snapshot(args.catalog, include_drafts=not args.published_only)
    except (AdapterError, CatalogError) as e:
        print(e, file=sys.stderr)
        return 2
    t0 = time.perf_counter()
    try:
        index = TextIndex.build(snap, embedder, args.batch_size,
                                progress=lambda done, total: print(f"\r{done}/{total} sản phẩm", end="", flush=True))
    except TextIndexUnavailable as e:
        print(f"\n{e}", file=sys.stderr)
        return 1
    root = args.out or Path(os.environ.get("VNSTORE_TEXT_INDEX_DIR", ROOT / "artifacts" / "indexes" / "text"))
    out = index.save(root / model_dir_name(embedder.model_id, embedder.revision))
    print(f"\nĐã dựng {len(index.product_ids)} vector {index.dim} chiều bằng {embedder.model_id}@{embedder.revision} "
          f"trong {time.perf_counter() - t0:.1f}s → {out}")
    print(f"Catalog {snap.version} ({snap.sha256[:12]}…), {'gồm draft' if snap.include_drafts else 'chỉ published'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
