# GĐ6 — Bộ lọc trên trang tìm bằng ảnh — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ6 (PLAN.md mục 1: "Ba kiểu tìm kiếm dùng chung catalog, bộ lọc và trang kết quả") — nợ kỹ thuật trong BACKLOG |
| Trạng thái | ✅ Hoàn thành |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy` (không đổi) |
| Commit | Chưa commit (trên `08320a6`) |

## Đã làm

- **API** `POST /search/image` nhận thêm `filters`: JSON trong query (body đã dành cho ảnh), cùng schema `FiltersIn` với `POST /search`. JSON sai hoặc giá âm → 422 `invalid_filters`. Bộ lọc người dùng là ràng buộc cứng, ghi vào `applied_filters` với `source: "user"`, giống tìm bằng chữ.
- **Trang `#/image`**: sau khi có kết quả, hiện panel bộ lọc dùng chung `FilterPanel` với trang tìm chữ (danh mục, giá, chất liệu, màu, thương hiệu, làng nghề, căn cứ nguồn gốc) và chip "Xóa bộ lọc". Đổi bộ lọc thì gửi lại **đúng ảnh đã chuẩn bị** (không cắt/mã hóa lại). Chọn ảnh mới thì bộ lọc về rỗng. Bộ lọc giữ trong trạng thái trang, không đưa lên URL (ảnh không nằm trong URL nên không tải lại được).

## Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| Pytest mới (4) `tests/test_voice_image_api.py` | Lọc `cói` + giá ≤ 500k: mọi kết quả đúng chất liệu và giá, facet còn `cói`; 3 kiểu `filters` sai → 422 |
| E2E mới (desktop/mobile) `e2e/voice_image.spec.ts` | Tìm ảnh → tick "cói" → request có `filters={"materials":["cói"],…}`, chip "Chất liệu: cói", không còn "Khăn lụa" → "Xóa bộ lọc" |
| `scripts/run_all_tests.py` | **8/8 bước**, 370 backend (+1 skip), 22 Pillow, 98 E2E |

E2E dùng adapter ảnh giả (histogram byte); không phải số đo model.

## Giới hạn

Mỗi lần đổi bộ lọc là một lượt embedding mới (~20 ms với SigLIP2 trên GPU, theo smoke trước). Nếu đang có lượt khác chạy, API trả 429 như cũ. Chưa cache embedding của ảnh truy vấn.
