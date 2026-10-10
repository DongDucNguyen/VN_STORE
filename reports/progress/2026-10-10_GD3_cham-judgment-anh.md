# GĐ3 — Pool và trang chấm judgment cho query ảnh — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3 (PLAN.md mục 8.1: "Pool top kết quả của mọi baseline cộng mẫu ngẫu nhiên để gán nhãn") — BACKLOG P1.2 |
| Trạng thái | ✅ Công cụ xong; manifest ảnh vẫn 0 query |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfd…` (không đổi) |
| Commit | Chưa commit (trên `08320a6`) |

## 1. Mục tiêu

Trước đợt này chưa có công cụ tạo pool và chấm `judgment`/`independence_review`. Xong khi chấm xong một packet thử trên dữ liệu tổng hợp và audit đạt `recorded_checks_passed` với judgment do người nhập.

## 2. Đã làm

- **[prepare_image_review.py](../../scripts/benchmark/prepare_image_review.py)** tạo `packet.json` + `index.html`:
  - Pool mỗi query = top K cosine ảnh của **từng** adapter (gộp theo sản phẩm, không lọc theo chữ). Với `image_text`, thêm top K của ảnh + chữ (bộ lọc cứng) và BM25 trên `text_vi`. Cộng N sản phẩm ngẫu nhiên cố định theo seed + qid.
  - Pool được xáo theo hash: trang không cho thấy thứ hạng hay model nào tìm ra. Nguồn của từng sản phẩm chỉ lưu trong `pool_sources` để làm hồ sơ.
  - Phần còn lại của gallery đi kèm, vì audit yêu cầu nhãn đủ gallery cho no-match.
  - Chỉ mục nạp từ `artifacts/indexes/image/` nếu khớp, không thì dựng trong bộ nhớ. Audit manifest chạy trước; `invalid` thì dừng.
- **[image_review_template.html](../../scripts/benchmark/image_review_template.html)**: trang offline cùng phong cách trang duyệt keyword.
  - Hiện ảnh query, tác vụ, yêu cầu chữ; mỗi sản phẩm có ảnh, thuộc tính, giá và ô chấm 0–3.
  - Chỉ xác nhận được khi: chấm hết danh sách chính; không có sản phẩm 2–3 thì đã chấm cả phần còn lại; `exact` có đáp án thì đã chọn sản phẩm đúng (SKU tùy chọn).
  - Ô đánh giá độc lập với gallery, ghi chú bắt buộc. Tự lưu nháp, có Lưu/Nạp bản nháp gắn `packet_id`.
- **[apply_image_judgments.py](../../scripts/benchmark/apply_image_judgments.py)**:
  - `catalog_sha256` của file chấm = manifest = `database.json`; qid có trong manifest và `sha256` ảnh không đổi.
  - Ghi đè judgment cũ cần `--replace-judged`.
  - Chạy `audit()` trên bản tạm cạnh manifest; `invalid` thì xóa bản tạm, không ghi gì.
- [backend/tests/image_review_demo.py](../../backend/tests/image_review_demo.py): manifest tổng hợp 3 query trên catalog fixture + packet bằng adapter giả, dùng chung cho pytest và E2E.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Pytest mới (3) | `pytest tests/test_image_judgment.py` | Pool + phần còn lại = đúng 12 sản phẩm published, không trùng; có nguồn random và BM25 cho `image_text`; cùng seed → cùng thứ tự. Áp 3 judgment → audit **`recorded_checks_passed`**. 7 ca sai bị chặn đúng lý do (`incomplete_no_match`, `exact_target`, sha đổi, qid lạ, catalog lệch, `unknown_product`, sai định dạng), manifest không đổi, không còn file tạm |
| E2E mới (desktop/mobile) | `npx playwright test e2e/image_review.spec.ts` | Mở packet qua `file://`; xác nhận bị chặn khi chưa chọn exact; no-match bị chặn tới khi chấm đủ gallery; xuất → `apply_image_judgments.py` "áp 2", audit `pending_review` (1 query chưa chấm); nháp còn sau khi tải lại trang |
| Dữ liệu thật | `prepare_image_review.py --split dev …` | `invalid: split dev không có query cần chấm (pending_collection)`, không tạo thư mục |
| Toàn bộ | `scripts/run_all_tests.py` | **8/8 bước**, 360 backend (+1 skip), 22 test Pillow, 94 E2E |

## 4. Số đo

Không có. Embedder trong test là `ByteHistogramEmbedder` (giả, không hiểu ảnh), nên pool trong test không phản ánh model.

## 5. Khác với kế hoạch

Backlog gợi ý "baseline giả" trong pool. Đã dùng BM25 trên `text_vi` (với `image_text`) cộng mẫu ngẫu nhiên thay cho baseline giả, vì chúng có ý nghĩa hơn với người chấm. Có thể thêm adapter giả bằng `--adapter tests.fakes:ByteHistogramEmbedder` nếu muốn.

## 6. Chưa làm / nợ kỹ thuật

- Chưa có công cụ đối chiếu hai người chấm cho ảnh (như `audit_reviews.py` của keyword).
- Chưa có crop/vùng chọn trong packet; người chấm chỉ thấy ảnh query đầy đủ.

## 7. Rủi ro và việc đang chặn

Vẫn 0 query ảnh thật (P0.5). Catalog đổi (P0.2/P1.4) thì packet và judgment phải làm lại; script chặn trường hợp này.

## 8. Bước tiếp theo

Khi có ~60 query dev: tạo packet với SigLIP2 + DINOv2, chấm, áp, rồi chạy `eval_image.py --split dev`.
