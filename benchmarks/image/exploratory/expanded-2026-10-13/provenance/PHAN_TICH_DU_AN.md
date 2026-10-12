# Phân tích trước khi thu ảnh — 13/10/2026

## 1. Diễn giải yêu cầu và ranh giới

Người dùng cần một thư mục `tmp_data` chứa ảnh **tải thực từ Internet** để thử tìm kiếm bằng ảnh trong VNStore. Cần hiểu dự án trước khi chọn ảnh. Đây là tác vụ chuẩn bị dữ liệu thử, không phải sửa ứng dụng, nhập catalog, huấn luyện hoặc nghiệm thu model.

Chỉ ghi bên trong `tmp_data`. Ngoài thư mục này chỉ đọc. Không chạy importer, build frontend, pytest mặc định, server có tự dựng index hoặc downloader model vì chúng có thể sinh file/cache ngoài phạm vi. Python chạy với `-B`; dùng Pillow đã có, không cài dependency. Không sửa `.gitignore`, `PLAN.md`, báo cáo tiến độ, database, benchmark, nhãn, split hoặc gallery. Công cụ ghi file kiểm tra đường dẫn sau `resolve()` phải nằm trong `tmp_data`.

## 2. Toàn cảnh dự án và bằng chứng đã đọc

Đối chiếu `PLAN.md`, `README.md`, hai báo cáo GĐ5–6 ngày 13/10 đang mở trong IDE, backlog, tài liệu nhập liệu, hướng dẫn GĐ5/GĐ6, benchmark ảnh/split; khảo sát cấu trúc mã nguồn, kiểm thử, frontend và script. Đọc trực tiếp catalog, mã API, media, snapshot, pipeline/index ảnh, adapter ONNX, cấu hình và các đoạn fusion tìm kiếm, giao diện tìm ảnh. Đây là rà soát kiến trúc và các đường đi liên quan, không phải kiểm chứng từng dòng của mọi tệp hay chạy lại toàn bộ dự án.

| Thành phần | Vai trò hiện tại | Ý nghĩa đối với bộ ảnh thử |
|---|---|---|
| `database.json` và schema | Catalog là nguồn sự thật; snapshot được validate, ảnh/nguồn/thuộc tính gắn product ID | Chọn nhóm ảnh dựa trên dữ liệu thực, không suy nguồn gốc/SKU từ hình |
| `data_collection/`, `assets/products/` | Nguồn thu thập, importer, lịch sử và gallery hiện hành | Chỉ đọc URL và hash; tải lại qua mạng vào tmp_data, không chép/sửa gallery |
| `backend/app/catalog/` | Snapshot, kiểm tham chiếu, hiển thị và quyền công bố | Mặc định tìm trên published; không đưa draft thành đáp án chắc chắn |
| `backend/app/search/` | Chuẩn hóa Việt/không dấu, BM25, từ điển, giá/phủ định, semantic tùy chọn | Ảnh + text dùng cùng cơ chế lọc; có thể hết đáp án do giá/chất liệu |
| `backend/app/voice/`, `ml/asr.py` | ASR/VAD, gợi ý, người dùng sửa và xác nhận transcript | Là luồng riêng dùng chung search; không cần audio cho tác vụ hiện tại |
| `backend/app/image/`, `ml/image.py` | Crop, embedding ONNX, cosine, gộp nhiều ảnh theo sản phẩm | Cần ảnh vật thể rõ và ảnh có nền/nhiều vật thể; tách đối chứng gallery |
| `backend/app/main.py`, `modalities.py`, `media.py` | API, model readiness, kiểm upload và giới hạn đồng thời | File tải phải giải mã được và đạt giới hạn JPEG/PNG/WebP |
| `frontend/` | React/TypeScript/Vite; browse, chi tiết, favorites, chữ/voice/ảnh, diagnostics, thu/duyệt mẫu | Bộ ảnh dùng trực tiếp qua `#/image`; xem cả ảnh rồi thử chọn vùng |
| `scripts/benchmark/`, `benchmarks/` | Thu/duyệt, dedup, registry họ, split, evaluator, no-match, locked test | Bộ tmp chỉ là exploratory/smoke, không tự đặt review/split hay công bố metric |
| `experiments/`, `artifacts/`, `reports/` | Cấu hình ứng viên, index/model/kết quả dẫn xuất, báo cáo lịch sử | Không tải model, chạy benchmark hoặc thay cấu hình/index trong đợt này |

Phạm vi sản phẩm: website demo khám phá sản phẩm Việt, tìm chữ/giọng nói/ảnh, có danh mục/thương hiệu/nguồn gốc; không phải hệ thống thanh toán, kho hay tài khoản marketplace.

## 3. Hiện trạng xác nhận bằng dữ liệu và mã

- Catalog: `seed-006-enriched`, SHA-256 `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`; 330 sản phẩm, 328 published, 2 draft; 814 ảnh, 23 danh mục.
- Số published theo nhóm gốc: gốm sứ 65; mây tre/cói 66; dệt may 66; gỗ/sơn mài/trang trí 65; thực phẩm 66. Có danh mục trong taxonomy không đồng nghĩa đang có đủ sản phẩm/ảnh thuộc loại đó.
- Manifest ảnh chính thức đang có `samples: []`; hash catalog đã khớp seed-006. Một số đoạn README/hướng dẫn vẫn mô tả snapshot cũ seed-004 hoặc 0 published: dùng JSON hiện hành để xác định trạng thái.
- Luồng ảnh thực: UI giải mã/chỉnh EXIF → người dùng crop → JPEG tối đa 1024 px, bỏ metadata → POST `/search/image` bằng body nhị phân → embedding → cosine, gộp ảnh cùng product → RRF với chữ/OCR → hard filter → trả “mẫu tương tự”. Qua Vite, đường API là `/api/search/image`.
- UI nhận file tối đa 20 MiB. API nhận JPEG/PNG/WebP, tối đa 8 MiB, ít nhất 32 px mỗi chiều và tối đa 40 triệu pixel. Bộ tải được chọn để bản thân file cũng vừa giới hạn API.
- Có SigLIP2, DINOv2, OpenCLIP chạy ONNX; không suy model đang bật từ việc có class trong mã. Index phải khớp catalog/model/hash; thiếu hoặc cũ thì ảnh có thể trả 503. Mỗi modality một lượt, có thể nhận 429 khi gọi đồng thời.
- OCR là tùy chọn và trọng số mặc định 0; `image_min_similarity=null` mặc định. Vì vậy ảnh ngoài catalog vẫn có thể trả top tương tự. Không đặt yêu cầu “mọi ảnh âm tính đều phải trả rỗng” cho cấu hình mặc định.
- Cache query ảnh/OCR chỉ trong bộ nhớ, có TTL, dùng khi đổi bộ lọc với `reuse`; bấm tìm mới chạy đầy đủ. Không khởi động server để thử trong phạm vi tác vụ này.
- Báo cáo mới nhất ghi 735 backend, 22 Pillow, 140 E2E đạt. Đây là kết quả lịch sử của kiểm thử phần mềm, không phải kết quả vừa chạy và không chứng minh chất lượng tìm ảnh.

## 4. Thiết kế bộ dữ liệu

Mục tiêu bộ nhỏ khoảng 40 file, dễ tải và xem thủ công:

1. Khoảng 25 ảnh nguồn ngoài gallery, phủ 5 nhóm. Ưu tiên ảnh có thông tin tác giả/giấy phép từ Wikimedia Commons. Đây là ứng viên tìm tương tự; không gán SKU/nhãn liên quan chưa được chấm.
2. Khoảng 5 ảnh đồ vật ngoài phạm vi catalog (máy tính, xe đạp, bóng) để quan sát false positive. Ghi `negative_candidate`, không tự tạo ground truth no-match.
3. Khoảng 10 ảnh từ URL chính thức đang được catalog tham chiếu, hai ảnh mỗi nhóm, tải lại qua mạng. Ghi `gallery_control`, product ID tham chiếu và quyền ảnh như catalog; chỉ kiểm tra smoke. Ảnh này có thể trùng byte hoặc cùng nguồn gallery, tuyệt đối không gọi là query độc lập.

Không tạo ảnh AI/augment để giả làm ảnh chụp độc lập. Không cố đủ số bằng ảnh sai chủ đề. Chọn thủ công từ kết quả tìm, xem contact sheet sau tải và kiểm định dạng/hash. Số lượng thực tế và lỗi tải được ghi tại `manifest.json` và `checks/validation.json`.

Mỗi file lưu URL trang nguồn, URL ảnh gốc và bản thực tải, thời điểm, tác giả/giấy phép nếu nguồn cung cấp, format, kích thước, byte, SHA-256, vai trò, nhóm và nguồn gốc. Thumbnail từ Wikimedia vẫn thuộc cùng ảnh gốc; hash byte bản tải không được trình bày như hash bản gốc độ phân giải đầy đủ. Không tự xác nhận độc lập chỉ vì khác SHA-256; kiểm tra perceptual hash chỉ là cảnh báo gần trùng.

Ảnh nước ngoài có thể dùng để thử tương tự về hình dáng, nhưng không chứng minh món đồ là sản phẩm Việt, đúng vật liệu hoặc đúng hãng. Ảnh bảo tàng có domain khác ảnh khách hàng; kết quả trên bộ này chỉ giúp phát hiện lỗi ban đầu.

## 5. Tiêu chí hoàn thành

- Ảnh tồn tại cục bộ trong tmp_data, có thể mở, không phải HTML đổi đuôi.
- Mỗi ảnh đạt giới hạn upload; manifest giữ đúng hash và nguồn; phát hiện trùng nội bộ/gallery theo bytes và cảnh báo gần trùng.
- Có trang HTML offline xem ảnh và nguồn, danh sách ca ảnh + tiếng Việt, hướng dẫn dùng `#/image`.
- Có đối chiếu bên ngoài tmp_data trước/sau: metadata mọi tệp thông thường, hash nội dung mã/tài liệu/catalog/dữ liệu, không băm lại các model/dependency nhiều GB.
- Không nhập bộ này vào benchmark chính thức. Muốn nghiệm thu theo PLAN vẫn cần query độc lập, duyệt relevance/identity/họ, quyền, nhóm nguồn/phiên và split khóa; không thể hoàn tất chỉ bằng tải ảnh Internet.
