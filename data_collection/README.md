# Thu thập dữ liệu sản phẩm

## Snapshot hiện tại — seed-003-dot-002 (10/10/2026)

**330 sản phẩm draft, 814 ảnh, 7 thương hiệu + 2 nhà sản xuất, 23 danh mục.** Đợt 002 thêm 300 sản phẩm từ 6 website chính thức (Minh Long, Hanoia, Marou, Vietcraft, Hanhsilk, SenSilk), 60 mỗi nhóm PLAN, do một collector riêng thu trong thư mục staging rồi nhập bằng `scripts/import_raw/import_staging.py` (chỉ thêm bản ghi mới qua `safe_import`). Hồ sơ nguồn, ánh xạ ID và sửa đổi: [batches/2026-10-10_dot-002/](batches/2026-10-10_dot-002/README.md). Báo cáo: [GĐ1 — nhập đợt 002](../reports/progress/2026-10-10_GD1_nhap-dot-002.md).

- 300 sản phẩm mới **không** nằm trong `raw/<site>.json` + `editorial.json`. Nguồn sự thật của chúng là `batches/2026-10-10_dot-002/catalog.staging.json` + `id_map.json`; `build_drafts.py` chỉ quản lý 30 sản phẩm đợt 001 và bỏ qua bản ghi ngoài batch (đã kiểm: `no_op`, 0 xung đột).
- Ảnh mới nằm ở `assets/products/<product-id>/img-<…>-<n>.<ext>`, giữ nguyên bytes gốc (277,7 MB). Quyền vẫn `unknown`.

## Snapshot trước — seed-002-taxonomy

Ngày 10/10/2026 đã thêm nhánh `go-son-mai-binh-lo` (Bình, lọ trang trí) và chuyển hai bình Mystery/Vita theo tên, chất liệu có trong `raw/hanoia.json`. Catalog có 23 danh mục, vẫn 30 draft/45 ảnh; không đổi giá, claim hay quyền ảnh.

**Baseline dùng cho lần nhập tiếp theo:** [baseline của run đã áp dụng](import_runs/2026-10-10_144329-548668_drafts/baseline.json). [Báo cáo thay đổi](../reports/progress/2026-10-10_GD1_taxonomy-va-snapshot.md) và [packet nhãn mới](../artifacts/keyword_review/2026-10-10_seed-002-taxonomy/index.html).

Importer nhận `categories` tùy chọn trong editorial và ghép theo ID với cùng chính sách xung đột như các collection khác. Danh mục không có trong editorial vẫn được giữ; baseline cũ chưa có collection categories vẫn đọc được. Không sửa raw/manifest lịch sử chỉ để đổi taxonomy.

## Cập nhật ảnh — 10/10/2026

Đã tải **52 ảnh ứng viên cho 30/30 sản phẩm**, chọn **45 ảnh** vào `database.json` (`seed-001-images`).
Loại khỏi catalog 6 ảnh thanh chocolate Marou dùng chung và 1 infographic Minh Long; vẫn giữ file và lý do trong manifest.
4 ảnh Hanoia được lấy bản lớn 1.200–3.000 px từ liên kết có trên trang, thay cho thumbnail 285 px.

- `assets/products/<product-id>/`: file ảnh tải từ nguồn, không tạo ảnh AI, không thay nền hay xóa watermark.
- `images/2026-10-10/manifest.json`: URL trang/ảnh, SKU, thời điểm, SHA-256, kích thước, kết quả đối chiếu và quyết định chọn/loại.
- `images/2026-10-10/pages/`: 24 trang HTML và 6 phản hồi API công khai của Kilomet109.
- `images/2026-10-10/database.before.json`: bản DB trước khi ghép ảnh.
- `../artifacts/image_review/2026-10-10/`: 5 contact sheet và `index.html` duyệt 45 ảnh được chọn.
- `../reports/data_quality/2026-10-10_image-audit.json`: kết quả kiểm tra file, API và tính ổn định khi nhập lại.

Browser không có kết nối trong phiên này; người dùng đã đồng ý chuyển sang công cụ web và tải HTTPS trực tiếp từ nguồn chính thức.
Kilomet109 trả 403 cho trang HTML khi tải trực tiếp; Store API công khai đối chiếu đủ tên, permalink, SKU và 16 URL ảnh. Lịch sử lỗi/retry được giữ trong manifest.

`editorial.json` trỏ tới manifest ảnh. `build_drafts.py` tự ghép lại các ảnh đã duyệt và giữ quyết định loại ảnh chung.
Không tự nâng trạng thái quyền ảnh: các sản phẩm vẫn `draft`, quyền vẫn `unknown`, `reviewed_at` của sản phẩm vẫn null vì đợt này chỉ đối chiếu ảnh.

```bash
.venv/Scripts/python scripts/import_raw/apply_images.py --dry-run
.venv/Scripts/python scripts/import_raw/build_drafts.py --dry-run
.venv/Scripts/python scripts/validate_catalog/audit_images.py
```

Để thu thập **đợt mới**, cài các thư viện tại `scripts/import_raw/requirements-images.txt`, chọn thư mục batch mới trong collector rồi chạy `collect_images.py`.
Các script thu thập từ chối ghi đè batch đã có/đã duyệt. Không chạy lại đợt cũ để thay bằng chứng.
Script `retry_official_images.py` là bước xử lý lỗi của đợt này, cũng từ chối sửa manifest đã duyệt.

## Cấu trúc

```text
data_collection/
  raw/<site>.json      dữ liệu thô đúng như nguồn (URL, thời điểm, trích dẫn căn cứ, URL ảnh)
  editorial.json       quyết định biên tập: tên tiếng Việt, danh mục, chất liệu, tiêu chí nguồn gốc kèm nguồn
scripts/import_raw/build_drafts.py   ghép raw + editorial → database.json (status draft)
scripts/import_raw/safe_import.py    merge ba phía, diff, backup và kiểm tra trước khi ghi
data_collection/import_runs/<run>/  catalog.before.json, catalog.proposed.json, baseline.json
reports/data_quality/*_import-*.json / .md   kết quả mỗi lần chạy
```

## Nhập lại dữ liệu và giữ chỉnh sửa biên tập

Importer hiện ghép ba phía: bản đã sinh ở lần nhập trước (**baseline**), DB hiện tại và dữ liệu mới từ raw/editorial/manifest.

- Nguồn không đổi: giữ chỉnh sửa trong DB, gồm review, quyền ảnh, chú thích và các trường biên tập khác.
- DB không đổi nhưng nguồn đổi: đề xuất cập nhật từ nguồn.
- Hai phía sửa khác nhau cùng một trường: ghi xung đột và không ghi DB.
- Mảng (ảnh, biến thể, claim…) được so sánh nguyên mảng; không ghép theo vị trí, không chuyển giấy phép từ ảnh này sang ảnh khác.
- Bản ghi không có trong batch mới được giữ nguyên; bản ghi đã xóa khỏi DB không tự xuất hiện lại nếu nguồn không đổi.
- Chặn cập nhật bản ghi sản phẩm đã review hoặc không còn `draft`, và chặn thay đổi nguồn/metadata được sản phẩm đó tham chiếu trực tiếp. Việc biên tập lại cần được xử lý có chủ đích.

Baseline khởi tạo của `seed-001-images` được giữ tại [baseline lịch sử](import_runs/2026-10-10_012920-036113_drafts/baseline.json); baseline hiện hành được dẫn ở đầu tài liệu. Baseline là đầu ra generator, không phải bản sao các chỉnh sửa thủ công. Không sửa baseline hoặc tự cập nhật checksum của nó.

Xem trước sau khi sửa `editorial.json` hoặc raw:

```bash
.venv/Scripts/python scripts/import_raw/build_drafts.py --dry-run --baseline data_collection/import_runs/2026-10-10_144329-548668_drafts/baseline.json --catalog-version seed-003-draft
```

Đọc báo cáo Markdown/JSON được in ra: `changes` có giá trị trước/sau, `conflicts` có giá trị baseline/DB/nguồn. Lệnh trả mã `1` khi có xung đột, validation lỗi hoặc ghi thất bại; mã `0` cho preview hợp lệ, no-op hoặc ghi thành công. `--dry-run` vẫn lưu báo cáo và bản xem trước nhưng không ghi catalog.

Khi diff đã đúng và không còn lỗi, bỏ `--dry-run` để áp dụng cùng đầu vào. Có thể chọn `--catalog` và `--editorial` khác mặc định. Importer yêu cầu `--catalog-version` mới khi nội dung DB thay đổi, so bytes DB ngay trước khi thay file và lưu bản trước trong thư mục run. Nếu có bất kỳ xung đột nào, toàn bộ lần nhập không được ghi.

Sau một lần áp dụng thành công, dùng `baseline.json` của **run mới đó** cho lần kế tiếp. Baseline có `eligible: true` chỉ khi run `applied` hoặc `no_op`; bản preview có thay đổi và run bị chặn không được dùng. Không có baseline thì importer chỉ chấp nhận bản ghi giống hệt hoặc thêm ID mới, không ghi đè bản ghi khác nội dung.

Giải quyết xung đột bằng cách đối chiếu nguồn, thống nhất lại DB và raw/editorial; chạy preview lại. Không có cờ `--force`. Bản `catalog.proposed.json` của run bị chặn chỉ dùng để xem, không dùng thay DB bằng tay.

`apply_images.py --dry-run` cũng lưu diff/backup. Nó giữ nguyên quyền, note, caption, thứ tự gallery và catalog version khi nhập lại; nếu ảnh local khác manifest hoặc manifest định loại ảnh đã local/đã ghi nhận quyền, lệnh báo xung đột. Khi thực sự thêm/cập nhật ảnh phải chỉ định `--catalog-version` mới.

Kiểm tra bytes trước khi ghi là kiểm tra thay đổi đồng thời, không khóa trình soạn thảo hay tạo giao dịch xuyên nhiều file. Tránh sửa DB trong khi importer đang ghi; nếu tiến trình bị ngắt, dùng snapshot và trạng thái run để đối chiếu trước khi chạy lại.

## Audit ảnh và API cho catalog hiện tại

```bash
.venv/Scripts/python scripts/validate_catalog/audit_images.py
```

Audit lấy số lượng từ DB, hỗ trợ catalog rỗng, hơn 100 sản phẩm và các trạng thái `draft`/`published`/`archived`. Kiểm tra hai chế độ API: chỉ published và có draft. Phân trang danh sách, kiểm tra chi tiết và từng endpoint ảnh, so bytes API với hash file. Ảnh của sản phẩm ẩn phải trả 404; file chưa tải/mất file được ghi riêng trong chất lượng dữ liệu.

Bật thêm kiểm tra raw/editorial, baseline và manifest cụ thể:

```bash
.venv/Scripts/python scripts/validate_catalog/audit_images.py --editorial data_collection/editorial.json --baseline data_collection/import_runs/2026-10-10_144329-548668_drafts/baseline.json --manifest data_collection/images/2026-10-10/manifest.json
```

`--manifest` lặp được cho nhiều batch và không phụ thuộc thứ tự sản phẩm. `--baseline` cần đi cùng `--editorial`. Nếu không truyền, các kiểm tra bổ sung được ghi là bỏ qua, không tự suy đoán đã đạt.

Dùng `--catalog` để chọn catalog khác, `--report-dir` để chọn thư mục báo cáo. `--review-out artifacts/image_review/<ten-moi>` tạo bảng ảnh HTML nội bộ và từ chối ghi đè thư mục đã có. [Bảng ảnh lần chạy mới nhất](../artifacts/image_review/2026-10-10_generic-audit/index.html) đã tải được cả 45 ảnh bằng Chrome headless.

Mỗi lượt tạo `reports/data_quality/<timestamp>_image-audit.json`, trả mã 1 khi validation/API/kiểm tra bổ sung lỗi. `passed` có thể đi kèm cảnh báo thiếu file của draft: xem `validation_issues` và `quality.image_files` trước khi kết luận ảnh đã đủ. `hash_verified_api_images` đếm ID ảnh duy nhất đã phục vụ và khớp hash qua hai chế độ; ảnh archived được kiểm tra file nhưng không nằm trong số phục vụ API.

Audit không sửa DB, không cấp quyền hay thay người đối chiếu ảnh; không đo latency server thật. Phần kiểm tra chạy offline bằng TestClient, tạm cấu hình API trong cùng tiến trình rồi khôi phục; không dùng song song với request khác trong cùng tiến trình Python.

## Đợt 001 (10/10/2026): 30 sản phẩm draft

Thu thập qua Chrome từ 5 website chính thức. Dữ liệu lấy từ endpoint có cấu trúc của chính website (Shopify/Haravan `/products`, WooCommerce Store API, JSON-LD), không đọc chữ từ ảnh chụp màn hình. Ảnh **chưa tải về**: chỉ lưu URL gốc, vì bản quyền ảnh thuộc thương hiệu.

Ký hiệu tiêu chí: TH = thương hiệu Việt, SX = sản xuất tại Việt Nam, NL = nguyên liệu Việt, TC = thủ công/truyền thống, LN = làng nghề. Mọi tiêu chí đều ở mức "nhà sản xuất công bố", chưa xác minh độc lập.

| # | Sản phẩm | Thương hiệu / NSX | Giá (VND) | Ảnh | Tiêu chí = true | Nguồn |
|---|---|---|---|---|---|---|
| 1 | Chén cơm 11 cm Jasmine – Thạch Vân | Minh Long | 63.720 | 1 | TH | [link](https://minhlong.com/products/chen-com-11-cm-jasmine-thach-van) |
| 2 | Bình hoa 30 cm Hồn Việt | Minh Long | 4.374.000 | 2 | TH | [link](https://minhlong.com/products/binh-hoa-30-cm-hoa-van-hon-viet) |
| 3 | Bình hoa 27 cm Sen Vàng | Minh Long | 2.559.600 | 2 | TH | [link](https://minhlong.com/products/binh-hoa-27-cm-men-ngoc-hoa-van-sen-vang) |
| 4 | Bộ trà 0.5 L Camellia – Chỉ Vàng | Minh Long | 874.800 | 3 | TH | [link](https://minhlong.com/products/bo-tra-0-5-l-camellia-chi-vang) |
| 5 | Ly sứ dưỡng sinh 0.48 L có nắp ống hút – Biển Xanh | Minh Long | 333.720 | 1 | TH | [link](https://minhlong.com/products/ly-su-duong-sinh-0-48-l-k1-nap-ong-hut-duong-sinh-bien-xanh) |
| 6 | Dĩa tròn 15 cm Jasmine Lys – Trắng Ngà | LY'S | 28.080 | 1 | **chưa có** | [link](https://minhlong.com/products/dia-tron-15-cm-hoa-van-trang-nga) |
| 7 | Giỏ tre đan tròn viền gỗ | Vietnam Handicraft Co., Ltd. | Liên hệ | 1 | SX | [link](https://vietcraft.vn/product/round-bamboo-woven-storage-basket-from-vietnam/) |
| 8 | Chụp đèn treo đan seagrass | Vietnam Handicraft Co., Ltd. | Liên hệ | 2 | SX | [link](https://vietcraft.vn/product/handwoven-seagrass-pendant-lampshade-made-in-vietnam/) |
| 9 | Túi lục bình đan tay đính vỏ sò | Vietnam Handicraft Co., Ltd. | Liên hệ | 1 | SX, NL | [link](https://vietcraft.vn/product/handcrafted-water-hyacinth-handbag-with-seashell-embellishments-from-vietnam/) |
| 10 | Giỏ mây đan hình bầu dục | Vietnam Handicraft Co., Ltd. | Liên hệ | 2 | **chưa có** | [link](https://vietcraft.vn/product/wholesale-hand-woven-oval-rattan-basket-natural-bulk-storage-supplier-vietnam/) |
| 11 | Giỏ đan seagrass | Vietnam Handicraft Co., Ltd. | Liên hệ | 1 | SX, NL | [link](https://vietcraft.vn/product/woven-seagrass-basket-from-vietnam/) |
| 12 | Khay mây đan tay | Vietnam Handicraft Co., Ltd. | Liên hệ | 1 | SX | [link](https://vietcraft.vn/product/woven-rattan-tray-handmade-in-vietnam/) |
| 13 | Bát gáo dừa phủ sơn vẽ tay | Vietnam Handicraft Co., Ltd. | Liên hệ | 1 | SX, TC | [link](https://vietcraft.vn/product/wholesale-hand-painted-lacquer-coconut-bowls-from-vietnam/) |
| 14 | Bát tre cuộn phủ sơn | Vietnam Handicraft Co., Ltd. | Liên hệ | 1 | SX | [link](https://vietcraft.vn/product/lacquer-spun-bamboo-bowl-made-in-vietnam/) |
| 15 | Sô-cô-la đen Bến Tre 78% Single Origin 80g | Marou | 140.000 | 2 | NL | [link](https://maisonmarou.com/products/ben-tre-78-single-origin-80g) |
| 16 | Sô-cô-la đen Tiền Giang 70% Single Origin 80g | Marou | 140.000 | 2 | NL | [link](https://maisonmarou.com/products/tien-giang-70-single-origin-80g) |
| 17 | Sô-cô-la đen Lâm Đồng 74% Single Origin 80g | Marou | 140.000 | 2 | NL | [link](https://maisonmarou.com/products/lam-dong-74-single-origin-80g) |
| 18 | Sô-cô-la đen 68% quất Mekong – Tiền Giang 80g | Marou | 170.000 | 2 | NL | [link](https://maisonmarou.com/products/mekong-kumquat-tien-giang-68-80g) |
| 19 | Sô-cô-la đen 100% Vietnam 60g | Marou | 170.000 | 2 | NL | [link](https://maisonmarou.com/products/vietnam-100-cacao-dark-chocolate-bar) |
| 20 | Sô-cô-la đen Bà Rịa 76% Single Origin 80g | Marou | 140.000 | 2 | NL | [link](https://maisonmarou.com/products/ba-ria-76-single-origin-chocolate-bar) |
| 21 | Bình hoa Mystery | Hanoia | 16.500.000 | 1 | TH, TC | [link](https://hanoia.com/binh-hoa-mystery-a18mt01.html) |
| 22 | Bình hoa Vita | Hanoia | 4.950.000 | 1 | TH | [link](https://hanoia.com/binh-hoa-vita-pc26vt01.html) |
| 23 | Hộp vuông Botanica size S | Hanoia | 5.500.000 | 1 | TH | [link](https://hanoia.com/hop-vuong-botanica-size-s-af26bt03.html) |
| 24 | Hộp đan tre Ethnic size S | Hanoia | 950.000 | 1 | TH | [link](https://hanoia.com/hop-dan-tre-ethnic-size-s-ou17et02.html) |
| 25 | Áo khoác Phi vải gai dầu nhuộm chàm | Kilomet109 | Liên hệ | 2 | SX, NL, TC | [link](https://www.kilomet109.com/shop/phieu-collection-2017-mans-phi-hemp-jacket/) |
| 26 | Áo sơ mi Thông cotton nhuộm tự nhiên | Kilomet109 | Liên hệ | 3 | SX, NL | [link](https://www.kilomet109.com/shop/phieu-collection-2017-mens-thong-batik-shirt/) |
| 27 | Váy dài Vân bằng lụa Vân | Kilomet109 | Liên hệ | 3 | SX, NL | [link](https://www.kilomet109.com/shop/mien-collection-2019-womans-van-dress/) |
| 28 | Chân váy Hà cotton batik nhuộm chàm | Kilomet109 | Liên hệ | 2 | SX, NL | [link](https://www.kilomet109.com/shop/phieu-collection-2017-ha-skirt/) |
| 29 | Áo khoác Vang I vải gai dầu nhuộm chàm | Kilomet109 | Liên hệ | 3 | SX, NL, TC | [link](https://www.kilomet109.com/shop/mien-collection-2019-mans-vang-1-jacket/) |
| 30 | Vòng cổ vải Xoắn | Kilomet109 | Liên hệ | 3 | SX, NL | [link](https://www.kilomet109.com/shop/phieu-collection-2017-womans-xoan-necklaces/) |

## Checklist cho người kiểm tra (trước khi chuyển `published`)

1. Mở link nguồn và đối chiếu tên, SKU, giá, chất liệu. Giá có thể đã thay đổi sau ngày 10/10/2026.
2. Đọc lại từng trích dẫn căn cứ trong `raw/<site>.json` và từng tiêu chí trong `editorial.json`. Có thể nâng hoặc hạ `value`/`status`, nhưng phải ghi lý do.
3. **Ảnh**: file, `local_path` và `sha256` đã có từ đợt đối chiếu ảnh 10/10/2026. Trước khi published, bổ sung bằng chứng quyền sử dụng từ thương hiệu hoặc thay bằng ảnh tự chụp rồi cập nhật `usage_rights.status` đúng thực tế.
4. Đặt `reviewed_at`, đổi `status` sang `published`, chạy validator.

## Câu hỏi mở cần người quyết định

- **Minh Long, Hanoia**: trang sản phẩm không ghi nơi sản xuất nên SX = unknown. Cần tài liệu nhà sản xuất hoặc nhãn sản phẩm.
- **Marou**: trang ghi "Vietnam's first bean-to-bar chocolate maker… crafted entirely in our factory" nhưng không nêu địa chỉ nhà máy, nên SX và TH để unknown.
- **Kilomet109**: TH = unknown (trang không tự nhận là thương hiệu Việt). Giá niêm yết bằng USD (165–475 USD) nên catalog để "Liên hệ".
- **vietcraft.vn**: site bán sỉ, không có giá. Công ty vừa sản xuất vừa thu mua từ mạng lưới làng nghề, nên chưa biết làng nghề cụ thể. "Seagrass" giữ nguyên tiếng Anh vì chưa xác minh tương ứng là cói hay cỏ biển. "Lacquer" chưa chắc là sơn mài (sơn ta).
- **Hanoia**: nhiều sản phẩm làm bằng resin/MDF/composite. Chỉ bình Mystery ghi rõ "nền sơn mài".
- **Chưa có tiêu chí Việt nào = true** (chưa đủ điều kiện vào catalog theo PLAN.md mục 2): #6 Dĩa LY'S, #10 Giỏ mây bầu dục.
- **Ảnh dùng chung**: ảnh bao bì `80g_bar_front_Bk_shadow_new.jpg` lặp ở 6 sản phẩm Marou. Không dùng làm ảnh đại diện hay đưa vào benchmark ảnh.
- **Chưa thu thập được**: Trung Nguyên Legend (extension trình duyệt không được phép chạy script trên domain này); bamboovietnam.com (catalog chỉ có mã, không có thông tin).
