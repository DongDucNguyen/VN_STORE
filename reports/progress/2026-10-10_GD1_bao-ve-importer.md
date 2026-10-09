# GĐ1 — Bảo vệ dữ liệu khi nhập lại — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1: nhập dữ liệu, truy vết và giữ chỉnh sửa biên tập |
| Trạng thái | Hoàn thành đợt bảo vệ importer; GĐ1 vẫn còn review/quyền ảnh và mở rộng catalog |
| Người thực hiện | Codex |
| Catalog | `seed-001-images` — 30 draft, 45 ảnh |
| SHA-256 DB | `459d5237b5ef5b47de2d2abeee88de4f15ace707f0b63f766b7df27705598062` — giữ nguyên |
| Commit | Workspace chưa có `.git`; hash mã nguồn lưu trong báo cáo kiểm chứng |

## 1. Mục tiêu đợt này

Xử lý nợ kỹ thuật ưu tiên từ [báo cáo trước](2026-10-10_GD1_dieu-kien-cong-bo-va-toan-du-an.md): importer thay toàn bộ bản ghi trùng ID có thể làm mất review, quyền ảnh và chỉnh sửa thủ công. Tiếp tục triển khai trong phạm vi dữ liệu/công cụ hiện có, đồng thời lưu kết quả để phiên sau tiếp nối được.

## 2. Đã triển khai

### Ghép ba phía và chặn xung đột

Thêm `scripts/import_raw/safe_import.py`. `build_drafts.py` sinh dữ liệu riêng từ raw/editorial/manifest, sau đó so với baseline của lần nhập thành công và DB hiện tại:

- Nguồn không đổi thì giữ dữ liệu người biên tập đã sửa trong DB.
- DB không đổi so với baseline thì nhận cập nhật nguồn.
- Hai phía thay đổi khác nhau cùng một trường thì báo xung đột; không ghi bất kỳ thay đổi nào của lần nhập đó.
- Object ghép theo trường, mảng coi là một khối. Không ghép ảnh/giấy phép theo vị trí mảng.
- Không tự xóa bản ghi vì batch mới bỏ ID đó; không tự khôi phục bản ghi đã xóa khỏi DB khi nguồn không đổi.
- Chặn cập nhật sản phẩm đã có review hoặc không còn draft. Chặn cả nguồn/metadata thay đổi nếu được sản phẩm đã review tham chiếu trực tiếp.
- Không có baseline thì chỉ thêm ID mới hoặc giữ bản ghi giống hệt; không ghi đè bản ghi khác nội dung.

Không có cờ ép ghi đè. Xung đột cần được giải quyết bằng dữ liệu và quyết định biên tập có căn cứ, rồi chạy preview lại.

### Diff, snapshot và ghi có kiểm tra

Mỗi lần nhập lưu:

```text
data_collection/import_runs/<timestamp>_<kind>/
  catalog.before.json
  catalog.proposed.json
  baseline.json
reports/data_quality/<timestamp>_import-<kind>.json
reports/data_quality/<timestamp>_import-<kind>.md
```

JSON báo cáo có hash DB đầu vào, hash các file nguồn, giá trị trước/sau, giá trị ba phía khi xung đột, lỗi validator và trạng thái. Baseline chỉ hợp lệ khi run draft đã áp dụng hoặc no-op; preview có thay đổi chưa được dùng làm baseline. Baseline được kiểm tra checksum/cấu trúc khi nạp.

Khi DB thay đổi, CLI yêu cầu tên phiên bản mới qua `--catalog-version`. Trước khi ghi, lưu bản gốc, validate đề xuất, so lại bytes DB rồi thay file nguyên khối. Nếu DB đã đổi trong lúc xử lý, ghi báo cáo `write_failed` và không ghi đè. No-op không viết lại DB, giữ nguyên cả định dạng/bytes.

`catalog.proposed.json` được serialize chuẩn JSON/LF nên hash đề xuất có thể khác hash DB gốc dù diff nội dung rỗng. Hash đề xuất không phải khẳng định DB đã bị thay đổi.

### Ghép ảnh giữ thông tin biên tập

`apply_images.py` giữ nguyên quyền, ghi chú quyền, caption, thứ tự gallery và catalog version khi nhập lại. Phát hiện ảnh local khác manifest hoặc manifest định loại ảnh đã local/đã ghi nhận quyền thì báo xung đột. Không tự gắn quyền đã cấp cho ảnh chưa được xác nhận là đúng asset. Dữ liệu vừa sinh từ raw có chế độ riêng để nhận caption đã đối chiếu trong manifest; không áp dụng chế độ đó vào DB biên tập.

CLI ghép ảnh cũng có dry-run, diff, snapshot và phiên bản mới cho thay đổi thực. Công cụ audit ảnh được chuyển sang dùng importer mới và ghi file kết quả có timestamp để không đè lịch sử.

### Tài liệu

Đã cập nhật [quy trình nhập lại](../../data_collection/README.md#nhập-lại-dữ-liệu-và-giữ-chỉnh-sửa-biên-tập), [hướng dẫn nhập liệu](../../docs/huong-dan-nhap-lieu.md), README gốc và chỉ mục tiến độ.

## 3. Kiểm chứng

| Kiểm tra | Cách chạy / dữ liệu | Kết quả |
|---|---|---|
| Toàn bộ backend | `.venv/Scripts/python -X utf8 -m pytest backend/tests -q -p no:cacheprovider` | **168 passed**, 1,26 giây; 1 cảnh báo deprecation Starlette/httpx |
| 31 ca mới | `backend/tests/test_safe_import.py` trong suite trên | Giữ review/quyền, merge độc lập, xung đột mảng, xóa/giữ ID, nguồn liên quan review, stale write, snapshot/baseline, CLI version/dry-run và ảnh |
| Khởi tạo baseline | `build_drafts.py --dry-run` trên DB thật | No-op, 0 xung đột, 0 lỗi |
| Nhập với baseline | `build_drafts.py --dry-run --baseline data_collection/import_runs/2026-10-10_012920-036113_drafts/baseline.json` | No-op, 0 xung đột, 0 lỗi |
| Ghép ảnh | `apply_images.py --dry-run` | No-op, 0 xung đột, 0 lỗi |
| API và file thật | `scripts/validate_catalog/audit_images.py` | 45/45 ảnh qua API đúng SHA-256; reimport/idempotency đạt; mặc định 0 sản phẩm, include-drafts 30 |
| Keyword smoke | Audit: Marou Bến Tre 78% | Đúng sản phẩm ở hạng 1; không phải benchmark |
| Frontend | Không đổi mã/config frontend trong đợt này | Không chạy lại build/E2E; kết quả đợt trước là 50 E2E, typecheck/build đạt |

Lượt thử đầu của suite importer trong sandbox đạt 17 ca nhưng 7 ca lỗi setup do thư mục tạm Windows bị chặn. Các lượt hoàn chỉnh sau được chạy ngoài sandbox; kết quả cuối 168/168 đạt. Không có test chức năng nào bị bỏ qua để đạt kết quả.

## 4. Kết quả và nơi lưu

- [Baseline khởi tạo đã kiểm chứng](../../data_collection/import_runs/2026-10-10_012920-036113_drafts/baseline.json).
- [Diff nhập lại draft (JSON)](../data_quality/2026-10-10_013245-858603_import-drafts.json) · [Markdown](../data_quality/2026-10-10_013245-858603_import-drafts.md).
- [Diff ghép ảnh (JSON)](../data_quality/2026-10-10_013246-202968_import-images.json) · [Markdown](../data_quality/2026-10-10_013246-202968_import-images.md).
- [Audit API/ảnh thật](../data_quality/2026-10-10_013247-044637_image-audit.json).
- [Kết quả kiểm chứng và hash mã nguồn](../data_quality/2026-10-10_safe-import-validation.json).

DB, raw, editorial, manifest ảnh và nhãn keyword không bị thay đổi trong đợt này. Các trường `licensed`/reviewed trong kiểm thử chỉ nằm trên bản sao thử nghiệm; không phải quyền hoặc review mới của catalog thật.

## 5. Giới hạn còn lại

1. Ghi DB dùng kiểm tra bytes trước atomic replace; không khóa trình soạn thảo và không phải giao dịch xuyên file DB/baseline/report. Vẫn cần tránh chỉnh DB đồng thời; nếu tiến trình bị ngắt, kiểm tra snapshot và trạng thái run trước khi tiếp tục.
2. Mảng được giữ nguyên khối nên hai chỉnh sửa độc lập trong cùng mảng vẫn có thể cần giải quyết xung đột thủ công. Đây là lựa chọn bảo toàn thông tin thay vì tự đoán cách ghép.
3. Chặn nguồn thay đổi hiện kiểm tra tham chiếu trực tiếp từ sản phẩm. Chưa dựng đồ thị phụ thuộc bắc cầu để tự phát hiện mọi thay đổi qua brand/maker/place trung gian.
4. `audit_images.py` vẫn dành riêng cho seed 30 draft/45 ảnh. Cần tổng quát hóa khi thêm batch hoặc công bố sản phẩm.
5. Importer không xác minh nội dung nguồn hay cấp phép ảnh. Catalog vẫn có 30 sản phẩm chờ review, 45 ảnh quyền unknown, 2 sản phẩm thiếu tiêu chí Việt có nguồn và chưa có benchmark chính thức.

## 6. Bước tiếp theo

1. Dùng [checklist công bố](../data_quality/2026-10-10_011803-480875_publication-readiness.md) để xử lý quyền ảnh và review sản phẩm; importer đã có cơ chế giữ các chỉnh sửa này.
2. Duyệt [360 cặp keyword](../../artifacts/keyword_review/2026-10-10_seed-001/index.html), xuất nhãn thật, kiểm tra bằng evaluator và mở rộng query/no-match.
3. Rà soát taxonomy hai bình Hanoia, bổ sung dữ liệu thiếu và thu batch mới. Trước khi đổi DB, chạy preview với baseline; khi đổi snapshot phải cập nhật các packet/hash benchmark tương ứng.
4. Thu query ảnh/audio độc lập có quyền sử dụng, khóa splits trước khi chọn và đo model voice/image.
