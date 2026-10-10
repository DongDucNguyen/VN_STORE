# Quy trình kiểm tra và phân xử nhãn keyword

Áp dụng cho packet catalog đầy đủ hiện tại. Đây là hướng dẫn thực hiện, chưa phải biên bản chấm nhãn.

## Trước khi chấm

1. Giữ cùng packet, catalog và rubric cho hai người. Chạy `audit_reviews.py` để kiểm tra hash và tập sản phẩm. Khi catalog đổi, tạo packet mới và đối chiếu lại nhãn; không chỉ sửa hash trong file cũ.
2. Chọn mã người chấm ổn định, không cần lưu thông tin cá nhân ngoài mã đó. Mỗi người dùng profile trình duyệt/nháp riêng; không xem điểm người kia trước khi xuất.
3. Đọc truy vấn đúng nguyên văn và kiểm tra thuộc tính có căn cứ trong catalog. Không suy luận xuất xứ/quyền/giá còn thiếu từ tên hoặc hình ảnh. Ghi các trường hợp thiếu dữ liệu để người phân xử quyết định.

## Rubric 0–3

| Điểm | Cách hiểu |
|---|---|
| 0 | Không liên quan hoặc rõ ràng không đáp ứng yêu cầu bắt buộc |
| 1 | Có liên quan nhưng thiếu căn cứ đáp ứng yêu cầu quan trọng hoặc chỉ gần với nhu cầu |
| 2 | Phù hợp với nhu cầu và các ràng buộc có căn cứ |
| 3 | Rất phù hợp, trực tiếp đáp ứng món/đặc tính người dùng tìm |

Điểm 2–3 được tính là có sản phẩm phù hợp. `has_answer=false` chỉ khi đã kiểm tra toàn bộ ứng viên và không có điểm >=2. Không giảm điểm vì sản phẩm xếp thấp trong BM25; trang chấm sắp thứ tự theo hash để tránh phụ thuộc thứ hạng.

Nếu truy vấn có giá tối đa nhưng sản phẩm chưa có giá, không tự suy ra đáp ứng ngân sách. Nếu truy vấn yêu cầu chất liệu/nguồn gốc mà trường đó chưa rõ, ghi nhận thiếu căn cứ thay vì tự xác minh từ ảnh. Người chấm cần thống nhất cách xử lý các trường hợp này trong rubric trước khi dùng kết quả để so model.

## Đối chiếu và phân xử

1. Lưu nguyên hai file export, chạy audit với hai `--review`. Giữ báo cáo có hash file đầu vào.
2. Người phân xử đọc từng cặp bất đồng cùng truy vấn, thuộc tính/nguồn và lý do của người chấm. Ưu tiên bất đồng đi qua ngưỡng 1↔2 vì làm đổi quyết định phù hợp.
3. Xử lý riêng bất đồng `group_id`: các paraphrase cùng ý định phải cùng nhóm và split. Không dùng kết quả model hoặc locked test để điều chỉnh nhóm nhằm làm điểm đẹp hơn.
4. Lưu quyết định trong một file nhãn mới; giữ nguyên hai bản gốc. Ghi biên bản mới trong `reports/benchmark/` với qid, product_id, hai điểm, điểm cuối, lý do, mã người phân xử, thời điểm và hash các file liên quan. Không tự động lấy điểm cao/thấp/trung bình.
5. Tính lại `has_answer` từ nhãn cuối; ghi người phân xử trong `labeled_by`, `reviewed_at` thực và hash catalog. Chạy audit một file trên kết quả cuối, rồi mới chạy evaluator.

Không có bất đồng không chứng minh hai người đã chấm độc lập hay nhãn luôn đúng. Báo cáo tỷ lệ đồng ý là thống kê mô tả, không phải điểm retrieval, khoảng tin cậy hay chứng nhận chất lượng benchmark.

## Trước khi gọi là baseline chính thức

- Có nhãn người thật và biên bản xử lý bất đồng của phần được chấm đôi.
- Catalog/split/rubric/cấu hình đo được khóa, không rò nhóm qua split.
- Ghi rõ độ phủ nhãn, quy mô query và số ca no-match. Seed 12 query chưa đại diện mục tiêu 600 query của PLAN.md.
- Chạy evaluator trên nhãn cuối; giữ `run.json`, per-query predictions và hash, không đổi nhãn theo kết quả test rồi tiếp tục gọi đó là test độc lập.
