"""Adapter embedding ảnh chạy ONNX Runtime.

    VNSTORE_IMAGE_ADAPTER=app.ml.image:SigLIP2Base   (google/siglip2-base-patch16-224, Apache-2.0)
    VNSTORE_IMAGE_ADAPTER=app.ml.image:DINOv2Base    (facebook/dinov2-base, Apache-2.0)
    VNSTORE_IMAGE_ADAPTER=app.ml.image:OpenCLIPViTB32 (laion/CLIP-ViT-B-32-laion2B-s34B-b79K, MIT)

Ảnh giải mã bằng Pillow, xoay theo EXIF, ghép nền trắng nếu có alpha, chuyển RGB, rồi resize/crop/
chuẩn hóa theo preprocessor_config.json của checkpoint (cài đặt lại bằng NumPy, không qua torch).
Luôn float32. Cấu hình này nằm trong `preprocess` và được ghi vào manifest chỉ mục.
"""
from __future__ import annotations

import io
from collections.abc import Sequence

from ..media import MediaError
from . import LazyModel, fill_dims, hf_file, hf_json, session

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
    input_name = "pixel_values"
    processor_file = "preprocessor_config.json"
    cls_token = False  # True: lấy token 0 của output dạng (batch, token, dim)
    license = "apache-2.0"

    def __init__(self, batch_size: int = 16):
        self.batch_size = batch_size
        self._model = LazyModel()

    @property
    def preprocess(self) -> dict:
        return {"decode": DECODE, "runtime": "onnxruntime", "onnx": f"{self.onnx_repo}/{self.onnx_file}",
                "processor": f"{self.processor_file} (numpy)",
                "output": f"{self.output}[:, 0]" if self.cls_token else self.output, "dtype": "float32"}

    def processor_config(self) -> dict:
        """Cấu hình tiền xử lý dạng preprocessor_config.json của Transformers."""
        return hf_json(self.onnx_repo, self.revision, self.processor_file)

    def _load(self):
        cfg = self.processor_config()
        from PIL import Image
        _, h, w = pixel_values(Image.new("RGB", (512, 512)), cfg).shape  # kích thước sau tiền xử lý

        def shapes(name, dims):  # chỉ batch đổi (1 khi tìm, tới batch_size khi dựng chỉ mục)
            return tuple(fill_dims(dims, {0: b, 1: 3, 2: h, 3: w}) for b in (1, 1, self.batch_size))

        sess = session(hf_file(self.onnx_repo, self.revision, self.onnx_file), shapes)
        names = [o.name for o in sess.get_outputs()]
        if self.output not in names:
            raise RuntimeError(f"{self.onnx_file} không có output {self.output}; có {names}")
        (inp,) = [i for i in sess.get_inputs() if i.name == self.input_name] or [None]
        if inp is None:
            raise RuntimeError(f"{self.onnx_file} không có input {self.input_name}")
        batch = inp.shape[0] if isinstance(inp.shape[0], int) else self.batch_size  # bản export cố định batch
        return cfg, sess, batch

    def embed(self, images: Sequence[bytes]) -> list[list[float]]:
        import numpy as np
        cfg, sess, step = self._model.get(self._load)
        decoded = [decode(b) for b in images]  # lỗi giải mã báo trước khi chạy model
        out: list[list[float]] = []
        for i in range(0, len(decoded), step):
            batch = np.stack([pixel_values(img, cfg) for img in decoded[i:i + step]])
            (vec,) = sess.run([self.output], {self.input_name: batch})
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


class OpenCLIPViTB32(_OnnxVision):
    """Baseline OpenCLIP của PLAN §7.1. Bản ONNX chỉ có phần thị giác do dự án Immich xuất từ OpenCLIP; model card
    không ghi license riêng, trọng số gốc của LAION là MIT. Đã đối chiếu đầu ra với bản xuất độc lập
    onnx-community/CLIP-ViT-B-32-laion2B-s34B-b79K-ONNX (image_embeds) trên 41 ảnh catalog: cosine ≥ 0,9999998
    (scripts/benchmark/crosscheck_openclip.py, 11/10/2026). Output `embedding` là vector chiếu 512 chiều, đã chuẩn
    hóa L2. Bản export cố định batch 1."""
    model_id = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"
    onnx_repo = "immich-app/ViT-B-32__laion2b-s34b-b79k"
    revision = "19a057a0fb927cf239541300e74237cd56c7ffe2"
    onnx_file = "visual/model.onnx"
    input_name = "image"
    processor_file = "visual/preprocess_cfg.json"
    output = "embedding"
    license = "mit"

    def processor_config(self) -> dict:
        return openclip_processor(hf_json(self.onnx_repo, self.revision, self.processor_file))


def openclip_processor(cfg: dict) -> dict:
    """preprocess_cfg của OpenCLIP (resize cạnh ngắn bicubic → center crop → /255 → normalize) sang dạng Transformers."""
    if cfg.get("resize_mode") != "shortest" or cfg.get("interpolation") != "bicubic" or cfg.get("mode") != "RGB":
        raise RuntimeError(f"preprocess_cfg OpenCLIP chưa hỗ trợ: {cfg}")
    h, w = cfg["size"] if isinstance(cfg["size"], list) else (cfg["size"], cfg["size"])
    if h != w:
        raise RuntimeError("OpenCLIP resize_mode=shortest cần ảnh vuông")
    return {"do_resize": True, "size": {"shortest_edge": h}, "resample": 3, "do_center_crop": True,
            "crop_size": {"height": h, "width": w}, "do_rescale": True, "rescale_factor": 1 / 255,
            "do_normalize": True, "image_mean": cfg["mean"], "image_std": cfg["std"]}
