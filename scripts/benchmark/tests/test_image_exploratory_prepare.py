"""Pillow tests for run_image_exploratory.prepare(): generated images only.

prepare() mirrors frontend prepareImage(): EXIF orientation, normalized crop, white background for alpha,
long side ≤1024 without upscaling, JPEG q90.
  python -m unittest discover -s scripts/benchmark/tests -p test_image_exploratory_prepare.py -v
"""
from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
from run_image_exploratory import prepare  # noqa: E402


def encode(img: Image.Image, fmt: str, **kw) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, **kw)
    return buf.getvalue()


def decode(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


class PrepareTests(unittest.TestCase):
    def test_output_is_jpeg_and_small_images_are_not_upscaled(self):
        out = decode(prepare(encode(Image.new("RGB", (300, 200), (10, 120, 200)), "PNG"), None))
        self.assertEqual((out.format, out.size), ("JPEG", (300, 200)))

    def test_long_side_capped_at_1024_keeping_aspect(self):
        out = decode(prepare(encode(Image.new("RGB", (3000, 1500), "gray"), "JPEG"), None))
        self.assertEqual(out.size, (1024, 512))

    def test_crop_uses_normalized_box(self):
        img = Image.new("RGB", (200, 100), (255, 0, 0))
        img.paste((0, 0, 255), (100, 0, 200, 100))  # right half blue
        out = decode(prepare(encode(img, "PNG"), [0.5, 0.0, 1.0, 1.0]))
        self.assertEqual(out.size, (100, 100))
        r, g, b = out.convert("RGB").getpixel((50, 50))
        self.assertGreater(b, 200)
        self.assertLess(r, 60)

    def test_exif_orientation_applied_before_crop(self):
        img = Image.new("RGB", (200, 100), (255, 0, 0))
        img.paste((0, 255, 0), (0, 0, 100, 100))  # left half green in stored pixels
        exif = Image.Exif()
        exif[0x0112] = 6  # rotate 90° CW on display: stored left half becomes top half
        out = decode(prepare(encode(img, "JPEG", exif=exif.tobytes(), quality=95), [0.0, 0.0, 1.0, 0.5]))
        self.assertEqual(out.size, (100, 100))
        r, g, b = out.convert("RGB").getpixel((50, 50))
        self.assertGreater(g, 200)
        self.assertLess(r, 60)

    def test_transparent_png_flattened_on_white(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        out = decode(prepare(encode(img, "PNG"), None))
        self.assertEqual(out.mode, "RGB")
        self.assertTrue(all(c > 245 for c in out.getpixel((32, 32))))

    def test_palette_and_webp_inputs(self):
        for img, fmt in ((Image.new("P", (40, 40), 3), "PNG"), (Image.new("RGB", (40, 40), "white"), "WEBP")):
            self.assertEqual(decode(prepare(encode(img, fmt), None)).format, "JPEG")


if __name__ == "__main__":
    unittest.main()
