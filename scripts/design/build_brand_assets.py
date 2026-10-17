"""Tạo biến thể WebP cho web từ bộ master Nếp Việt v2 (design.md §8).

Đọc PNG trong assets/design-elements/nep-viet-v2, thu nhỏ theo kích thước hiển thị tối đa (≈2x mật độ điểm ảnh)
và ghi vào frontend/public/brand/. Không sửa file master. Chạy lại khi master thay đổi:

    python scripts/design/build_brand_assets.py

Cần Pillow có hỗ trợ WebP.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets" / "design-elements" / "nep-viet-v2"
OUT = ROOT / "frontend" / "public" / "brand"

# (tên xuất, file master, chiều rộng đích, chất lượng, vùng cắt tương đối (x0, y0, x1, y1) hoặc None)
JOBS: list[tuple[str, str, int, int, tuple[float, float, float, float] | None]] = [
    ("bamboo-branch", "cutouts/bamboo-opening-branch.png", 480, 76, None),
    ("bamboo-shadow", "cutouts/bamboo-shadow-clean.png", 820, 60, None),
    ("ceramic-still-life", "cutouts/ceramic-opening-still-life.png", 340, 82, None),
    ("non-la", "cutouts/non-la-section-cutout.png", 720, 80, None),
    ("textile-edge", "cutouts/textile-edge.png", 360, 80, None),
    ("lotus-botanical-01", "botanical/lotus-botanical-01.png", 360, 78, None),
    ("lotus-botanical-02", "botanical/lotus-botanical-02.png", 560, 78, None),
    ("footer-landscape", "scenes/footer-landscape.png", 2172, 72, None),
    ("footer-landscape-sm", "scenes/footer-landscape.png", 1100, 72, None),
    ("lotus-midpage", "scenes/lotus-midpage-desktop.png", 2172, 74, None),
    ("lotus-midpage-md", "scenes/lotus-midpage-desktop.png", 1280, 74, None),
    ("lotus-midpage-mobile", "scenes/lotus-midpage-mobile.png", 820, 74, None),
    ("weave-macro", "textures/bamboo-weave-macro.png", 300, 74, None),
    ("weave-strip", "textures/bamboo-weave-macro.png", 900, 70, (0.0, 0.40, 1.0, 0.58)),
    ("craft-hands", "editorial/craft-hands-editorial.png", 1100, 76, None),
    ("craft-workbench", "editorial/craft-workbench.png", 760, 76, None),
    ("category-ceramics", "categories/category-ceramics.png", 640, 78, None),
    ("category-weaving", "categories/category-weaving.png", 640, 78, None),
    ("category-textiles", "categories/category-textiles.png", 640, 78, None),
    ("category-wood-lacquer", "categories/category-wood-lacquer.png", 640, 78, None),
    ("category-specialties", "categories/category-specialties.png", 640, 78, None),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    for name, rel, width, quality, box in JOBS:
        im = Image.open(SRC / rel)
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        if box:
            w, h = im.size
            im = im.crop((round(box[0] * w), round(box[1] * h), round(box[2] * w), round(box[3] * h)))
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        target = OUT / f"{name}.webp"
        im.save(target, "WEBP", quality=quality, method=6)
        report.append({"file": target.name, "source": rel, "width": im.width, "height": im.height,
                       "bytes": target.stat().st_size})
        print(f"{target.name:28} {im.width}x{im.height} {target.stat().st_size // 1024} KB")
    (OUT / "README.md").write_text(
        "# Brand assets (sinh tự động)\n\n"
        "Biến thể WebP của bộ master `assets/design-elements/nep-viet-v2`, tạo bởi "
        "`scripts/design/build_brand_assets.py`. Đây là ảnh minh họa tạo bằng AI cho lớp trang trí/biên tập — "
        "không phải ảnh sản phẩm, ảnh tư liệu làng nghề hay chứng cứ nguồn gốc. Không sửa tay; chạy lại script.\n",
        encoding="utf-8")
    (OUT / "sizes.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
