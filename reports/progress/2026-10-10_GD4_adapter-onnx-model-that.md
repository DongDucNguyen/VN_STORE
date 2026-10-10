# GĐ4 — Adapter model thật trên ONNX Runtime + smoke đầu tiên — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ4 (PLAN.md mục 9: "Adapter và sàng lọc các model voice/image") |
| Trạng thái | 🟡 Một phần: **5 adapter thật chạy trên GPU**, đã có smoke. Chưa sàng lọc được vì vẫn 0 clip/0 ảnh query VNStore |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfdc090af7981773dd4689179d0ca47bfe992deed3c2713c7628c801f16`, không thay đổi |
| Commit | Chưa commit |

Tiếp nối [khung adapter voice/ảnh](2026-10-10_GD4_khung-adapter-voice-anh.md).

## 1. Mục tiêu đợt này

Viết adapter cho model thật theo shortlist PLAN §6.1/§7.1, chạy được trên máy demo (RTX 5070 Ti 16 GB), kiểm tra từng adapter cho ra kết quả hợp lý, và đo thử end-to-end qua API.

## 2. Đã làm

**Đổi hướng: ONNX Runtime thay cho PyTorch.** Đã cài `torch 2.14.1+cu130` vào `.venv-ml`, nhưng Windows **Application Control chặn** `torch_cpu.dll`, `torch_cuda.dll`, `torch_python.dll`… (WinError 4551). Vì vậy cả bản CPU cũng không chạy được. Tôi **không** tìm cách vượt chính sách này. `onnxruntime.dll` (Microsoft) và các gói runtime CUDA 13/cuDNN 9 `nvidia-*` thì nạp được, nên đã gỡ torch và chuyển sang `onnxruntime-gpu[cuda,cudnn]==1.31.0`. Mọi model đều chạy trên `CUDAExecutionProvider`.

**Adapter** (`backend/app/ml/`, cài bằng `backend/requirements-ml.txt`):

| Adapter | Checkpoint gốc | Bản ONNX (revision ghim) | License | Ghi chú |
|---|---|---|---|---|
| `app.ml.image:SigLIP2Base` | google/siglip2-base-patch16-224 | onnx-community/…-ONNX `ba1f3b08` `vision_model.onnx` | Apache-2.0 | `pooler_output`, 768 chiều |
| `app.ml.image:DINOv2Base` | facebook/dinov2-base | onnx-community/dinov2-base-ONNX `9a1732c7` | Apache-2.0 | Token CLS của `last_hidden_state` (= `pooler_output` của Transformers) |
| `app.ml.asr:PhoWhisperBase` | vinai/PhoWhisper-base `7ebdb9e8` | onnx-community/PhoWhisper-base-ONNX `41a94b87` | BSD-3-Clause | Tokenizer/cấu hình lấy từ repo onnx-community |
| `app.ml.asr:PhoWhisperSmall` | vinai/PhoWhisper-small `a86b604c` | huuquyet/PhoWhisper-small `515c6b55` | BSD-3-Clause (repo export ghi wtfpl) | Bản export của bên thứ ba; tokenizer lấy từ repo VinAI |
| `app.ml.asr:PhoWhisperSmallInt8` | như trên | cùng repo, `*_quantized.onnx` | như trên | Lượng tử hóa int8 |

- Bản export `huuquyet` có `pytorch_model.bin` **trùng SHA-256** với `vinai/PhoWhisper-small` (`9ec6f07c…`). Điều này cho thấy đúng trọng số gốc, nhưng chưa chứng minh file ONNX được xuất từ chính file đó.
- **Ảnh**: giải mã bằng Pillow, xoay theo EXIF, ghép nền trắng nếu có alpha. Resize/crop/chuẩn hóa được cài lại bằng NumPy theo `preprocessor_config.json` của từng checkpoint. Luôn tính fp32 và ghi cấu hình vào manifest chỉ mục.
- **ASR**: `WhisperFeatureExtractor` (NumPy, không cần torch) → encoder → decoder với KV-cache, giải mã greedy. Prompt cố định `<|vi|><|transcribe|><|notimestamps|>`, chặn token theo `generation_config` và mọi token timestamp. Không đưa transcript hay đáp án vào prompt.
- **VAD**: Silero VAD v6.2.3 (MIT, `silero_vad.onnx` ghim SHA-256 `1a153a22…`, chạy CPU). Gắn mặc định vào adapter PhoWhisper qua móc `detect_speech`. API và `eval_voice.py` gọi móc này sau bộ chặn năng lượng (mã lỗi mới `audio_no_speech`). Tắt bằng `VNSTORE_ASR_VAD=0`.
- **Bộ chặn năng lượng**: hạ từ −50 xuống **−60 dBFS**, vì −50 đã chặn nhầm một clip FLEURS nói nhỏ (−50,1 dBFS). Giờ nó chỉ bắt im lặng số hoặc micro chết.
- **Stopword**: thêm "bằng", "này", "nhưng", "giống" (chỉ dạng có dấu). Lý do: truy vấn ảnh + "bằng mây" đưa "Váy dài Vân bằng lụa" vào top 5.
- **Công cụ**: `make_fleurs_smoke.py` tạo bộ smoke từ FLEURS vi_vn (CC-BY-4.0): 30 câu đọc + 1 clip nhiễu trắng −35 dBFS; float32 được đổi sang PCM16; chỉ đọc member `dev/<số>.wav`. `sanity_image_gallery.py` kiểm tra adapter ảnh bằng leave-one-out trên gallery. `test_ml_adapters.py` là test model thật, chỉ chạy khi bật.
- Chỉ mục ảnh thật đã dựng tại `artifacts/indexes/image/` cho SigLIP2 và DINOv2 (45 ảnh, ~2 giây mỗi model).

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Toàn bộ (môi trường thường) | `.venv/Scripts/python scripts/run_all_tests.py` | **TẤT CẢ ĐẠT 7/7**; backend **340 passed, 1 skipped** (file test ML); **84 E2E passed** |
| Test model thật | `VNSTORE_RUN_ML_TESTS=1 .venv-ml/Scripts/python -m pytest backend/tests/test_ml_adapters.py` | **6 passed** (4,7 giây) |
| Keyword sau khi thêm stopword | `eval_keyword.py` smoke + `compare_keyword.py` so với run 15:10 | `comparable_descriptive`, mọi delta = 0, **0 truy vấn đổi thứ hạng** ([so sánh](../benchmark/2026-10-10_164127-729840_keyword-comparison.md)) |
| API với model thật trên catalog thật (cổng 8020, gồm draft) | `/health`, `/search/image`, `/search/voice` qua HTTP | Cả hai modality `ok`, chỉ mục nạp từ đĩa khớp catalog; kết quả ở mục 4 |
| DB không đổi | SHA-256 `database.json` | `41ac0dfd…` |

## 4. Số đo — SMOKE, không phải benchmark

Máy: Windows 11, RTX 5070 Ti 16 GB, onnxruntime-gpu 1.31.0 CUDA EP, batch=1, warm-up 1 clip/ảnh, không khóa tải máy. **Không dùng các số dưới đây để chọn model.** Dữ liệu không phải truy vấn VNStore, nhãn chưa được người duyệt, mẫu nhỏ.

**Voice — FLEURS vi_vn dev, 30 câu đọc Wikipedia + 1 clip nhiễu** (`eval_voice.py --allow-unreviewed`):

| Cấu hình | WER norm | CER norm | WER raw | Bịa chữ trên nhiễu | Chặn nhầm lời | ASR p50 / p95 (ms) | RTF p50 |
|---|---|---|---|---|---|---|---|
| PhoWhisper-base, ngưỡng −50 dBFS, không VAD | 0,161 | 0,128 | 0,255 | 1/1 | 1 | 352 / 506 | 0,034 |
| PhoWhisper-base, −60 dBFS + VAD | 0,127 | 0,097 | 0,228 | 0/1 | 0 | 360 / 511 | 0,033 |
| PhoWhisper-base, −60 dBFS, không VAD | 0,127 | 0,097 | 0,228 | 1/1 | 0 | 521 / 916 | 0,057 |
| PhoWhisper-small fp32 + VAD | **0,109** | **0,080** | 0,222 | 0/1 | 0 | 809 / 1677 | 0,078 |
| PhoWhisper-small int8 + VAD | 0,104 | 0,079 | 0,216 | 0/1 | 0 | 2397 / 3116 | 0,232 |

- Không có VAD, model sinh cả câu từ nhiễu ("các thành phố tham gia cuộc sống…"). Có VAD thì nhiễu bị chặn và không chặn nhầm lời.
- WER raw cao hơn nhiều so với normalized, chủ yếu do hoa/thường và dấu câu: PhoWhisper xuất chữ thường, không dấu câu.
- Bản int8 chậm hơn fp32 khoảng 3 lần: có lẽ các nút lượng tử hóa không chạy trên CUDA EP (chưa profile). Chênh lệch WER fp32/int8 trên 30 câu nằm trong mức nhiễu.
- Độ trễ hai lượt base cùng cấu hình chênh nhau, cho thấy số đo latency chưa ổn định. Cần chốt protocol đo trước khi so sánh.
- Run: `experiments/results/20261010-1634…`, `…1636…`, `…1637…`, `…1638…`, `…1639…` (`*_voice_*fleurs-smoke`).

**Ảnh — leave-one-out trên gallery** (26 query = ảnh của sản phẩm có ≥2 ảnh, cắt giữa 85%, thu nhỏ 60%, JPEG q75; [báo cáo](../benchmark/2026-10-10_163135-250387_image-gallery-sanity.md)):

| Adapter | Hit@1 | Hit@5 | MRR@10 | Embed p50 |
|---|---|---|---|---|
| SigLIP2-base | 0,96 | 1,00 | 0,98 | 9 ms |
| DINOv2-base | 0,81 | 1,00 | 0,89 | 15 ms |
| ByteHistogram (giả, đối chứng) | 0,08 | 0,12 | 0,09 | 3 ms |

Ảnh cùng phiên chụp của nhà bán, nên dễ hơn nhiều so với ảnh người dùng chụp. Kết quả này chỉ chứng tỏ adapter không lỗi; embedder giả gần mức ngẫu nhiên đúng như kỳ vọng.

**End-to-end HTTP với model thật** (PhoWhisper-small + SigLIP2, catalog thật gồm draft):
- Ảnh giỏ mây đã biến đổi: lần đầu 903 ms (nạp model), sau đó **17–30 ms**. Top 1 đúng "Giỏ mây đan hình bầu dục". Thêm "bằng mây, không lấy tre" thì bộ lọc cứng loại sản phẩm tre.
- Giọng nói, clip 8,9 giây: lần đầu 4,1 giây, sau đó **~0,94 giây**, đạt mục tiêu thăm dò p95 ≤ 3 giây (PLAN §8.4) trên clip này. Clip nhiễu: 422 `audio_no_speech` sau 30 ms.

## 5. Khác với kế hoạch

- PLAN §4 dự kiến PyTorch/Transformers. Trên máy này dùng ONNX Runtime vì chính sách bảo mật chặn torch. Nếu nhóm muốn fine-tune (PLAN §6.2, §7.2) thì cần máy/GPU thuê không bị chính sách này, hoặc quản trị máy cho phép torch; tôi không thay đổi chính sách.
- Chưa có OpenCLIP, ViCLIP-OT, PhoWhisper-medium, Qwen3-ASR: chưa tìm được bản ONNX đáng tin cho các model này. Lớp `PhoWhisperMedium` dạng torch cũ đã bỏ. Hiện có 3 cấu hình voice (base, small, small int8) và 2 cấu hình ảnh, cộng một baseline giả.
- Dùng FLEURS (câu đọc Wikipedia) làm smoke vì chưa có giọng nói truy vấn mua sắm. Bộ này không thay bộ 600 clip của PLAN và không có mã người nói.

## 6. Chưa làm / nợ kỹ thuật

- Tiền xử lý ảnh cài lại bằng NumPy chưa được đối chiếu số học với image processor của Transformers (cần torch). Chỉ mới kiểm gián tiếp qua leave-one-out.
- Chưa profile vì sao int8 chậm; chưa thử fp16 hay TensorRT EP.
- Chưa có protocol latency cố định (khóa tải máy, số lượt lặp) nên p50/p95 hiện chỉ để tham khảo.
- Ngưỡng VAD (0,5; 250 ms), −60 dBFS, RRF và top-K ảnh vẫn chưa được hiệu chỉnh trên dev VNStore.
- Giao diện chưa được thử trong trình duyệt với model thật; E2E vẫn dùng adapter giả (luồng giống hệt, chỉ khác adapter).

## 7. Rủi ro và việc đang chặn

- **Dữ liệu GĐ3 vẫn là điểm nghẽn**: 0 clip giọng nói và 0 ảnh query thật có quyền sử dụng. Smoke ở trên không thay được benchmark.
- Bản export PhoWhisper-small là của bên thứ ba; nên tự export lại khi có môi trường torch hợp lệ, rồi so đầu ra.

## 8. Bước tiếp theo

1. Nhóm dữ liệu thu 60–100 clip truy vấn mua sắm (có đồng ý) và ảnh query theo hai README benchmark. Khi có dữ liệu, chạy `eval_voice.py`/`eval_image.py` cho 3 cấu hình voice và 2 cấu hình ảnh.
2. Chốt protocol đo latency trên máy này. Thử `PhoWhisperSmall` fp16 hoặc TensorRT nếu cần giảm p95.
3. Để demo, chạy API trong `.venv-ml` với `PhoWhisperSmall` + `SigLIP2Base` (lệnh trong README). Đây là lựa chọn tạm cho demo, **chưa phải** lựa chọn model theo PLAN §8.3.
