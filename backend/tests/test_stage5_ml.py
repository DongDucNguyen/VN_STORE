"""Optional real OCR/vision integration plus decoded crop. Not a quality benchmark."""
import io
import os
from pathlib import Path

import pytest

if os.environ.get("VNSTORE_RUN_ML_TESTS") != "1":
    pytest.skip("Opt-in ML environment required", allow_module_level=True)

from PIL import Image
from app.catalog.store import load_snapshot
from app.image.index import ImageIndex
from app.image.pipeline import crop_image, retrieve
from app.ml.image import SigLIP2Base
from app.ml.ocr import RapidOCRLatin
from app.search.config import SearchConfig
from app.search.engine import SearchEngine

ROOT = Path(__file__).resolve().parents[2]


def test_crop_uses_normalized_coordinates_and_removes_metadata():
    img = Image.new("RGB", (120, 80), "red")
    raw = io.BytesIO()
    exif = Image.Exif()
    exif[274], exif[270] = 6, "private metadata"
    img.save(raw, format="PNG", exif=exif)
    cropped = Image.open(io.BytesIO(crop_image(raw.getvalue(), [.25, .25, .75, .75])))
    assert cropped.size == (40, 60) and cropped.getpixel((0, 0)) == (255, 0, 0)
    assert not cropped.getexif()


def test_real_ocr_shared_retrieval_path():
    snap = load_snapshot(ROOT / "database.json", include_drafts=True)
    product = snap.products["p-marou-ba-ria-76-80g"]
    data = (ROOT / product["images"][0]["local_path"]).read_bytes()
    emb = SigLIP2Base()
    from app.modalities import ImageService
    index = ImageIndex.load(ImageService.index_dir(emb))
    index.check(snap, emb)
    ocr = RapidOCRLatin()
    result, diag = retrieve(data, emb, index, SearchEngine(snap, SearchConfig(ocr_weight=.35)), ocr=ocr)
    assert diag["ocr_error"] is None and "MAROU" in diag["ocr_text"].upper()
    assert len([name for name in ocr.config["file_sha256"] if name.endswith(".onnx")]) == 3
    assert "latin.ttf" in ocr.config["file_sha256"] and result["results"]
    assert any("ocr" in r["matched_fields"] for r in result["results"])
    assert result["applied_filters"] == []
