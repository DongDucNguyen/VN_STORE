# GĐ2 — Rà soát hồi quy toàn dự án — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2, kiểm tra liên quan GĐ1/GĐ3 |
| Trạng thái | Hoàn thành đợt rà soát; 7/7 bước kiểm tra đạt |
| Người thực hiện | Codex |
| Catalog | `seed-002-taxonomy`: 23 danh mục, 30 draft, 45 ảnh |
| SHA-256 DB | `41ac0dfdc090af7981773dd4689179d0ca47bfe992deed3c2713c7628c801f16` — không thay đổi |
| Commit | Workspace chưa có `.git`; lưu hash file trong báo cáo JSON |

## 1. Phạm vi

Rà soát cấu trúc, kế hoạch, API/snapshot, trình bày sản phẩm, tìm kiếm, importer ba phía, công cụ ảnh/packet nhãn và bộ kiểm thử. Tập trung phần vừa sửa: ảnh mất/rỗng, fallback gallery/card, taxonomy và đồng bộ fixture. Đây là kiểm tra hồi quy chức năng, không phải chứng nhận bảo mật, kiểm thử tải hay benchmark retrieval chính thức.

## 2. Phát hiện và sửa

### Danh sách sản phẩm tương tự cũ khi chuyển trang

`ProductPage` xóa dữ liệu chi tiết và trạng thái ảnh khi đổi ID nhưng chưa xóa `similar`. Khi API chi tiết sản phẩm mới trả trước API tương tự, danh sách của sản phẩm trước có thể hiện dưới sản phẩm mới.

- Đã tái hiện trên Chrome desktop: giữ response tương tự của sản phẩm mới ở trạng thái chờ; kiểm thử nhận 1 tiêu đề “Sản phẩm tương tự” trong khi kỳ vọng 0.
- Sửa bằng `setSimilar([])` trong effect đổi ID; giữ cơ chế bỏ response cũ qua cờ `alive`.
- Test cùng tình huống trên desktop/mobile đã đạt.
- [Ảnh chụp và trace trước sửa](../../artifacts/review/2026-10-10_project-recheck/before-fix/) được giữ riêng, không bị lượt chạy sau ghi đè.

### Fixture chưa đồng bộ taxonomy

Lượt chạy toàn bộ đầu tiên có 216 backend test và 64 E2E đạt, nhưng bước kiểm tra fixture khớp generator thất bại. Generator dùng taxonomy từ DB; fixture chưa có danh mục `go-son-mai-binh-lo` được thêm ở đợt trước.

- Diff chỉ có đúng một danh mục mới; không thay sản phẩm giả hay giá/nhãn giả.
- Đã chạy `backend/tests/fixtures/make_fixture.py`; checksum 24 SVG fixture giữ nguyên.
- [Diff và hash trước/sau](../../artifacts/review/2026-10-10_project-recheck/fixture-sync.json).
- Chạy lại toàn bộ sau đồng bộ: 7/7 bước đạt. Không sửa DB thật để làm test qua.

### Bổ sung ca lỗi ảnh và chỉnh tài liệu

- Thêm 4 E2E: HTTP 404 và mất kết nối, mỗi ca trên desktop/mobile. Card báo lỗi nhưng vẫn mở chi tiết; gallery chuyển sang ảnh còn tải được.
- Các ca này chỉ chấp nhận console message của lỗi tài nguyên cố ý gây ra; lỗi JavaScript hoặc console khác vẫn làm test thất bại.
- Thêm 1 backend test cho file ảnh bị thay bằng thư mục sau khi snapshot đã nạp; API bỏ ảnh đó và chọn ảnh kế tiếp.
- Test packet dùng `monkeypatch.syspath_prepend` để khôi phục đường dẫn import sau test.
- Cập nhật phần mở đầu PLAN để dẫn đến trạng thái hiện hành, tránh mô tả dự án vẫn chưa có dữ liệu/API.
- README phân biệt reporter dòng của `run_all_tests.py` với HTML từ `npm run test:e2e`; kiểm tra đường dẫn cục bộ trong 6 tài liệu chính không có link mất đích.

## 3. Kiểm chứng

Lệnh cuối: `.venv/Scripts/python.exe -X utf8 scripts/run_all_tests.py`.

| Kiểm tra | Kết quả cuối |
|---|---|
| Validate DB thật | 0 lỗi, 0 cảnh báo |
| Validate fixture | 0 lỗi, 0 cảnh báo |
| Fixture khớp generator | Đạt sau đồng bộ taxonomy |
| Pytest backend | **216 passed**, 1 cảnh báo deprecation Starlette/httpx |
| TypeScript | Đạt |
| Vite build | Đạt, 28 module; `artifacts/build/` |
| Playwright | **64 passed**, 20,3 giây; Chrome desktop + Pixel 7 giả lập, 2 worker |

So với đợt trước: thêm 1 backend test và 6 E2E (4 lỗi mạng/404, 2 chuyển sản phẩm). Backend gồm cả regression importer, audit, taxonomy và công cụ benchmark. E2E gồm catalog, tìm kiếm, yêu thích, packet nhãn và xử lý ảnh lỗi; dữ liệu sản phẩm UI chủ yếu là fixture giả.

Kiểm tra dữ liệu thật bổ sung:

- [Audit ảnh/API](../data_quality/2026-10-10_150156-567231_image-audit.json): passed, 45 ảnh duy nhất đúng hash qua API; cover/gallery/count nhất quán, chế độ mặc định có 0 sản phẩm, chế độ draft có 30. Import với baseline hiện hành cho dữ liệu identical; manifest idempotent.
- [Audit packet nhãn](../benchmark/2026-10-10_150155-845183_keyword-review-audit.json): `pending_review`, 12 truy vấn × 30 sản phẩm = 360 cặp; packet khớp catalog, chưa có export của người duyệt.
- DB, packet, seed query, raw, editorial và manifest không đổi checksum so với đợt xử lý ảnh lỗi. Không tạo `seed_reviewed.jsonl`.

## 4. Hồ sơ kết quả

- [Kết quả tổng hợp và hash mã nguồn](../data_quality/2026-10-10_project-recheck-validation.json).
- [Log cuối đầy đủ](../../artifacts/review/2026-10-10_project-recheck/final-tests.log), [mã thoát/thời gian](../../artifacts/review/2026-10-10_project-recheck/final-tests.json): exit 0.
- [Log lượt đầu](../../artifacts/review/2026-10-10_project-recheck/full-tests.log): exit 1 do fixture chưa khớp; giữ lại để truy vết, không coi là lượt thành công.

Lần xin chạy lại cuối lượt trước không được thực thi vì hệ thống duyệt tự động hết hạn mức. Sau yêu cầu tiếp tục, lệnh được duyệt và chạy thành công. Pytest/Vite/Chrome dùng môi trường ngoài sandbox do giới hạn tiến trình/thư mục tạm Windows. Không bỏ qua cơ chế duyệt. Reporter dòng không tạo HTML E2E mới.

## 5. Giới hạn và bước tiếp theo

1. Chưa có nhãn benchmark người duyệt, chưa đo baseline chính thức; tiếp tục chấm packet hiện hành, audit export và phân xử.
2. 30 sản phẩm vẫn draft, 45 ảnh chưa rõ quyền; cần review/quyền và căn cứ Việt còn thiếu trước công bố. Giữ [checklist công bố](../data_quality/2026-10-10_144424-872002_publication-readiness.md).
3. Chưa mở rộng từ 30 lên 300 sản phẩm; còn thiếu giá ở 14 sản phẩm, chất liệu ở 2, thương hiệu ở 8, nhà sản xuất ở 16.
4. Voice/image vẫn trả 503 có thông báo; cần dữ liệu query có quyền, nhãn và benchmark trước chọn model.
5. Kiểm tra file lúc trả API vẫn dùng metadata; không hash/giải mã lại mỗi request. Khoảng thời gian file thay đổi giữa kiểm tra và đọc vẫn là giới hạn đã ghi ở đợt trước.
6. Fixture cố ý dùng taxonomy/từ điển từ DB: sau thay taxonomy cần chạy generator và cả `run_all_tests.py`, không chỉ pytest/E2E riêng lẻ.

Không có thay đổi dependency, không xác minh lại độ mới của website nguồn hoặc giấy phép ảnh trong đợt rà soát này.
