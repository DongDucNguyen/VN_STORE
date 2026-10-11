# GĐ6 — tích hợp giao diện, demo và chuẩn bị locked test

Ngày 11/10/2026. Mục tiêu PLAN §9: giao diện voice/ảnh hoạt động end-to-end, có báo cáo lựa chọn model và benchmark locked test. **Phần tích hợp/công cụ đã có; nghiệm thu chất lượng vẫn chờ dev đã duyệt và cấu hình GĐ5 được chốt.**

## Luồng ứng dụng

- Keyword, voice và ảnh dùng chung catalog, thẻ sản phẩm và bộ lọc. Voice hiện transcript trong ô tìm; người dùng sửa và bấm Tìm để gửi truy vấn keyword mới.
- Kết quả đầu tiên của voice lấy trực tiếp từ `/search/voice`, không gửi lại `/search`. Handoff giữ trong bộ nhớ 30 giây, gắn token với đúng transcript; đổi bộ lọc/phân trang/sửa chữ gửi truy vấn mới. Reload hoặc URL không có handoff hợp lệ trở về tìm bằng chữ.
- Hủy ghi âm, hủy chờ micro hoặc hủy ASR ngăn kết quả cũ điều hướng trang. Khi quyền micro về muộn sau khi rời trang, track được giải phóng. Hủy fetch phía trình duyệt không đồng nghĩa đã ngắt kernel inference đang chạy trên máy chủ.
- Ảnh được sửa orientation, crop, resize và bỏ metadata ở trình duyệt. Đổi ảnh/crop/yêu cầu mới hoặc rời trang hủy yêu cầu cũ; kết quả đến muộn không được ghi đè. Bộ lọc gửi lại ảnh đã chuẩn bị, không encode lại, kèm `reuse=1`: máy chủ dùng lại embedding/OCR của đúng ảnh đó (khóa theo SHA-256, tối đa 8 ảnh, 120 giây, chỉ trong bộ nhớ, không ghi đĩa) nên không chạy model lần nữa. Lượt bấm **Tìm** luôn chạy đầy đủ, không đọc cache; evaluator không dùng cache. OCR lỗi không được lưu vào cache. Response ghi `visual.query_cache` = `hit`/`miss`. Khi model chưa sẵn sàng có nút **Kiểm tra lại**.
- API trả `body_read` trong `timings_ms` voice/ảnh. Đây là thời gian đọc body ở máy chủ, không phải toàn bộ upload trên mạng. Mỗi modality dùng gate 1 lượt; lượt khác bị từ chối 429, không có hàng đợi inference do ứng dụng quản lý. Threadpool/hệ điều hành vẫn có thể thêm thời gian điều phối.
- Mọi kết quả ảnh vẫn ghi “mẫu tương tự”; nguồn gốc lấy từ catalog. Không dùng OCR/độ tương đồng làm bằng chứng xuất xứ.

## Đo từ trình duyệt

1. Mở `#/diagnostics` trên cùng tab demo. Xem trạng thái model/catalog và bấm **Bắt đầu đo**.
2. Dùng liên kết trên trang để thực hiện keyword, voice và ảnh. Không reload tab giữa phiên.
3. Quay lại `#/diagnostics`, bấm **Dừng đo**, rồi **Xuất số đo JSON**. Ghi riêng cấu hình máy, browser, mạng, thời điểm khởi động model và điều kiện đo.
4. Lưu file vào thư mục phù hợp dưới `reports/benchmark/`, tổng hợp:

```powershell
.venv/Scripts/python -X utf8 scripts/benchmark/browser_timings.py <export.json> --warmup 1 --context "RTX 5070 Ti; Chrome desktop; localhost; model thật; smoke FLEURS/gallery"
```

Số đo bắt đầu ở lúc trang gửi keyword, bấm dừng voice hoặc bấm tìm ảnh (gồm chuẩn bị ảnh). Kết thúc sau hai animation frame khi response đã được render. Không tính thời gian nói hoặc đợi toàn bộ ảnh thẻ sản phẩm tải xong. `server_ms` giữ timings API; không lấy hiệu browser/server để khẳng định riêng độ trễ mạng.

Phân bố độ trễ chỉ gồm lượt thành công. Export v2 thêm `outcomes`: số lượt **lỗi** và **hủy/bị thay trước khi hiện kết quả** theo từng modality (chỉ số đếm); trang chẩn đoán hiện tổng lỗi/hủy. Keyword không đếm yêu cầu bị thay khi còn chờ phản hồi (React StrictMode gọi effect hai lần lúc mount ở chế độ dev, nếu đếm sẽ ra hủy giả); chỉ đếm lỗi và kết quả bị thay trước khi vẽ. Mỗi mẫu có `cached` (ảnh đổi bộ lọc trúng cache máy chủ). Lưu tối đa 200 lượt trong bộ nhớ tab; không localStorage, không gửi telemetry. Export không chứa câu tìm, transcript, audio, ảnh hoặc ID sản phẩm. Xóa số đo/reload sẽ xóa phiên. Số đo đang dở khi dừng/xóa phiên không được thêm lại.

CLI nhóm theo modality/catalog/model/revision/cached (lượt trúng cache **không bao giờ** gộp với lượt tìm đầy đủ, không bỏ warmup ở nhóm cache), bỏ số lượt warmup đã khai báo **trong từng nhóm chạy model**, báo bảng thành công/lỗi/hủy/tỉ lệ lỗi với export v2 (v1 không có số này, cần đo lại trước khi nghiệm thu), p50/p95 nearest-rank, cảnh báo dưới 20 lượt đo. `first_observation_ms` chỉ là lượt đầu quan sát, không tự gọi là cold start. Output mới `.json`/`.md` nằm trong `reports/benchmark/`; không ghi “đạt chất lượng” từ số đo latency.

## Smoke trình duyệt với model thật

Lệnh riêng, không nằm trong suite fixture thường ngày:

```powershell
cd frontend
npx.cmd playwright test --config playwright.smoke.config.ts
```

Prerequisite: `.venv-ml` đã cài ML/OCR, model cache và index SigLIP2 khớp catalog hiện hành; file FLEURS smoke đã có trong `artifacts/voice_smoke/fleurs-vi-dev/`. Không tự thu hoặc tạo clip VNStore trong lệnh này.

Config chạy API `127.0.0.1:8011`, Vite `127.0.0.1:5181`, Chrome desktop/mobile tuần tự; tự dừng server sau test. Profile thử nghiệm cố định: PhoWhisper-small + VAD 0,5/250 ms, năng lượng −60 dBFS; SigLIP2 + RapidOCR Latin + OCR RRF weight 0,35; GPU auto, TensorRT off, draft catalog on. **Đây là profile kiểm tra tích hợp, chưa phải cấu hình được chọn trên dev.**

Test dùng mic giả phát lại 4 giây FLEURS và 3 ảnh bao bì Marou khác nhau từ gallery. Mỗi thiết bị có 3 keyword, 3 ảnh tìm đầy đủ (`query_cache=miss`, OCR > 0 ms), 1 lượt đổi bộ lọc trúng cache (`hit`, embed 0 ms) và 3 voice; kiểm tra response/model, OCR không lỗi, transcript sửa được và export 10 lượt. Không chấm WER/Recall/nDCG, không coi ảnh gallery là query độc lập. Desktop chạy trước có thể nạp model; mobile kế tiếp dùng server đã warm. Không so cold start giữa hai thiết bị từ các lượt này.

Ảnh chụp và export lưu dưới `artifacts/stage6-smoke/`. Log và bảng số đo theo từng đợt được liên kết trong `reports/progress/`. Smoke không thay kiểm thử trên điện thoại vật lý, quyền micro người thật hoặc mạng nội bộ thực tế.

## Hồ sơ lựa chọn và tiền kiểm locked test

Chỉ làm sau khi sàng lọc GĐ4 và ablation GĐ5 trên dev đã duyệt. Sao chép `experiments/configs/selection.template.json` thành `selection.json`; người phụ trách ghi người chọn, thời điểm, lý do chất lượng/chi phí/phân nhóm. Không tự điền người duyệt để vượt gate.

Mỗi modality tham chiếu `ablation_report`, `report_sha256`, `run_name`, hash của `run.json` và `predictions.jsonl` được chọn. Lấy hash bằng `Get-FileHash -Algorithm SHA256`, ghi dạng chữ thường. Cấu hình model/revision/env được đọc từ bằng chứng dev, không tự dựng lại từ trí nhớ. Dữ liệu cả train/dev/test phải khóa trước khi chọn; thay manifest/nhãn/split/code thì cần đối chiếu lại dev.

```powershell
.venv/Scripts/python -X utf8 scripts/benchmark/stage6_readiness.py `
  --selection experiments/configs/selection.json `
  --keyword-queries <keyword-reviewed.jsonl> --voice-queries <voice-relevance-reviewed.jsonl>
```

Mặc định dùng catalog, manifest voice/ảnh, registry họ và split plan trong cấu trúc repo. Nếu chọn crop, truyền thêm `--image-crops <fixed-test-crops.json>`; kiểm tra qid/hash nguồn/tọa độ chuẩn hóa. Full-image tường minh là `[0,0,1,1]`; không nhận null. Sidecar test phải được chọn trước khi xem kết quả model, không dùng sidecar dev.

Tiền kiểm ghi file mới vào `reports/acceptance/`: hash đầu vào, tình trạng selection, keyword/voice/ảnh test, cấu hình lấy từ dev và lý do bị chặn. Không nạp model, chạy inference hay tạo prediction test. `blocked` trả mã thoát khác 0. `ready_for_locked_test_review` chỉ nghĩa các điều kiện kiểm tra đã qua, **không phải nghiệm thu**, cũng không đảm bảo pool đủ top K của mọi model.

Các gate chính: selection thực sự có bằng chứng ablation đủ điều kiện và đúng hash/code; cùng catalog/visibility, cùng cấu hình ngôn ngữ sau ASR và nhánh chữ ảnh; test labels đã duyệt, voice consent/transcript/relevance hợp lệ, registry/split ảnh đã khóa. Yêu cầu ít nhất 5 cụm đóng góp cho từng lớp/tác vụ để tránh kết luận từ một cụm. Đây là mức tối thiểu cho CI; mục tiêu quy mô PLAN vẫn cao hơn.

## Chạy và báo cáo locked test khi đủ điều kiện

Chưa chạy trên dữ liệu VNStore (tiền kiểm vẫn blocked). Toàn bộ quy trình dưới đây do `scripts/benchmark/locked_test.py` thực hiện; các bước thủ công phía sau chỉ để hiểu nó làm gì.

### Sổ mở test (`reports/acceptance/locked_test_ledger.jsonl`)

- Append-only, mỗi dòng có `prev_sha256` của dòng trước: sửa hoặc xóa dòng làm `read()` báo "hash chain broken" và mọi lệnh dừng. **Không sửa tay.** Đây là bằng chứng chống sửa, không phải phân quyền: ai đọc được manifest vẫn xem được file test.
- `eval_keyword.py`, `eval_voice.py`, `eval_image.py` với `--split test` từ chối chạy nếu không có `VNSTORE_LOCKED_TEST_ID` của một phiên đang mở có modality đó, và mỗi modality chỉ chạy **một lần** trong phiên. Evaluator tự ghi `run_recorded` (hash `run.json`/`predictions.jsonl`) và `locked_test_id` vào run. Keyword nay cũng cần `--confirm-locked-test`, không nhận `--no-write`/`--allow-unverified` trên test.
- Mở lần thứ hai cần `--rerun-reason`; báo cáo ghi số lần mở, lý do và các lần mở trước dùng cùng dữ liệu test. Nếu đã sửa theo lỗi test thì cần bộ test mới hoặc ghi rõ đây là đánh giá khám phá.

### Lệnh

```powershell
# 1. Tiền kiểm + in lệnh sẽ chạy (không ghi sổ, không inference)
.venv/Scripts/python -X utf8 scripts/benchmark/locked_test.py open --dry-run --opened-by "<người chịu trách nhiệm>" `
  --keyword-queries <keyword-test-reviewed.jsonl> --voice-queries <voice-relevance-reviewed.jsonl> [--image-crops <test-crops.json>]
# 2. Mở test thật: chạy lại tiền kiểm, ghi sổ, chạy 3 evaluator trong tiến trình riêng, đóng phiên, viết báo cáo
.venv/Scripts/python -X utf8 scripts/benchmark/locked_test.py open --opened-by "<người chịu trách nhiệm>" `
  --keyword-queries … --voice-queries … [--image-crops …]
# 3. Gắn số đo browser trên máy/mạng được chốt (JSON của browser_timings.py) → báo cáo mới
.venv/Scripts/python -X utf8 scripts/benchmark/locked_test.py report --id <LT…> --browser <summary.json> [--browser …]
# 4. Người có thẩm quyền ký nghiệm thu (chỉ bước này đặt quyết định)
.venv/Scripts/python -X utf8 scripts/benchmark/locked_test.py signoff --id <LT…> --report <report.json> `
  --by "<tên>" --decision accepted|rejected --note "<lý do, hạn chế>" [--accept-with-limits]
.venv/Scripts/python -X utf8 scripts/benchmark/locked_test.py status   # liệt kê phiên
.venv/Scripts/python -X utf8 scripts/benchmark/locked_test.py close --id <LT…> --reason "<lý do>"  # phiên bị gián đoạn
```

`open` dùng `.venv-ml` cho voice/ảnh (`--ml-python`), xóa mọi biến `VNSTORE_*` của shell (trừ `VNSTORE_MODEL_DIR`, `VNSTORE_TRT_CACHE`) rồi áp đúng env của run dev được chọn; keyword dùng cấu hình ngôn ngữ (`accent_weight`, `min_token_coverage`, `strict_accents`) của selection; ảnh luôn đặt `VNSTORE_IMAGE_CROPS=""` và chỉ truyền `--crops` test khi cấu hình chọn yêu cầu crop. Log từng evaluator nằm ở `reports/acceptance/<LT…>/`.

Báo cáo `reports/acceptance/*_locked-test-<LT…>.md/.json` đối chiếu PLAN §8.4 với N, số cụm và CI 95% bootstrap theo cụm (group_id keyword, người nói voice, họ ảnh): keyword Success@5 ≥ 0,85 và p95 ≤ 500 ms; voice mức giảm Success@5 ≤ 0,10, accuracy giá/phủ định ≥ 0,90, p95 ≤ 3 s (clip ≤ 8 s), chênh Success@5 giữa vùng giọng ≤ 0,10 (cần ≥ 5 người nói mỗi vùng); ảnh Recall@5 exact ≥ 0,80, nDCG@10 similar ≥ 0,70, p95 ≤ 2 s. Trạng thái từng tiêu chí: `met`, `met_uncertain` (điểm đạt nhưng CI cắt ngưỡng), `not_met`, `insufficient_sample` (< 5 cụm, < 20 lượt browser), `incomplete_judgments`, `not_measured`. p95 trong run là pipeline máy chủ; p95 browser chỉ lấy nhóm đúng model đã chọn, không lấy nhóm cache. Báo cáo luôn `benchmark_approved=false`, `acceptance=awaiting_human_signoff`; ký `accepted` khi chưa `all_targets_met` cần `--accept-with-limits` và ghi hạn chế. Tiêu chí hard filter của PLAN dựa vào bộ regression backend, không nằm trong báo cáo này.

Các bước dưới đây là nội dung `open` tự thực hiện; giữ để kiểm tra chéo.

1. Lưu selection, preflight, hash code/dataset, cấu hình máy, rubric và ngân sách đo. Ghi người chịu trách nhiệm mở test và thời điểm; đối chiếu không có run test chính thức trước đó.
2. Áp đúng env từ selection cho **từng modality**. Với crop, thay đường dẫn sidecar dev bằng sidecar test đã khóa; không đổi trọng số/ngưỡng từ lỗi test.
3. Chạy `eval_keyword.py --split test --queries …`; `eval_voice.py --split test --confirm-locked-test --adapter … --queries …`; `eval_image.py --split test --confirm-locked-test --adapter … --families … --split-plan …` (thêm `--crops …` nếu có). Catalog/visibility phải giống dev; evaluator ảnh lấy visibility từ manifest.
4. Lưu run/predictions dưới `experiments/results/`. Kiểm tra không bỏ query, không lỗi OCR, relevance đủ cutoff. Thiếu nhãn không được coi là điểm 0 hoặc âm tính; ghi tình trạng chưa nghiệm thu.
5. Báo cáo riêng keyword nDCG/Success; voice WER/CER, suy giảm retrieval, giá/phủ định, giọng/thiết bị/ồn; ảnh exact/similar/image+text và no-match. Khi so hai run dùng `compare_runs.py` cho CI paired theo người nói/họ; không chọn lại hyperparameter từ test.
6. Gắn số đo browser cùng máy/mạng, RAM/VRAM/model size từ run. Đối chiếu PLAN §8.4: keyword Success@5 ≥85%, p95 ≤500 ms; voice drop ≤10 điểm %, giá/phủ định ≥90%, p95 ≤3 giây với clip ≤8 giây; ảnh Recall@5 ≥80%, nDCG similar ≥0,70, p95 ≤2 giây. Báo số mẫu và hạn chế trước khi kết luận.
7. Lập báo cáo `reports/acceptance/` và `reports/progress/YYYY-MM-DD_GD6_…md`, cập nhật README tiến độ/BACKLOG. Nếu sửa dựa trên lỗi test, xác nhận bằng test mới hoặc ghi rõ đánh giá khám phá.
