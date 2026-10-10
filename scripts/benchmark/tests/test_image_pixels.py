"""Optional Pillow tests: generated patterns only, no benchmark/user photos.

Run with a Python that has scripts/benchmark/requirements-images.txt:
  python -m unittest discover -s scripts/benchmark/tests -p test_image_pixels.py -v
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
import audit_image_pixels as pixels


def pattern(kind=0):
    image = Image.new("RGB", (32, 24))
    for y in range(image.height):
        for x in range(image.width):
            image.putpixel((x, y), ((x * (13 + kind) + y * 7) % 256,
                                   (y * 17 + x * kind) % 256, (x * y + kind * 31) % 256))
    return image


def encoded(image=None, note=None, fmt="PNG", **kwargs):
    image = image if image is not None else pattern()
    if note is not None:
        meta = PngImagePlugin.PngInfo(); meta.add_text("test", note); kwargs["pnginfo"] = meta
    output = io.BytesIO(); image.save(output, format=fmt, **kwargs)
    return output.getvalue()


class DecodeTests(unittest.TestCase):
    def test_png_and_jpeg_fully_decode(self):
        for fmt in ("PNG", "JPEG", "WEBP"):
            with self.subTest(fmt=fmt):
                result = pixels.decode_image(encoded(fmt=fmt))
                self.assertEqual(result["format"], fmt)
                self.assertEqual((result["display_width"], result["display_height"]), (32, 24))
                self.assertEqual(len(result["dhash64"]), 16)

    def test_metadata_change_preserves_pixel_hash(self):
        a, b = encoded(note="one"), encoded(note="two")
        self.assertNotEqual(pixels.digest(a), pixels.digest(b))
        self.assertEqual(pixels.decode_image(a)["pixel_sha256"], pixels.decode_image(b)["pixel_sha256"])

    def test_exif_orientation_changes_display_dimensions(self):
        exif = Image.Exif(); exif[274] = 6
        result = pixels.decode_image(encoded(fmt="JPEG", exif=exif))
        self.assertEqual((result["stored_width"], result["stored_height"]), (32, 24))
        self.assertEqual((result["display_width"], result["display_height"]), (24, 32))

    def test_transparency_is_composited_on_white(self):
        a = encoded(Image.new("RGBA", (8, 8), (255, 0, 0, 0)))
        b = encoded(Image.new("RGB", (8, 8), "white"))
        self.assertEqual(pixels.decode_image(a)["pixel_sha256"], pixels.decode_image(b)["pixel_sha256"])

    def test_solid_colors_show_why_dhash_is_only_a_candidate(self):
        a = pixels.decode_image(encoded(Image.new("RGB", (8, 8), "red")))
        b = pixels.decode_image(encoded(Image.new("RGB", (8, 8), "blue")))
        self.assertNotEqual(a["pixel_sha256"], b["pixel_sha256"])
        self.assertEqual(a["dhash64"], b["dhash64"])
        self.assertTrue(a["low_information"] and b["low_information"])

    def test_corrupt_and_truncated_images_fail(self):
        for raw in (b"<html>not an image</html>", encoded()[:-40], encoded(fmt="JPEG")[:-100], b""):
            with self.subTest(size=len(raw)), self.assertRaises((OSError, ValueError, SyntaxError)):
                pixels.decode_image(raw)

    def test_unsupported_format_fails(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            pixels.decode_image(encoded(fmt="BMP"))

    def test_animated_png_fails(self):
        raw = encoded(save_all=True, append_images=[pattern(1)], duration=100, loop=0)
        with self.assertRaisesRegex(ValueError, "multi-frame"):
            pixels.decode_image(raw)

    def test_pixel_and_byte_limits(self):
        raw = encoded()
        with patch.object(pixels, "MAX_PIXELS", 10), self.assertRaisesRegex(ValueError, "pixels"):
            pixels.decode_image(raw)
        with patch.object(pixels, "MAX_BYTES", 10), self.assertRaisesRegex(ValueError, "size"):
            pixels.decode_image(raw)

    def test_hamming_threshold_boundary_and_invalid_threshold(self):
        a = {"key": "a", "kind": "query", "split": "dev", "status": "decoded", "dhash64": "0" * 16,
             "pixel_sha256": "a" * 64, "low_information": False}
        b = {**a, "key": "b", "split": "test", "dhash64": "0" * 15 + "7", "pixel_sha256": "b" * 64}
        self.assertEqual(pixels.find_candidates([a, b], 2), [])
        match = pixels.find_candidates([a, b], 3)[0]
        self.assertEqual(match["distance"], 3)
        self.assertEqual(match["relationship"], "query_cross_split")
        self.assertEqual(match["review_priority"], "high")
        with self.assertRaises(ValueError): pixels.find_candidates([a, b], 65)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.catalog = root / "gallery/database.json"
        self.catalog.parent.mkdir()
        data = json.loads((ROOT / "backend/tests/fixtures/catalog.fixture.json").read_bytes())
        data["products"] = [data["products"][0]]
        for index, image in enumerate(data["products"][0]["images"]):
            image["local_path"] = f"gallery-{index}.png"
            raw = encoded(pattern(index))
            (self.catalog.parent / image["local_path"]).write_bytes(raw)
            image.update(sha256=pixels.digest(raw), width=32, height=24)
        self.catalog.write_text(json.dumps(data), encoding="utf-8")
        self.manifest = root / "query/manifest.json"
        (self.manifest.parent / "raw").mkdir(parents=True)
        self.data = {"manifest_version": "1.0.0", "catalog_sha256": pixels.digest(self.catalog.read_bytes()),
                     "include_drafts": False, "samples": []}
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")

    def query(self, qid, raw, split="dev"):
        (self.manifest.parent / f"raw/{qid}.png").write_bytes(raw)
        self.data["samples"].append({"qid": qid, "task": "similar", "text_vi": None, "split": split,
            "family_id": qid, "capture_session_id": qid, "source_asset_id": qid, "source_asset_sha256": pixels.digest(raw),
            "image_path": f"raw/{qid}.png", "sha256": pixels.digest(raw), "source_url": None,
            "usage_rights": {"status": "unknown", "evidence": None}, "independence_review": None, "judgment": None})
        self.save()

    def test_empty_queries_still_decode_gallery_without_approval(self):
        result = pixels.audit_pixels(self.manifest, self.catalog)
        self.assertEqual(result["status"], "pending_collection")
        self.assertEqual(result["summary"]["decoded"], 2)
        self.assertFalse(result["benchmark_approved"])

    def test_metadata_reencode_matches_gallery_pixels(self):
        self.query("q1", encoded(note="metadata changed"))
        result = pixels.audit_pixels(self.manifest, self.catalog)
        self.assertEqual(result["collection_audit"]["status"], "pending_review")
        self.assertEqual(result["status"], "requires_visual_review")
        self.assertTrue(any(p["match"] == "normalized_pixels" and p["relationship"] == "query_gallery"
                            for p in result["candidates"]))

    def test_cross_split_reencoded_queries_are_flagged(self):
        self.query("q1", encoded(pattern(3), note="one"), "train")
        self.query("q2", encoded(pattern(3), note="two"), "test")
        result = pixels.audit_pixels(self.manifest, self.catalog)
        self.assertTrue(any(p["match"] == "normalized_pixels" and p["relationship"] == "query_cross_split"
                            for p in result["candidates"]))

    def test_bytes_valid_but_query_decode_invalid(self):
        self.query("q1", b"not a photo")
        result = pixels.audit_pixels(self.manifest, self.catalog)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["summary"]["failed"], 1)

    def test_catalog_dimensions_mismatch_is_reported(self):
        data = json.loads(self.catalog.read_bytes()); data["products"][0]["images"][0]["width"] = 99
        self.catalog.write_text(json.dumps(data), encoding="utf-8")
        self.data["catalog_sha256"] = pixels.digest(self.catalog.read_bytes()); self.save()
        result = pixels.audit_pixels(self.manifest, self.catalog)
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any(i["code"] == "dimension_mismatch" for i in result["issues"]))

    def test_invalid_collection_stops_pixel_scan(self):
        self.data["catalog_sha256"] = "0" * 64; self.save()
        with patch.object(pixels, "read_image", side_effect=AssertionError("must not decode")):
            result = pixels.audit_pixels(self.manifest, self.catalog)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["images"], [])

    def test_containment_and_checksum_fail_before_decode(self):
        with self.assertRaises(ValueError):
            pixels.read_image(self.manifest.parent / "raw", "../../gallery/gallery-0.png", None)
        with self.assertRaisesRegex(ValueError, "checksum"):
            pixels.read_image(self.catalog.parent, "gallery-0.png", "0" * 64)

    def test_input_change_between_audits_is_detected(self):
        real_audit = pixels.audit_manifest
        def mutate(*args):
            report = real_audit(*args)
            self.manifest.write_text("{}", encoding="utf-8")
            return report
        with patch.object(pixels, "audit_manifest", side_effect=mutate):
            result = pixels.audit_pixels(self.manifest, self.catalog)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("changed", result["issues"][0]["message"])

    def test_review_escapes_names_and_encodes_local_paths(self):
        result = pixels.audit_pixels(self.manifest, self.catalog)
        result["images"][0]["name"] = '<script>alert("x")</script>'
        page = pixels.render_review(result, self.manifest.parent / "review")
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("gallery-0.png", page)

    def test_cli_keeps_inputs_and_writes_reports(self):
        before = {p: p.read_bytes() for p in self.catalog.parent.parent.rglob('*') if p.is_file()}
        reports = self.manifest.parent / "reports"
        review = self.manifest.parent / "review"
        argv = ["audit_image_pixels.py", "--manifest", str(self.manifest), "--catalog", str(self.catalog),
                "--report-dir", str(reports), "--review-out", str(review)]
        with patch.object(sys, "argv", argv): self.assertEqual(pixels.main(), 0)
        files = list(reports.glob("*.json")); self.assertEqual(len(files), 1)
        self.assertTrue(files[0].with_suffix(".md").exists())
        self.assertTrue((review / "index.html").exists())
        self.assertTrue(all(p.read_bytes() == raw for p, raw in before.items()))
        with patch.object(sys, "argv", argv), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            pixels.main()

    def test_cli_requires_review_for_query_gallery_pixel_match(self):
        self.query("q1", encoded(note="new metadata"))
        reports = self.manifest.parent / "reports"
        with patch.object(sys, "argv", ["audit_image_pixels.py", "--manifest", str(self.manifest),
                "--catalog", str(self.catalog), "--report-dir", str(reports)]):
            self.assertEqual(pixels.main(), 2)
        result = json.loads(next(reports.glob("*.json")).read_bytes())
        self.assertEqual(result["status"], "requires_visual_review")
        self.assertFalse(result["benchmark_approved"])

    def test_cli_records_decode_failure_without_creating_review_page(self):
        self.query("q1", b"not an image")
        reports, review = self.manifest.parent / "reports", self.manifest.parent / "review"
        with patch.object(sys, "argv", ["audit_image_pixels.py", "--manifest", str(self.manifest),
                "--catalog", str(self.catalog), "--report-dir", str(reports), "--review-out", str(review)]):
            self.assertEqual(pixels.main(), 1)
        self.assertFalse(review.exists())
        result = json.loads(next(reports.glob("*.json")).read_bytes())
        self.assertEqual(result["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
