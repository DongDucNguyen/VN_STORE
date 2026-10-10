# GĐ3 — Giải mã và đối chiếu ảnh gần trùng — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3; kiểm tra ảnh gallery hỗ trợ GĐ1 |
| Trạng thái | Hoàn thành công cụ/kiểm thử; 45/45 ảnh gallery giải mã được; 0 query thật |
| Người thực hiện | Codex |
| Catalog | `seed-002-taxonomy`, 30 draft, 45 ảnh; không đổi |
| SHA-256 DB | `41ac0dfdc090af7981773dd4689179d0ca47bfe992deed3c2713c7628c801f16` |
| Commit | Chưa có `.git`; báo cáo kiểm chứng lưu hash code |

## 1. Đã triển khai

Thêm `scripts/benchmark/audit_image_pixels.py`, chạy sau và tái sử dụng audit manifest. Công cụ giải mã dữ liệu thực thay vì chỉ kiểm tra file/hash; tạo cặp ứng viên gần trùng để người duyệt đối chiếu.

- Dùng `verify()` và đọc đầy đủ pixel; giới hạn 25 MiB/20 triệu pixel, chỉ JPEG/PNG/WebP tĩnh. File hỏng/bị cắt, animation, format không hỗ trợ, hash hoặc kích thước sai đều được báo lỗi.
- Kiểm tra đường dẫn nằm trong thư mục cho phép; đối chiếu checksum bytes trước giải mã và hash manifest/catalog/schema trước/sau scan.
- Chuẩn hóa EXIF orientation/alpha nền trắng/RGB trong bộ nhớ; lưu pixel SHA-256 và dHash 64 bit, không sửa ảnh gốc.
- Gợi ý Hamming distance ≤6 mặc định; ghi ngưỡng, thuật toán, phiên bản Pillow/Python, hash code và từng file.
- Phân nhóm cặp gallery cùng/khác sản phẩm, query cùng/khác split và query–gallery; ứng viên query–gallery hoặc khác split trả `requires_visual_review` (exit 2), không tự xóa/duyệt.
- Tạo trang HTML chỉ đọc cạnh báo cáo, ảnh theo cặp và toàn gallery. Từ chối ghi đè thư mục review có sẵn; nội dung văn bản được escape, đường dẫn ảnh được URL-encode.
- Bổ sung môi trường dependency tùy chọn và test `unittest` riêng, không thêm dependency vào API runtime.

## 2. Kết quả trên catalog thật

Lệnh đã chạy:

```bash
python scripts/benchmark/audit_image_pixels.py --review-out artifacts/image_review/2026-10-10_pixel-audit
```

| Mục | Kết quả |
|---|---|
| Gallery | **45/45 giải mã được**, 0 file lỗi; checksum/kích thước khớp |
| Định dạng | 14 JPEG, 19 PNG, 12 WebP |
| Query độc lập | **0**; manifest vẫn `pending_collection` |
| Cặp có cùng hash pixel sau chuẩn hóa | **0** |
| Ứng viên dHash ≤6 | **19**: 1 cặp cùng sản phẩm, 18 cặp khác sản phẩm |
| Ảnh ít tương phản theo ngưỡng công cụ | 0 |
| Trang đối chiếu | 83 tham chiếu ảnh (19 cặp ×2 +45), tất cả trỏ tới file hiện có |

Không diễn giải 19 ứng viên thành 19 cặp ảnh trùng thật. Không có query nên hiện chưa có cặp query–gallery/khác split để đánh giá độc lập trên dữ liệu thật.

### Quan sát mẫu bằng mắt của Codex

Đã xem trực tiếp 4 file thuộc 2 cặp, không phải nghiệm thu toàn bộ gallery hoặc review của người thứ hai:

- `img-minhlong-binh-hoa-hon-viet-30cm-1` và `...-2`: dHash distance 0 nhưng họa tiết mặt trang trí khác nhau; giữ cả hai, không tự loại ảnh dựa trên dHash.
- `img-marou-ben-tre-78-80g-1` và `img-marou-ba-ria-76-80g-1`: distance 1, cùng bố cục bao bì nhưng ảnh thứ nhất xanh và ghi Bến Tre 78%, ảnh thứ hai đỏ/cam và ghi Bà Rịa 76%. Đây là ví dụ hash gần nhau không có nghĩa cùng SKU.

Các nhận xét chỉ ghi tại báo cáo; không đặt `reviewed_at`, không cấp quyền, không thêm nhãn vào manifest.

## 3. Kiểm thử

```bash
python -m unittest discover -s scripts/benchmark/tests -p test_image_pixels.py -v
```

**22 test đạt**, 0,321 giây trong unittest; chạy bằng Python hệ thống 3.14.6 với Pillow 12.3.0 và jsonschema 4.26.0. Log lưu interpreter và mã thoát. Test dùng ảnh mẫu sinh trong thư mục tạm, không dùng làm query benchmark hoặc sửa ảnh thật.

Phạm vi: JPEG/PNG/WebP, đổi metadata, EXIF, alpha, ảnh đơn sắc gây false positive, file HTML/PNG/JPEG bị cắt, BMP/animation, giới hạn bytes/pixel, ngưỡng Hamming, gallery/query trùng pixel, query khác split, mismatch kích thước/hash, path escape, input đổi giữa audit, HTML escape, CLI 0/1/2 và không ghi đè review.

Không sửa mã backend/frontend/audit manifest cũ, không chạy lại các bộ không bị ảnh hưởng. **289 test backend** là kết quả đợt [khung thu query ảnh](2026-10-10_GD3_khung-thu-query-anh.md); **64 E2E/typecheck/build** là kết quả đợt rà soát UI/API trước. Không cộng 22 test riêng vào số pytest backend hay ghi các lượt cũ thành lượt mới.

## 4. Hồ sơ đã lưu

- [Báo cáo scan](../benchmark/2026-10-10_152959-680994_image-pixels.md), [JSON đầy đủ](../benchmark/2026-10-10_152959-680994_image-pixels.json).
- [Trang đối chiếu 19 cặp và gallery](../../artifacts/image_review/2026-10-10_pixel-audit/index.html).
- [Log 22 test](../../artifacts/review/2026-10-10_image-pixels/pixel-tests.log).
- [Tổng hợp kiểm chứng/checksum](../benchmark/2026-10-10_image-pixels-validation.json).
- [Hướng dẫn và lệnh chạy](../../benchmarks/image/README.md#giải-mã-ảnh-và-gợi-ý-gần-trùng-tùy-chọn).

## 5. Giới hạn và bước tiếp theo

Ngưỡng dHash là heuristic chưa hiệu chỉnh trên dữ liệu độc lập; có false positive và false negative, đặc biệt nền trắng/bao bì/crop. Chưa áp dụng ICC color management, OCR, embedding, so vùng crop hoặc nhận dạng sản phẩm. Hash pixel so ảnh RGB sau alpha nền trắng, không phải xác thực nguồn gốc. Scan đọc bytes tại thời điểm chạy, không khóa file; trang HTML liên kết ảnh hiện hành nên cần đối chiếu checksum nếu ảnh về sau thay đổi.

Trên máy này `.venv` chưa có Pillow; tool và test ảnh dùng Python hệ thống có sẵn dependency. Không cài lại package hoặc thay cấu hình backend. `run_all_tests.py` vẫn kiểm tra bộ runtime thông thường, không tự chạy bộ ảnh tùy chọn; lệnh riêng đã ghi trong hướng dẫn.

Bước tiếp theo: người duyệt đối chiếu các cặp còn lại và ghi quyết định có căn cứ; thu query thật có quyền, phân nhóm trước chia split, chạy cả audit cấu trúc và pixel rồi phân xử trước khóa test. Chưa chọn model hoặc đo image retrieval. Catalog/raw/editorial/manifest/packet/seed và 45 ảnh gốc giữ nguyên; trạng thái quyền vẫn unknown, 30 sản phẩm vẫn draft.
