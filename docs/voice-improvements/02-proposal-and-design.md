# Đối chiếu đề xuất và thiết kế

| Đề xuất | Triển khai | Giới hạn nghiệm thu |
|---|---|---|
| Nhầm n/l và gần âm | Sinh ứng viên từ cụm catalog, một âm tiết đổi trong cụm, không sửa thương hiệu/SKU/giá/phủ định | Đây là gợi ý theo văn bản; không gắn nhãn chắc chắn dựa trên âm thanh |
| Cụm có nghĩa | Ưu tiên cụm nhiều token trong tên/alias, danh mục, chất liệu; giữ bản gốc và truy vấn do người dùng xác nhận | Không chèn token/thuộc tính, không tự áp dụng gợi ý |
| Nói nhỏ | Đo mức tín hiệu, clipping; hướng dẫn ghi lại; gain giới hạn và lọc rumble tùy chọn sau VAD | Không bật gain/lọc mặc định; chưa có dev để hiệu chỉnh |
| Tiếng Anh/Việt–Anh | Chọn vi/en/auto theo request; auto dùng logits token ngôn ngữ của model, giữ transcribe; hiển thị kết quả để sửa | Chọn ngôn ngữ toàn clip không phải nhận diện chuyển ngôn ngữ từng từ; cần benchmark riêng |

## Hợp đồng và tương thích

- Giữ `/search/voice` cũ với bản chép lời và kết quả; thêm chế độ `review=true` chỉ nhận dạng, không truy hồi trước khi xác nhận.
- Giao diện dùng review; người dùng sửa/chọn gợi ý rồi mới gọi tìm chữ, lưu bản gốc cùng kết quả trong bộ nhớ ngắn hạn.
- Adapter cũ `transcribe(clip) -> str` vẫn dùng được. Adapter hỗ trợ metadata cung cấp phương thức riêng; lựa chọn ngôn ngữ không hỗ trợ phải báo rõ, không lặng lẽ bỏ qua.
- Chia sẻ xử lý âm thanh giữa API và evaluator để tránh đo một đường chạy nhưng demo dùng đường khác.
- Không lưu audio mới hoặc transcript vào đĩa trong request. Không tạo nhãn benchmark tự động.

## Cơ sở kỹ thuật

- [Whisper Transformers](https://huggingface.co/docs/transformers/en/model_doc/whisper): language token điều khiển ngôn ngữ; task transcribe khác translate.
- [Bài báo PhoWhisper](https://openreview.net/pdf?id=x3c3MkJfpG): model được fine-tune từ Whisper đa ngôn ngữ cho tiếng Việt nhiều vùng giọng. Điều này không bảo đảm chất lượng tiếng Anh sau fine-tune.

Các ngưỡng quality và luật gợi ý là heuristic có kiểm thử hồi quy; chưa được hiệu chỉnh trên dữ liệu VNStore đã duyệt.
