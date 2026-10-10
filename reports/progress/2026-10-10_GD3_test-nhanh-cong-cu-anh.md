# GĐ3 — Test nhanh công cụ ảnh — 10/10/2026

Theo yêu cầu kiểm tra đơn giản phần vừa triển khai; không mở rộng chức năng.

| Kiểm tra | Kết quả |
|---|---|
| `python -m unittest discover -s scripts/benchmark/tests -p test_image_pixels.py -v` | **22 test đạt**, exit 0 |
| `python scripts/benchmark/audit_image_pixels.py` (report-dir riêng) | **45/45 ảnh giải mã được**, 0 lỗi |
| Gợi ý gần trùng | Vẫn 19 cặp; chưa kết luận là ảnh trùng |
| SHA-256 DB, manifest query và 45 ảnh | Giữ nguyên trước/sau kiểm tra |
| Tổng thời gian test + scan | 4,04 giây |

Scan vẫn `pending_collection` vì chưa có query độc lập; không phải lỗi công cụ. Không chạy lại bộ backend/frontend không bị thay đổi.

- [Kết quả JSON](../benchmark/2026-10-10_image-pixels-smoke-validation.json).
- [Log test](../../artifacts/review/2026-10-10_image-pixels-smoke/tests.log).
- [Scan mới](../../artifacts/review/2026-10-10_image-pixels-smoke/2026-10-10_153634-290445_image-pixels.json).

Không sửa mã nguồn hay dữ liệu sản phẩm. Việc tiếp theo vẫn là đối chiếu các cặp ứng viên và thu query thật có quyền.
