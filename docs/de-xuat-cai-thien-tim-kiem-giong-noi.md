# Các điểm cần cải thiện cho tìm kiếm bằng giọng nói

**Trạng thái (12/10/2026):** Đã triển khai bước xem/sửa/xác nhận bản chép lời, gợi ý theo catalog, cảnh báo chất lượng âm và chọn ngôn ngữ theo request; xem [hồ sơ triển khai](voice-improvements/README.md). Chưa nghiệm thu chất lượng nhận dạng và tìm kiếm trên mẫu giọng nói VNStore đã được duyệt. Tăng âm/lọc âm vẫn tắt mặc định; nhận diện tự động chọn ngôn ngữ cho cả clip, chưa xử lý tin cậy câu pha Việt–Anh.

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

## 4. Cải thiện nhận dạng tiếng Anh và câu pha Việt–Anh

- Khi người dùng nói hoàn toàn bằng tiếng Anh hoặc xen tiếng Anh trong câu tiếng Việt, bản chép lời hiện còn lẫn từ của hai ngôn ngữ và chép sai từ tiếng Anh.
- Cải thiện nhận diện ngôn ngữ theo từng đoạn hoặc từng từ trong câu pha Việt–Anh; dùng âm thanh và ngữ cảnh để giữ đúng ngôn ngữ của mỗi từ.
- Ưu tiên nhận dạng chính xác tên thương hiệu, tên sản phẩm và thuật ngữ tiếng Anh có trong danh mục; không tự dịch hoặc sửa từ tiếng Anh thành từ khác khi không có căn cứ.

**Cần kiểm tra:** Dùng bộ câu tiếng Anh và Việt–Anh do người duyệt chép lời; đo riêng tỷ lệ chép sai từ tiếng Anh, tỷ lệ lẫn ngôn ngữ và chất lượng kết quả tìm kiếm của từng nhóm.

## 5. Tránh chép âm tiếng Anh thành từ tiếng Việt

- Có trường hợp người dùng phát âm một từ tiếng Anh nhưng hệ thống trả về từ tiếng Việt có âm gần giống, khiến truy vấn tìm kiếm sai ý định.
- Đối chiếu các cách hiểu tiếng Anh và tiếng Việt với âm thanh, ngữ cảnh câu và từ vựng sản phẩm trước khi chọn bản chép lời; giữ cách viết tiếng Anh nếu bằng chứng phù hợp hơn.
- Khi hai cách hiểu đều có khả năng đúng, cho người dùng xem và sửa bản chép lời trước khi tìm kiếm.

**Cần kiểm tra:** Lập bộ mẫu gồm các từ tiếng Anh dễ bị chép thành từ tiếng Việt gần âm; đo tỷ lệ chuyển sai ngôn ngữ và kiểm tra kết quả tìm kiếm sau khi sửa.

## 6. Cải thiện nhận dạng giọng miền Nam, miền Trung và miền Tây

- Bổ sung mẫu giọng nói thực tế từ người nói miền Nam, miền Trung và miền Tây, gồm cách phát âm, ngữ điệu và từ địa phương thường gặp khi tìm sản phẩm.
- Đánh giá và cải thiện nhận dạng theo từng nhóm giọng, tránh sửa từ đúng thành từ khác chỉ vì khác cách phát âm phổ thông.
- Kiểm tra cả câu thuần tiếng Việt và câu pha Việt–Anh ở từng nhóm giọng để tránh lỗi chồng lấp giữa giọng vùng miền và nhận diện ngôn ngữ.

**Cần kiểm tra:** Đo tỷ lệ chép sai và chất lượng kết quả tìm kiếm riêng cho từng nhóm giọng; so sánh trước và sau cải thiện trên cùng bộ mẫu đã được người duyệt chép lời.

## Nguyên tắc khi triển khai

Mọi chỉnh sửa bản chép lời cần có căn cứ từ âm thanh và ngữ cảnh, giữ được bản gốc để đối chiếu, và đánh giá trên dữ liệu người dùng đã được phép sử dụng. Chỉ đưa thay đổi vào luồng mặc định sau khi xác nhận nó cải thiện kết quả tìm kiếm mà không làm tăng lỗi sửa sai.
