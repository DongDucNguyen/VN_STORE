# GĐ1 — Taxonomy, schema, nguồn dữ liệu — báo cáo ngày 09/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1 (PLAN.md mục 9, Tuần 1) |
| Trạng thái | 🟡 Một phần: hạ tầng dữ liệu xong; **chưa có sản phẩm thật nào** |
| Người thực hiện | Claude Code |
| Phiên bản catalog | `seed-000-taxonomy`, SHA-256 bắt đầu bằng `3f62fd9236a3c472` |

## 1. Mục tiêu

Điều kiện hoàn thành: `database.json` validate được; nguồn và ảnh hợp lệ; có báo cáo thiếu dữ liệu; 30 bản ghi thật rồi mở rộng lên 300.

## 2. Đã làm

- **`database.schema.json`** (JSON Schema 2020-12): mô tả đủ các collection và nhóm trường trong PLAN.md mục 3.2. Schema tự kiểm tra những quy tắc sau:
  - Giá phải là số dương hoặc `null`, không chấp nhận 0. Có giá thì phải có `price_source_id` và `observed_at`.
  - Claim nguồn gốc nhận ba giá trị `true` / `false` / `"unknown"`. Claim `true`/`false` phải có `source_ids` và `checked_at`.
  - Mỗi ảnh phải ghi `usage_rights.status`.
  - Bí danh của thương hiệu/nhà sản xuất phải có nguồn.
  - Địa danh giữ cả `name_as_sourced`, `name_normalized` và `historical_names`.
- **`backend/app/catalog/validation.py`**: kiểm tra những gì schema không làm được:
  - Trùng ID, slug, SKU hoặc ID ảnh.
  - Tham chiếu hỏng tới danh mục, thương hiệu, nhà sản xuất, nơi chốn, nguồn, hoặc SKU của ảnh.
  - Vòng lặp trong cây danh mục.
  - File ảnh bị thiếu hoặc lệch SHA-256.
  - Quy tắc `published`: có nguồn; có ảnh có file thật và rõ quyền; có ít nhất một tiêu chí Việt `true` có nguồn. Thiếu một trong ba là lỗi.
  - Sản phẩm draft thiếu ảnh chỉ bị cảnh báo, không bị coi là lỗi.
- **`scripts/validate_catalog/validate.py`**: CLI chạy validator, ghi báo cáo `reports/data_quality/<ngày>_<catalog_version>.{md,json}`. Báo cáo gồm số lượng, trạng thái, phân bố theo nhóm, tỷ lệ thiếu từng trường, ảnh trùng SHA-256. Có lỗi thì trả mã thoát 1.
- **`database.json` seed**:
  - Taxonomy 5 nhóm gốc, 22 danh mục (nhóm theo PLAN.md mục 2).
  - Từ điển tìm kiếm có ngữ cảnh: đồng nghĩa, cách gọi vùng miền (cốc/ly, bát/chén chỉ áp dụng trong danh mục bát đĩa, trà/chè), quan hệ rộng–hẹp (gốm → sứ/sành), và các cặp **dễ nhầm không được mở rộng** (mây/tre, mây/cói, lụa/lúa, sơn mài/gỗ sơn, dệt/thêu).
  - Đơn vị tiền, khối lượng và thể tích.
  - `brands`, `makers`, `places`, `sources`, `products` để trống, vì chưa có dữ liệu thật đã kiểm tra.
- **`docs/huong-dan-nhap-lieu.md`**: quy tắc nhập liệu, quy trình từng sản phẩm, điều kiện để được `published`, mẫu JSON trống.
- **Fixture kiểm thử** `backend/tests/fixtures/` gồm 13 sản phẩm, ảnh placeholder SVG, sinh bằng `make_fixture.py`. Đây là **dữ liệu giả có gắn nhãn rõ**: domain `example.invalid`, publisher "FIXTURE — dữ liệu giả", giao diện hiện banner cảnh báo. Fixture chỉ dùng cho test và thử giao diện, không được chép sang `database.json`.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Seed catalog hợp lệ | `.venv/Scripts/python scripts/validate_catalog/validate.py` | 0 lỗi, 0 cảnh báo; đã ghi `reports/data_quality/2026-10-09_seed-000-taxonomy.md` |
| Fixture hợp lệ | `... validate.py --catalog backend/tests/fixtures/catalog.fixture.json --no-report` | 0 lỗi, 0 cảnh báo |
| Validator bắt đúng lỗi | `pytest tests/test_validation.py` | 12 test đạt: trùng ID/SKU/slug/ảnh, tham chiếu hỏng, giá 0, giá thiếu nguồn, claim `true` thiếu nguồn, quy tắc published, vòng danh mục, báo cáo chất lượng |

## 4. Khác với kế hoạch

- Ảnh gắn với biến thể qua `variant_sku` thay vì `variant_id`, vì biến thể được định danh bằng SKU (đã là khóa duy nhất).
- Thêm `editor_note`, `origin_source_ids` (cho thương hiệu) và `archived_copy_path` (cho nguồn) để lưu căn cứ.

## 5. Chưa làm

- **Chưa có sản phẩm thật.** Mình đã thử lấy dữ liệu từ web: trang chính thức thử truy cập trả lỗi 404, còn kết quả tìm kiếm chủ yếu là trang danh bạ, không đủ làm nguồn. Mình cũng không xác nhận được quyền dùng ảnh. Theo nguyên tắc "không bịa" của PLAN.md, việc thu thập phải do người làm, có kiểm tra bằng mắt.
- Perceptual hash để phát hiện ảnh gần trùng: cần Pillow + imagehash, sẽ thêm khi có ảnh thật. Hiện chỉ phát hiện trùng theo SHA-256.
- Chưa có công cụ nhập liệu (form hoặc CSV → JSON). Hiện nhập trực tiếp JSON theo mẫu, sau đó chạy validator.

## 6. Rủi ro và việc đang chặn

- Chất lượng và tốc độ thu thập dữ liệu là phụ thuộc lớn nhất (PLAN.md mục 9). Nguồn thiếu ảnh hợp lệ có thể buộc điều chỉnh cơ cấu 5 nhóm × 60 sản phẩm.
- Quyền dùng ảnh: cần mẫu email/xin phép thống nhất trước khi liên hệ thương hiệu.

## 7. Bước tiếp theo

1. Nhóm dữ liệu nhập 30 sản phẩm thật (khoảng 6 mỗi nhóm) theo hướng dẫn, chạy validator, review chéo, rồi `published`.
2. Rà lại schema sau 30 bản ghi đầu và ghi các điều chỉnh vào báo cáo kế tiếp.
3. Mở rộng lên 300, theo dõi tỷ lệ thiếu dữ liệu trong `reports/data_quality/`.
