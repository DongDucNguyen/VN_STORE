# Đợt 002 — 300 sản phẩm thật từ 6 website chính thức (10/10/2026)

Hồ sơ nguồn của đợt thu thập do một collector riêng thực hiện trong thư mục staging `tmp_data/` (đã xóa sau khi nhập). Catalog chính được cập nhật lên **`seed-003-dot-002`**: 30 → 330 sản phẩm, tất cả **draft**, quyền ảnh **unknown**. Báo cáo tiến độ: [GĐ1 — nhập đợt 002](../../../reports/progress/2026-10-10_GD1_nhap-dot-002.md).

## Nội dung

| Đường dẫn | Nội dung |
|---|---|
| `catalog.staging.json` | Catalog staging nguyên bản (ID tạm `p-tmp-…`), SHA-256 `9cb80a2e…` như collector bàn giao |
| `id_map.json` | Ánh xạ ID staging → ID chính thức (sản phẩm, ảnh, nguồn, brand/maker), SKU `VNS-TMP-…` → `VNS-…`, tên được thêm SKU vì trùng, sửa đổi kèm lý do |
| `import_map.json` | Ánh xạ brand/maker staging → bản ghi đã có; brand mới `brand-hanhsilk`, `brand-sensilk` |
| `corrections.json` | Sửa lỗi bóc tách đã đối chiếu với nguồn (1 mục: màu của `AF26ER01`) |
| `raw/` | Phản hồi HTTP gốc + `.meta.json` (URL, thời điểm, hash, header); `archived_copy_path` của nguồn giới thiệu trỏ vào đây |
| `records/` | Product record tách từ API/JSON-LD; `archived_copy_path` của 300 nguồn sản phẩm trỏ vào đây |
| `product_pages.zip` | 300 trang sản phẩm (HTML + metadata HTTP/hash) dùng để kiểm tra HTTP 200/tên/canonical |
| `product_evidence.json` | Theo từng sản phẩm: URL, record, response, trích đoạn căn cứ claim/thuộc tính, ghi chú |
| `image_manifest.json`, `image_selection.json`, `shared_images.json`, `image_checks.json` | Mọi lượt tải ảnh (kể cả ảnh bị loại: URL, hash, lý do), quyết định chọn gallery, kết quả giải mã |
| `near_duplicate_candidates.json` | 904 cặp ảnh gần trùng (dHash ≤5) giữa các sản phẩm khác nhau: gợi ý đối chiếu, không phải kết luận (ID ảnh cũ, tra `id_map.json`) |
| `excluded.json`, `selection_summary.json`, `quality_report.json`, `final_verification.json`, `source_page_checks.json` | Ứng viên bị loại kèm lý do, hạn ngạch, kiểm tra của collector (5.873 điều kiện đạt) |
| `errors/`, `baseline/` | Lỗi truy cập nguồn (Kilomet109 403, URL 404), snapshot DB/schema lúc collector bắt đầu |
| `collector/` | README, phân tích, rà soát phiên, báo cáo chất lượng và script của collector (chạy trong `tmp_data/`, giữ làm hồ sơ, không chạy lại từ đây); `CHECKSUMS.sha256` theo bố cục staging gốc |

Không giữ: 160 ảnh không được chọn (URL/hash/lý do nằm trong `image_manifest.json`, `image_selection.json`), trang duyệt `review.html`/`near_duplicate_review.html`, contact sheet và `products.csv` (dẫn xuất, dùng ID cũ).

## Cách nhập (tái lập)

```bash
.venv/Scripts/python scripts/import_raw/import_staging.py --staging <thư-mục-staging> \
    --batch-dir data_collection/batches/2026-10-10_dot-002 --catalog-version seed-003-dot-002 \
    --map data_collection/batches/2026-10-10_dot-002/import_map.json \
    --corrections data_collection/batches/2026-10-10_dot-002/corrections.json [--dry-run]
```

Script kiểm checksum staging, hash ảnh, trùng SKU/URL với DB; đổi ID tạm theo quy ước catalog; chép ảnh vào `assets/products/<id>/`; rồi ghép qua `safe_import.merge_catalog` (chỉ thêm bản ghi mới, không ghi đè) và `execute_import`. Lần áp dụng: `data_collection/import_runs/2026-10-10_211726-963893_staging/` (catalog trước/sau), báo cáo `reports/data_quality/2026-10-10_211726-963893_import-staging.md`.

## Giới hạn (giữ nguyên từ collector)

- 300 record website ≠ 300 họ sản phẩm: có size/màu/hộp quà cùng dòng. Phải gom họ trước khi chia benchmark.
- Claim là lời công bố của thương hiệu/nhà sản xuất, chưa xác thực độc lập. Không tự gán làng nghề, chứng nhận.
- 60 sản phẩm chưa có giá (giá 0/biến thể chưa ánh xạ → null), 135 chưa có chất liệu, 77 chỉ có 1 ảnh.
- Nhóm thực phẩm hiện toàn là chocolate Marou; dệt may là lụa Hanhsilk/SenSilk (Kilomet109 trả 403 nên không thu thêm).
