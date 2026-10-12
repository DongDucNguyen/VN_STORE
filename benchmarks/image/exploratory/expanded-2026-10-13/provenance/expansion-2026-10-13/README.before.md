# Bộ ảnh thử tìm kiếm VNStore

Ngày chuẩn bị: **13/10/2026**. Phạm vi ghi file: **chỉ `tmp_data/`**.

**Rà soát lại:** [Báo cáo chi tiết ngày 13/10](audit-2026-10-13/BAO_CAO_RASOAT.md). Có **44 file ảnh tổng cộng** = 40 ảnh test + 2 ảnh bị loại + 2 contact sheet. Đã đọc lại 40 URL nguồn và đối chiếu bytes. Bộ ảnh hợp lệ để bắt đầu thử thủ công, **chưa đủ để xác nhận chất lượng tìm kiếm**: 10 ảnh trùng gallery, chưa có nhãn relevance/độc lập/split; 3 ảnh nón và 2 ảnh cà phê không được mặc định là ca có đáp án trong catalog.

Mở **[index.html](index.html)** để xem ảnh theo nhóm, tên file và nguồn. Ảnh tải trực tiếp nằm trong **[images/](images/)**; chọn các file này ở trang `#/image` của VNStore.

## Bộ ảnh và mục đích

| Thư mục dưới `images/` | Số ảnh đã tải | Cách sử dụng |
|---|---:|---|
| `similar_candidate/` | 25 | 5 ảnh/nhóm: gốm sứ, mây tre/cói, dệt may, gỗ/sơn mài, thực phẩm; thử mẫu tương tự |
| `negative_candidate/ngoai-catalog/` | 5 | Laptop/bàn phím, xe đạp, bóng; quan sát kết quả ít liên quan |
| `gallery_control/` | 10 | 2 ảnh/nhóm từ chính URL gallery; kiểm tra luồng và tìm lại ảnh đã biết |

**40 ảnh dùng để test**, gồm 34 JPEG, 4 PNG, 2 WebP. Hai ảnh bị loại sau xem nội dung được giữ riêng ở `excluded/`, không nằm trong manifest hoặc danh sách ca thử. Số thực tế đã tải và kiểm tra được ghi tại [checks/validation.json](checks/validation.json). Manifest tải nằm ở [manifest.json](manifest.json), có URL trang/ảnh, thời điểm, kích thước, checksum và quyền được ghi nhận. Không đổi tên file theo đuôi nếu chưa đổi định dạng.

Kết quả bàn giao: **12,79 MiB** ảnh test; **40/40** giải mã và kiểm tra giới hạn API đạt; không trùng byte giữa các ảnh test. Đối chiếu 814 ảnh gallery xác nhận đúng **10 ảnh đối chứng trùng byte**, 30 ảnh còn lại không trùng byte gallery. Một cặp bao bì Marou có dHash gần nhau, được giữ để thử phân biệt biến thể. Có **50 ca thử** (40 ảnh thuần + 10 ảnh/chữ), chưa chạy inference.

Đối chiếu ngoài `tmp_data`: **28.565 tệp** giữ nguyên size/mtime, trong đó **2.745 tệp** được đối chiếu thêm SHA-256; không thêm/xóa/thay đổi tệp ngoài phạm vi. Hash catalog không đổi. Chi tiết giới hạn của phép đối chiếu nằm trong `checks/outside_comparison.json`.

Ảnh lấy từ Wikimedia Commons và URL nguồn chính thức được catalog tham chiếu (Minh Long, Vietcraft, Hanoia, Hanhsilk, Marou). Tác giả/giấy phép Commons được giữ theo metadata nguồn. Ảnh đối chứng giữ `usage_rights` như catalog, có thể vẫn `unknown`; việc tải nội bộ không tự tạo giấy phép công bố. Thông tin đầy đủ nằm ở từng ảnh trong manifest và hồ sơ API trong `evidence/`.

## Cách thử trên ứng dụng đang chạy

1. Vào trang **Tìm bằng ảnh** (`#/image`). Nếu báo chưa sẵn sàng, xem trạng thái model/index trong `#/diagnostics`; một file ảnh hợp lệ không làm model tự sẵn sàng.
2. Chọn ảnh ở `images/`. Bắt đầu bằng `gallery_control` để biết sản phẩm tham chiếu từ `expected_product_id` trong manifest, sau đó thử `similar_candidate`.
3. Tìm với toàn ảnh, ghi lại top 5/10. Với giỏ có trứng/nấm hoặc ảnh nhiều giỏ, kéo chọn đúng một giỏ rồi tìm lại. Đây là thử crop trong giao diện, không phải ảnh độc lập mới.
4. Thêm chữ theo [test_cases.json](test_cases.json): “dưới 500k”, “có quai, dưới 400k”, “không lấy màu đỏ”, “Marou”… Kiểm tra diễn giải và các bộ lọc thực sự được áp dụng; không mặc định mọi từ mô tả đều là bộ lọc cứng.
5. Thử ảnh bao bì: chocolate, cà phê và Marou. OCR chỉ có tác dụng nếu adapter/trọng số OCR đã được bật trong môi trường chạy; đợt chuẩn bị này không thay cấu hình.
6. Thử `negative_candidate`: ghi lại kết quả thiếu liên quan hoặc trả rỗng. Cấu hình mặc định chưa đặt ngưỡng cosine no-match, vì vậy trả kết quả không tự chứng minh lỗi API.
7. Đổi bộ lọc và chọn ảnh khác liên tiếp để quan sát luồng tương tác. Bộ ảnh này chưa kèm kết quả inference; ghi model, cấu hình, thời gian, top-k và nhận xét nếu tự chạy so sánh.

API nhận **body nhị phân ảnh**, không phải JSON/base64 hay form multipart. Endpoint backend là `POST /search/image?text=...`; qua Vite là `/api/search/image`. Trình duyệt thu nhỏ file thành JPEG tối đa 1024 px và bỏ metadata trước khi gửi, nên kết quả gửi nguyên file qua API có thể khác nhẹ.

## Giới hạn kết luận

- Nhóm `gallery_control` được tải lại từ Internet, trùng nguồn catalog; không dùng để đo chất lượng độc lập. Product ID chỉ là tham chiếu nguồn, không phải cam kết đứng hạng 1.
- Các ảnh Commons khác gallery theo nguồn tìm, nhưng chưa có người duyệt độc lập/identity/relevance/họ sản phẩm. Ảnh bảo tàng, sản phẩm nước ngoài hoặc ảnh cùng phiên chụp có thể không đại diện ảnh người dùng.
- `negative_candidate` là tình huống dự định kiểm tra, chưa phải nhãn no-match chính thức. Không tự gán điểm 0 cho toàn catalog.
- Không gán train/dev/test. `judgment` để null, `benchmark_approved=false`; không nhập vào `benchmarks/image/manifest.json` hay thay registry/split hiện hành.
- Kiểm tra SHA-256 phát hiện trùng bytes. dHash ≤ 6 chỉ gợi ý gần trùng, có thể báo nhầm trên nền trắng/hoa văn; khác hash không chứng minh độc lập.
- Bản tải Commons có thể là thumbnail 1280 px do nguồn cung cấp; giữ nguyên bytes tải về. Hash bản tải và URL bản gốc được ghi riêng. Contact sheet chỉ để xem nhanh, không phải ảnh query mới.

## Hồ sơ đi kèm

- [PHAN_TICH_DU_AN.md](PHAN_TICH_DU_AN.md): diễn giải đề bài, kiến trúc toàn hệ thống, trạng thái thực và lý do chọn bộ ảnh.
- [manifest.json](manifest.json): từng file, nguồn, quyền, hash, vai trò; không cùng schema benchmark chính thức.
- [test_cases.json](test_cases.json): ca ảnh thuần và 10 ca ảnh + tiếng Việt; chưa có đáp án chấm relevance.
- [checks/validation.json](checks/validation.json): Pillow decode, giới hạn API bằng `inspect_image`, hash, so trùng với 814 ảnh gallery.
- [checks/outside_comparison.json](checks/outside_comparison.json): đối chiếu file ngoài tmp_data trước/sau; phạm vi kiểm tra được ghi rõ.
- [preview/](preview/): contact sheet toàn bộ ảnh.
- [checks/visual_review.json](checks/visual_review.json): ghi nhận xem nội dung, ảnh khó/cần crop, các cặp cần giữ cùng nhóm nguồn nếu sau này làm benchmark.
- `candidates.json`, `selection.json`, `evidence/`: ứng viên, lựa chọn và metadata nguồn.
- `collect_images.py`, `verify_and_preview.py`: script tải/kiểm tra; ghi file được giới hạn trong tmp_data.

Để kiểm tra lại **offline**, từ gốc VNStore dùng môi trường đã có Pillow:

```powershell
.\.venv-ml\Scripts\python.exe -B -X utf8 tmp_data/verify_and_preview.py
```

Lệnh chỉ ghi preview/báo cáo trong tmp_data, đọc gallery để so sánh, không nạp model hoặc chạy máy chủ. Không cần chạy test/build toàn dự án cho tác vụ thêm dữ liệu này.

Tải tiếp các mục thất bại, nếu có (cần truy cập Internet):

```powershell
.\.venv-ml\Scripts\python.exe -B -X utf8 tmp_data/collect_images.py fetch
```

File đã có và đúng checksum được giữ lại. Không chạy lại `discover` sau khi đã chốt lựa chọn nếu muốn giữ nguyên mapping candidate ID.
