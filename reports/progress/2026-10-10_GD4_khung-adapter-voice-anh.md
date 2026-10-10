# GĐ4 — Khung adapter, chỉ mục và evaluator cho voice/ảnh — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ4 (PLAN.md mục 9: "Adapter và sàng lọc các model voice/image"), một phần UI của GĐ6 |
| Trạng thái | 🟡 Một phần: đã có khung không phụ thuộc model; **chưa cài/chạy model thật**, chưa có dữ liệu query |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfdc090af7981773dd4689179d0ca47bfe992deed3c2713c7628c801f16`, không thay đổi |
| Commit | Chưa commit; mọi thay đổi nằm trong working tree trên `main` |

## 1. Mục tiêu đợt này

Các việc của GĐ1–3 còn lại đều cần người làm: duyệt draft, xin quyền ảnh, chấm 360 cặp và thu ảnh/audio thật. Đợt này làm phần GĐ4 không cần chờ dữ liệu: một đường đi hoàn chỉnh cho tìm bằng giọng nói và ảnh. Khi có checkpoint, chỉ cần viết adapter, dựng chỉ mục và chạy evaluator; không phải sửa API/UI.

## 2. Đã làm

**Backend** (`backend/app/`)
- `media.py`: kiểm tra WAV PCM16 (8–48 kHz, 0,3–15 giây, ≤2 MB, trộn stereo về mono) bằng thư viện chuẩn. Chặn clip im lặng (khung 50 ms to nhất < −50 dBFS) trước ASR. Nhận ảnh JPEG/PNG/WebP theo chữ ký file, không tin Content-Type; giới hạn ≤8 MB, ≥32 px, ≤40 MP. Kiểm tra kích thước trước khi giải mã để chặn ảnh "bom".
- `adapters.py`: Protocol `ASRAdapter` (`model_id`, `revision`, `transcribe`) và `ImageEmbedder` (`preprocess`, `embed`). Adapter nạp qua `VNSTORE_ASR_ADAPTER` / `VNSTORE_IMAGE_ADAPTER` dạng `module:Class`. `Gate` giới hạn 1 lượt inference đồng thời cho mỗi modality.
- `image/index.py`: chỉ mục float32 kèm manifest gồm model/revision, tiền xử lý, hash catalog, hash từng ảnh và checksum vectors. File được ghi tạm rồi thay nguyên khối. `check()` báo `index_stale` khi đổi model hoặc tiền xử lý, khi ảnh của sản phẩm đang hiển thị thiếu/đổi, hoặc khi ảnh đã bị gỡ. Cosine gộp theo `product_id`, lấy góc chụp giống nhất.
- `modalities.py` + `main.py`: trạng thái `ok | unavailable | error | index_missing | index_stale | index_invalid` hiện trong `/health` (`search.models`, kèm lý do). Chỉ mục ảnh nằm trong `Bundle` cùng snapshot nên được thay nguyên khối khi nạp lại catalog. `POST /search/voice` trả bản chép lời + kết quả tìm theo bản chép lời. `POST /search/image?text=` trả "mẫu tương tự". Lỗi đầu vào trả 413/415/422 có mã ổn định; bận trả 429; lỗi model trả 503 `model_error` và không lộ chi tiết nội bộ.
- `search/engine.py`: tách `search()` thành `_execute()` để ảnh dùng chung bộ lọc cứng, diễn giải, relaxations và facets. `search_visual()` gộp hạng ảnh với BM25 bằng RRF (k=60, top 50 sản phẩm theo ảnh), không cộng cosine với BM25 (PLAN §4). Hành vi keyword giữ nguyên: 289 test cũ vẫn đạt.

**Script**
- `scripts/build_indexes/build_image_index.py`: dựng chỉ mục cho một adapter vào `artifacts/indexes/image/<model@revision>/`.
- `scripts/benchmark/asr_metrics.py`: WER theo âm tiết, CER giữ dấu, raw/normalized, micro, chính sách `vi-asr-v1`. Không bỏ dấu và không đổi cách viết số để điểm đẹp hơn.
- `scripts/benchmark/retrieval_metrics.py`: nDCG/mAP/Success/Recall/MRR, cùng chính sách "chưa chấm → null" như `eval_keyword.py`.
- `scripts/benchmark/eval_voice.py`: chạy đúng thứ tự giải mã → chặn im lặng → ASR. Chấm WER/CER, độ đúng giá và phủ định (so `parse_query` của bản chuẩn và bản model), tỉ lệ bịa chữ trên clip im lặng, p50/p95, RTF và WER theo vùng/thiết bị/môi trường. Chặn trùng người nói giữa split; test cần `--confirm-locked-test`.
- `scripts/benchmark/eval_image.py`: chạy `audit()` có sẵn trước. Chấm exact Recall@1/5/10 và MRR@10; similar/image_text nDCG@10, mAP@10 và Success@5; ghi phân bố `top_similarity` để hiệu chỉnh ngưỡng no-match.
- `benchmarks/voice/`: manifest rỗng, schema 1.0.0 và README. Đã bổ sung mục chạy đánh giá vào `benchmarks/image/README.md`.

**Frontend**
- `media.ts`: MediaRecorder → giải mã → OfflineAudioContext 16 kHz mono → WAV. Khử ồn của trình duyệt để tắt (PLAN §6.2). Ảnh được cắt theo vùng chọn, thu nhỏ ≤1024 px và mã hóa lại JPEG nên EXIF/GPS bị bỏ.
- `VoiceSearch.tsx`: trạng thái chuẩn bị/đang nghe (đồng hồ, tự dừng sau 10 giây)/đang chép lời/lỗi. Lỗi gồm: micro bị chặn, không có micro, micro bận, trình duyệt không hỗ trợ, ghi quá ngắn (<0,7 giây, không gửi), model chưa sẵn sàng và lỗi từ máy chủ. Bản chép lời chuyển sang `#/search?q=…&via=voice` để sửa trong ô tìm.
- `ImageSearchPage.tsx` (`#/image`): chụp/chọn ảnh, kéo chọn vùng, ô "Yêu cầu thêm", diễn giải bộ lọc, cảnh báo "không khẳng định đúng sản phẩm". Ảnh hỏng/sai định dạng bị chặn trước khi gửi; model chưa sẵn sàng thì nút tìm bị tắt. Không hiển thị cosine như phần trăm.

**Kiểm thử**: `backend/tests/fakes.py` có adapter GIẢ (`FakeASR` trả câu cố định, `ByteHistogramEmbedder` dùng histogram byte). E2E chạy với hai adapter này và micro giả của Chrome phát âm 440 Hz.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Toàn bộ | `.venv/Scripts/python scripts/run_all_tests.py` | **TẤT CẢ ĐẠT 7/7** |
| Backend | (trong bước trên) | **337 passed** (289 cũ + 48 mới: media 10, chỉ mục/gộp hạng 12, API 18, metric/evaluator 8) |
| E2E desktop + mobile | (trong bước trên) | **84 passed** (64 cũ + 20 mới) |
| Độ ổn định E2E voice/ảnh | `npx playwright test --repeat-each=3 e2e/voice_image.spec.ts` | 60/60 passed |
| Dựng chỉ mục trên catalog thật bằng adapter giả | `build_image_index.py --adapter tests.fakes:ByteHistogramEmbedder --out <scratch>` | 45 vector, exit 0; adapter sai → exit 2 |
| Evaluator trên manifest thật (rỗng) | `eval_voice.py --adapter tests.fakes:FakeASR --split dev`; `eval_image.py … --split dev` | `pending_collection`, exit 0, không ghi kết quả |
| DB không đổi | `sha256sum database.json` | `41ac0dfd…` như trước |

Test cũ "giọng nói và ảnh báo chưa sẵn sàng" giờ giả lập `/health` vì backend E2E đã bật adapter giả. Trạng thái 503 thật khi chưa cấu hình adapter vẫn được pytest kiểm tra (`test_voice_and_image_unavailable`, `test_index_missing_without_autobuild`, `test_bad_adapter_spec_reports_error`).

## 4. Số đo

Không có số đo chất lượng. Mọi lần chạy đều dùng adapter giả trên dữ liệu tổng hợp/fixture, nên **không được dùng làm benchmark** hay để so model.

## 5. Khác với kế hoạch

- Máy hiện tại có **GPU NVIDIA RTX 5070 Ti 16 GB** (driver 591.86, CUDA 13.1, theo `nvidia-smi`). Báo cáo trước ghi GĐ4 "cần GPU", nhưng có thể sàng lọc trên máy này trước khi thuê GPU. Ngân sách/cấu hình máy đo vẫn cần quản lý dự án chốt.
- Cắt vùng ảnh làm ở trình duyệt (để bỏ metadata luôn), không phải ở API. Evaluator ảnh hiện dùng ảnh query nguyên bản. Ablation crop (PLAN §7.2) cần thêm trường vùng chọn vào manifest khi thu dữ liệu.
- Cosine thuần Python thay cho NumPy: đủ cho vài trăm ảnh và không thêm dependency vào API. Đo lại khi catalog lớn.

## 6. Chưa làm / nợ kỹ thuật

- Chưa có adapter thật cho PhoWhisper/Qwen3-ASR/OpenCLIP/SigLIP2/DINOv2/ViCLIP-OT. Chưa cài PyTorch/Transformers và chưa kiểm license/revision từng checkpoint.
- Chưa có OCR bao bì, ngưỡng no-match đã hiệu chỉnh, bootstrap CI, n-best/contextual biasing và nDCG end-to-end cho voice qua `keyword_qid`.
- Ngưỡng im lặng −50 dBFS, `RRF_K=60`, `IMAGE_TOP_K=50` là giá trị khởi đầu, cần tinh chỉnh trên dev.
- Trang ảnh chưa có bảng bộ lọc như trang tìm chữ; chỉ có ô "Yêu cầu thêm".

## 7. Rủi ro và việc đang chặn

- Vẫn **0 clip giọng nói và 0 ảnh query thật**. Không thể sàng lọc model khi chưa có dữ liệu GĐ3 và người nói đồng ý.
- RTX 5070 Ti (Blackwell) cần bản PyTorch có CUDA ≥12.8. Python 3.14 trong `.venv` có thể chưa có wheel cho mọi thư viện ML; nên dùng môi trường riêng cho adapter.

## 8. Bước tiếp theo

1. Tạo môi trường ML riêng, chưa đụng `backend/requirements.txt`. Viết adapter cho 1 ASR (PhoWhisper-small) và 1 embedder ảnh (SigLIP2-base), kiểm license/revision. Dựng chỉ mục 45 ảnh và smoke qua API bằng ảnh/giọng tự tạo.
2. Nhóm dữ liệu thu 60–100 clip dev và ảnh query theo hai README benchmark; chạy `eval_voice.py`/`eval_image.py` cho ≥3 cấu hình mỗi modality (PLAN §8.3).
3. Song song: duyệt packet keyword 360 cặp và 30 draft (vẫn chặn baseline GĐ2).
