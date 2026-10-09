# GĐ1–GĐ3 — Rà soát toàn dự án và điều kiện công bố — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1: chất lượng catalog; kiểm chứng hồi quy GĐ2 và công cụ GĐ3 |
| Trạng thái | Hoàn thành đợt bổ sung công cụ; các giai đoạn dự án vẫn chưa đủ điều kiện nghiệm thu |
| Người thực hiện | Codex |
| Phiên bản catalog | `seed-001-images` |
| SHA-256 catalog | `459d5237b5ef5b47de2d2abeee88de4f15ace707f0b63f766b7df27705598062` |
| Commit | Workspace chưa có `.git`; kết quả kiểm chứng lưu hash các file thay đổi |

## 1. Mục tiêu đợt này

Đối chiếu cấu trúc và mã nguồn hiện tại với PLAN.md, các báo cáo trước, catalog, importer, benchmark và bộ kiểm thử. Tiếp tục phần có thể hoàn thành mà không tự gán quyền ảnh, nhãn benchmark hay kết quả review của con người.

## 2. Phân tích hiện trạng toàn dự án

| Thành phần | Đang có / kiểm chứng | Phần còn thiếu |
|---|---|---|
| Catalog và schema | JSON Schema 2020-12; 30 sản phẩm/30 biến thể, 22 danh mục, 5 thương hiệu, 2 nhà sản xuất, 6 địa danh, 37 nguồn; catalog hiện tại 0 lỗi/0 cảnh báo | 270 sản phẩm để đạt mục tiêu 300; review dữ liệu và điều kiện công bố |
| Ảnh thật | 45 ảnh được chọn từ 52 ứng viên ở đợt trước; manifest và bằng chứng nguồn đã lưu; lần này kiểm tra lại 45 file và 45 phản hồi API đúng SHA-256 | 45 ảnh còn quyền `unknown`; 19 sản phẩm chỉ có một ảnh; chưa có kiểm tra gần trùng bằng perceptual hash |
| Backend | FastAPI, nạp snapshot sau validation, catalog/facets/detail/similar, phục vụ ảnh trong thư mục catalog | Chưa có inference voice/image; chưa có quy trình triển khai vận hành |
| Tìm kiếm chữ | BM25, chuẩn hóa tiếng Việt, giá, phủ định/hard filter; trọng số danh mục cha thấp hơn danh mục lá từ đợt trước | Chưa có baseline trên nhãn được người kiểm tra; ca no-match vẫn cần đánh giá |
| Frontend | React/TypeScript/Vite; xem/lọc/tìm, gallery, yêu thích trên thiết bị, xử lý lỗi; build và E2E desktop/mobile đạt | Voice/image báo chưa sẵn sàng; chưa có upload và kết quả model thật |
| Benchmark keyword | Evaluator kiểm tra nhãn/split/hash, metric cho pool đã chấm; trang review offline 360 cặp (12 query × 30 sản phẩm) | Seed vẫn chưa duyệt; chưa có nhãn chính thức, tập 600 query, khóa split hoặc baseline được nghiệm thu |
| Voice/image benchmark | Kế hoạch rubric, split và metric trong PLAN.md | Chưa có audio người thật, query ảnh độc lập, manifest đồng ý sử dụng, adapter, embeddings hay chạy model |
| Import và khả năng chạy lại | Với DB hiện tại, build + merge + apply_images cho kết quả bằng DB; apply_images idempotent | Merge thay toàn bộ bản ghi trùng ID, có thể ghi đè chỉnh sửa thủ công/review; apply_images còn ghi đè note quyền và version. Cần bảo vệ trước đợt biên tập tiếp theo |
| Kiểm thử và truy vết | 137 backend test, 50 E2E; báo cáo từng đợt, hash DB/code | Chưa có Git commit; cần giữ bản sao trước khi cập nhật dữ liệu. Số test không chứng minh chất lượng retrieval trên dữ liệu thật |

Kết luận: phần catalog và tìm chữ đã có chức năng dùng để phát triển; nút thắt hiện nay là dữ liệu được duyệt và benchmark. Chưa đủ căn cứ tuyên bố hoàn thành GĐ1/GĐ2 hoặc chọn model voice/image.

## 3. Đã triển khai trong đợt này

### Kiểm tra file ảnh dùng chung

Trong `backend/app/catalog/validation.py`, bổ sung `inspect_image_file`:

- Chặn đường dẫn tuyệt đối, vượt thư mục catalog và đường dẫn resolve ra bên ngoài trước khi đọc/hash file; vẫn kiểm tra ranh giới khi `check_files=False`.
- Phân biệt chưa có local_path, mất file, file rỗng, không đọc được, checksum sai và file hợp lệ.
- Ảnh sai checksum không còn được tính vào ảnh đủ điều kiện công bố.
- Báo cáo chất lượng phân biệt không có bản ghi ảnh, không có file hợp lệ và không có ảnh đủ quyền kèm file hợp lệ.
- Hash trùng dùng kết quả kiểm tra đã đọc được; file không đọc được tạo lỗi rõ ràng thay vì làm công cụ dừng bằng traceback.

Kiểm tra file chưa giải mã định dạng, chưa đối chiếu nội dung ảnh và chưa xác minh giấy phép. Đây là phạm vi rõ ràng của kết quả `valid`.

### Báo cáo từng sản phẩm trước khi công bố

Thêm `backend/app/catalog/readiness.py` và `scripts/validate_catalog/readiness.py`. Công cụ kiểm tra catalog hiện tại, mô phỏng `published` trên bản sao rồi gom lỗi/cảnh báo theo sản phẩm. Tách riêng điều kiện kỹ thuật, `reviewed_at` và thiếu sót biên tập. Nếu schema sai, công cụ xuất lỗi và bỏ đánh giá sản phẩm. Không thay đổi DB.

Đầu ra có timestamp để không ghi đè báo cáo cùng ngày; lưu Markdown/JSON và SHA-256 DB:

- [Báo cáo điều kiện công bố](../data_quality/2026-10-10_011803-480875_publication-readiness.md)
- [Dữ liệu báo cáo JSON](../data_quality/2026-10-10_011803-480875_publication-readiness.json)
- [Kết quả kiểm chứng đợt này](../data_quality/2026-10-10_publication-checks.json)

### Kiểm thử và tài liệu

Thêm 17 ca kiểm thử cho ranh giới đường dẫn, checksum, file lỗi, báo cáo không sửa dữ liệu, lỗi chung và phân biệt review với kỹ thuật. Cập nhật README và hướng dẫn nhập liệu. Playwright mặc định 2 worker để giảm lỗi tài nguyên đã ghi nhận ở đợt trước; vẫn ghi đè được bằng CLI.

## 4. Kiểm chứng

Môi trường: Windows 11, Python 3.14.6; Chrome theo cấu hình Playwright hiện tại. Không cài thêm thư viện.

| Kiểm tra | Lệnh / cách thực hiện | Kết quả |
|---|---|---|
| Backend | `.venv/Scripts/python -X utf8 -m pytest backend/tests -q -p no:cacheprovider` | **137 passed**, 0,96 giây; 1 cảnh báo deprecation Starlette/httpx |
| Fixture | Gọi `scripts.run_all_tests.check_fixture_in_sync()` | Khớp generator |
| Typecheck | `npx.cmd tsc -b` trong frontend | Exit 0 |
| Build | `npx.cmd vite build --outDir ../artifacts/build --emptyOutDir` trong frontend | Exit 0; 27 module; artifact trong `artifacts/build/` |
| E2E | `npx.cmd playwright test --reporter=line` trong frontend | **50 passed**, 16,7 giây, 2 worker, desktop/mobile; gồm review packet thật |
| Điều kiện công bố | `.venv/Scripts/python -X utf8 scripts/validate_catalog/readiness.py` | Exit 0; DB hiện tại hợp lệ; 0/30 đủ kiểm tra kỹ thuật để công bố |
| Ảnh/API DB thật | Python inline với FastAPI TestClient: GET chi tiết từng sản phẩm, GET từng ảnh, so SHA-256 với DB | 30 chi tiết đạt; **45/45 ảnh đạt**; mặc định 0 sản phẩm, include-drafts 30 |
| Keyword DB thật | TestClient: `Marou Ben Tre 78%` | Đúng `p-marou-ben-tre-78-80g` ở hạng 1; chỉ smoke test |
| Reimport | Tính `apply_images(merge(catalog, build(editorial), batch, timestamp))` trong bộ nhớ và so với DB | Bằng DB hiện tại; không khẳng định bảo toàn chỉnh sửa thủ công trong tương lai |
| DB không bị sửa | So bytes trước/sau kiểm tra và hash với báo cáo đợt trước | Không thay đổi |

Lượt pytest đầu trong sandbox đạt 28 ca và lỗi setup một ca do không truy cập được thư mục tạm. Vite/Playwright cũng bị `spawn EPERM` trong sandbox. Các lượt hoàn chỉnh nêu trên đã được cho phép chạy ngoài sandbox và đạt; đây là giới hạn môi trường, không phải test chức năng bị bỏ qua. E2E dùng reporter dòng nên không tạo báo cáo HTML mới; không dùng HTML cũ làm bằng chứng cho lượt này.

## 5. Số liệu và việc cần xử lý

| Chỉ số DB thật | Kết quả |
|---|---|
| Sản phẩm draft / published | 30 / 0 |
| File ảnh hợp lệ | 45/45 |
| File trùng byte theo SHA-256 | 0 nhóm |
| Sản phẩm thiếu ảnh đủ quyền và file hợp lệ | 30/30 — do quyền ảnh, không phải mất file |
| Sản phẩm chưa ghi nhận review | 30/30 |
| Sản phẩm chưa có tiêu chí Việt true có nguồn | 2: `p-lys-dia-tron-jasmine-trang-nga-15cm`, `p-vietcraft-gio-may-bau-duc-vh24040` |
| Biến thể chưa có giá VND | 14/30 |
| Thiếu chất liệu / thương hiệu / nhà sản xuất | 2 / 8 / 16 sản phẩm |
| Dưới 2 ảnh | 19/30 sản phẩm |

Không phát sinh nhãn do người duyệt, nguồn mới, giấy phép hoặc benchmark chính thức trong đợt này. Không tự đặt giá hay suy luận xuất xứ để lấp dữ liệu thiếu.

## 6. Khác với kế hoạch / giới hạn

Ưu tiên chất lượng dữ liệu và công cụ kiểm tra theo thứ tự trong PLAN.md. Chưa bắt đầu model vì chưa có bộ đo tương ứng. Quyền ảnh và việc người thứ hai kiểm tra nội dung là các bước cần bằng chứng thực; báo cáo không thay thế các bước đó.

`reviewed_at` thiếu vẫn là cảnh báo của validator hiện tại; readiness báo riêng là chưa review. Mục `passes_recorded_checks` không phải lệnh hay quyết định tự công bố sản phẩm. Test đường dẫn symlink dùng mô phỏng kết quả resolve, không cần tạo symlink Windows thật.

## 7. Nợ kỹ thuật và rủi ro còn lại

1. Importer có thể ghi đè chỉnh sửa sau review. Trước đợt cập nhật dữ liệu tiếp theo cần cơ chế phát hiện xung đột, bảo toàn quyền/review và báo diff.
2. Hai bình Hanoia đang thuộc `go-son-mai-tranh`; cần rà soát danh mục phù hợp rồi cập nhật editorial/DB và dữ liệu benchmark liên quan đồng bộ.
3. SHA-256 không phát hiện gần trùng, ảnh hỏng định dạng nhưng hash được khai báo khớp hoặc ảnh sai sản phẩm. Cần tiếp tục duyệt bằng mắt; bổ sung decode/perceptual hash khi mở rộng dữ liệu.
4. Luồng API trình bày draft dựa trên local_path đã khai báo; nếu file bị xóa sau khi nạp snapshot, việc phục vụ ảnh có thể thất bại. Chưa triển khai theo dõi thay đổi file trong lúc chạy.
5. Chưa có locked split, nhãn độc lập/giải quyết bất đồng, benchmark latency end-to-end hoặc số đo model. Không suy rộng từ test fixture và seed chưa duyệt.

## 8. Bước tiếp theo theo ưu tiên

1. Bảo vệ importer trước ghi đè dữ liệu đã biên tập; có dry-run diff và test cho review/quyền ảnh.
2. Theo checklist từng sản phẩm để bổ sung bằng chứng quyền, kiểm tra nguồn/claim và ghi nhận người duyệt; chỉ sau đó cân nhắc `published`.
3. Duyệt 360 cặp trong [trang review keyword](../../artifacts/keyword_review/2026-10-10_seed-001/index.html), xuất nhãn thật và chạy evaluator; thêm query/no-match theo rubric.
4. Mở rộng đợt thu thập thứ hai theo độ phủ danh mục, nguồn và khả năng dùng ảnh; giữ snapshot/hash cho mỗi lần thay catalog.
5. Thu audio/ảnh query độc lập có đồng ý sử dụng, khóa splits rồi triển khai adapter và đo model trên cùng bộ dữ liệu.
