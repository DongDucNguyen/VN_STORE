# GĐ5 — Phân tích tiến độ, tối ưu tiếng Việt, OCR/crop/fusion và ablation

Ngày 11/10/2026. Người thực hiện: Codex. Trạng thái: **đã triển khai và kiểm thử các nhánh tối ưu cơ sở cùng công cụ ablation; chưa nghiệm thu GĐ5 theo PLAN** vì thiếu dev VNStore đã duyệt và hai ứng viên cuối GĐ4. Không có model/cấu hình mới được bật mặc định.

Catalog `seed-004-hanhsilk-materials`, SHA-256 trước/sau `5448a8f4f8161e14cda4f6c3bac921c46af4c02be359dfe20c8ddd312572cecb`. Working tree đã có nhiều thay đổi GĐ3–4 trước phiên; giữ nguyên các phần đó, không stage/commit/push.

## 1. Tiến độ thực tế đến hiện tại

| Giai đoạn | Kết quả đã có | Khoảng cách tới nghiệm thu |
|---|---|---|
| GĐ0 | Khung dự án, môi trường, kiểm thử | Đã hoàn thành |
| GĐ1 | 330 sản phẩm, 814 ảnh, 23 danh mục; validator/snapshot/import có kiểm soát | 330 draft, 0 published; cả 814 quyền ảnh vẫn unknown; 128 sản phẩm thiếu chất liệu, 96 dưới 2 ảnh |
| GĐ2 | Catalog API/UI, BM25 tiếng Việt, giá/phủ định/bộ lọc, yêu thích | Chưa có baseline keyword từ nhãn được duyệt; chế độ mặc định chỉ published nên catalog còn rỗng |
| GĐ3 | Công cụ thu/nhập/duyệt voice, ảnh, họ và kế hoạch split; 107 câu keyword dev nháp | Manifest thật có 0 voice và 0 query ảnh; chưa có registry họ đã duyệt và split ảnh đã khóa |
| GĐ4 | 4 cấu hình PhoWhisper, 3 adapter ảnh, screening, chi phí và bootstrap | FLEURS/gallery chỉ là smoke; chưa chọn hai ứng viên mỗi modality trên dev VNStore |
| GĐ5 | Phiên này: cấu hình ngôn ngữ/VAD/RRF, OCR Latin thật, crop/multi-view, calibration và runner ablation | Chưa có bằng chứng cải thiện trên dev đã duyệt; chưa chọn pipeline cuối; các thử nghiệm semantic/fine-tune có điều kiện còn chờ dữ liệu |
| GĐ6–7 | UI voice/ảnh/crop, lỗi và hồi quy desktop/mobile đã có | Chưa chạy locked test, nghiệm thu mục tiêu chất lượng và độ trễ từ trình duyệt |

Đã vượt mục tiêu số lượng 300 sản phẩm, nhưng chưa vượt điều kiện công bố và chất lượng. Số test không được quy đổi thành phần trăm hoàn thành dự án. Đường găng là quyền/duyệt catalog → nhãn và query độc lập → sàng lọc GĐ4 → chứng minh tối ưu GĐ5 → locked test.

## 2. Đã triển khai trong phiên

1. `SearchConfig` dùng chung API/evaluator, validate nghiêm kiểu/range/NaN/khóa lạ. Mặc định tái tạo baseline. Tùy chọn tỷ lệ âm tiết khớp và khớp dấu để khảo sát các kết quả lỏng như “gạo”/“gáo”; không cưỡng bức đổi transcript/tên riêng.
2. Weighted RRF ảnh/chữ, `rrf_k`, top K và heuristic bỏ RRF chữ phổ biến. Trọng số chữ 0 bỏ cả fusion chữ và hint mềm; hard filter giá/phủ định/bộ lọc người dùng vẫn áp dụng.
3. OCR Latin qua `rapidocr==3.4.1` và ONNX, ba trọng số được ghim SHA-256. API/evaluator dùng chung `image/pipeline.py`. OCR chỉ đóng góp một ranking; không sinh hard filter hay claim nguồn gốc. Khi OCR lỗi, API tiếp tục bằng ảnh/chữ, run ghi lỗi và không đủ điều kiện chọn.
4. Crop xyxy chuẩn hóa sau EXIF transpose; sidecar gắn qid + hash nguồn, kiểm tra trước model và chống file thay đổi trong lúc chạy. So full/crop trên cùng tập query, không sinh crop từ đáp án. Multi-view max cosine so với ảnh đầu tiên mỗi sản phẩm, dùng cùng chỉ mục.
5. Gate VAD và năng lượng cấu hình được, dùng chung API/evaluator, lưu config vào run. Thêm `pipeline_ms` để chi phí VAD/OCR không bị giấu trong số đo riêng ASR/embedding.
6. `ablate.py`: ma trận 5 biến thể × 2 voice, 7 × 2 ảnh, 4 keyword; cùng ngân sách và tiến trình riêng cho voice/ảnh. Lưu cả khi tất cả run lỗi. Không nhận test; thiếu dữ liệu/crop, thiếu pool, lỗi OCR, chưa đủ cụm đều được báo. So cặp với baseline theo cụm; không tự chọn production.
7. `calibrate_no_match.py`: chỉ nhận dev đã duyệt có cả hai lớp; bảng precision/recall/F1 theo ngưỡng và giới hạn false reject. Đề xuất chỉ để chạy lại toàn retrieval, không sửa API. Ngưỡng API loại sản phẩm dưới cosine trước fusion nên chữ/OCR không thể vượt gate.
8. Ghi cấu hình search vào run keyword/voice; so voice yêu cầu cùng search config. So run ảnh thêm kiểm tra cùng catalog/visibility và bootstrap false accept/reject. Tài liệu vận hành: [GĐ5](../../docs/giai-doan-5.md).

## 3. Kết quả đo — chỉ smoke

### Keyword

[Ma trận 107 câu dev nháp, 4 cấu hình](../../experiments/ablations/20261011-113049-657948_keyword/report.json), mỗi cấu hình 3 lượt đo. Đây là nhãn chưa duyệt, không có giá trị nghiệm thu.

| Cấu hình | Số câu no-match nháp vẫn trả kết quả / 12 |
|---|---|
| Baseline | 12 |
| Coverage 0,50 | 8 |
| Coverage 0,75 | 3 |
| Coverage 0,75 + đúng dấu | 1 |

Không suy ra cấu hình cuối tốt hơn: no-match chưa chấm đủ catalog; baseline có 95 query trả về sản phẩm chưa được chấm. nDCG chỉ có 12 câu đủ nhãn ở baseline, Success@5 có 14; so cặp trên đúng các câu đủ nhãn cho delta 0, nhưng coverage còn quá ít để khẳng định không giảm recall. Các trung bình trên số câu đủ nhãn khác nhau không thể so trực tiếp. Các biến thể vẫn tắt mặc định.

### OCR/crop

[Smoke OCR 6 ảnh catalog × full/crop giữa 85%](../benchmark/2026-10-11_113410-873424_ocr-smoke.json): 12 lượt, 8 lượt có chữ, 4 lượt rỗng ở ảnh gốm. Adapter đọc được MAROU/SAIGON và một số chữ bao bì nhưng vẫn nhầm chữ/số/dấu. Không có transcript OCR chuẩn nên không tính accuracy/CER hay tuyên bố hỗ trợ tiếng Việt đạt chuẩn.

Lượt đầu gồm nạp model: 2.450 ms; các lượt sau 353–1.265 ms trên CPU. Đây là số đơn lẻ lúc máy còn chạy công việc khác, không phải p95 chính thức. Chi phí OCR đáng kể so với embedding ảnh ~vài chục ms trong smoke trước, nên không bật OCR mặc định. Crop giữa ở smoke chỉ kiểm tra code, không phải vùng vật thể do người duyệt.

### Voice

Đã hoàn tất cả 10 run của ma trận FLEURS có sẵn: 31 clip (30 lời nói + 1 nhiễu), 5 cấu hình cho mỗi PhoWhisper-base/small, 3 lượt latency. [Báo cáo máy đọc và so cặp](../../experiments/ablations/20261011-113058-735181_voice/report.json), [kết quả từng cấu hình](../../experiments/ablations/20261011-113058-735181_voice/runs/). Chỉ có 1 cụm đóng góp WER nên không suy luận thống kê chất lượng VNStore. Một số lượt chạy đồng thời kiểm thử/CPU OCR, vì vậy latency chỉ tham khảo.

Base baseline WER 0,1267; tắt VAD giữ WER câu có lời nhưng sinh chữ ở clip nhiễu. Ngưỡng năng lượng −50 dBFS chặn nhầm 1 câu, WER tăng thành 0,1606 và độ đúng phủ định trên 5 câu giảm 1,0 → 0,8. Small baseline WER 0,1092; tắt VAD cũng sinh chữ ở clip nhiễu; ngưỡng −50 dBFS làm WER tăng lên 0,1455, chặn nhầm 1 câu và giảm độ đúng phủ định còn 0,8. VAD threshold 0,35 hoặc min speech 150 ms giữ WER baseline trên mẫu nhỏ này. Các thử nghiệm không cung cấp lý do thay baseline đang dùng.

Manifest VNStore thật vẫn rỗng. Đã chạy runner voice/ảnh trên manifest này: không có run chất lượng nào được tạo; báo chờ collection (ảnh còn chờ crop). Không tự tạo relevance, registry, consent hoặc sản phẩm published.

## 4. Kiểm chứng

| Hạng mục | Kết quả và bằng chứng |
|---|---|
| Test mới GĐ5 | 24 ca regression cho cấu hình, khớp tiếng Việt, OCR/hard filter, gate, crop/hash, VAD, equal budget, lỗi subprocess, calibration và chống tuning test |
| Toàn backend cuối | **507 passed, 2 skipped**, 1 cảnh báo Starlette/httpx; [log](2026-10-11_GD5_backend-final.log) |
| Pillow, frontend, E2E | **22 Pillow**, typecheck/build và **104/104 E2E** desktop/mobile đạt; [log hồi quy](2026-10-11_GD5_kiem-thu.log) |
| Catalog | Validate catalog + fixture, fixture khớp generator đạt; hash DB không đổi |
| Model OCR thật | Cài môi trường ML riêng, checksum 3 model đạt, chạy 12 lượt full/crop trên ảnh thật; smoke có file/hash/text/timing |
| Tích hợp model/crop | **2/2 test ML mới đạt**: OCR + SigLIP2 thật qua pipeline chung; crop đúng orientation/kích thước và bỏ EXIF. [Log](2026-10-11_GD5_ml-final.log) |

Lượt full suite đầu có 2 test registry lỗi do wrapper monkeypatch chưa nhận kwargs mới `ocr/crops`. Đã cập nhật wrapper để tiếp tục kiểm tra thay/xóa registry trong lúc inference; chạy lại **toàn bộ backend** đạt như trên. Không bỏ assertion chống input thay đổi. Hai module ML được skip trong môi trường backend thường theo thiết kế; module GĐ5 mới đã chạy riêng với `VNSTORE_RUN_ML_TESTS=1` bằng `.venv-ml` sau khi ma trận voice kết thúc. Kiểm tra cuối `git diff --check` đạt; hash catalog không đổi.

Sandbox Windows chặn thư mục temp pytest và pip/network; đã chạy các bước cần thiết ngoài sandbox qua cơ chế quyền được cấp. Không có hành động bị auto-review từ chối.

## 5. Công việc chưa thể đóng

| Đầu việc | Điều kiện còn thiếu / bước tiếp theo |
|---|---|
| Chứng minh cải thiện và chọn ứng viên cuối — tiêu chí GĐ5 | Dev VNStore có người duyệt, cùng catalog/split, hai ứng viên GĐ4; chấm bổ sung pool và chạy ma trận đầy đủ |
| Chọn crop và ngưỡng no-match chính thức | Query độc lập có vùng chọn cố định, đủ no-match; replay retrieval và đánh giá Recall/nDCG/Success/phân nhóm sau đề xuất ngưỡng |
| OCR tiếng Việt trên bao bì | Transcript OCR và relevance thật; đo chất lượng và chi phí trước khi giữ nhánh này |
| Semantic BGE-M3, denoise, contextual biasing/n-best, remove-background | Các thử nghiệm tùy điều kiện trong PLAN chưa triển khai trong phiên; cần baseline/dev để quyết định và đo lợi ích, không mặc định áp dụng |
| Hard negatives/fine-tune | Train có quyền và đủ nhãn; môi trường export/train dùng được PyTorch. Không lấy lỗi dev/test làm train |
| Công bố catalog, locked test, latency trình duyệt | Quyền ảnh/duyệt dữ liệu, chốt cấu hình và máy đo, rồi GĐ6 |

Vì vậy **không ghi GĐ5 “hoàn thành toàn bộ”**. Đã hoàn tất phần triển khai nêu ở mục 2 và kiểm chứng tương ứng; phần nghiên cứu có điều kiện, dữ liệu, chứng minh cải thiện và lựa chọn cuối vẫn mở. Thứ tự hành động và lệnh tái lập nằm trong [hướng dẫn GĐ5](../../docs/giai-doan-5.md).
