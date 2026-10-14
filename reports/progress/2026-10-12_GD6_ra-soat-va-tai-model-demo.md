# GĐ6 — Rà soát toàn dự án và chuẩn bị model demo — 12/10/2026

| | |
|---|---|
| Trạng thái | Luồng demo đã kiểm chứng; nghiệm thu chất lượng vẫn bị chặn bởi dữ liệu chưa duyệt |
| Catalog | `seed-006-enriched`, SHA-256 `52ba684ed1da2381a06cb354ab1c95f458d68b781b52518b59bc65100262265e` |
| Commit | Chưa stage/commit/push |

## Phân tích hiện trạng

- 330 sản phẩm: 328 `published` cho demo nội bộ, 2 `draft`; 814 ảnh, quyền sử dụng của cả 814 ảnh vẫn `unknown`. Có 74 sản phẩm thiếu giá, 96 sản phẩm có dưới 2 ảnh, 6 sản phẩm thiếu chất liệu. Chế độ mặc định hiển thị 328 sản phẩm.
- Các luồng keyword, voice, image/OCR, duyệt và thu thập có mã nguồn và bài kiểm thử. Profile demo là PhoWhisper-small + Silero VAD, SigLIP2 + RapidOCR Latin; đây chưa phải selection từ benchmark dev đã duyệt.
- Môi trường ban đầu thiếu Python, Node, model cache và chỉ mục ảnh. Đã đặt Python 3.14.0 dạng gói cục bộ, Node 24.0.0, hai venv và các dependency trong thư mục dự án. Bộ cài Python `.exe` trả mã 1603 nên dùng gói Python NuGet chính thức dạng cục bộ.

## Đã xử lý

1. Thêm `scripts/download_demo_models.py` để tải trước các revision model vào cache dự án và ghi manifest SHA-256. Profile demo có 14 file/1,78 GiB. Tùy chọn `--all-candidates` đã tải đủ 4 cấu hình PhoWhisper và 3 adapter ảnh trong `screening.json`: 31 file/3,48 GiB, ghi `artifacts/models/screening-manifest.json`. Cache Hugging Face mặc định là `artifacts/hf-cache/`, có thể đổi bằng `VNSTORE_HF_CACHE`.
2. RapidOCR 3.4.1 còn tải `latin.ttf` khi khởi tạo dù đã có ba file ONNX. Đã ghim SHA-256 của font, lưu tại `artifacts/models/rapidocr-3.4.1/` và chỉ định đường dẫn local. Sau đó luồng OCR chạy khi `HF_HUB_OFFLINE=1`.
3. Dựng chỉ mục SigLIP2 cho 814 ảnh của catalog hiện tại. Tạo lại `benchmarks/families/proposal.json` vì hash catalog cũ khiến trang duyệt họ và ba bài pytest lỗi. Danh tính 35 họ, 83 cặp ứng viên và 8 cụm ảnh dùng chung giữ nguyên; sai khác cosine tối đa 0,0004 do lượt inference nên giữ thứ tự/điểm cũ để không đổi ánh xạ gợi ý máy. Gắn lại provenance và xác minh gợi ý cũ qua `apply_family_review` trong bộ nhớ: 294 họ nếu chấp nhận toàn bộ, 12 tách, 14 gộp, 3 cụm đề nghị loại.
4. Tạo trang duyệt họ hiện hành tại `artifacts/family_review/2026-10-12_seed-006/index.html`. Mẫu FLEURS công khai chỉ dùng để thử kỹ thuật giọng nói, không là truy vấn VNStore hoặc benchmark chất lượng.
5. Tạo packet chấm keyword thường cho catalog hiện tại: seed 12 truy vấn/138 cặp và dev 107 truy vấn/1.366 cặp ở `artifacts/keyword_review/2026-10-12_seed-006_*`. Gợi ý máy keyword cũ mang hash catalog khác nên không gắn vào packet hiện tại; cần rà lại trước khi dùng.

## Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| Catalog + fixture | 0 lỗi; catalog có 1 cảnh báo về quyền ảnh trong chế độ demo nội bộ |
| Backend pytest | 601 đạt, 4 skip, 1 cảnh báo deprecation Starlette/httpx |
| Model thật trong cache offline | `test_ml_adapters.py`: 7/7 đạt (gồm PhoWhisper-base, SigLIP2, DINOv2, OpenCLIP); base-fp16 và small-int8 chép được mẫu FLEURS riêng |
| Giải mã ảnh Pillow | 22 đạt |
| Frontend typecheck/build | Đạt |
| E2E fixture desktop/mobile | 120/120 đạt; chạy server riêng trên Windows để Playwright trả mã thoát sạch |
| Trang duyệt họ desktop/mobile | 4/4 đạt |
| Browser model thật với `HF_HUB_OFFLINE=1` | 2/2 đạt; mỗi thiết bị 3 keyword, 3 ảnh đầy đủ, 1 lượt cache ảnh, 3 voice; export 10 lượt, 0 lỗi/hủy |
| API model thật, chế độ mặc định ẩn draft | `/health`: 328 visible, keyword/voice/image `ok`; cả ba endpoint tìm trả 200 khi offline |
| Tải lại từ cache khi offline | 14/14 file xác minh SHA-256, không cần mạng |
| Audit file ảnh + API | 814 ảnh có hash đúng qua API; [JSON](../data_quality/2026-10-12_153123-700694_image-audit.json) |
| OCR trên ảnh gallery | Đọc được chữ một số ảnh; [JSON](../benchmark/2026-10-12_152706-455736_ocr-smoke.json) chỉ là smoke, có ảnh không phát hiện chữ |
| Tiền kiểm locked test | `blocked` như [báo cáo](../acceptance/2026-10-12_083115-037378_stage6-readiness.md) |

## Giới hạn và bước tiếp theo

Thiếu `selection.json` từ dev đã duyệt, nhãn keyword test, clip voice test đã duyệt, registry họ/split ảnh đã khóa và ảnh query độc lập. Không mở locked test hoặc xem smoke là chỉ số chất lượng. Quyền ảnh hiện vẫn `unknown` dù catalog cho phép demo nội bộ.

Máy hiện tại có RTX 3050 Laptop 6 GB, driver 566.14 (`nvidia-smi` báo CUDA 12.7). ONNX Runtime GPU 1.31.0 với runtime CUDA 13 khởi tạo CUDA lỗi 801 và tự rơi về CPU; smoke thành công trên CPU, chưa xác nhận hiệu năng GPU trên máy này. Có thể đặt `VNSTORE_ML_DEVICE=cpu` khi chạy demo để chọn CPU tường minh. Không dùng số đo từ báo cáo cũ trên RTX 5070 Ti để dự đoán độ trễ máy này.

`artifacts/` bị gitignore: môi trường Python/Node cục bộ, cache model, mẫu FLEURS và chỉ mục ảnh cần được giữ hoặc tạo lại khi chuyển máy.
