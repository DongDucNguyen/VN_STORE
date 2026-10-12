# VNStore — Tổng quan tiến độ toàn dự án — 12/10/2026

## Kết luận hiện tại

VNStore đã có các luồng chính của demo: duyệt catalog, tìm bằng chữ, giọng nói và ảnh, cùng bộ công cụ thu dữ liệu, duyệt nhãn và đánh giá. Phần triển khai kỹ thuật đã tiến xa hơn phần nghiệm thu chất lượng. Điểm nghẽn chính là dữ liệu giọng nói/ảnh truy vấn thật và nhãn do người duyệt; chưa đủ căn cứ kết luận đạt toàn bộ PLAN.

Báo cáo đối chiếu trực tiếp `database.json`, hai manifest benchmark, thư mục families/splits, báo cáo các đợt và working tree. Số kiểm thử bên dưới là kết quả đã lưu ngày 12/10, không phải chạy lại trong lượt lập báo cáo này.

## Theo giai đoạn

| GĐ | Phạm vi | Trạng thái thực tế |
|---|---|---|
| 0 | Khởi tạo kiến trúc và môi trường | Hoàn thành: backend FastAPI, frontend React/TypeScript, môi trường API/ML và công cụ kiểm thử |
| 1 | Catalog, taxonomy, nguồn và ảnh | Đạt quy mô demo: 330 sản phẩm, 328 published nội bộ, 2 draft, 814 ảnh, 23 danh mục. Một số thuộc tính bổ sung tự động chưa được người duyệt lại; quyền ảnh chưa xác minh |
| 2 | Tìm kiếm chữ, UI/API, bộ lọc | Đã triển khai BM25, chuẩn hóa tiếng Việt, giá/phủ định và bộ lọc. Có 600 truy vấn và baseline nhãn máy được chấp nhận theo quyết định trước; chưa phải đánh giá độc lập bằng nhãn người |
| 3 | Thu dữ liệu, duyệt nhãn, khóa split | Công cụ đã có. Voice 0 clip; image 0 ảnh truy vấn. Chưa có families.json đã duyệt; split ảnh mới ở bản preview |
| 4 | Adapter và chọn model | Có 4 cấu hình PhoWhisper + Silero VAD; 3 adapter ảnh SigLIP2/DINOv2/OpenCLIP; công cụ sàng lọc chất lượng/chi phí. Model chạy được qua ONNX; chưa chọn chính thức trên dev VNStore đã duyệt |
| 5 | Tối ưu ngôn ngữ, audio, OCR, crop, fusion | Đã có cấu hình và công cụ ablation. Đợt 12/10 bổ sung gợi ý cụm, ngôn ngữ theo request và quality audio. Chưa chứng minh lợi ích trên dữ liệu thực; semantic/n-best/fine-tune còn mở |
| 6 | Tích hợp và nghiệm thu cuối | Luồng UI/API, hủy yêu cầu, diagnostics, review transcript, công cụ locked test đã có. Chưa chạy locked test hoặc ký nghiệm thu chất lượng cuối |
| 7 | Ca khó và hoàn thiện dự phòng | Chưa mở thành đợt riêng; cần kết quả phân tích lỗi thực tế để xác định phạm vi |

## Dữ liệu và chất lượng tìm kiếm

Catalog hiện hành `seed-006-enriched`, SHA-256 `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`.

| Chỉ số | Toàn catalog (330) | Sản phẩm published (328) |
|---|---:|---:|
| Thiếu chất liệu | 6 | 6 |
| Thiếu màu | 196 | 195 |
| Thiếu giá | 74 | 73 |

Chế độ công bố là `internal_demo`, cho phép ảnh chưa xác minh quyền. Trạng thái published hiện tại không tương đương sẵn sàng công bố công khai. Không tự điền giá hoặc thuộc tính thiếu khi không có căn cứ.

Keyword có train 300 / dev 180 / test 120 câu. Nhãn train/dev do máy; test chưa có nhãn người. Baseline trên dev: Success@5 = 92,0%, nDCG@10 = 0,839. Đây là số đo trên nhãn máy, có thể lạc quan. Điểm yếu rõ: 18/18 truy vấn dev không có đáp án vẫn nhận kết quả; các nhóm tiếng Anh pha, nhu cầu và thuộc tính còn yếu.

Giọng nói và ảnh chỉ có smoke trên dữ liệu ngoài/fixture/gallery. Hai manifest VNStore hiện đều rỗng nên chưa có kết quả benchmark người dùng thật, chưa đủ cơ sở chọn model cuối.

## Thay đổi mới nhất — giọng nói

- Giữ transcript gốc; người dùng xem/sửa/chọn gợi ý và xác nhận trước khi tìm.
- Gợi ý n/l, dấu và cụm từ dựa trên sản phẩm/danh mục/chất liệu, không tự áp dụng hoặc thêm thuộc tính.
- Cảnh báo âm nhỏ/vỡ tiếng; gain giới hạn và high-pass tùy chọn, đều tắt mặc định.
- Chọn Việt/Anh/auto theo request; nhận diện ngôn ngữ ở mức clip, chưa bảo đảm chất lượng Việt–Anh trong cùng câu.
- Evaluator dùng chung pipeline API, báo cáo theo nhóm âm lượng/tag và mức ảnh hưởng của gợi ý. Bộ câu dev tăng từ 24 lên 29.

## Kiểm thử và trạng thái mã nguồn

- 632 backend đạt, 3 module ML bỏ qua theo chế độ opt-in.
- 22 kiểm thử ảnh Pillow, typecheck và build đạt.
- Một lượt đầy đủ có 126/126 E2E đạt. Lượt kiểm tra thêm có một ca catalog lỗi tài nguyên Chrome WebSocket; chạy lại riêng hai lần với một worker đều đạt, giữ nguyên kiểm tra console.
- 101 kiểm thử voice/API/evaluator chuyên biệt đạt; 4 smoke ONNX thật đạt. Không cộng các con số này thành tổng test duy nhất vì có phần chạy lại/trùng phạm vi.
- Working tree đang có thay đổi chưa commit, gồm đợt cải thiện voice và tài liệu; không stage/commit/push trong lượt báo cáo.

## Ưu tiên tiếp theo

1. Thu và duyệt pilot voice/ảnh truy vấn thật; với voice cần tiếng nhỏ/xa, vùng giọng, tên riêng, English/Việt–Anh và tiếng ồn.
2. Duyệt họ sản phẩm, quyết định ảnh dùng chung và khóa split ảnh.
3. Chấm/xác nhận relevance bằng người để đánh giá keyword, voice và ảnh độc lập; giữ test tách khỏi tinh chỉnh.
4. Xử lý no-match và các lỗi keyword cụ thể, đo lại trên dev; chạy sàng lọc model và ablation audio/ngôn ngữ/OCR/fusion.
5. Chốt cấu hình trên dev rồi mới mở locked test và nghiệm thu theo PLAN.

Nếu mục tiêu gần nhất là demo nội bộ, đã có chức năng để tiếp tục thử nghiệm. Nếu mục tiêu là khẳng định chất lượng tìm kiếm hoặc công bố rộng rãi, còn các điều kiện dữ liệu, đánh giá và quyền ảnh nêu trên. Không đưa phần trăm hoàn thành chung vì các giai đoạn có khối lượng và điều kiện nghiệm thu khác nhau.

## Hồ sơ đối chiếu

- [Catalog và bộ truy vấn 600 câu](2026-10-11_GD1-2_bo-sung-tu-dong.md).
- [Quyết định baseline nhãn máy](2026-10-11_GD2_baseline-nhan-may.md).
- [Đợt cải thiện voice](2026-10-12_GD5-6_cai-thien-tim-kiem-giong-noi.md).
- [Kết quả kiểm thử máy đọc được](../../docs/voice-improvements/checks/verification-summary.json).
- [Hồ sơ phân tích và hướng dẫn voice](../../docs/voice-improvements/README.md).

Một số đoạn cũ trong README/backlog còn ghi seed-004, 330 draft hoặc số test cũ. Báo cáo này dùng snapshot hiện hành và mốc cập nhật mới nhất để tránh trộn trạng thái lịch sử với hiện tại.
