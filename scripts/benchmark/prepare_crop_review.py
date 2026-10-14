"""Tạo trang duyệt vùng cắt (crop_review.html) cho bộ ảnh thử khám phá.

    python scripts/benchmark/prepare_crop_review.py
    python scripts/benchmark/prepare_crop_review.py --dataset benchmarks/image/exploratory/<phiên bản>

Trang đặt cạnh manifest để link tương đối tới raw/images/ hoạt động khi mở offline. Mỗi ca crop hiện ảnh
gốc với vùng đề xuất từ crops.json, hướng dẫn cắt và đúng phần ảnh sẽ gửi đi (cạnh ≤1024 px như giao diện).
Người duyệt đồng ý, vẽ lại hoặc loại từng vùng rồi xuất crops.reviewed.json; chạy lại bằng
`run_image_exploratory.py --crops <file>`. Trang không hiện kết quả tìm kiếm để vùng được chốt trước khi xem.
Tạo lại trang khi crops.json hoặc test_cases.json đổi: nháp trong trình duyệt gắn với hash crops.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_image_exploratory import valid_box  # noqa: E402

TEMPLATE = Path(__file__).with_name("crop_review_template.html")
DEFAULT_DATASET = ROOT / "benchmarks" / "image" / "exploratory" / "expanded-2026-10-13"


def build(ds: Path) -> dict:
    manifest = json.loads((ds / "manifest.json").read_text(encoding="utf-8"))
    cases = json.loads((ds / "test_cases.json").read_text(encoding="utf-8"))["cases"]
    crops_bytes = (ds / "crops.json").read_bytes()
    crops = json.loads(crops_bytes)
    images = {it["id"]: it for it in manifest["images"]}
    out = []
    for c in cases:
        if c["task"] != "manual_crop_comparison":
            continue
        if c["case_id"] not in crops["crops"]:
            raise SystemExit(f"{c['case_id']}: chưa có vùng đề xuất trong crops.json")
        if not valid_box(crops["crops"][c["case_id"]]):
            raise SystemExit(f"{c['case_id']}: vùng đề xuất không hợp lệ: {crops['crops'][c['case_id']]}")
        it = images[c["image_id"]]
        if not (ds / it["image_path"]).is_file():
            raise SystemExit(f"{c['image_id']}: thiếu file {it['image_path']}")
        out.append({"case_id": c["case_id"], "image_id": c["image_id"], "image_path": it["image_path"],
                    "instruction": c["crop_instruction_vi"], "proposed": crops["crops"][c["case_id"]],
                    "role": it["role"], "group": it["group"], "topic": it.get("topic"),
                    "title": it["title"].removeprefix("File:")})
    extra = set(crops["crops"]) - {c["case_id"] for c in out}
    if extra:
        raise SystemExit(f"crops.json có ca không thuộc test_cases: {sorted(extra)}")
    return {"dataset_version": manifest["dataset_version"], "format": crops["format"],
            "chosen_by": crops["chosen_by"], "source_crops_sha256": hashlib.sha256(crops_bytes).hexdigest(),
            "cases": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--out", type=Path, help="mặc định <dataset>/crop_review.html")
    args = ap.parse_args()
    ds = args.dataset.resolve()
    out = (args.out or ds / "crop_review.html").resolve()
    if out.parent != ds:
        raise SystemExit("Trang phải nằm trong thư mục bộ dữ liệu để link tới raw/ hoạt động")
    packet = build(ds)
    payload = json.dumps(packet, ensure_ascii=False).replace("<", "\\u003c")
    out.write_text(TEMPLATE.read_text(encoding="utf-8").replace("__PACKET_JSON__", payload), encoding="utf-8")
    print(f"{len(packet['cases'])} vùng → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
