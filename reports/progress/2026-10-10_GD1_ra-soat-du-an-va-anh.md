# GĐ1 — Rà soát toàn dự án và thu thập ảnh thật — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1 (dữ liệu), rà soát GĐ0–GĐ7 theo PLAN.md mục 9 |
| Trạng thái | Hoàn thành đợt ảnh cho 30/30 sản phẩm; GĐ1 tổng thể còn một phần |
| Người thực hiện | Codex theo yêu cầu người dùng |
| Catalog | `seed-001-images` |
| SHA-256 DB qua API | `459d5237b5ef5b47de2d2abeee88de4f15ace707f0b63f766b7df27705598062` |
| Commit | Workspace hiện không có thư mục `.git`; không tạo commit |

## 1. Mục tiêu đợt này

Kiểm tra tiến độ thực tế so với kế hoạch, rà soát mã và dữ liệu toàn dự án, lấy ảnh thật chính xác cho mọi sản phẩm đang có trong DB, lưu nguồn và kết quả theo cấu trúc hiện tại.

Browser được yêu cầu không có kết nối (`iab` unavailable; inventory không có browser). Người dùng đã cho phép dùng công cụ web và tải trực tiếp từ nguồn chính thức. Đợt này không dùng trình duyệt kết nối để thu thập; Chrome chỉ được dùng bởi bộ E2E có sẵn trên ứng dụng local.

## 2. Kết quả thu thập ảnh

| Nguồn chính thức | Sản phẩm | Ảnh tải | Ảnh chọn vào DB | Căn cứ |
|---|---:|---:|---:|---|
| Minh Long / LY'S | 6 | 10 | 9 | Tên và SKU trang sản phẩm, liên kết ảnh, xem ảnh |
| Vietnam Handicraft | 8 | 10 | 10 | Tên trang, mã VH trên trang/ảnh, liên kết ảnh |
| Maison Marou | 6 | 12 | 6 | Tên, SKU, bao bì đúng xuất xứ và tỷ lệ cacao |
| Hanoia | 4 | 4 | 4 | Tên, mã sản phẩm và ảnh chính `data-original` |
| Kilomet109 | 6 | 16 | 16 | Store API công khai: tên, permalink, SKU và toàn bộ URL ảnh |
| **Tổng** | **30** | **52** | **45** | **30/30 sản phẩm có ảnh local** |

Đã xem toàn bộ 52 ảnh trên 5 contact sheet. 45 ảnh được chọn có tổng dung lượng 14.144.051 byte (~13,49 MiB), gồm 19 PNG, 14 JPEG và 12 WebP theo định dạng thực. Một số URL đuôi `.jpg` trả WebP; file được đặt đúng phần mở rộng sau giải mã, không chỉ tin đuôi URL.

Ảnh sản phẩm lấy nguyên nội dung từ website chính thức/CDN, không sinh AI, không đổi nền, không xóa watermark. Việc xác nhận là đối chiếu ảnh do nhà sản xuất/nhãn hàng cung cấp, không phải xác thực vật thể ngoài đời hay giám định nguồn gốc.

- Loại 6 ảnh thanh chocolate dùng chung `80g_bar_front_Bk_shadow_new.jpg`: không phân biệt SKU. Giữ ảnh bao bì riêng cho cả 6 sản phẩm Marou.
- Loại ảnh infographic đặc tính chung của bộ trà Camellia: không phải ảnh chụp sản phẩm.
- 7 file bị loại vẫn lưu trong hồ sơ, có `decision=exclude`; không gắn vào catalog hay coi là ảnh query benchmark.
- Hanoia: ảnh Mystery 3.000×3.000; Vita, Botanica, Ethnic 1.200×1.200, thay thumbnail 285×285. Metadata lần tải thumbnail được giữ trong `previous_download`; file tại đường dẫn đã được thay bằng bản lớn.
- Kilomet109: lượt đầu bị 403 ở HTML và 8 ảnh; tải lại và API công khai thành công. Tất cả 16 URL ảnh khớp API, cả 6 SKU/permalink khớp sản phẩm. Lỗi ban đầu vẫn nằm trong manifest.
- Bát gáo dừa dùng SKU nội bộ `VNS-VIETCRAFT-VH2615`, không khẳng định SKU nội bộ xuất hiện trên trang; căn cứ là mã VH2615 trên ảnh và tên/trang sản phẩm tương ứng.
- 19/30 sản phẩm hiện chỉ có một ảnh được chọn. Không bổ sung ảnh gần giống hoặc ảnh chung để đủ số lượng.

### Đầu ra

- [Ảnh gốc](../../assets/products/) theo `assets/products/<product-id>/<image-id>.<ext>`.
- [Manifest chi tiết](../../data_collection/images/2026-10-10/manifest.json): đủ danh sách 30 sản phẩm, 52 ứng viên, URL, SKU, hash, kích thước, thời điểm, căn cứ và quyết định chọn/loại.
- [Trang/API nguồn](../../data_collection/images/2026-10-10/pages/): 24 HTML + 6 JSON; có hash trong manifest.
- [DB trước khi nhập](../../data_collection/images/2026-10-10/database.before.json).
- [Bảng duyệt ảnh](../../artifacts/image_review/2026-10-10/index.html) và 5 contact sheet cùng thư mục.
- [Báo cáo chất lượng catalog](../data_quality/2026-10-10_seed-001-images.md), [audit ảnh/API](../data_quality/2026-10-10_image-audit.json).

DB cập nhật `local_path`, `source_url` bản lớn khi có, `sha256`, `width`, `height`, mô tả ảnh và góc ảnh đã xem. Giữ `draft`, `usage_rights.status=unknown`, `reviewed_at=null`; đối chiếu ảnh không thay cho review sản phẩm và bằng chứng cấp phép. Giá và nhận định nguồn gốc giữ dữ liệu cũ.

Importer được bổ sung bước đọc manifest đã duyệt thông qua `editorial.json.image_manifest`, tránh chạy lại `build_drafts.py` làm mất ảnh local hoặc đưa ảnh chung trở lại. Manifest chưa duyệt, ảnh thiếu căn cứ, đường dẫn ngoài `assets/products`, file mất hoặc sai checksum đều bị từ chối khi ghép.

## 3. Phân tích dự án hiện tại

Đã rà soát PLAN/README/hướng dẫn nhập liệu, schema và 30 bản ghi, raw/editorial, toàn bộ module catalog/search/API, các trang/component chính frontend, cấu hình và bộ test, script nhập/validate, báo cáo và thư mục benchmark/experiments. Không đánh giá thư viện bên thứ ba trong node_modules/.venv như mã của dự án.

| Thành phần | Thực trạng và đánh giá |
|---|---|
| Dữ liệu | JSON là nguồn sự thật, 22 danh mục, 5 thương hiệu, 2 nhà sản xuất, 6 địa điểm, 37 nguồn, 30 sản phẩm/30 biến thể. Đạt 30/300 mục tiêu số lượng (10%), chưa có sản phẩm published. Không dùng tỷ lệ này làm % hoàn thành toàn dự án. |
| Schema/validator | Có schema 2020-12, kiểm tra liên kết, SKU/id, vòng danh mục, checksum, quy tắc published và báo cáo thiếu dữ liệu. Schema hợp lệ không đồng nghĩa thông tin đầy đủ hoặc đã được duyệt. |
| Catalog backend | FastAPI, snapshot catalog + BM25 cùng phiên bản, mặc định chỉ published; có health/hash, list/detail, facets, brands/makers/places, similar theo thuộc tính và phục vụ file ảnh. Sau ghép, 45 endpoint ảnh trả đúng byte trong chế độ draft. |
| Keyword | BM25 nhiều trường, bản có/không dấu, bigram âm tiết, ưu tiên cụm tên riêng, synonym theo ngữ cảnh, nhận tiền tiếng Việt, phủ định/bộ lọc, autocomplete và gợi ý nới điều kiện. Chưa có fuzzy Telex/VNI tổng quát, semantic retrieval hay thí nghiệm tokenizer theo kế hoạch. |
| Frontend | React/TypeScript/Vite, trang chủ/tìm kiếm/chi tiết/thương hiệu/làng nghề/yêu thích, gallery, responsive, filter trên URL và nguồn gốc có căn cứ. Giá unknown hiện Liên hệ. Yêu thích lưu localStorage. |
| Voice/image | Chỉ có endpoint trả 503 `model_unavailable` và thông báo UI. Chưa có upload, ASR, embedding, vector index, OCR hoặc pipeline inference. Thu ảnh catalog không đồng nghĩa image search đã chạy. |
| Benchmark/ML | Thư mục benchmark/experiments chưa có dataset, split, rubric, predictions hay metrics thật. 94 test backend và 44 E2E là regression trên fixture, không chứng minh các ngưỡng Success@5/Recall@5 trong PLAN. |
| Vận hành | Chạy local được; Vite proxy `/api` và `/images`. Có script test chung nhưng chưa có cấu hình deploy/CI và quy trình benchmark/model. Workspace không có Git metadata, chưa gắn được kết quả với commit. |

### Vấn đề cần xử lý tiếp

1. **Dữ liệu chưa công bố được theo quy tắc dự án:** 30 draft, 45 quyền ảnh unknown, 30 sản phẩm chưa review toàn bộ; LY'S dĩa trắng ngà và giỏ mây bầu dục chưa có tiêu chí Việt true. Mặc định website hiển thị 0 sản phẩm là đúng logic hiện tại, không phải mất DB.
2. **Coverage còn thiếu:** 14/30 biến thể chưa có giá VND; 2 sản phẩm thiếu chất liệu; 8 không có thương hiệu (có thể là hàng theo nhà sản xuất, không tự bịa brand); 16 chưa gắn nhà sản xuất. Còn 270 sản phẩm để đạt mục tiêu số lượng GĐ1.
3. **Taxonomy cần review:** hai bình Hanoia đang ở `go-son-mai-tranh` (nhóm tranh) dù là bình hoa. Các chất liệu resin/MDF/composite và cách gắn nhóm sơn mài cần xem lại theo mô tả nguồn, tránh suy luận từ tên thương hiệu. Chưa sửa taxonomy trong đợt ảnh này.
4. **Benchmark chưa bắt đầu:** cần tập truy vấn và nhãn do người kiểm tra, ảnh query độc lập khác phiên/nguồn với gallery, khóa split trước khi thử model. Không đưa ảnh tải này vừa làm gallery vừa làm test query.
5. **Tái nhập sản phẩm:** đã giải quyết việc mất ảnh khi importer chạy lại; importer hiện vẫn là quy trình dựng draft từ raw/editorial, chưa phải merge bảo toàn mọi chỉnh sửa review/published thủ công. Cần thiết kế trước khi vận hành biên tập nhiều người.
6. **Giới hạn frontend/runtime:** ví dụ tìm kiếm trang chủ vẫn thiên về fixture (Bát Tràng/khăn lụa), chưa bám 30 sản phẩm hiện có. Trường API `images_pending_rights` hiện tính ảnh thiếu file; sau khi tải file thì không phản ánh 45 ảnh còn unknown quyền. Khi làm luồng biên tập cần tách rõ trạng thái tải ảnh và quyền dùng ảnh.
7. **Kiểm thử môi trường:** chạy 10 worker E2E có một lần `ERR_NO_BUFFER_SPACE`; 2 worker qua 44/44. FastAPI TestClient cảnh báo deprecation httpx; không thay dependency trong đợt này.

## 4. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Baseline validate/fixture/backend/typecheck | `.venv/Scripts/python -X utf8 scripts/run_all_tests.py --skip-e2e` | Validate thật/fixture 0 lỗi; fixture khớp generator; backend 94 passed; typecheck đạt. Build bị sandbox chặn spawn EPERM ở lượt này. |
| Build độc lập ngoài sandbox | `npx.cmd vite build --outDir ../artifacts/build --emptyOutDir` trong frontend | Đạt, 27 modules. Gọi npx.ps1 trước đó bị Execution Policy; dùng npx.cmd không thay chính sách hệ thống. |
| E2E lượt đầu | `npx.cmd playwright test --reporter=line` | 43 passed, 1 failed: ERR_NO_BUFFER_SPACE; 10 workers. |
| E2E chạy lại | `npx.cmd playwright test --workers=2 --reporter=line` | **44 passed**, desktop + mobile, 14,9 s. Không sửa assertion để bỏ qua lỗi. |
| Nhập ảnh | `.venv/Scripts/python -X utf8 scripts/import_raw/apply_images.py` | 30 sản phẩm, 45 ảnh, 0 lỗi. |
| Nhập lại raw, chỉ kiểm tra | `.venv/Scripts/python -X utf8 scripts/import_raw/build_drafts.py --dry-run` | 30 draft, 37 nguồn, 0 lỗi/0 cảnh báo. |
| Validate sau ghép | `.venv/Scripts/python -X utf8 scripts/validate_catalog/validate.py` | **0 lỗi, 0 cảnh báo**, tạo báo cáo mới seed-001-images. |
| Audit dữ liệu thật | `.venv/Scripts/python -X utf8 scripts/validate_catalog/audit_images.py` | **30/30 detail có ảnh; 45/45 API ảnh HTTP 200, MIME image, SHA-256 khớp; reimport toàn bộ bằng DB hiện tại; apply ảnh lặp lại không đổi DB**. |
| Backend regression sau ghép ảnh | `.venv/Scripts/python -X utf8 -m pytest backend/tests -q -p no:cacheprovider` | **94 passed**, 1 cảnh báo deprecation httpx, 0 lỗi. |

Một smoke query `Marou Bến Tre 78%` trả đúng sản phẩm ở hạng 1 trên 30 draft thật. Đây là kiểm tra tích hợp một ca, không phải baseline chất lượng tìm kiếm. Không có số đo latency inference/model trong đợt này.

## 5. Tiến độ theo PLAN và bước tiếp theo

GĐ0 hoàn thành khung local. GĐ1 hoàn thành mốc 30 bản ghi draft và ảnh cho toàn bộ 30 bản ghi, chưa đạt mốc 300/review/quyền. GĐ2 có UI/API/keyword và regression đạt, còn baseline thật. GĐ3–GĐ7 chưa bắt đầu các đầu ra benchmark/model/integration theo kế hoạch.

Ưu tiên tiếp theo: review taxonomy và bằng chứng dữ liệu của 30 sản phẩm; bổ sung quyền dùng ảnh để published; mở rộng catalog có kiểm soát; xây bộ keyword benchmark và ảnh query độc lập; sau đó mới sàng lọc model voice/image và đo tài nguyên. Để xem kết quả ảnh ngay trong bản phát triển, bật `VNSTORE_INCLUDE_DRAFTS=1` trước khi khởi động backend.
