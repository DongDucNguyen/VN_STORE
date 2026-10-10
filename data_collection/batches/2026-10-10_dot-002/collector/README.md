# tmp_data — 300 sản phẩm thật cho VNStore

Thu ngày **10/10/2026**, múi giờ **Asia/Saigon**. Toàn bộ công việc ghi file trong `tmp_data`; không nhập vào catalog chính. Phân tích yêu cầu nằm trong [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md).

## Mở ngay

- [review.html](review.html): duyệt offline 300 sản phẩm, tìm tên/SKU/chất liệu, lọc nhóm và nguồn, xem nhiều ảnh; không cần server hoặc Internet để xem ảnh.
- [catalog.json](catalog.json): catalog độc lập đúng schema 1.0.0 hiện có, đường dẫn ảnh tương đối từ thư mục này.
- [products.csv](products.csv): bảng tra cứu UTF-8 BOM, mở được bằng Excel.
- [QUALITY_REPORT.md](QUALITY_REPORT.md) và [quality_report.json](quality_report.json): kết quả kiểm tra.
- [product_evidence.json](product_evidence.json): URL, mã nguồn, thời điểm, trích đoạn căn cứ, quy tắc và file phản hồi của từng sản phẩm.
- [SESSION_REVIEW.md](SESSION_REVIEW.md): rà soát toàn bộ phiên, các sửa lỗi và phần chờ con người.
- [near_duplicate_review.html](near_duplicate_review.html): bảng ứng viên ảnh gần trùng để đối chiếu.

## Kết quả

**300 sản phẩm mới, 60 mỗi nhóm**: gốm sứ; mây tre/đan; dệt may/phụ kiện; gỗ/trang trí; thực phẩm đóng gói. **302 SKU/định danh biến thể**. Không trùng URL hoặc SKU với 30 sản phẩm tại thời điểm bắt đầu.

| Nguồn chính thức | Sản phẩm được chọn |
|---|---:|
| hanhsilk | 30 |
| hanoia | 64 |
| marou | 60 |
| minhlong | 60 |
| sensilk | 30 |
| vietcraft | 56 |

**769 ảnh gallery local**, giải mã được và có SHA-256; 223 sản phẩm có 2–4 ảnh, 77 có 1 ảnh. Tổng lượt URL ảnh trong manifest hiện tại: 802 tải được, 2 lỗi. Ảnh loại vẫn được giữ làm bằng chứng và không được tham chiếu trong gallery cuối. Không sinh ảnh AI hoặc thay nội dung ảnh.

**240 sản phẩm có giá VND**, 60 chưa rõ giá; 135 chưa nhập chất liệu. Thực phẩm không được tự gán thành phần khi chưa trích riêng. WooCommerce dạng variable có thể giữ giá null vì giá tối thiểu của nhóm không phải giá của một SKU xác định. Tình trạng hàng là snapshot của nguồn, không phải kho thời gian thực.

**Schema/tham chiếu/hash/file ảnh: ĐẠT**, 0 lỗi, 0 cảnh báo validator. Kiểm tra độc lập **5873 điều kiện** về record gốc, giá, SKU, ảnh, URL và liên kết offline đều đạt. **300/300 trang sản phẩm trả HTTP 200**, tên và canonical URL khớp. Logic tìm kiếm/lọc trang duyệt đã được chạy kiểm tra bằng Node (chưa kiểm thử render bằng browser). Hash `database.json` chính so với đầu phiên: **không đổi**.

## Trạng thái và giới hạn

- Tất cả **draft**, `reviewed_at=null`; tất cả quyền ảnh **unknown**. Cần người duyệt và giấy phép/đồng ý sử dụng ảnh trước khi công bố. Việc kiểm tra website không phải xác thực độc lập hàng hóa.
- Bộ này đếm **product record của website**, không khẳng định 300 họ sản phẩm độc lập. Bao gồm kích cỡ, mẫu màu và hộp quà khác nhau có record/SKU riêng. Phải gom họ trước khi chia benchmark.
- Gallery không phải ảnh query độc lập. Hash khác nhau không bảo đảm không gần trùng về hình ảnh. Đã chạy dHash 64 bit, ngưỡng khoảng cách ≤5: **904 cặp ứng viên** giữa các sản phẩm khác nhau; chưa xác nhận là ảnh trùng. Nền trắng, hình dáng/hộp quà tương tự có thể làm dHash gần nhau. Không tự xóa ảnh hoặc tạo nhãn benchmark từ phép đo này. Ảnh trùng SHA-256 với 45 ảnh catalog gốc: **0**.
- Nguồn tiếng Anh giữ tên chính thức ở aliases/raw. Một số tên Việt mới là mô tả biên tập ngắn cần người duyệt. Không tự gán làng nghề, chứng nhận, quốc gia thương hiệu từ tên, hoặc nguồn nguyên liệu từ ảnh.
- Chỉ kiểm tra thị giác sơ bộ ảnh đại diện qua 10 contact sheet, không thay review của con người; chưa đối chiếu bằng mắt toàn bộ ảnh phụ.
- Không chạy bộ test toàn dự án vì các lệnh mặc định ghi ra ngoài `tmp_data`. Mã validator được import chỉ đọc bằng Python `-B`.

## Hồ sơ

```text
raw/                       phản hồi HTTP gốc + .meta.json (URL, thời điểm, hash, headers)
product_pages/             300 trang chi tiết đã kiểm tra + metadata HTTP/hash
records/                   product record tách từ API/JSON-LD, có thể có ứng viên không chọn
images/                    ảnh tải nguyên bytes; gồm cả ảnh được giữ làm bằng chứng
review_sheets/             10 contact sheet ảnh đại diện cho đối chiếu sơ bộ
baseline/                  snapshot catalog/schema đầu phiên + hash đầu vào
errors/                    lỗi truy cập nguồn (ví dụ Kilomet109 403, URL 404)
catalog.json               nguồn sự thật cho 300 bản ghi staging cuối
product_evidence.json      ánh xạ record → raw → URL nguồn → claim
image_manifest.json        URL ảnh, thời điểm tải, format, kích thước, hash/lỗi
image_selection.json       quyết định loại ảnh trùng/lỗi khỏi gallery
shared_images.json         nhóm ảnh dùng chung phát hiện khi chọn gallery
excluded.json              lý do loại ứng viên được ghi nhận (không phải mọi record vượt quota)
integration_notes.json     mapping tham khảo cho lần nhập riêng, chưa áp dụng
CHECKSUMS.sha256           checksum các file bàn giao (không gồm bản thân file này)
```

## Tái kiểm tra và chạy lại

Từ thư mục gốc dự án, chỉ tạo/cập nhật đầu ra trong `tmp_data`:

```powershell
.venv-ml/Scripts/python.exe -B -X utf8 tmp_data/audit_and_export.py
.venv-ml/Scripts/python.exe -B -X utf8 tmp_data/final_verification.py
node tmp_data/check_review_ui.cjs
.venv-ml/Scripts/python.exe -B -X utf8 tmp_data/finish_handoff.py
```

`build_catalog.py` dựng lại catalog từ raw và xóa ánh xạ ảnh local trong catalog, nên sau đó phải chạy `download_images.py` (tái sử dụng manifest ảnh), rồi audit/export. Nếu tập sản phẩm/ảnh đổi, chạy lại `check_product_pages.py` và `check_near_duplicates.py` trước kiểm tra cuối. Collector giữ raw đã tồn tại; snapshot baseline được bảo vệ khỏi ghi đè. Khi thu đợt mới nên dùng một thư mục staging mới. Các file raw/record/ảnh của ứng viên cũ được giữ làm hồ sơ; chỉ `catalog.json` quyết định thành viên bộ bàn giao cuối.

## Bàn giao cho agent tích hợp

Đọc [integration_notes.json](integration_notes.json). **Không chép đè `database.json` bằng `catalog.json` này**: bộ staging chỉ gồm 300 sản phẩm mới và các entity cần thiết, không gồm 30 sản phẩm cũ. Việc ghép, ánh xạ brand, di chuyển ảnh, dựng index và đổi packet benchmark là công việc riêng, cần tuân theo pipeline nhập an toàn và phạm vi người dùng cho phép.
