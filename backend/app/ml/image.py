"""Adapter embedding ảnh chạy ONNX Runtime.

    VNSTORE_IMAGE_ADAPTER=app.ml.image:SigLIP2Base   (google/siglip2-base-patch16-224, Apache-2.0)
    VNSTORE_IMAGE_ADAPTER=app.ml.image:DINOv2Base    (facebook/dinov2-base, Apache-2.0)

Ảnh giải mã bằng Pillow, xoay theo EXIF, ghép nền trắng nếu có alpha, chuyển RGB, rồi resize/crop/
chuẩn hóa theo preprocessor_config.json của checkpoint (cài đặt lại bằng NumPy, không qua torch).
Luôn float32. Cấu hình này nằm trong `preprocess` và được ghi vào manifest chỉ mục.
"""
from __future__ import annotations

import io
from collections.abc import Sequence

from ..media import MediaError
from . import LazyModel, hf_file, hf_json, session

FORMATS = {"JPEG", "PNG", "WEBP"}
DECODE = "pillow; exif_transpose; alpha->white; RGB"


def decode(data: bytes):
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in FORMATS:
            raise MediaError("image_invalid", "Chỉ nhận ảnh JPEG, PNG hoặc WebP.", 415)
        img.load()
        img = ImageOps.exif_transpose(img)
    except MediaError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as e:
        raise MediaError("image_invalid", "Không giải mã được ảnh; file có thể bị hỏng.") from e
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.getchannel("A"))
        return bg
    return img.convert("RGB")


def pixel_values(img, cfg: dict):
    """Theo quy ước image processor của Transformers: resize → center crop → rescale → normalize → CHW."""
    import numpy as np
    from PIL import Image
    resample = Image.Resampling(cfg.get("resample", 2))
    size = cfg.get("size") or {}
    if cfg.get("do_resize", True):
        if "shortest_edge" in size:
            s = size["shortest_edge"]
            w, h = img.size
            short, long = (w, h) if w <= h else (h, w)
            new_short, new_long = s, int(s * long / short)
            img = img.resize((new_short, new_long) if w <= h else (new_long, new_short), resample)
        else:
            img = img.resize((size["width"], size["height"]), resample)
    if cfg.get("do_center_crop"):
        crop = cfg["crop_size"]
        w, h = img.size
        left, top = (w - crop["width"]) // 2, (h - crop["height"]) // 2
        img = img.crop((left, top, left + crop["width"], top + crop["height"]))
    x = np.asarray(img, dtype=np.float32)
    if cfg.get("do_rescale", True):
        x = x * float(cfg.get("rescale_factor", 1 / 255))
    if cfg.get("do_normalize", True):
        x = (x - np.array(cfg["image_mean"], dtype=np.float32)) / np.array(cfg["image_std"], dtype=np.float32)
    return x.transpose(2, 0, 1)


class _OnnxVision:
    model_id: str      # checkpoint gốc
    revision: str      # revision repo ONNX đã ghim
    onnx_repo: str
    onnx_file: str
    output: str        # tên output dùng làm vector
    cls_token = False  # True: lấy token 0 của output dạng (batch, token, dim)
    license = "apache-2.0"

    def __init__(self, batch_size: int = 16):
        self.batch_size = batch_size
        self._model = LazyModel()

    @property
    def preprocess(self) -> dict:
        return {"decode": DECODE, "runtime": "onnxruntime", "onnx": f"{self.onnx_repo}/{self.onnx_file}",
                "processor": "preprocessor_config.json (numpy)",
                "output": f"{self.output}[:, 0]" if self.cls_token else self.output, "dtype": "float32"}

    def _load(self):
        cfg = hf_json(self.onnx_repo, self.revision, "preprocessor_config.json")
        sess = session(hf_file(self.onnx_repo, self.revision, self.onnx_file))
        names = [o.name for o in sess.get_outputs()]
        if self.output not in names:
            raise RuntimeError(f"{self.onnx_file} không có output {self.output}; có {names}")
        return cfg, sess

    def embed(self, images: Sequence[bytes]) -> list[list[float]]:
        import numpy as np
        cfg, sess = self._model.get(self._load)
        decoded = [decode(b) for b in images]  # lỗi giải mã báo trước khi chạy model
        out: list[list[float]] = []
        for i in range(0, len(decoded), self.batch_size):
            batch = np.stack([pixel_values(img, cfg) for img in decoded[i:i + self.batch_size]])
            (vec,) = sess.run([self.output], {"pixel_values": batch})
            if self.cls_token:
                vec = vec[:, 0]
            out.extend(vec.astype(np.float32).reshape(len(batch), -1).tolist())
        return out


class SigLIP2Base(_OnnxVision):
    model_id = "google/siglip2-base-patch16-224"
    onnx_repo = "onnx-community/siglip2-base-patch16-224-ONNX"
    revision = "ba1f3b0843f24bc5417d38e19c37b287d719b2f4"
    onnx_file = "onnx/vision_model.onnx"
    output = "pooler_output"


class DINOv2Base(_OnnxVision):
    model_id = "facebook/dinov2-base"
    onnx_repo = "onnx-community/dinov2-base-ONNX"
    revision = "9a1732c724ef0847dcedf00d3d5a93f61dea0370"
    onnx_file = "onnx/model.onnx"
    # Bản ONNX chỉ xuất last_hidden_state (đã qua layernorm); pooler_output của Dinov2Model là token CLS.
    output = "last_hidden_state"
    cls_token = True
