# Hướng dẫn nhập liệu catalog

Dành cho người thu thập và nhập sản phẩm vào `database.json`. Quy tắc gốc ở PLAN.md mục 2–3.

## Nguyên tắc

1. **Không bịa.** Không tự đặt giá, đánh giá, tồn kho, chứng nhận hay xuất xứ. Thiếu giá thì `price_vnd: null` (giao diện hiển thị "Liên hệ"); không dùng 0.
2. **Nguồn trước, dữ liệu sau.** Tạo bản ghi `sources` (URL, đơn vị phát hành, thời điểm truy cập) rồi mới nhập thông tin lấy từ nguồn đó.
3. **Tiêu chí Việt tách riêng.** Mỗi tiêu chí là một `origin_claims` với `value` là `true` / `false` / `"unknown"`. `unknown` ≠ `false`. Claim có giá trị `true` hoặc `false` bắt buộc có `source_ids` và `checked_at`.
   - `manufacturer_declared`: nhà sản xuất/bên bán tự công bố.
   - `source_checked`: đã đối chiếu tài liệu nguồn. **Không** có nghĩa là đã xác thực độc lập hàng hóa.
4. **Không suy luận.** Không suy ra "thương hiệu Việt" từ tên tiếng Việt, hay "thủ công" từ hình ảnh.
5. **Ảnh phải rõ quyền dùng.** `usage_rights.status` là `owned` (tự chụp), `licensed` hoặc `permission_granted` (có văn bản/email cho phép, ghi vào `note`/`source_id`). Ảnh `unknown` chỉ được nằm trong sản phẩm `draft`.
6. **Mô tả tự biên tập.** Viết ngắn dựa trên thuộc tính có nguồn; không chép dài mô tả của bên bán.
7. **Địa danh giữ tên gốc.** `name_as_sourced` giữ nguyên cách nguồn ghi; `name_normalized` dùng cho hiển thị và tìm kiếm; tên cũ đưa vào `historical_names`.

## Quy trình cho mỗi sản phẩm

1. Chọn nguồn (ưu tiên website chính thức của thương hiệu/nhà sản xuất, catalog nghệ nhân/HTX có quyền dùng, dữ liệu nhà cung cấp, ảnh tự chụp).
2. Lưu `sources` gồm URL, `retrieved_at`, `supports` (thuộc tính nguồn này xác nhận: `price`, `materials`, `made_in_vn`…). Nên lưu bản chụp trang vào `archived_copy_path`.
3. Tạo hoặc tái sử dụng `brands` / `makers` / `places`.
4. Lưu ảnh vào `assets/products/<product-id>/<image-id>.<ext>`, ghi `local_path` tương đối so với thư mục gốc dự án, dùng dấu `/`.
5. Nhập sản phẩm với `status: "draft"`.
6. Chạy `.venv/Scripts/python scripts/validate_catalog/validate.py`, sửa đến khi không còn lỗi.
7. Người thứ hai kiểm tra bằng mắt: ảnh khớp sản phẩm, claim khớp nguồn. Khi đạt thì đặt `reviewed_at` và chuyển sang `published`.

Nếu chạy lại importer sau khi đã chỉnh sửa DB, dùng baseline của lần nhập thành công gần nhất và xem diff trước. Xem [quy trình nhập lại an toàn](../data_collection/README.md#nhập-lại-dữ-liệu-và-giữ-chỉnh-sửa-biên-tập). Không sửa baseline để làm mất dấu xung đột; importer giữ riêng thay đổi thủ công và dữ liệu sinh từ nguồn.

## Điều kiện để một sản phẩm được `published` (validator kiểm tra)

- Có ít nhất một nguồn trong `source_ids`.
- Có ít nhất một ảnh có file thật và quyền dùng rõ ràng.
- Có ít nhất một tiêu chí Việt `value: true` kèm nguồn.
- Mọi tham chiếu (danh mục, thương hiệu, nơi chốn, nguồn, SKU) đều hợp lệ; ID, slug và SKU không trùng.

## Báo cáo điều kiện công bố

Chạy từ thư mục gốc:

```bash
.venv/Scripts/python scripts/validate_catalog/readiness.py
```

Lệnh tạo cặp Markdown/JSON có timestamp trong `reports/data_quality/`, kèm SHA-256 catalog và danh sách việc cần xử lý cho từng sản phẩm. Lệnh mô phỏng `published` trên bản sao; không sửa `database.json` hay quyền ảnh.

- `technical_ready`: đạt các kiểm tra kỹ thuật khi mô phỏng công bố, gồm file ảnh và quyền được ghi trong DB.
- `review_recorded`: đã có `reviewed_at`. Công cụ không xác nhận thay người duyệt.
- `passes_recorded_checks`: đạt kỹ thuật và đã ghi nhận review; vẫn cần quyết định biên tập trước khi đổi trạng thái.
- `editorial_gaps`: giá, chất liệu, thương hiệu, nhà sản xuất, số ảnh; đây là mục bổ sung, không phải tất cả đều chặn công bố.

File ảnh hợp lệ ở đây nghĩa là nằm trong thư mục catalog, đọc được, khác rỗng và khớp SHA-256 nếu có khai báo. Công cụ không giải mã định dạng, nhận diện nội dung hoặc xác minh giấy phép. Mọi ảnh gắn với sản phẩm `published` phải có quyền được chấp nhận; ảnh còn `unknown` cần xử lý quyền hoặc loại khỏi gallery trước khi công bố.

Mã thoát `0` nghĩa là catalog hiện tại hợp lệ; không đồng nghĩa có sản phẩm đủ điều kiện công bố. Catalog sai schema trả mã `1` và không đánh giá từng sản phẩm. Dùng `--catalog` và `--report-dir` để chọn đầu vào và thư mục báo cáo.

## Quy ước ID

Chữ thường không dấu, nối bằng gạch ngang: `p-binh-gom-men-lam-01`, `brand-ten-thuong-hieu`, `src-ten-nguon-yyyymmdd`, `place-lang-gom-bat-trang`.

## Mẫu sản phẩm tối thiểu

Toàn bộ giá trị dưới đây là **chỗ trống cần thay**, không phải dữ liệu thật.

```json
{
  "id": "p-<ten-san-pham>",
  "slug": "p-<ten-san-pham>",
  "name_vi": "<tên theo nguồn>",
  "status": "draft",
  "category_id": "<id danh mục trong database.json>",
  "brand_id": null,
  "maker_id": null,
  "short_description_vi": "<1–2 câu tự viết>",
  "materials": [],
  "colors": [],
  "variants": [
    { "sku": "<SKU theo nguồn>", "price_vnd": null, "price_source_id": null, "observed_at": null, "availability": "unknown" }
  ],
  "origin": { "brand_origin_country": null, "manufacturing_country": null, "material_origins": [], "place_ids": [], "craft_village_id": null },
  "origin_claims": [
    { "claim_type": "made_in_vn", "value": "unknown", "status": "unverified", "source_ids": [], "checked_at": null }
  ],
  "images": [],
  "source_ids": ["<src-id>"],
  "created_at": "2026-10-09T00:00:00+07:00",
  "updated_at": "2026-10-09T00:00:00+07:00",
  "reviewed_at": null
}
```

## Hạn ngạch đợt 1 (PLAN.md mục 2)

30 sản phẩm thật để kiểm chứng cấu trúc → 300 sản phẩm (khoảng 60 mỗi nhóm): gốm sứ; mây tre/cói; dệt may và phụ kiện truyền thống; đồ gỗ/sơn mài/trang trí; thực phẩm đóng gói/đặc sản. Mục tiêu 2–4 ảnh mỗi sản phẩm cho tập benchmark.
