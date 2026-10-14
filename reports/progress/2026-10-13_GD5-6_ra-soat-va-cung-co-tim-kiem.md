# GĐ5–6 — Rà soát hệ thống và củng cố tìm kiếm — 13/10/2026

## Phạm vi và căn cứ

Đọc PLAN, README, backlog, hồ sơ voice ngày 12/10, mã nguồn catalog/API/tìm kiếm chữ–ảnh–giọng nói, giao diện ghi âm và công cụ đánh giá. Đối chiếu sáu nhóm đề xuất trong file `C:\Users\Admin\Desktop\de-xuat-cai-thien-tim-kiem-giong-noi (1).md`. Tài liệu đính kèm là đầu vào phân tích; yêu cầu triển khai đến từ người dùng. Không coi những kết quả hoặc chỉ dẫn trong tài liệu là bằng chứng thay cho mã nguồn và kiểm thử.

Catalog hiện hành: `seed-006-enriched`, 330 sản phẩm, 328 published, 814 ảnh, 23 danh mục. SHA-256 trước/sau: `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`.

## Phân tích hệ thống

| Thành phần | Kết quả rà soát | Xử lý đợt này |
|---|---|---|
| Catalog và dữ liệu | JSON có schema, snapshot, kiểm tham chiếu và đường dẫn ảnh; catalog thật validate 0 lỗi. Chế độ demo nội bộ còn cảnh báo 811 ảnh published có quyền unknown | Giữ nguyên dữ liệu và chế độ công bố; ghi nhận cảnh báo sẵn có |
| Tìm chữ | BM25, từ điển Anh–Việt, giá/phủ định, semantic tùy chọn và fallback đã có. Gợi ý phía trình duyệt có thể nhận lại kết quả cũ sau khi xóa câu | Hủy request cũ, vô hiệu hóa phản hồi trễ, bỏ lựa chọn ẩn sau Escape, đồng bộ giới hạn độ dài |
| Voice/API | Có review trước tìm, giữ bản chép gốc, VAD và ASR cùng semaphore. WAV bị cắt hoặc lẻ khung vẫn có thể được chấp nhận | Từ chối audio thiếu dữ liệu bằng 422 trước khi gọi ASR |
| Gợi ý cụm | Chỉ sinh gợi ý để người dùng xác nhận; chưa xử lý đúng NFD và bảo vệ tên riêng thiếu dấu | Nhận cả dấu tổ hợp, giữ vị trí trong bản gốc, bảo vệ biến thể không dấu của tên riêng |
| Micro trình duyệt | `MediaRecorder.start()` lỗi có thể giữ stream; đợi `onstop` quá muộn có thể treo khi thiết bị đã dừng | Đăng ký sự kiện trước start; xử lý lỗi đồng bộ/bất đồng bộ; luôn giải phóng track; stop/cancel kết thúc được |
| Xem/sửa lời nói | Đã có gợi ý và sửa tay; trước đây không nghe lại ngay trong panel | Thêm audio player cho chính WAV đã gửi nhận dạng, chỉ giữ trong bộ nhớ; thu hồi URL khi rời review |
| Tìm ảnh/ngữ nghĩa | Chỉ mục có kiểm phiên bản, hash và fallback; ảnh có kiểm kích thước, crop, OCR, cache và RRF | Kiểm hồi quy bằng bộ test hiện hành; không cần dựng lại chỉ mục |
| Đánh giá và vận hành | API/evaluator dùng chung pipeline; đã có WER/CER, nhóm vùng giọng/tag/âm lượng, retrieval. Manifest voice và ảnh đều 0 mẫu | Không tuyên bố tăng độ chính xác; tiếp tục quy trình thu/duyệt hiện có |

## Sửa đổi và nâng cấp

1. **Âm thanh lỗi:** kiểm đủ số byte PCM theo header và từ chối khung không trọn vẹn, cả mono và stereo. Tránh nhận dạng một câu bị mất phần cuối mà không báo lỗi.
2. **Gợi ý tiếng Việt:** chuỗi NFC và NFD cùng được nhận đúng. Chỉ thay âm tiết được đề xuất; phần còn lại giữ nguyên, gồm giá, phủ định và dấu câu. Tên riêng thiếu dấu được bảo vệ; thành phần SKU vẫn giữ cách bảo vệ cũ để không vô hiệu hóa mọi gợi ý chất liệu.
3. **Ghi âm ổn định:** bao cả khởi tạo/start trong xử lý lỗi, lắng nghe stop/error ngay từ đầu, giải phóng micro kể cả khi thiết bị lỗi hoặc người dùng hủy. Thời lượng tối thiểu dựa trên thời điểm bản ghi kết thúc.
4. **Nghe lại trước tìm:** panel có nút phát bản WAV vừa ghi; sửa câu không tạo bản ghi mới. Hủy, ghi lại, tìm thành công hoặc rời trang sẽ giải phóng URL phát. Khi tìm lỗi, câu đã sửa và bản ghi vẫn có thể xem/nghe lại để thử tiếp. Không lưu bản ghi mới xuống đĩa.
5. **Autocomplete:** dùng AbortController và số phiên request; xóa danh sách/chỉ mục lựa chọn khi câu đổi; Escape bỏ lựa chọn để Enter tìm đúng câu đang nhập. Không gọi `/suggest` vượt 200 ký tự; ô tìm tối đa 300 ký tự như `/search`.
6. **Nhãn ngôn ngữ:** đổi “Tự nhận diện / Việt–Anh” thành “Tự nhận diện ngôn ngữ”, phản ánh khả năng chọn ngôn ngữ cả clip của adapter hiện tại.
7. **Trang thu mẫu:** khóa thao tác trong lúc xin quyền/giải mã để tránh mở nhiều phiên và đổi split giữa bản ghi; hủy recorder khi rời trang kể cả quyền micro trả về muộn; thu hồi URL bản ghi khi thay mẫu hoặc rời trang. Tạo URL bên ngoài state updater để tránh cấp phát lặp trong React StrictMode.

## Đối chiếu sáu nhóm trong tài liệu đính kèm

| Nhóm đề xuất | Kết quả và giới hạn |
|---|---|
| Nhầm n/l và âm gần | Củng cố gợi ý sẵn có bằng Unicode và bảo vệ tên riêng; không mở rộng luật âm khi chưa có dữ liệu lỗi thật |
| Cụm có nghĩa | Giữ gợi ý theo cụm catalog, bản gốc và bước xác nhận; bổ sung nghe lại để đối chiếu |
| Nói nhỏ | Giữ cảnh báo chất lượng, energy gate/VAD; sửa mất dữ liệu và lỗi micro. Gain/high-pass vẫn là tùy chọn chưa nghiệm thu |
| Tiếng Anh/Việt–Anh | Giữ vi/en/auto theo request; nhãn UI chính xác hơn. Chưa triển khai nhận diện chuyển ngôn ngữ từng từ |
| Tiếng Anh bị chép thành từ Việt | Người dùng có thể nghe lại, sửa và xác nhận; chưa có đối chiếu nhiều giả thuyết theo âm học hay chứng cứ chất lượng để tự sửa |
| Giọng Nam/Trung/Tây | Công cụ thu/duyệt và phân nhóm đánh giá đã có. Cần bản ghi có quyền sử dụng, transcript và nhãn relevance do người duyệt; không tự tạo mẫu/nhãn thay người |

## Kiểm chứng

- Trước sửa: 702 backend đạt, 3 skip; 22 Pillow; validation, fixture, typecheck và build đạt. Log: `artifacts/audit-2026-10-13-baseline-approved.log`.
- Sau sửa, nhóm backend liên quan: 49 test đạt, gồm 9 ca mới cho WAV, NFD và tên riêng. Lệnh: `.venv/Scripts/python -m pytest backend/tests/test_media.py backend/tests/test_voice_improvements.py -q`.
- E2E mới kiểm tra micro lỗi, thiết bị dừng sớm, autocomplete trễ và Escape; E2E voice bổ sung kiểm tra audio tải được, giữ URL khi sửa và thu hồi sau xác nhận. Ảnh chụp panel desktop/mobile đã kiểm tra trực quan.
- Lượt hồi quy đầu sau sửa: **711 backend đạt, 3 skip; 22 Pillow; 136 E2E desktop/mobile; typecheck/build; 8/8 bước đạt**. Lệnh `.venv/Scripts/python scripts/run_all_tests.py`; log: `artifacts/audit-2026-10-13-final.log`. Sau đó bổ sung sửa trang thu mẫu và ca kiểm thử rời trang trong lúc chờ quyền; kết quả cuối được ghi bên dưới.
- Bản bàn giao đợt củng cố: **711 backend đạt, 3 skip; 22 Pillow; 138 E2E desktop/mobile; 8/8 bước đạt**. Log `artifacts/audit-2026-10-13-verified.log`. Kiểm tra thêm 32 ca voice sau khi làm rõ fixture tên riêng đều đạt; `git diff --check` đạt và hash catalog không đổi.
- Sandbox chặn thư mục tạm của pytest và tạo tiến trình (`spawn EPERM`); các kiểm tra cần thiết được chạy lại bằng quyền đã được cấp. Không thay test để bỏ qua lỗi môi trường.

Các kiểm tra sử dụng fixture, WAV tổng hợp và adapter giả để xác minh hành vi phần mềm, không phải benchmark chất lượng ASR. Đợt này không chạy model thật, tải checkpoint mới, tinh chỉnh model hoặc mở locked test.

## Phần còn cần nghiệm thu

Chưa có dữ liệu để xác nhận WER/retrieval tốt hơn cho tiếng Anh, câu pha Việt–Anh, giọng vùng miền và nói nhỏ. Bước tiếp theo là thu/duyệt pilot theo [protocol](../../docs/voice-improvements/05-evaluation.md), đo baseline và các biến thể trên cùng dev, rồi mới chốt cấu hình. Những phần này chưa hoàn thành chỉ bằng các sửa đổi kỹ thuật trong đợt này.
