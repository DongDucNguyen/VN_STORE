# GĐ5–6 — Cải thiện tìm kiếm giọng nói — 12/10/2026

| | |
|---|---|
| Giai đoạn | GĐ5 tối ưu voice, GĐ6 giao diện/API; bổ sung công cụ GĐ3 |
| Trạng thái | Hoàn thành triển khai kỹ thuật; chưa nghiệm thu chất lượng ASR trên người dùng thật |
| Người thực hiện | Codex |
| Catalog | `seed-006-enriched`, SHA-256 `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993` |
| Commit | Chưa commit; không stage/commit/push |

## 1. Mục tiêu

Phân tích toàn hệ thống, phân tích đề xuất bốn nhóm điểm yếu voice, triển khai cải thiện và lưu tiến độ/kết quả theo thư mục. Hồ sơ đầy đủ ở [docs/voice-improvements](../../docs/voice-improvements/README.md), gồm bản sao đề xuất, phân tích, thiết kế, nhật ký, hướng dẫn và protocol đánh giá.

## 2. Đã làm

- Giữ bản ASR gốc; API review không truy hồi; UI cho sửa/chọn gợi ý, xác nhận rồi mới tìm. Hủy/ghi lại, giữ nội dung sửa khi lỗi mạng.
- Gợi ý cụm 2–4 token theo catalog, nhầm n/l/dấu, chỉ thay một âm tiết; bảo vệ tên/giá/phủ định/SKU. Danh mục–chất liệu ghép theo cùng sản phẩm. Không tự thêm thuộc tính hoặc áp gợi ý.
- Đo âm nhỏ/clipping, hướng dẫn ghi lại; gain tối đa 12 dB và high-pass 80 Hz tùy chọn, đều tắt mặc định. VAD xét audio gốc trước xử lý, cùng semaphore với ASR.
- PhoWhisper ONNX hỗ trợ vi/en/auto theo request; giữ task transcribe; metadata ngôn ngữ và cờ cắt câu. Không thay cấu hình của request khác trên model dùng chung.
- Evaluator dùng cùng pipeline, thêm nhóm volume/tag, gợi ý tốt/xấu/ngang và retrieval giả định nếu có nhãn. Ma trận hai model × năm biến thể; thêm năm câu dev ứng viên.

## 3. Kiểm chứng

| Kiểm tra | Lệnh / hồ sơ | Kết quả |
|---|---|---|
| Trước sửa | `scripts/run_all_tests.py` | 603 backend, 22 Pillow, 120 E2E; 8/8 bước đạt |
| Hồi quy | `scripts/run_all_tests.py`, [log](../../docs/voice-improvements/checks/verified.log) | 632 backend, 3 skip ML opt-in; 22 Pillow; typecheck/build; 126 E2E đạt |
| Sau chỉnh độ trễ cuối | pytest 5 tệp voice/API/benchmark/TRT như [nhật ký](../../docs/voice-improvements/03-progress.md) | 101 đạt |
| ONNX thật | opt-in pytest `test_voice_languages_ml.py` + phần ASR/VAD của `test_ml_adapters.py`, [log](../../docs/voice-improvements/checks/onnx-smoke.log) | 4 đạt; model base/small chạy vi/en/auto, VAD và transcript tiếng Việt đạt |
| Catalog | kiểm tra SHA-256 trước/sau | Không đổi; 330 sản phẩm, 328 published, 814 ảnh |
| Benchmark dev | `eval_voice.py --adapter app.ml.asr:PhoWhisperSmall --split dev` | `pending_collection`, không ghi run giả |
| UI | E2E desktop/mobile và xem [ảnh](../../docs/voice-improvements/checks/voice-review-mobile.png) | Bản gốc, câu sửa, gợi ý, cảnh báo và hành động hiển thị đầy đủ |

Chạy kiểm tra thêm sau cùng: 632 backend đạt, 125/126 E2E đạt; một ca catalog gặp `net::ERR_NO_BUFFER_SPACE` từ WebSocket của Vite/Chrome. Chạy lại riêng ca đó với `--workers=1 --repeat-each=2`: 2/2 đạt, exit 0. Giữ nguyên kiểm tra console; [log và kết quả chi tiết](../../docs/voice-improvements/checks/verification-summary.json) phân biệt rõ lần chạy này với lần đầy đủ 126/126 đạt.

## 4. Số đo

Không báo mức tăng accuracy/WER/retrieval. Test synthetic/fixture chỉ kiểm hợp đồng; smoke ngôn ngữ dùng FLEURS **tiếng Việt** đã có trên máy. Chế độ English chạy được không chứng minh độ chính xác tiếng Anh. Manifest VNStore vẫn 0 clip.

## 5. Khác với kế hoạch

Không tự động sửa transcript theo tên gần âm và không bật gain/denoise/auto language làm mặc định khi chưa có dev. Bộ lọc high-pass chỉ xử lý DC/ù thấp, không phải denoiser tổng quát. Ngôn ngữ được nhận diện theo clip, chưa tách code-switch từng đoạn.

## 6. Nợ kỹ thuật

Cần mẫu và transcript chuẩn đã duyệt cho âm vùng miền/nhầm âm, nói nhỏ/xa, tiếng ồn, English và Việt–Anh; relevance để đo tìm kiếm. Bộ gợi ý hiện ưu tiên tránh sửa sai nên có thể bỏ sót; chưa có n-best/rescore âm học/fine-tune.

## 7. Rủi ro và việc chặn

Gợi ý theo văn bản có thể không đúng ý nói; UI yêu cầu xác nhận. PhoWhisper fine-tune tiếng Việt có thể vẫn yếu tiếng Anh dù đổi prompt. Chưa thay model mặc định hoặc tuyên bố GĐ4–6 nghiệm thu chất lượng.

## 8. Bước tiếp theo

Thu/duyệt pilot theo [05-evaluation.md](../../docs/voice-improvements/05-evaluation.md), chạy ma trận dev với nhãn relevance, phân tích nhóm lỗi và gợi ý có hại; chỉ đổi mặc định sau khi có bằng chứng. Locked test chưa mở.
