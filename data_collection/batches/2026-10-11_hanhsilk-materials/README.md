# Bổ sung chất liệu cho 9 sản phẩm Hanhsilk (11/10/2026)

Catalog `seed-003-dot-002` (`e38a4dd8…`) → `seed-004-hanhsilk-materials` (`5448a8f4…`).

- [apply_materials.py](apply_materials.py) sửa có giới hạn và chạy lại được. Script dừng nếu hash catalog đầu vào khác `BEFORE`. Script kiểm tra response API gốc của đợt 002 (`raw/hanhsilk-products.raw`, hash trong `product_evidence.json`), so từng bản ghi đã tách với response và yêu cầu **đúng nguyên văn** câu chất liệu trong `description`/`short_description` của chính sản phẩm (bảng `PHRASES`). Không suy ra từ tên hay tag.
- Thay đổi gồm: 9 `materials` đang rỗng → `["lụa tơ tằm"]`, `updated_at` của 9 sản phẩm, `supports` của 9 nguồn, `catalog_version`. Không đổi trạng thái `draft`, quyền ảnh, giá hay claim.
- Chạy qua `safe_import`: 2 lần dry-run (`preview.json`, báo cáo `reports/data_quality/2026-10-11_025221…`, `…025238…`), 1 lần áp (`result.json`, `…025242…`). Bản trước, bản đề xuất và baseline nằm trong `data_collection/import_runs/2026-10-11_0252*_hanhsilk-materials/`.
- `family-proposal.before.json` và `image-manifest.before.json` là bản trước khi dựng lại theo catalog mới. Đề xuất họ dựng lại có nội dung giống hệt, chỉ khác hash/phiên bản catalog. Manifest ảnh vẫn 0 query.
- Căn cứ là mô tả của nhà cung cấp lưu ngày 10/10/2026, không phải chứng nhận độc lập. Người duyệt sản phẩm vẫn phải xác nhận khi publish.

Ảnh hưởng: mọi packet/trang gắn hash catalog cũ đều lệch. Đã dựng lại chỉ mục SigLIP2 và DINOv2, packet keyword `2026-10-11_seed-004_*` và trang duyệt họ `2026-10-11_seed-004` (nạp được bản nháp của trang seed-003). Xem [báo cáo](../../../reports/progress/2026-10-11_GD3_dong-bo-seed-004-va-khoa-split.md).
