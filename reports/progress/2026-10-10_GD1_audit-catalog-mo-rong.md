# GĐ1 — Audit catalog mở rộng — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1: chất lượng ảnh/dữ liệu; kiểm chứng hồi quy backend |
| Trạng thái | Hoàn thành đợt tổng quát hóa audit; còn review dữ liệu/quyền ảnh và mở rộng catalog |
| Người thực hiện | Codex |
| Catalog | `seed-001-images`, 30 draft, 45 ảnh |
| SHA-256 DB | `459d5237b5ef5b47de2d2abeee88de4f15ace707f0b63f766b7df27705598062` — giữ nguyên |
| Commit | Workspace chưa có `.git`; hash mã nguồn có trong báo cáo kiểm chứng |

## 1. Mục tiêu

Xử lý mục còn lại từ [đợt bảo vệ importer](2026-10-10_GD1_bao-ve-importer.md): audit cũ gắn cố định 30 draft/45 ảnh, manifest một batch và thứ tự sản phẩm. Công cụ cần tiếp tục chạy được khi thêm dữ liệu hoặc có sản phẩm published.

## 2. Đã triển khai

Viết lại `scripts/validate_catalog/audit_images.py`:

- Lấy số lượng và trạng thái từ catalog; không còn số 30/45 hay truy vấn Marou cố định.
- Kiểm tra riêng chế độ published-only và include-drafts, bao gồm phân trang vượt 100 sản phẩm. Đối chiếu tập ID, tổng số và số phần tử để phát hiện thiếu/trùng.
- Sản phẩm/ảnh bị ẩn phải trả 404; ảnh local hợp lệ của sản phẩm hiển thị phải trả đúng bytes/hash và content type ảnh.
- Tách ảnh chưa có local_path, file thiếu, file hợp lệ; hỗ trợ catalog rỗng và schema/checksum lỗi.
- Đếm ảnh qua API theo ID duy nhất, không cộng trùng ảnh published được kiểm tra ở cả hai chế độ.
- Lưu và khôi phục biến môi trường/cặp trạng thái API sau khi chạy, kể cả khi TestClient lỗi.
- Kiểm tra importer qua `--editorial`/`--baseline`, manifest qua `--manifest` (lặp được). Khi không bật, ghi rõ skipped.
- Xuất JSON có timestamp; tạo bảng ảnh HTML bằng `--review-out` trong thư mục mới, không ghi đè bảng cũ. Đường dẫn ảnh tương đối và nội dung HTML được escape; chỉ liên kết nguồn HTTP(S).

Đã bổ sung 12 ca regression trong `backend/tests/test_image_audit.py`, cập nhật README, hướng dẫn thu thập và chỉ mục tiến độ.

## 3. Kiểm chứng

| Kiểm tra | Lệnh / phạm vi | Kết quả |
|---|---|---|
| Toàn bộ backend | `.venv/Scripts/python -X utf8 -m pytest backend/tests -q -p no:cacheprovider` | **180 passed**, 3,50 giây; 1 cảnh báo deprecation Starlette/httpx |
| Catalog tổng hợp | 12 ca mới: trộn trạng thái, URL-only/mất file, rỗng, 101 sản phẩm, checksum sai, khôi phục trạng thái, manifest đảo thứ tự, lỗi manifest, HTML và CLI | Đạt; dữ liệu fixture không phải benchmark |
| DB thật + importer + manifest | Lệnh audit đầy đủ bên dưới | `passed`, **45 ảnh duy nhất qua API đúng hash**, importer no-op và manifest idempotent |
| Gallery thật | Chrome headless 1280×900, mở file HTML và chờ mọi ảnh tải xong | 30 sản phẩm, 45/45 ảnh tải được, 0 lỗi JS, không tràn ngang |
| Kiểm tra hiển thị | Xem ảnh chụp `desktop.png` | Chữ tiếng Việt và ảnh hiện đúng ở viewport đầu; không phải lần đối chiếu lại toàn bộ nội dung sản phẩm |
| Frontend ứng dụng | Không đổi mã/config ứng dụng | Không chạy lại bộ E2E 50 ca; kết quả cũ vẫn là bằng chứng của đợt trước |

Lệnh audit đã chạy:

```bash
.venv/Scripts/python -X utf8 scripts/validate_catalog/audit_images.py --editorial data_collection/editorial.json --baseline data_collection/import_runs/2026-10-10_012920-036113_drafts/baseline.json --manifest data_collection/images/2026-10-10/manifest.json --review-out artifacts/image_review/2026-10-10_generic-audit
```

Pytest và Chrome headless chạy ngoài sandbox do giới hạn thư mục tạm/khởi tạo tiến trình đã được xác định ở các đợt trước. Audit TestClient chạy trong sandbox.

## 4. Kết quả đã lưu

- [Audit DB thật](../data_quality/2026-10-10_014142-102770_image-audit.json).
- [Bảng ảnh HTML mới](../../artifacts/image_review/2026-10-10_generic-audit/index.html).
- [Kết quả kiểm tra bằng trình duyệt](../../artifacts/image_review/2026-10-10_generic-audit/browser-check.json) và [ảnh chụp desktop](../../artifacts/image_review/2026-10-10_generic-audit/desktop.png).
- [Kiểm chứng và hash mã nguồn](../data_quality/2026-10-10_generic-audit-validation.json).

DB vẫn 30 draft; chế độ mặc định 0 sản phẩm, include-drafts 30. Không đổi raw/editorial, quyền ảnh, review sản phẩm hay nhãn keyword. Không tạo benchmark chính thức trong đợt này.

## 5. Giới hạn

- `passed` có thể đi cùng cảnh báo file thiếu ở draft; phải đọc phần chất lượng ảnh, không hiểu là tất cả bản ghi đều có file.
- TestClient kiểm tra chức năng cùng tiến trình, không đo mạng, tải hay latency server thật. Không chạy audit trong tiến trình đang đồng thời phục vụ request khác.
- File/hash hợp lệ không chứng minh ảnh đúng sản phẩm hoặc có giấy phép. Lần kiểm tra Chrome chỉ xác nhận ảnh hiện tại tải/giải mã được trong Chrome.
- Kiểm tra manifest là đối chiếu batch đã chỉ định, không tự tìm mọi manifest trong dự án. Đường dẫn ảnh của importer manifest vẫn theo cấu trúc assets của repo.

## 6. Việc tiếp theo

1. Hoàn thiện quyền ảnh và review theo [checklist công bố](../data_quality/2026-10-10_011803-480875_publication-readiness.md). Hai sản phẩm còn thiếu tiêu chí Việt có nguồn.
2. Duyệt 360 cặp keyword và xuất nhãn người kiểm tra để chạy baseline chính thức; seed hiện vẫn unverified.
3. Rà soát taxonomy Hanoia, mở rộng batch sản phẩm và cập nhật snapshot/hash/packet benchmark sau khi DB đổi.
4. Thu audio và query ảnh độc lập có quyền sử dụng trước khi triển khai đo model.
