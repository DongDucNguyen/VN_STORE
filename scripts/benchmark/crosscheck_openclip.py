"""Đối chiếu adapter OpenCLIPViTB32 (bản ONNX thị giác của Immich) với bản export độc lập của onnx-community.

    .venv-ml/Scripts/python -X utf8 scripts/benchmark/crosscheck_openclip.py [--every 20] [--limit 41]

Không có torch để so với checkpoint gốc, nên so hai bản ONNX do hai bên xuất độc lập từ
laion/CLIP-ViT-B-32-laion2B-s34B-b79K trên cùng ảnh catalog và cùng tiền xử lý NumPy. Bản onnx-community gồm cả
text tower: chạy với chuỗi token rỗng và chỉ lấy image_embeds. Hai bản khớp không chứng minh tiền xử lý NumPy
khớp image processor của Transformers (nợ kỹ thuật riêng). Chạy CPU để không phụ thuộc GPU. Lần đầu tải ~600 MB.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REPO = "onnx-community/CLIP-ViT-B-32-laion2B-s34B-b79K-ONNX"
REVISION = "de693d0c5a5b263ae94ece9bf751e0cda14305d8"
EMPTY_TEXT = [[49406, 49407]]  # <start_of_text><end_of_text>


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--every", type=int, default=20, help="lấy 1 ảnh mỗi N ảnh catalog")
    ap.add_argument("--limit", type=int, default=41)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    os.environ.setdefault("VNSTORE_ML_DEVICE", "cpu")

    import numpy as np
    import onnxruntime as ort

    from app.ml.image import OpenCLIPViTB32, decode, hf_file, hf_json, pixel_values

    db = json.loads(args.catalog.read_text(encoding="utf-8"))
    paths = [im["local_path"] for p in db["products"] for im in p.get("images", [])][::args.every][:args.limit]
    a = np.array(OpenCLIPViTB32().embed([(ROOT / x).read_bytes() for x in paths]), dtype=np.float32)
    cfg = hf_json(REPO, REVISION, "preprocessor_config.json")
    sess = ort.InferenceSession(str(hf_file(REPO, REVISION, "onnx/model.onnx")), providers=["CPUExecutionProvider"])
    ids = np.array(EMPTY_TEXT, dtype=np.int64)
    b = np.array([sess.run(["image_embeds"], {"pixel_values": pixel_values(decode((ROOT / x).read_bytes()), cfg)[None],
                                              "input_ids": ids, "attention_mask": np.ones_like(ids)})[0][0]
                  for x in paths], dtype=np.float32)
    na, nb = (v / np.linalg.norm(v, axis=1, keepdims=True) for v in (a, b))
    cos = (na * nb).sum(1)
    nearest = lambda m, i: int(np.argsort(-(m @ m[i]))[1])  # noqa: E731
    report = {"images": len(paths), "cosine_min": float(cos.min()), "cosine_mean": float(cos.mean()),
              "max_abs_diff_normalized": float(np.abs(na - nb).max()),
              "norm_adapter_mean": float(np.linalg.norm(a, axis=1).mean()),
              "same_nearest_neighbour": sum(nearest(na, i) == nearest(nb, i) for i in range(len(paths))),
              "reference": f"{REPO}@{REVISION}"}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    ok = report["cosine_min"] > 0.9999 and report["same_nearest_neighbour"] == len(paths)
    print("KHỚP" if ok else "LỆCH: kiểm tra lại bản export/tiền xử lý")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
