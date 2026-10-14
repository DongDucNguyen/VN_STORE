# Giảm độ trễ nhận dạng English — 14/10/2026

## Nguyên nhân và thay đổi

Đo trực tiếp Whisper-small.en trên máy RTX 3050 Laptop 6 GB cho thấy encoder fp16 chạy CPU mất khoảng 1,0–1,1 giây trên cả câu ngắn và clip 6,5 giây. Đây là phần tốn thời gian nhất; decoder int8 chạy CPU mất khoảng 0,3–0,5 giây. Cấu hình mới giữ nguyên checkpoint, tokenizer, VAD, prompt, thuật toán greedy và hai decoder int8, nhưng đưa riêng encoder fp16 lên CUDA. Đây là giá trị mặc định của `scripts/run_gpu_cuda12.ps1` (`-EnglishDevice hybrid`).

Script GPU đặt `VNSTORE_ASR_PRELOAD_ENGLISH=1`: backend nạp và chạy thử VAD, encoder, decoder lúc khởi động. Như vậy backend mất khoảng 15 giây để sẵn sàng trên máy thử, đổi lại yêu cầu English đầu tiên không phải đợi nạp model. Khi không preload, một yêu cầu đầu với WAV SAPI 22,05 kHz mất 9,0 giây; số đó gồm cả khởi tạo bước đổi tần số nên không thể quy hết cho model. Biến này là tùy chọn; khi không đặt, backend vẫn nạp model theo nhu cầu.

## Đo trên cùng máy và audio

Gọi tuần tự API `/search/voice?language=en&review=true`, 5 lượt cho mỗi WAV sau một lượt khởi động nóng; số trong bảng là trung vị thời gian phía client. Đây là phép đo cục bộ, không phải benchmark tải đồng thời hoặc độ trễ mạng thực tế.

| WAV | Thời lượng | Trước: encoder + decoder CPU | Sau: encoder CUDA + decoder CPU | Giảm |
|---|---:|---:|---:|---:|
| Câu ngắn SAPI | 2,17 giây | 1.429 ms | 408 ms | 3,5 lần |
| FLEURS English | 6,54 giây | 1.785 ms | 725 ms | 2,5 lần |

Độ chính xác: bản chép lời **giống hệt** cấu hình CPU trên cả 11 clip FLEURS và 20 clip SAPI có nhiễu, âm cuối yếu. WER tương ứng vẫn là **10/184** và **0/100** từ. Bộ thử nhỏ, đặc biệt SAPI là tiếng tổng hợp, nên chưa đại diện đầy đủ cho giọng người dùng thật. Frontend giữ thêm 300 ms sau khi bấm dừng để tránh cắt âm cuối; khoảng chờ này vẫn cộng vào thời gian người dùng cảm nhận.

Sau khi nạp English, tiếng Việt, nhận diện ngôn ngữ `auto` và tìm ảnh, GPU còn khoảng **0,9–1,2 GiB** tùy trạng thái phiên chạy; gọi English và tìm ảnh đồng thời đều trả HTTP 200. Cấu hình full Whisper-small.en fp16 trên GPU trước đó chỉ còn khoảng 10 MiB và dễ hết bộ nhớ, nên decoder vẫn chạy CPU.

Sau một lần khởi động backend với preload, yêu cầu đầu tiên với WAV FLEURS 16 kHz mất **918 ms**, lượt kế tiếp **703 ms**. Mẫu SAPI 22,05 kHz cần thêm bước đổi tần số; lần đầu dùng riêng loại WAV đó mất lâu hơn do khởi tạo bước xử lý tín hiệu. Frontend gửi WAV 16 kHz.

Kiểm thử `python -m pytest -q backend/tests`: **635 passed, 5 skipped**. Sau khi khởi động lại, `/health` qua API và proxy Vite trả HTTP 200, voice/image đều `ok`; các yêu cầu thử tiếng Việt, English `auto` và tìm ảnh đều trả HTTP 200. Ba lượt English qua proxy Vite sau khi nạp đủ model mất 837, 699 và 726 ms trên cùng clip FLEURS; đây cũng chỉ là smoke cục bộ.

## Chạy lại

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_gpu_cuda12.ps1
& .\.venv-ml-gpu\Scripts\python.exe -X utf8 scripts/benchmark/profile_english_latency.py --repeats 5
```

Các báo cáo JSON gốc nằm trong `artifacts/voice_smoke/latency-english-cpu.json` và `artifacts/voice_smoke/latency-english-hybrid.json` trên máy thử; `artifacts/` được gitignore. Để so CPU, chạy script GPU với `-EnglishDevice cpu`, rồi đo lại cùng WAV.
