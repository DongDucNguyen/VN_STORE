# Cải thiện nhận dạng tiếng Anh — 14/10/2026

## Vấn đề và cách sửa

Giao diện đã gửi `language=en`, nhưng API vẫn dùng PhoWhisper-small tinh chỉnh cho tiếng Việt. Đổi token ngôn ngữ của model này không tạo ra năng lực nhận dạng English tương đương model English. Chế độ `auto` cũng dùng logits ngôn ngữ của PhoWhisper, nên nhận nhầm một clip English là `vi` với xác suất báo cáo 1,0.

`BilingualWhisper` hiện định tuyến `vi` đến PhoWhisper-small và `en` đến [Whisper-small.en](https://huggingface.co/openai/whisper-small.en). Model English dùng bản [ONNX đã ghim revision](https://huggingface.co/onnx-community/whisper-small.en): encoder fp16 và decoder int8 trên CPU, vì encoder int8 có toán tử `ConvInteger` chưa được ONNX Runtime CPU 1.20.2 hỗ trợ trên máy này. [Whisper-tiny đa ngôn ngữ](https://huggingface.co/onnx-community/whisper-tiny) chạy trên CPU để chọn `vi` hoặc `en` cho cả clip ở chế độ `auto`; ngôn ngữ khác trả lỗi rõ ràng. Kết quả API ghi model thực sự đã chép lời. PhoWhisper và SigLIP2 tiếp tục dùng GPU.

## Đo thử tái lập được

Tập smoke là 11 clip ≤15 giây từ [google/fleurs](https://huggingface.co/datasets/google/fleurs), `en_us/validation`, revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`; các row 0 và 2–11. Script `scripts/benchmark/fetch_fleurs_en_smoke.py` lưu audio PCM16 và manifest trong `artifacts/voice_smoke/fleurs-en-dev/`. `scripts/benchmark/smoke_english_asr.py` gọi cùng API `review=true` và tính micro WER sau chuẩn hóa chữ thường/dấu câu. Đây là mẫu công khai chưa được VNStore duyệt, **không phải benchmark nghiệm thu**.

| Cấu hình | Lỗi / 184 từ tham chiếu | Micro WER |
|---|---:|---:|
| Trước: PhoWhisper-small với `language=en` | 181 | 0,9837 |
| Sau: Whisper-small.en CPU, chọn English | 10 | 0,0543 |
| Sau: `auto` → Whisper-small.en CPU | 10 | 0,0543 |

`auto` nhận đúng `en` ở 11/11 clip trên; một clip FLEURS tiếng Việt nhận đúng `vi`. Sau khi tải cả tiếng Việt, tiếng Anh và tìm bằng ảnh, API/proxy đều báo `ok`; truy vấn ảnh trả đúng sản phẩm mẫu. GPU dùng 4.207 MiB, còn khoảng 1.796 MiB khả dụng. Cache offline đã kiểm tra 25 tệp (2,37 GiB). Một test tích hợp ONNX English/auto đạt; toàn backend: 633 đạt, 5 bỏ qua, 1 cảnh báo deprecation từ thư viện test.

## Giới hạn

- Chưa đo trên giọng nói sản phẩm VNStore đã duyệt, giọng Việt nói tiếng Anh, môi trường ồn hoặc câu xen hai ngôn ngữ. Không suy rộng WER smoke thành chất lượng thực tế.
- `auto` chọn một ngôn ngữ cho cả clip; người dùng nên chọn English trực tiếp nếu biết ngôn ngữ. Xác suất trả về là xác suất token ngôn ngữ của detector, không phải độ tin cậy của bản chép lời.
- English chạy trên CPU để giữ GPU cho ảnh và tiếng Việt; độ trễ sẽ phụ thuộc máy và độ dài clip. Cần đo trên dữ liệu dev đã duyệt trước khi đặt mục tiêu hiệu năng chính thức.

## Chạy lại

```powershell
$env:HF_HUB_OFFLINE = '1'
& .\.venv-ml-gpu\Scripts\python.exe -X utf8 scripts/download_demo_models.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_gpu_cuda12.ps1
& .\.venv-ml-gpu\Scripts\python.exe -X utf8 scripts/benchmark/smoke_english_asr.py --language en
& .\.venv-ml-gpu\Scripts\python.exe -X utf8 scripts/benchmark/smoke_english_asr.py --language auto
```
