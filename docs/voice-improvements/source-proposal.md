# Các điểm cần cải thiện cho tìm kiếm bằng giọng nói

**Trạng thái:** Ghi nhận yêu cầu, chưa triển khai. Cần thu mẫu giọng nói và bản chép lời do người duyệt để đánh giá trước khi thay đổi luồng nhận dạng.

## 1. Sửa lỗi do phát âm không chuẩn hoặc nhầm âm

- Nhận diện các trường hợp dễ nhầm như **n/l**, cùng các cặp âm khác xuất hiện trong dữ liệu người dùng thực tế.
- Đề xuất từ đúng chính tả dựa trên âm thanh, ngữ cảnh câu và từ vựng sản phẩm; tránh thay hàng loạt chỉ vì hai từ gần âm.
- Giữ lại bản chép lời gốc và cho người dùng xem, sửa đề xuất trước khi tìm kiếm nếu hệ thống chưa đủ chắc chắn.

**Cần kiểm tra:** Cùng một ý định tìm kiếm, thử nhiều cách phát âm vùng miền và xác nhận hệ thống chọn đúng từ mà không làm sai tên riêng hoặc thương hiệu.

## 2. Trả về cụm từ có nghĩa, phù hợp ngữ cảnh sản phẩm

- Sau nhận dạng giọng nói, xét cả **cụm từ** thay vì sửa từng từ riêng lẻ. Ví dụ, khi người nói phát âm gần với “bát sứ”, ưu tiên cụm “bát sứ” nếu âm thanh và ngữ cảnh sản phẩm cùng ủng hộ, thay vì một cụm vô nghĩa.
- Kết hợp từ vựng danh mục, chất liệu và tên sản phẩm để xếp hạng các cách hiểu; không tự thêm chất liệu hoặc thuộc tính khi âm thanh không đủ căn cứ.
- Hiển thị cụm từ hệ thống dùng để tìm kiếm để người dùng có thể sửa ngay.

**Cần kiểm tra:** So sánh bản chép lời gốc, cụm từ được đề xuất và kết quả tìm kiếm trên các câu nói thật; ghi nhận cả trường hợp sửa đúng và sửa sai.

## 3. Giọng nói nhỏ dễ bị nhận dạng sai

- Kiểm tra mức âm lượng và chất lượng tín hiệu trước khi nhận dạng. Khi âm quá nhỏ, hướng dẫn người dùng nói gần micro hơn hoặc ghi âm lại.
- Thử tăng âm lượng có giới hạn và giảm nhiễu ở bước xử lý âm thanh; tránh khuếch đại nhiễu thành lời nói hoặc tạo từ không có trong bản ghi.
- Đánh giá riêng các mẫu nói nhỏ, nói xa micro và môi trường ồn để xác định mức cải thiện thực tế.

**Cần kiểm tra:** Đo tỷ lệ chép sai và tỷ lệ yêu cầu ghi âm lại theo từng mức âm lượng, đồng thời kiểm tra hệ thống không trả kết quả giả khi chỉ có tiếng ồn.

## 4. Nhận dạng tiếng Anh và câu pha tiếng Anh chưa đúng

- Hiện có trường hợp người dùng nói tiếng Anh nhưng kết quả thành từ tiếng Việt có âm gần giống, hoặc chép sai từ tiếng Anh.
- Bổ sung nhận diện ngôn ngữ hoặc hỗ trợ câu pha Việt–Anh, nhất là tên thương hiệu, tên sản phẩm và thuật ngữ phổ biến; giữ nguyên từ tiếng Anh khi phù hợp với âm thanh.
- Với trường hợp không chắc ngôn ngữ, hiển thị cách hiểu để người dùng chọn hoặc sửa, thay vì tự đổi sang tiếng Việt.

**Cần kiểm tra:** Dùng bộ câu tiếng Anh và Việt–Anh do người duyệt chép lời; đo lỗi nhận dạng và chất lượng kết quả tìm kiếm riêng cho từng nhóm.

## Nguyên tắc khi triển khai

Mọi chỉnh sửa bản chép lời cần có căn cứ từ âm thanh và ngữ cảnh, giữ được bản gốc để đối chiếu, và đánh giá trên dữ liệu người dùng đã được phép sử dụng. Chỉ đưa thay đổi vào luồng mặc định sau khi xác nhận nó cải thiện kết quả tìm kiếm mà không làm tăng lỗi sửa sai.
