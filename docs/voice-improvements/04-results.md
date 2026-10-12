# Kết quả triển khai và cách dùng

## Những thay đổi đã triển khai

| Thành phần | Tệp | Hành vi mới |
|---|---|---|
| Pipeline | `backend/app/voice/pipeline.py` | Dùng chung API/evaluator; giữ audio gốc; quality; tiền xử lý có cấu hình; metadata ngôn ngữ |
| Gợi ý | `backend/app/voice/suggestions.py` | Cụm 2–4 token từ sản phẩm hiển thị, alias/danh mục, chất liệu và cặp danh mục–chất liệu của cùng sản phẩm; chỉ đổi một âm tiết gần âm/dấu; tối đa 3 gợi ý |
| API | `backend/app/main.py`, `modalities.py` | `review=true` không chạy tìm kiếm; `raw_text` giữ nguyên; `language=vi/en/auto`; VAD và ASR cùng semaphore |
| ONNX | `backend/app/ml/asr.py` | Prompt theo ngôn ngữ từng request; auto dùng logits language token; task luôn transcribe; cờ truncated; profile TensorRT hỗ trợ prompt 1 hoặc 4 token |
| UI | `VoiceSearch.tsx`, `api.ts`, `SearchPage.tsx` | Ghi → xem gốc/cảnh báo/gợi ý → sửa/chọn → xác nhận → tìm; hủy/ghi lại; lỗi tìm vẫn giữ câu đã sửa |
| Đánh giá | `eval_voice.py`, `ablate.py` | Nhóm âm lượng/tag; gate rejection/hallucination từng nhóm; gợi ý top-1 tốt/xấu/ngang theo WER; retrieval giả định của gợi ý; ghi cấu hình gain/lọc |
| Thu mẫu | `collect/prompts.ts` | 5 câu dev ứng viên p25–p29: English, Việt–Anh, cụm sản phẩm, n/l, nói nhỏ/xa |

Ví dụ trên catalog thật `seed-006-enriched`: “khăn nụa” có gợi ý “khăn lụa”; “bát sử trắng” có gợi ý “bát sứ trắng”. Không tự thay bản gốc hoặc thực hiện tìm theo gợi ý. Không thêm “sứ” vào câu chỉ có “bát”. Câu nhận dạng với language=en không chạy bộ sửa gần âm tiếng Việt.

Luật hiện giới hạn n/l và thay dấu trong cùng âm tiết. Chưa thêm ch/tr, s/x… khi chưa có lỗi được ghi nhận trên dữ liệu thực. Từ trùng thành phần tên riêng/SKU được bảo vệ khá chặt, có thể bỏ sót gợi ý hữu ích; ưu tiên tránh đổi sai.

## Sử dụng

Khởi động backend/frontend theo README hiện hành. Không cần cài thêm thư viện. Model mặc định của hệ thống vẫn do `VNSTORE_ASR_ADAPTER` cấu hình.

1. Chọn **Tiếng Việt**, **English**, hoặc **Tự nhận diện / Việt–Anh** dưới ô tìm.
2. Bấm micro và **Dừng và xem lời**.
3. So bản chép lời gốc, sửa **Cụm từ dùng để tìm kiếm**, hoặc chọn gợi ý nếu đúng ý.
4. Bấm **Tìm theo câu này**. Có thể **Ghi lại** hoặc **Hủy**.

API cũ `POST /search/voice` vẫn trả kết quả theo transcript gốc đã chuẩn hóa khoảng trắng. Giao diện mới gọi `POST /search/voice?review=true&language=vi` rồi `POST /search` sau xác nhận. Adapter chỉ có `transcribe` vẫn dùng được với mặc định/vi; en/auto nhận lỗi `language_unsupported` nếu adapter không hỗ trợ, không âm thầm bỏ qua lựa chọn.

`transcript` có `raw_text`, `text`, `language`, `requested_language`, `language_probability`, `truncated`, `quality`, `suggestions`, `requires_confirmation`. Probability là xác suất token ngôn ngữ của model, **không phải xác suất cả câu đúng**. Gợi ý có `evidence=catalog_text_only`, `requires_confirmation=true`.

## Cấu hình thử nghiệm

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `VNSTORE_ASR_LANGUAGE` | `vi` | vi/en/auto cho adapter/evaluator; tham số ngôn ngữ trên request được ưu tiên |
| `VNSTORE_VOICE_MAX_GAIN_DB` | `0` | 0–12 dB; tăng đến mục tiêu peak-frame −28 dBFS, giới hạn biên độ |
| `VNSTORE_VOICE_HIGHPASS` | `0` | `1` bật bộ lọc thông cao một cực 80 Hz, giảm DC/ù thấp; không phải khử nhiễu giọng nói tổng quát |

Mức nói nhỏ: peak RMS khung 50 ms dưới −40 dBFS. Cảnh báo vỡ tiếng khi hơn 1% mẫu sát biên PCM. Ngưỡng này là heuristic, chưa được hiệu chỉnh. Energy gate/VAD xét audio gốc trước gain/lọc; tiếng bị VAD từ chối vẫn cần ghi lại. Không tuyên bố gain cứu được tất cả tiếng nói nhỏ. Audio gain/lọc đều tắt mặc định.

Không lưu audio hay transcript mới ra đĩa khi dùng tìm kiếm. Bản gốc đi cùng kết quả trong bộ nhớ; cache điều hướng voice hết hạn sau 30 giây. Thời gian người dùng đọc/sửa không được cộng vào độ trễ xử lý voice trong diagnostics.

## Kiểm chứng

Chi tiết số lượng và lệnh cuối cùng ở [nhật ký tiến độ](03-progress.md) và thư mục `checks/`. Các test WAV/tên sản phẩm giả kiểm tra hợp đồng kỹ thuật. Smoke ONNX sử dụng mẫu tiếng Việt FLEURS đã có, không đo chất lượng tiếng Anh/Việt–Anh. Manifest voice thật vẫn 0 clip; evaluator trả `pending_collection` và không tạo kết quả giả.

Đã đạt 632 backend, 22 Pillow, typecheck/build và 126 E2E; 4 smoke ONNX đạt. Lượt kiểm tra thêm có một lỗi tài nguyên WebSocket Chrome ở test catalog; chạy riêng ca đó hai lần với một worker đều đạt. Không nới kiểm tra console hoặc bỏ qua lỗi trong test.

Catalog giữ nguyên SHA-256 `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`: 330 sản phẩm, 328 published, 814 ảnh, 23 danh mục. Không dựng lại index ảnh vì không đổi dữ liệu hay model ảnh.

## Giới hạn còn lại

- Chưa có benchmark thật để khẳng định WER/retrieval tăng hoặc sửa sai giảm. Chưa bật auto/gain/lọc làm mặc định toàn hệ thống.
- Auto quyết định ngôn ngữ toàn clip; không tách đoạn chuyển Việt–Anh, không sinh n-best/rescore theo âm thanh.
- PhoWhisper fine-tune tiếng Việt; đổi language token không tương đương thay bằng model tiếng Anh đã được kiểm chứng.
- Gợi ý theo catalog không thay thế bằng chứng âm học và có thể sai; bắt buộc người dùng chọn. Chưa fine-tune hoặc tự động học từ lần sửa của người dùng.
- High-pass không loại được tiếng ồn quán cà phê tổng quát. Denoiser nặng chỉ nên bổ sung khi có dev và đo được tác hại/lợi ích.
- Nghiệm thu chất lượng theo PLAN và locked test vẫn chờ dữ liệu/nhãn do người làm.
