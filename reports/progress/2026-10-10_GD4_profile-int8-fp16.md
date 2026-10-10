# GĐ4 — Profile PhoWhisper int8/fp16, đo trên CPU — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ4–7 (PLAN.md mục 8.3: "Model quantized phải đo lại chất lượng"; mục 8.4: p95 voice ≤ 3 giây) — BACKLOG P1.7 |
| Trạng thái | 🟡 Đã có kết luận cho int8/fp16; TensorRT chưa thử vì chưa cài |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy` (không đổi) |
| Commit | Chưa commit (trên `08320a6`) |

## 1. Mục tiêu

Tìm lý do PhoWhisperSmallInt8 chậm ~3 lần trên CUDA. Thử fp16 và TensorRT EP. Mỗi biến thể đo lại chất lượng và độ trễ theo [protocol latency](2026-10-10_GD4_protocol-latency.md).

## 2. Đã làm

- Profile bằng `SessionOptions.enable_profiling` (script tạm trong scratchpad, không commit): gộp thời gian kernel theo (session, provider, op).
- Thêm adapter `app.ml.asr:PhoWhisperBaseFp16`, dùng bản fp16 chính thức trong cùng repo `onnx-community/PhoWhisper-base-ONNX` đã ghim (`revision = …+fp16`). Vào/ra vẫn là float32, cast nội bộ. Repo ONNX của PhoWhisper-small không có bản fp16.
- Đo trên CPU (`VNSTORE_ML_DEVICE=cpu`) cho small fp32 và int8, để biết khả năng chạy không cần GPU.

## 3. Kết quả profile

| Adapter (GPU) | Phần thời gian kernel trên CPU EP | Toán tử nặng nhất |
|---|---|---|
| PhoWhisperSmall fp32 | 19,6% (chủ yếu Concat/Unsqueeze/Gather nhỏ của cache) | MatMul, Add, Reshape trên CUDA |
| PhoWhisperSmallInt8 | **41,8%** | **`MatMulInteger` (encoder, decoder) và `DynamicQuantizeLinear` chạy trên CPU**, kéo theo `MemcpyFromHost/ToHost` mỗi bước giải mã |
| PhoWhisperBase fp16 | 4,1% | **`Cast` chiếm 10,4%** thời gian decoder (fp32↔fp16 ở mỗi bước) |

Kết luận: bản int8 lượng tử động (dynamic quantization) dùng toán tử mà CUDA EP của ORT 1.31 không có kernel, nên dữ liệu bị chuyển qua lại CPU–GPU. Đây là định dạng dành cho CPU, không phải lỗi cấu hình.

## 4. Số đo (FLEURS 30 câu + 1 clip nhiễu; smoke, không phải benchmark VNStore)

RTX 5070 Ti, driver 591.86, ORT 1.31.0; batch=1, warm-up 1; 3 lượt (GPU) hoặc 2 lượt (CPU). Không có cảnh báo máy bận.

| Adapter | Thiết bị | WER / CER norm. | p50 / p95 (ms) | Spread p95 | Cold first call (ms) | Đỉnh VRAM (MB) |
|---|---|---|---|---|---|---|
| PhoWhisperBase fp32 | GPU | 0,127 / 0,097 | 349 / 495 | 1,5% | 2.961 | 3.422 |
| PhoWhisperBase fp16 | GPU | 0,127 / 0,098 | 741 / 977 | **11,1%** | 3.846 | 2.697 |
| PhoWhisperSmall fp32 | GPU | 0,109 / 0,080 | 822 / 1.151 | 1,3% | 4.510 | 4.881 |
| PhoWhisperSmall int8 | GPU | 0,104 / 0,079 | 2.410 / 3.044 | 1,2% | 4.783 | 3.420 |
| PhoWhisperSmall fp32 | CPU | 0,109 / 0,080 | 2.099 / 2.441 | 2,9% | 6.164 | — |
| PhoWhisperSmall int8 | CPU | 0,103 / 0,077 | 2.324 / 2.796 | 0,5% | 4.314 | — |

- **fp16** không nhanh hơn trên GPU này: chậm gấp đôi, spread vượt 10%, chỉ tiết kiệm ~0,7 GB VRAM. Giải mã từng token với batch 1 bị giới hạn bởi độ trễ khởi chạy kernel chứ không phải tốc độ tính, và bản fp16 thêm nhiều `Cast`.
- **int8 trên CPU** cũng không nhanh hơn fp32 (p50 2,32 so với 2,10 giây) trên máy này; WER lệch nhẹ (0,103 so với 0,109) trên 30 câu, chưa đủ để kết luận là tốt hơn.
- **Small fp32 chạy CPU** có p95 2,44 giây với clip đọc 6,9–14,9 giây. Mục tiêu PLAN là p95 ≤ 3 giây với clip ≤ 8 giây; nếu demo không có GPU thì đây là cấu hình đáng thử, cần đo lại trên clip truy vấn VNStore.
- Đỉnh VRAM là của toàn máy; trước khi đo đã có sẵn ~1,2 GB của tiến trình khác.

Run ghi tại `experiments/results/*_voice_phowhisper-base-fp16-latency-protocol/`, `*_phowhispersmall-cpu-latency-protocol/`, `*_phowhispersmallint8-cpu-latency-protocol/`.

## 5. Khác với kế hoạch

TensorRT EP chưa thử. ORT liệt kê `TensorrtExecutionProvider` nhưng máy chưa có thư viện TensorRT (`nvinfer*.dll`). Cài gói `tensorrt` (~1–2 GB) là thêm phụ thuộc và có thể bị Application Control chặn như torch, nên cần người dùng quyết định.

## 6. Chưa làm

- TensorRT EP (chờ quyết định cài).
- Lượng tử tĩnh (QDQ) hoặc int8 có kernel CUDA cần công cụ export/calibration; nên làm trên máy có torch.
- Chưa đo RAM CPU (peak RSS) khi chạy CPU.

## 7. Khuyến nghị (chưa phải chọn model theo PLAN §8.3)

Giữ fp32 trên CUDA cho demo. Không dùng bản int8 hay fp16 hiện có vì không có lợi về độ trễ. Khi sàng lọc trên dev VNStore, đưa thêm "small fp32 trên CPU" vào bảng tài nguyên.
