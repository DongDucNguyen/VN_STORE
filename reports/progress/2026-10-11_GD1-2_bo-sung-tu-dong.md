# GĐ1–2 — Tự động bổ sung dữ liệu catalog và mở rộng truy vấn lên 600 — báo cáo ngày 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1 (chất lượng catalog), GĐ2 (bộ truy vấn PLAN §8.1: 600 câu, baseline) |
| Trạng thái | ✅ Đã làm những gì có căn cứ; phần không có nguồn (giá Vietcraft/Kilomet109, căn cứ Việt Nam của 2 draft, nhãn test) để lại có ghi lý do |
| Người thực hiện | Claude, theo yêu cầu "tự động bổ sung" của chủ dự án |
| Catalog | `seed-005-published-internal-demo` (`820f35b0…`) → **`seed-006-enriched` (`b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`)** |
| Commit | Chưa commit |

## 1. Bổ sung catalog từ trang nguồn đã lưu

`scripts/import_raw/enrich_from_archive.py`:
- đọc **bản lưu 300 trang sản phẩm** của đợt 002 (`product_pages.zip`) và bản ghi tách từ API/JSON-LD; chạy offline;
- **chỉ điền trường đang trống**, không sửa giá trị đã có, không đụng giá;
- mỗi sản phẩm được thêm một dòng `editor_note` ghi trường, giá trị và căn cứ, kèm cụm "(chưa người duyệt lại)";
- ghi qua `execute_import`: dry-run trước, có diff, kiểm tra hash, chặn khi validate lỗi;
- file căn cứ từng trường: [`…_import-enrich-evidence.json`](../data_quality/2026-10-11_151042-479047_import-enrich-evidence.json).

| Trường (328 sản phẩm published) | Trước | Sau | Căn cứ |
|---|---:|---:|---|
| Thiếu chất liệu | 128 | **6** | Minh Long 60: "sứ" theo trang chủ nguồn ("gốm sứ Minh Long"), trang sản phẩm không ghi. Marou 60: "cacao" vì tên nguồn là sô cô la. Vietcraft/Hanhsilk: "Material: …" trên trang hoặc tên |
| Thiếu màu | 253 | **195** | "Màu sắc: …" (SenSilk, Hanhsilk), "Color: …" (Vietcraft), màu tường minh trong tên nguồn Minh Long ("Trắng Ngà", "Màu Cam", "nền xanh ngọc"). Loại "Hoa Hồng" (tên hoa) |
| Thiếu giá | 73 | 73 | **Không bổ sung**: Vietcraft bán sỉ, không niêm yết; Kilomet109 niêm yết USD (đã quyết để "Liên hệ"); 4 sản phẩm Hanhsilk không có giá trên trang |

Màu còn thiếu chủ yếu ở 66 sản phẩm sô cô la Marou (màu bao bì không có nghĩa) và đồ mây tre Vietcraft không ghi màu.

**2 sản phẩm draft giữ nguyên**: Dĩa Jasmine Lys và Giỏ mây bầu dục VH24040.
- Trang thương hiệu LY'S không nêu quốc gia; mô tả VH24040 không ghi nơi sản xuất.
- Người biên tập trước đã ghi rõ quyết định "unknown" cho cả hai; suy "Việt Nam" từ công ty mẹ hay chữ "Supplier Vietnam" là đoán.

## 2. Hệ quả của việc đổi catalog (đã xử lý)

- **Dựng lại:** chỉ mục ảnh SigLIP2/DINOv2; `proposal.json` (nội dung họ giữ nguyên); trang duyệt họ `seed-006` (+ `_assisted`, nạp được nháp cũ); packet keyword `seed-006` (+ `_assisted`); gợi ý máy; nhãn máy; manifest ảnh query (0 mẫu, chỉ gắn lại hash). API khởi động lại.
- **Pool keyword thêm 57 cặp chưa chấm**, phần lớn đĩa Minh Long giờ khớp "sứ" và sản phẩm ngẫu nhiên chọn lại. Đã chấm bổ sung theo product_id (`EXTRA_BY_ID`); builder chặn nếu điểm bổ sung mâu thuẫn điểm cũ. Chính sách P1 không đổi vì chất liệu "sứ" mới điền cùng căn cứ cấp thương hiệu mà P1 đã xét.
- **Baseline 119 câu cũ:** Success@5 0,953 → **0,943**. Truy vấn mới trượt: "đầm lụa đen" ra **chụp đèn mây màu đen** và **bình "Đầm Sen"**. Màu "đen" mới điền làm tăng khớp, còn "đầm" chưa được hiểu là "váy". Ghi cho GĐ5.

## 3. Mở rộng bộ truy vấn keyword lên 600

`benchmarks/keyword/expansion/claude_criteria_v1.py`: 481 câu mới trong 232 nhóm ý định.
- Phủ gốm sứ, sơn mài, sô cô la, mây tre, lụa, thời trang.
- Đủ kiểu truy vấn: món cụ thể, thuộc tính, không dấu, vùng miền, lỗi gõ, xen tiếng Anh, giá, phủ định, nhu cầu, thương hiệu, không có đáp án.
- Câu diễn đạt lại của cùng ý định nằm cùng split. Cắt theo quy tắc cố định ghi trong file để đạt đúng cỡ.

| Split | Câu | Nguồn | Nhãn |
|---|---:|---|---|
| train | 300 | mới | máy, theo tiêu chí, phủ **toàn catalog** |
| dev | 180 | 119 cũ + 61 mới | máy (gợi ý cũ + tiêu chí) |
| test | 120 | mới | **không có nhãn**: locked test cần người chấm |

`scripts/benchmark/criteria_labels.py` chấm toàn bộ 330 sản phẩm theo tiêu chí của từng ý định: loại hàng, thương hiệu, chất liệu, màu, giá, phủ định, mong muốn phụ. Thang điểm theo `review_protocol.md`; lý do từng cặp lưu trong file.

Rà toàn bộ 232 nhóm phát hiện và đã sửa 3 lỗi hệ thống của bộ chấm:
- tên danh mục ("Bát, đĩa, chén ăn") làm đĩa khớp "chén";
- mô tả ("vườn dừa", "nhiệt độ cao") gây khớp nhầm;
- truy vấn chỉ nêu thuộc tính cho 1 điểm với hàng trăm sản phẩm không liên quan.

Sau khi sửa, loại hàng và đặc điểm bắt buộc chỉ so trên tên và alias.

Kiểm tra: 600 câu qua `validate_queries` (không trùng, không rò nhóm giữa split).

## 4. Baseline keyword với nhãn máy (BM25 mặc định, catalog seed-006)

| Split | Câu có đáp án | Success@5 | CI 95% (theo nhóm) | nDCG@10 | CI 95% | Không có hàng mà vẫn trả kết quả |
|---|---:|---:|---|---:|---|---:|
| dev 180 | 162 | **0,920** | [0,869; 0,963] | 0,839 | [0,796; 0,876] | 18/18 |
| train 300 | 270 | **0,859** | [0,810; 0,903] | 0,768 | [0,727; 0,809] | 29/30 |

Ngưỡng PLAN §8.4 (Success@5 ≥ 0,85) đạt trên cả hai split. Train sát ngưỡng và CI cắt ngưỡng, nên kết luận "đạt" trên train chưa chắc chắn.

Loại truy vấn yếu nhất:
- train: xen tiếng Anh 0,50, nhu cầu 0,58, lỗi gõ 0,80, thuộc tính 0,82;
- dev: đơn vị 0,75; vùng miền, thương hiệu và phủ định đều 0,83.

Run:
- `experiments/results/20261011-152050-453833_keyword_bm25-machine-dev-600`
- `experiments/results/20261011-152056-438267_keyword_bm25-machine-train-600`

## 5. Hạn chế

- **Toàn bộ nhãn train/dev do máy (Claude) đặt**, theo yêu cầu chủ dự án; chưa người nào xác nhận. Nhãn và BM25 cùng dựa trên chữ trong catalog nên điểm có thể lạc quan. Test 120 câu cần người chấm trước khi chạy locked test.
- **Dữ liệu bổ sung tự động chưa được người duyệt lại.** Chất liệu "sứ" cho Minh Long và "cacao" cho Marou là căn cứ cấp thương hiệu/tên, không phải từ thông số từng sản phẩm.
- Sản phẩm published bị sửa sau khi đã duyệt; `editor_note` ghi rõ điều này.
- Có thể dùng train để chỉnh hệ thống ở GĐ5, nhưng báo cải thiện phải trên dev, và kết luận cuối cùng trên test do người chấm.

## 6. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| `enrich_from_archive.py` dry-run rồi áp | 122 sản phẩm thêm chất liệu, 58 thêm màu; 0 lỗi, 0 xung đột |
| Validator catalog | 0 lỗi, 1 cảnh báo (chính sách demo nội bộ) |
| Test mới `test_catalog_enrich_and_criteria.py` | 14 đạt |
| Toàn dự án `run_all_tests.py` | **8/8 bước đạt: 603 backend (+2 skip), 22 Pillow, typecheck/build, 120 E2E** ([log](2026-10-11_GD1-2_bo-sung-full.log)) |
