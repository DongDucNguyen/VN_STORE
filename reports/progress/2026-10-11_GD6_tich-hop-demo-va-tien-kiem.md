# GĐ6 — Tích hợp giao diện, demo end-to-end và tiền kiểm locked test

| | |
|---|---|
| Ngày | 11/10/2026 |
| Giai đoạn | GĐ6 — PLAN §9: tích hợp voice/image vào giao diện, benchmark locked test |
| Trạng thái | 🟡 Hoàn thành phần tích hợp/công cụ và kiểm thử đợt này; chưa nghiệm thu chất lượng hoặc chạy locked test |
| Người thực hiện | Codex |
| Catalog | `seed-004-hanhsilk-materials`, SHA-256 `5448a8f4f8161e14cda4f6c3bac921c46af4c02be359dfe20c8ddd312572cecb` không đổi trước/sau |
| Commit | Chưa commit; không stage/commit/push. Giữ các thay đổi GĐ3–5 đã có trước phiên |

## 1. Mục tiêu và phân tích đầu vào

GĐ6 yêu cầu giao diện hoạt động end-to-end, báo cáo lựa chọn model và benchmark locked test. Trước phiên đã có ghi âm/transcript sửa được, chọn/crop ảnh, bộ lọc, lỗi và kiểm thử desktop/mobile. Còn thiếu handoff kết quả voice, bảo vệ thao tác bất đồng bộ, phép đo từ trình duyệt và hồ sơ tiền kiểm trước mở test.

GĐ4–5 chưa có model được chọn trên dev VNStore đã duyệt. Catalog vẫn 330 draft, 0 published; 814 quyền ảnh unknown. Manifest thực có 0 voice và 0 ảnh query. Vì vậy triển khai và kiểm chứng các phần độc lập với nhãn trước; không chạy test để chọn cấu hình hoặc tạo nhãn/người duyệt thay người thật.

## 2. Đã triển khai

1. **Voice dùng kết quả API trực tiếp.** `/search/voice` đã trả retrieval; UI nay sử dụng response này thay vì bỏ đi và gửi lại `/search`. Handoff giữ trong bộ nhớ 30 giây, gắn token/transcript; nói cùng câu lần nữa vẫn cập nhật. Sửa transcript, đổi bộ lọc hoặc phân trang thực hiện keyword search như trước.
2. **Hủy và chống kết quả cũ.** Hủy chờ quyền micro, ghi âm hoặc ASR; giải phóng track khi quyền micro về muộn sau khi rời trang. Abort fetch và kiểm tra phiên yêu cầu trước cập nhật. Ảnh mới/crop/yêu cầu mới không bị response cũ ghi đè; thêm nút hủy tìm ảnh và kiểm tra lại trạng thái model.
3. **Trang `#/diagnostics`.** Hiện trạng thái model/catalog, bật/tắt/xóa/xuất số đo. Chỉ giữ tối đa 200 lượt thành công trong bộ nhớ tab, không gửi telemetry hoặc lưu localStorage; export không có query/transcript/media/ID sản phẩm. Đo keyword từ lúc gửi yêu cầu, voice từ bấm dừng, ảnh từ bấm tìm gồm chuẩn bị ảnh, đến sau render. Không tính thời gian nói hoặc tải hết ảnh sản phẩm.
4. **Timings API.** Bổ sung `body_read` cho voice/ảnh; đây là thời gian máy chủ đọc body, không phải toàn bộ upload qua mạng. Gate ứng dụng vẫn từ chối lượt đồng thời bằng 429; hủy ở trình duyệt không đảm bảo dừng kernel inference đang chạy.
5. **Tổng hợp số đo.** `scripts/benchmark/browser_timings.py` nhóm theo modality/catalog/model/revision, loại warmup theo khai báo, tính p50/p95 nearest-rank, cảnh báo mẫu ít; ghi JSON/Markdown mới trong `reports/benchmark/`. Không đánh đồng latency với chất lượng retrieval.
6. **Tiền kiểm GĐ6.** `stage6_readiness.py`, mẫu `experiments/configs/selection.template.json` và thư mục `reports/acceptance/`. Kiểm tra selection có bằng chứng ablation reviewed-dev, hash run/prediction/code/catalog, cấu hình ngôn ngữ thống nhất; kiểm tra nhãn keyword/voice/ảnh test, consent, registry/split, số cụm và sidecar crop. Chỉ đọc/audit; không nạp model hay tạo prediction test.
7. **Smoke browser model thật.** `frontend/playwright.smoke.config.ts` và `frontend/smoke/stage6_real.spec.ts`: server riêng, desktop/mobile tuần tự, PhoWhisper-small + SigLIP2 + RapidOCR Latin; xuất số đo và ảnh chụp. Profile này chỉ kiểm tra tích hợp, không phải cấu hình chọn cuối.
8. **Tài liệu vận hành.** [Hướng dẫn GĐ6](../../docs/giai-doan-6.md), gồm kịch bản demo, phép đo, hồ sơ lựa chọn, điều kiện và trình tự locked test một lần, các giới hạn công cụ.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Unit GĐ6 ban đầu | `.venv/Scripts/python -X utf8 -m pytest backend/tests/test_stage6.py -q -p no:cacheprovider` | 17 đạt trước khi bổ sung 4 ca crop; bản cuối có 21 ca, đều nằm trong full suite đạt |
| E2E trọng tâm | `npx.cmd playwright test e2e/stage6.spec.ts e2e/voice_image.spec.ts --reporter=line` trong `frontend` | **32 đạt**: handoff không tìm lặp, sửa transcript, hủy ASR, quyền micro về muộn, đổi ảnh và export số đo; desktop/mobile |
| Toàn dự án sau sửa | `.venv/Scripts/python -X utf8 scripts/run_all_tests.py` | **8/8 bước đạt: 550 backend + 2 module ML skip, 22 Pillow, typecheck/build, 114 E2E**; catalog/fixture validate 0 lỗi, fixture khớp generator |
| Browser model thật, bản cuối | `npx.cmd playwright test --config playwright.smoke.config.ts` trong `frontend` | **2 đạt**, 44,6 giây; mỗi thiết bị 3 keyword + 3 ảnh + 3 voice; tổng 18 số đo |
| Tiền kiểm dữ liệu thật | `.venv/Scripts/python -X utf8 scripts/benchmark/stage6_readiness.py` | **blocked đúng với dữ liệu hiện tại**, không inference; xem phần 7 |
| Whitespace/catalog | `git -c core.safecrlf=false diff --check`; `Get-FileHash database.json -Algorithm SHA256` | Đạt; DB giữ nguyên hash |

Log: [E2E trọng tâm](2026-10-11_GD6_e2e-targeted.log), [full suite](2026-10-11_GD6_full.log), [browser model thật bản cuối](2026-10-11_GD6_real-browser-final.log). [Lượt smoke trước](2026-10-11_GD6_real-browser.log) cũng 2 đạt; lượt cuối chạy lại sau sửa mốc đo để bao gồm chuẩn bị ảnh. Chỉ lấy lượt cuối làm bảng số đo dưới đây.

Backend/E2E thường ngày dùng fixture và adapter giả, không đo chất lượng model. Full suite còn 1 warning Starlette/httpx có trước đó. Test model thật dùng ONNX; thông báo Transformers không tìm thấy PyTorch không làm hỏng lượt chạy. Không thay chính sách Windows để nạp PyTorch.

## 4. Số đo và bằng chứng demo — chỉ smoke

Máy RTX 5070 Ti; Chrome desktop và Pixel 7 **giả lập**; localhost. Mic giả phát lại 4 giây FLEURS, ảnh là bao bì Marou trong gallery. Profile: PhoWhisper-small, VAD 0,5/250 ms, năng lượng −60 dBFS; SigLIP2, OCR Latin CPU, OCR RRF weight 0,35; TensorRT off, draft catalog on.

Mỗi modality/thiết bị có 3 lượt; bỏ lượt đầu, **chỉ còn N=2**. p95 ở đây là thống kê mô tả rất ít mẫu, không phải bằng chứng đạt SLA hay mục tiêu PLAN. Chỉ gồm lượt thành công; desktop chạy trước, mobile dùng server đã warm. Không coi đây là điện thoại vật lý hoặc mạng nội bộ thực.

| Thiết bị | Luồng | N sau warmup | p50 (ms) | p95 (ms) |
|---|---|---:|---:|---:|
| Desktop | Keyword | 2 | 55,5 | 62,4 |
| Desktop | Ảnh + OCR | 2 | 496,5 | 531,2 |
| Desktop | Voice | 2 | 431,6 | 529,8 |
| Mobile giả lập | Keyword | 2 | 48,1 | 54,6 |
| Mobile giả lập | Ảnh + OCR | 2 | 496,5 | 497,4 |
| Mobile giả lập | Voice | 2 | 429,5 | 430,7 |

Lượt đầu desktop: **ảnh 2.064,7 ms, voice 3.464,0 ms**. Đây là lượt đầu quan sát trong phiên có nạp model, không phải phép đo cold start độc lập có đối chứng. Không dùng các lượt warm để che chi phí lần đầu.

Nguồn: export thô [desktop](../benchmark/2026-10-11_GD6_browser-desktop.json), [mobile](../benchmark/2026-10-11_GD6_browser-mobile.json); bảng tổng hợp [desktop](../benchmark/2026-10-11_051510-404151_browser-timings.md), [mobile](../benchmark/2026-10-11_051510-462002_browser-timings.md). JSON tổng hợp cùng tên lưu hash đầu vào và cảnh báo N nhỏ.

Ảnh chụp lưu dưới `artifacts/demo/2026-10-11_GD6/`: [ảnh desktop](../../artifacts/demo/2026-10-11_GD6/desktop/image-results.png), [voice mobile](../../artifacts/demo/2026-10-11_GD6/mobile/voice-results.png), [chẩn đoán mobile](../../artifacts/demo/2026-10-11_GD6/mobile/diagnostics.png). Đã xem trực tiếp ba ảnh này: bố cục và các trạng thái hiển thị phù hợp; vùng thẻ ở ngoài viewport có ảnh lazy-load chưa tải, không phải kết luận ảnh catalog hỏng.

FLEURS không phải câu mua sắm; transcript vẫn có thể trả nhiều kết quả khớp từ lỏng. Đợt này chỉ xác nhận đường đi browser/API/model và khả năng sửa câu; không chấm relevance hoặc tinh chỉnh no-match bằng smoke.

## 5. Khác với kế hoạch

Không có báo cáo chất lượng locked test hoặc quyết định chọn model cuối vì điều kiện GĐ3–5 chưa đạt. Thay vào đó đã hoàn thiện tích hợp, phép đo browser, tiền kiểm và hướng dẫn để chạy đúng khi dữ liệu sẵn sàng. Không tự điền `selection.json`, người duyệt hoặc nhãn test.

## 6. Nợ kỹ thuật và giới hạn

- Tiền kiểm không có khóa hệ thống ngăn mọi lần mở test; người phụ trách ghi sổ lần chạy trong `reports/acceptance/`. `ready_for_locked_test_review` không phải `benchmark_approved` và chưa chứng minh relevance đủ cutoff của mọi model.
- Cần đo ít nhất nhiều lượt hơn (CLI cảnh báo dưới 20 lượt), thêm lỗi/hủy, máy/mạng thực và thiết bị vật lý. Bản đo hiện tại không tính tải xong toàn bộ ảnh sản phẩm.
- Đổi bộ lọc ảnh vẫn thực hiện embedding lại ở server; cache embedding là tối ưu riêng, chưa triển khai trong GĐ6.
- Không thay đổi thuật toán xếp hạng hay tự bật profile OCR smoke làm cấu hình mặc định.

## 7. Đang chặn nghiệm thu

[Tiền kiểm cuối phiên](../acceptance/2026-10-11_051418-033523_stage6-readiness.md) ghi bốn mục bị chặn:

1. Chưa có `experiments/configs/selection.json` được chọn trên dev.
2. Chưa cung cấp bộ keyword test có nhãn đã duyệt.
3. Chưa có voice test đã duyệt và relevance liên kết.
4. Image audit chưa có registry họ/split đã khóa hợp lệ và query test độc lập.

Đầu vào catalog/manifest không đổi trong lúc kiểm tra. Kết quả là `blocked`, `benchmark_approved=false`, `inference_executed=false`. Không chạy locked test VNStore trong phiên này.

## 8. Bước tiếp theo

Nhóm dữ liệu hoàn tất quyền/catalog, thu query và duyệt nhãn/họ/split → screening GĐ4 → ablation/chọn cấu hình GĐ5 → điền hồ sơ selection và chạy lại tiền kiểm → mở locked test một lần → báo cáo chất lượng/phân nhóm/CI/tài nguyên và đo browser trên cấu hình máy/mạng được chốt. Trạng thái chi tiết được cập nhật trong [BACKLOG.md](BACKLOG.md).
