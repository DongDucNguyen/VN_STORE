# English: từ ngắn và âm cuối — 14/10/2026

## Thay đổi

- Profile GPU 6 GB nay mặc định dùng [Whisper-small.en](https://huggingface.co/openai/whisper-small.en) ONNX hybrid trên CPU cho English; PhoWhisper-small tiếng Việt và SigLIP2 tìm ảnh tiếp tục dùng CUDA. Cấu hình English GPU cũ (Whisper-base.en) vẫn có thể chọn bằng `-EnglishDevice cuda`.
- Bộ ghi âm trong trình duyệt giữ thêm 300 ms sau khi bấm dừng, giảm nguy cơ cắt phụ âm cuối nếu người dùng bấm hơi sớm. Thời gian này không được cộng vào ngưỡng tối thiểu 700 ms của đoạn ghi âm.
- Thêm script tạo audio bằng hai giọng Windows SAPI và script thêm nhiễu trắng SNR 10 dB, giảm âm lượng 180 ms cuối vùng có tiếng nói. Script smoke chấm WER, số câu đúng hoàn toàn và từ cuối câu.

## Kết quả thử

| Mẫu và model | Lỗi từ | Câu đúng hoàn toàn | Từ cuối đúng |
|---|---:|---:|---:|
| 20 WAV SAPI sạch, Whisper-base.en GPU | 0/100 | 20/20 | 20/20 |
| 20 WAV SAPI có nhiễu/đuôi nhỏ, Whisper-base.en GPU | 1/100 | 19/20 | 19/20 |
| Cùng 20 WAV có nhiễu/đuôi nhỏ, Whisper-small.en CPU | 0/100 | 20/20 | 20/20 |

Lỗi ở bản GPU là Zira đọc “Show me the red bags.” nhưng nhận thành “Show me the red bag.” — mất âm /s/ cuối. Bản CPU nhận đúng trên cùng file. Trên 11 clip FLEURS English công khai từ lần thử trước, base.en GPU có 14/184 lỗi từ, small.en CPU có 10/184. Các bộ này rất nhỏ, audio SAPI không đại diện giọng người dùng thật; kết quả không phải benchmark nghiệm thu.

Thử [Whisper-small.en fp16 ONNX](https://huggingface.co/onnx-community/whisper-small.en) trên GPU: model nhận dạng được English, nhưng sau khi nạp thêm PhoWhisper, SigLIP2 và `auto`, `nvidia-smi` chỉ còn **10 MiB VRAM** trên RTX 3050 Laptop 6 GB. Vì thế profile này không phù hợp làm mặc định. Cấu hình cuối cùng dùng 4.543 MiB GPU, còn 1.460 MiB sau khi nạp cả English, tiếng Việt, `auto`, ảnh và gọi voice/ảnh đồng thời.

## Xác minh

- English, tiếng Việt, `auto` và tìm ảnh qua API: HTTP 200; health qua Vite báo voice/image `ok`.
- Gọi English và tìm ảnh đồng thời: hai yêu cầu HTTP 200.
- 32 test backend liên quan đạt; TypeScript build/typecheck đạt; 2 E2E ghi âm trên Chrome desktop đạt (luồng bình thường và bấm dừng quá sớm).

Chạy lại bộ audio tổng hợp:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\benchmark\generate_english_tails.ps1
& .\.venv-ml-gpu\Scripts\python.exe -X utf8 scripts/benchmark/make_english_tail_stress.py
& .\.venv-ml-gpu\Scripts\python.exe -X utf8 scripts/benchmark/smoke_english_asr.py --manifest artifacts/voice_smoke/synthetic-en-tail-stress/manifest.json
```
