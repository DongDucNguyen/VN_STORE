# GĐ2 — Hiển thị khi ảnh mất hoặc tải lỗi — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2: catalog API/UI, kiểm thử hồi quy |
| Trạng thái | Hoàn thành xử lý ảnh lỗi; còn nhãn benchmark và review/quyền ảnh |
| Người thực hiện | Codex |
| Catalog | `seed-002-taxonomy`, 23 danh mục, 30 draft, 45 ảnh |
| SHA-256 DB | `41ac0dfdc090af7981773dd4689179d0ca47bfe992deed3c2713c7628c801f16` — giữ nguyên |
| Commit | Chưa có `.git`; hash mã nguồn lưu trong báo cáo kiểm chứng |

## 1. Vấn đề

API trước đây coi ảnh có `local_path` là ảnh có file. Nếu file bị mất sau khi nạp snapshot, sản phẩm vẫn trả URL ảnh đó làm ảnh đại diện/gallery và `images_missing_file` chưa phản ánh đúng. Frontend cũng chưa xử lý trường hợp URL có trong API nhưng ảnh tải/giải mã thất bại.

Đây là nợ kỹ thuật đã ghi trong báo cáo rà soát dự án. Thay đổi lần này giúp người dùng tiếp tục xem tên, giá, thuộc tính và chuyển sản phẩm khi ảnh lỗi.

## 2. Đã triển khai

### Backend và packet nhãn

- `CatalogSnapshot.image_path()` kiểm tra đường dẫn nằm trong catalog, file thường và khác rỗng; trả None khi file mất hoặc kiểm tra metadata/path gặp lỗi. Không làm API chi tiết bị lỗi theo file ảnh.
- Summary chọn ảnh còn file đầu tiên theo thứ tự gallery. Detail dùng cùng danh sách ảnh khả dụng cho cover/gallery và tính `images_missing_file`.
- Không bỏ bản ghi ảnh khỏi DB; khi file được phục hồi, lần trả dữ liệu tiếp theo nhận lại ảnh mà không cần sửa catalog.
- `images_pending_rights` vẫn đếm quyền unknown riêng, không nhập chung với file thiếu.
- Công cụ tạo packet nhãn chọn ảnh thay thế còn file khi ảnh đầu tiên bị thiếu.
- Audit ảnh/API bổ sung đối chiếu cover, danh sách gallery và số ảnh thiếu với kết quả kiểm tra file.

### Frontend

- Card hiện “Ảnh tạm thời không tải được” nếu browser không tải/giải mã được ảnh; tên, giá và liên kết chi tiết vẫn dùng được.
- Gallery bỏ ảnh lỗi khỏi danh sách trong phiên xem, chuyển sang ảnh khả dụng tiếp theo.
- Nếu tất cả ảnh lỗi, hiện thông báo và nút “Tải lại ảnh”. Nếu API không có ảnh, vẫn dùng thông báo “Chưa có ảnh”.
- Đổi sản phẩm xóa trạng thái ảnh lỗi của sản phẩm trước; thumbnail phản ánh ảnh đang được chọn.
- Không dùng ảnh khác sản phẩm hay ảnh tự tạo để lấp khoảng trống.

## 3. Kiểm chứng

| Kiểm tra | Lệnh / phạm vi | Kết quả |
|---|---|---|
| Toàn bộ backend | `.venv/Scripts/python -X utf8 -m pytest backend/tests -q -p no:cacheprovider` | **215 passed**, 4,43 giây; 1 cảnh báo deprecation Starlette/httpx |
| 9 ca backend mới | `backend/tests/test_image_availability.py` | Mất cover, mất toàn bộ/phục hồi, file rỗng, stat lỗi, path escape, draft URL-only, API sau nạp snapshot và ảnh thay thế trong packet |
| Typecheck | `npx.cmd tsc -b` trong frontend | Exit 0 |
| Build | `npx.cmd vite build --outDir ../artifacts/build --emptyOutDir` | Exit 0; 28 module; artifact `artifacts/build/` |
| Toàn bộ E2E | `npx.cmd playwright test --workers=2 --reporter=line` | **58 passed**, 18,5 giây, desktop/mobile |
| 8 E2E mới | 4 hành trình × 2 thiết bị trong `image_fallback.spec.ts` | Card lỗi vẫn mở được chi tiết; chuyển ảnh lỗi; tải lại sau phục hồi; đổi sản phẩm |
| Catalog thật | `audit_images.py` với editorial, baseline hiện hành và manifest | `passed`, **45 ảnh duy nhất qua API đúng hash**; cover/gallery/count khớp; importer identical, manifest idempotent |

Test backend chỉ xóa/ghi file trong thư mục tạm của fixture. E2E chỉ chặn response của ảnh fixture bằng bytes không phải ảnh để mô phỏng lỗi giải mã. Không xóa hay sửa ảnh sản phẩm thật. Các E2E mới vẫn yêu cầu không có lỗi JavaScript/console bất ngờ.

Pytest, Vite và Playwright chạy ngoài sandbox do giới hạn thư mục tạm/khởi tạo tiến trình Windows đã xác định ở các đợt trước. Typecheck và audit DB thật chạy trong sandbox. Reporter dòng không tạo báo cáo HTML E2E mới; không dùng HTML lịch sử làm bằng chứng cho lượt này.

## 4. Kết quả đã lưu

- [Audit file/API thật](../data_quality/2026-10-10_145539-586774_image-audit.json).
- [Kết quả kiểm chứng và hash mã nguồn](../data_quality/2026-10-10_image-fallback-validation.json).
- Code API: `backend/app/catalog/store.py`, `present.py`.
- Code UI: `frontend/src/components/ProductImage.tsx`, `ProductCard.tsx`, `pages/ProductPage.tsx`.
- Công cụ: `scripts/benchmark/prepare_review.py`, `scripts/validate_catalog/audit_images.py`.

DB, seed query, packet hiện tại, manifest và file ảnh thật giữ nguyên. Không cần đổi version/hash catalog hay tạo lại nhãn chỉ vì sửa hiển thị lỗi ảnh.

## 5. Giới hạn

- Kiểm tra đường dẫn/file khi trả API không hash lại hoặc giải mã từng ảnh; checksum được kiểm tra lúc nạp catalog và khi chạy audit. File bị sửa nội dung sau khi nạp cần audit/reload để phát hiện checksum sai.
- Vẫn có khoảng thời gian rất nhỏ giữa kiểm tra file và lúc FileResponse đọc file; frontend xử lý ảnh thất bại nhưng chưa có cơ chế khóa file/stream từ handle đã mở.
- Nếu không đọc được metadata file, API bỏ ảnh khỏi gallery. Trường hợp metadata đọc được nhưng không có quyền đọc nội dung hoặc lỗi mạng chỉ xuất hiện lúc browser tải, xử lý bằng thông báo/ảnh kế tiếp.
- Card chỉ biết ảnh đại diện trong response, nên khi tải lỗi sẽ hiện thông báo; gallery chi tiết mới có đủ danh sách để chuyển sang ảnh khác. Không tự retry vô hạn; gallery retry khi người dùng bấm.
- Các kết quả test là kiểm tra chức năng, không phải benchmark retrieval hay cam kết latency mới. Smoke keyword đợt trước giữ nguyên với hash mã nguồn của đợt đó.

## 6. Bước tiếp theo

1. Người duyệt dùng [packet hiện tại](../../artifacts/keyword_review/2026-10-10_seed-002-taxonomy/index.html) để chấm/xuất nhãn, audit và phân xử trước baseline keyword chính thức.
2. Xử lý review/quyền ảnh theo [checklist](../data_quality/2026-10-10_144424-872002_publication-readiness.md); 30 sản phẩm vẫn draft, 2 sản phẩm còn thiếu tiêu chí Việt có nguồn.
3. Thu batch dữ liệu tiếp theo với importer/baseline hiện hành, mở rộng độ phủ ngoài 30 sản phẩm.
4. Chuẩn bị query ảnh/audio độc lập có quyền sử dụng trước đo model.
