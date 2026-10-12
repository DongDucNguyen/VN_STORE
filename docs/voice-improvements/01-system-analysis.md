# Phân tích hệ thống

## Kiến trúc và phạm vi khảo sát

Đối chiếu PLAN, README, backlog, mã backend/frontend, pipeline ML, công cụ benchmark và bộ kiểm thử. Phạm vi triển khai tập trung luồng voice và các điểm giao với tìm kiếm chữ; không thay schema sản phẩm, dữ liệu catalog hoặc chỉ mục ảnh.

Snapshot xác minh: `seed-006-enriched`, 330 sản phẩm / 328 published / 814 ảnh / 23 danh mục; voice manifest 0 clip. Kiểm thử trước sửa: 603 backend, 22 Pillow, 120 E2E đạt ngoài sandbox. Vì vậy các con số seed-004/draft và 550/587 test trong một số tài liệu là lịch sử, không phải trạng thái hiện tại.

| Thành phần | Hiện trạng trong mã | Điểm cần lưu ý |
|---|---|---|
| Catalog | JSON có schema; snapshot có hash; reload nguyên khối; lọc published/draft | Tài liệu cũ còn ghi seed-004/draft trong khi DB hiện hành đã ở seed-006; lấy DB làm căn cứ |
| Tìm chữ | BM25 nhiều trường, nhánh có/không dấu, parser giá/phủ định, boost thuộc tính, bộ lọc cứng | Sửa transcript sai có thể đổi giá, vật liệu, phủ định và làm mất kết quả đúng |
| Voice API | WAV → energy gate → VAD → ASR → tìm chữ; 429 khi bận; lỗi riêng modality | VAD đang nằm ngoài semaphore; transcript bị gộp khoảng trắng; không có quality metadata hoặc gợi ý |
| ASR | 4 biến thể PhoWhisper ONNX; greedy; Silero VAD; model ghim revision | Prompt cố định vi; không có lựa chọn ngôn ngữ; giới hạn token chưa báo cắt câu |
| Giao diện voice | MediaRecorder → WAV mono 16 kHz; hủy request cũ, giới hạn thời lượng | Chuyển thẳng sang kết quả; chưa có bước xem bản gốc và chọn gợi ý trước tìm |
| Tìm ảnh | Model embedding, index ràng buộc snapshot, OCR/crop, RRF, cache | Không liên quan nguyên nhân voice; cần kiểm hồi quy vì dùng chung API/search |
| Thu và duyệt dữ liệu | Trang thu voice/ảnh, duyệt transcript, nhập ZIP và kiểm consent/split | Manifest voice/ảnh chưa có query thật; không đủ cơ sở tuyên bố chất lượng ASR tăng |
| Đánh giá | WER/CER, giá/phủ định, hallucination, retrieval, độ trễ, locked test | Chưa tách nhóm tiếng Anh/pha tiếng Anh, âm lượng, lỗi sửa đúng/sai |
| Vận hành | Python API và ML tách venv, Vite/React, ONNX CPU/GPU | PyTorch bị chính sách máy chặn; tiếp tục dùng ONNX sẵn có |

## Nguyên nhân và rủi ro

1. Nhầm n/l, dấu hoặc âm gần không thể xác nhận chỉ từ transcript. Catalog chỉ chứng minh cụm có tồn tại, không chứng minh người dùng đã nói cụm đó.
2. Thay từ đơn có thể phá cụm, tên riêng và ràng buộc. Chỉ sinh ứng viên cùng số âm tiết, giới hạn số thay đổi, bảo vệ tên/giá/phủ định; người dùng chọn mới áp dụng.
3. Ngưỡng năng lượng không phân biệt tiếng ồn với lời. Không hạ ngưỡng hoặc bật khuếch đại toàn bộ; giữ VAD, thêm cảnh báo âm nhỏ và thử tiền xử lý có giới hạn riêng.
4. Prompt vi có thể góp phần chép sai tiếng Anh. Cần bỏ ép vi khi người dùng chọn en/auto và giữ task transcribe. PhoWhisper đã fine-tune tiếng Việt nên lựa chọn ngôn ngữ chưa chứng minh nó giỏi tiếng Anh.
5. Kết quả kiểm thử fixture chỉ chứng minh hợp đồng kỹ thuật, không thay benchmark người nói thật.
