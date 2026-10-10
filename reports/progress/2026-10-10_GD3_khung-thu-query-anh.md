# GĐ3 — Khung thu thập và audit query ảnh — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3, chuẩn bị dữ liệu ảnh độc lập theo PLAN §8 |
| Trạng thái | Hoàn thành schema/audit; **0 query ảnh thật**, đang chờ thu thập |
| Người thực hiện | Codex |
| Catalog | `seed-002-taxonomy`, 30 draft, 45 ảnh gallery; không thay đổi |
| SHA-256 DB | `41ac0dfdc090af7981773dd4689179d0ca47bfe992deed3c2713c7628c801f16` |
| Commit | Chưa có `.git`; hash file lưu trong báo cáo kiểm chứng |

## 1. Mục tiêu và phần đã triển khai

Chuẩn bị hợp đồng dữ liệu để người thu thập có thể nhập query ảnh độc lập và phát hiện lỗi trước benchmark. Không lấy lại ảnh gallery làm bộ query hoặc tự tạo dữ liệu gắn nhãn người thật.

- [Schema manifest 1.0.0](../../benchmarks/image/manifest.schema.json): ID, task exact/similar/image+text, split, họ sản phẩm/phiên chụp/ảnh gốc, checksum query, quyền và hồ sơ review.
- [Manifest ban đầu](../../benchmarks/image/manifest.json) gắn hash DB hiện hành, hiển thị draft, danh sách rỗng. Không tạo ảnh, nhãn, danh tính hoặc bằng chứng quyền giả vào dữ liệu thật.
- `scripts/benchmark/audit_image_queries.py`: kiểm tra schema/catalog, hash snapshot, file trong raw/, checksum, giới hạn 25 MiB và tham chiếu nhãn/SKU.
- Chặn query trùng byte gallery, crop/augment có hash ảnh gốc trùng gallery, split rò qua họ/phiên/ảnh gốc/hash query/exact product. Dùng cả checksum ảnh gallery khai báo và đọc từ file.
- Ảnh dùng chung cho nhiều query text trong cùng split được ghi cảnh báo, đếm riêng số query và hash duy nhất; provenance không được tự mâu thuẫn.
- Các mục chưa có quyền/review/nhãn được đếm là pending. No-match cần đánh giá toàn bộ gallery hiển thị. Ngày giờ review phải hợp lệ, có múi giờ.
- Báo cáo JSON/Markdown có timestamp và hash inputs/code, không sửa catalog, manifest hay nhãn. Trạng thái không đồng nghĩa đủ điều kiện benchmark; `benchmark_approved` luôn false.
- [Hướng dẫn thu thập](../../benchmarks/image/README.md) mô tả đường dẫn, trường dữ liệu, grouping, review, lệnh audit và giới hạn.

## 2. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| Test riêng `test_image_query_audit.py` | **41 passed** |
| Toàn backend với code cuối | **289 passed**, 6,26 giây; 1 cảnh báo deprecation Starlette/httpx |
| Audit manifest thật | `pending_collection`, exit 0; **0 query**, 30 sản phẩm gallery hiển thị |
| File gallery thật | 45 file giữ đúng checksum DB; không thay ảnh |

Lệnh test: `.venv/Scripts/python.exe -X utf8 -m pytest backend/tests -q -p no:cacheprovider`.

Test sử dụng thư mục tạm và bytes/metadata giả được đánh dấu rõ; không phải benchmark hoặc ảnh người thật. Bao gồm giữ nguyên đầu vào, các nhóm rò split, duplicate gallery/original, quyền chưa đủ, provenance sai, checksum/file rỗng/mất/thư mục/quá cỡ, path escape, no-match thiếu nhãn, exact SKU sai, timestamp và CLI lưu lỗi.

Lượt test đầu phát hiện `FormatChecker` trong môi trường hiện có không bắt buộc timezone. Đã bổ sung kiểm tra datetime trực tiếp, gồm ngày không tồn tại và timezone thiếu; các ca đều đạt ở bản cuối. Kiểm tra raw/ trỏ ra ngoài thư mục được mô phỏng qua Path.resolve để không cần quyền tạo symlink trên Windows.

Không thay API/UI/search engine/evaluator, không chạy lại E2E/typecheck/build. **64 E2E/typecheck/build đạt** là kết quả [đợt rà soát UI/API trước](2026-10-10_GD2_ra-soat-hoi-quy-toan-du-an.md).

## 3. Hồ sơ đã lưu

- [Audit manifest thật](../benchmark/2026-10-10_152205-756943_image-query-audit.md).
- [JSON audit](../benchmark/2026-10-10_152205-756943_image-query-audit.json).
- [Log backend](../../artifacts/review/2026-10-10_image-query-audit/backend-tests.log).
- [Kết quả tổng hợp và hash](../benchmark/2026-10-10_image-query-tools-validation.json).

## 4. Giới hạn

Audit mới kiểm tra file/hash và thông tin đã khai báo; chưa giải mã định dạng, nhận diện nội dung, phash/gần trùng, xác minh giấy phép hoặc tính độc lập của người chấm. Bytes giả vẫn có thể đúng checksum; không được diễn giải `hash_verified` thành ảnh đã giải mã hoặc đúng sản phẩm.

Không thêm dependency runtime. Đã kiểm tra khả năng dùng Pillow: Python hệ thống có Pillow 12.3.0, nhưng `.venv` chưa có; cài cùng phiên bản bằng pip không tìm được distribution. Không đổi môi trường backend hoặc thêm phụ thuộc chưa kiểm chứng. Phần giải mã ảnh được để thành bước tiếp theo riêng; công cụ hiện hành chỉ cần dependency đã có.

Chưa có dữ liệu ảnh query thật, chưa có split được nghiệm thu/khóa, chưa có metric image retrieval hoặc model được chọn. Một mẫu có đủ hồ sơ cũng không đại diện đạt quy mô/độ đa dạng của PLAN.

## 5. Bước tiếp theo

1. Người thu thập cung cấp query độc lập và bằng chứng quyền; ghi bản gốc, họ sản phẩm và phiên chụp trước chia split.
2. Thêm bước giải mã ảnh và phát hiện gần trùng, kết hợp người duyệt kiểm tra gallery/nguồn; không dùng ảnh catalog để giả lập query thật.
3. Chấm exact/similar/image+text, phân xử, kiểm tra phân bố và khóa splits trước benchmark.
4. Tiếp tục duyệt packet keyword 360 cặp; thu audio có đồng ý sử dụng và tách theo người nói.

DB, raw/editorial, manifest ảnh catalog, packet keyword và seed query giữ nguyên. 30 sản phẩm vẫn draft; quyền 45 ảnh gallery vẫn unknown và không được thay bằng quyền của ảnh query.
