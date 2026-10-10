# GĐ3 — Công cụ thu và nhập ảnh query — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3 (PLAN.md mục 9) |
| Trạng thái | 🟡 Công cụ sẵn sàng; **vẫn 0 ảnh query thật** |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfd…`, không thay đổi |
| Commit | Chưa commit |

Song song với [công cụ thu âm](2026-10-10_GD3_cong-cu-thu-am.md): công cụ tương tự để thu ảnh query độc lập cho [benchmarks/image](../../benchmarks/image/README.md#thu-ảnh-bằng-trang-collectimage-thêm-10102026).

## Đã làm

- **Trang `#/collect/image`** ([CollectImagePage.tsx](../../frontend/src/pages/CollectImagePage.tsx)):
  - Nhập thông tin phiên: người chụp, phiên chụp, split, quyền và mã bằng chứng quyền. Mỗi ảnh có họ sản phẩm (gợi ý từ catalog qua API nếu có), tác vụ, và yêu cầu chữ cho `image_text`.
  - Ảnh được mã hóa lại JPEG q95 (≤2048 px) để bỏ EXIF/GPS. Hash ảnh gốc giữ ở `source_asset_sha256`; dùng lại ảnh gốc thì giữ `source_asset_id`.
  - Xuất zip `samples.json` + `raw/<qid>.jpg`. `judgment` và `independence_review` để null cho người duyệt.
- **`scripts/benchmark/import_image_session.py`**:
  - Chỉ nhận tên file mong đợi, kiểm tra hash và qid.
  - Chạy `audit()` có sẵn trên manifest đã gộp: schema, catalog hash, rò split theo họ/phiên/ảnh gốc, trùng gallery, quyền có bằng chứng.
  - `invalid` thì xóa file vừa ghi và giữ nguyên manifest; `--dry-run` cũng tự dọn.
- Sửa lỗi phát hiện khi viết: qid đánh số theo độ dài danh sách sẽ trùng sau khi bỏ một ảnh; đã đổi sang bộ đếm tăng dần.

## Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| `scripts/run_all_tests.py` | **7/7**; backend **345 passed, 1 skipped**; **88 E2E passed** |
| pytest `test_import_image_session*` | Nhập/dry-run (tự dọn), qid trùng, cùng họ ở split khác bị audit chặn với `split_leakage`, `../x.jpg` và ảnh ngoài `samples.json` bị từ chối; lỗi thì không để lại file |
| E2E `collect_image.spec.ts` (desktop + mobile) | Thêm 2 ảnh (`exact`, `image_text`), tải zip, script nhập `--dry-run` báo `audit: pending_review` |
| Dữ liệu thật | `database.json` và `benchmarks/image/manifest.json` (0 mẫu) không đổi |

## Giới hạn

- Mã hóa lại làm đổi pixel so với ảnh gốc (JPEG q95). Muốn giữ bản gốc thì nhóm dữ liệu lưu riêng theo `source_asset_id`; ảnh gốc có thể chứa GPS nên không đưa vào repo.
- Trang không tự phát hiện ảnh chụp lại màn hình/gallery. Audit chỉ bắt trùng byte; gần trùng vẫn cần `audit_image_pixels.py` và người duyệt.
- Chưa có giao diện chấm `judgment`; người duyệt vẫn sửa manifest trực tiếp.

## Bước tiếp theo

Phân họ sản phẩm vào split (120/40/40 họ theo PLAN §8.1), chụp thử một phiên, nhập, chạy `audit_image_pixels.py`, chấm judgment. Sau đó chạy `eval_image.py` cho SigLIP2 và DINOv2 trên dev.
