# GĐ6 — Khóa locked test, báo cáo nghiệm thu, lỗi/hủy browser và cache ảnh — báo cáo ngày 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ6 (PLAN.md mục 9: tích hợp giao diện voice/image, benchmark locked test → báo cáo lựa chọn model và demo end-to-end) |
| Trạng thái | 🟡 Phần agent làm được của GĐ6 đã hoàn tất; **chưa nghiệm thu**: thiếu selection trên dev đã duyệt và dữ liệu test đã duyệt nên chưa mở locked test |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-004-hanhsilk-materials`, SHA-256 `5448a8f4f8161e14cda4f6c3bac921c46af4c02be359dfe20c8ddd312572cecb`, không đổi trước/sau |
| Commit | Chưa commit; không stage/commit/push (người dùng tự commit) |

## 1. Mục tiêu đợt này

Yêu cầu: phân tích tiến độ và hoàn thành toàn bộ GĐ6. Điều kiện PLAN: giao diện voice/ảnh chạy end-to-end, báo cáo lựa chọn model, locked test chạy **một lần** sau khi chốt cấu hình trên dev.

Hiện trạng đầu phiên (đã kiểm tra lại, không chỉ đọc báo cáo cũ): manifest voice 0 clip, manifest ảnh 0 query, 330/330 sản phẩm `draft`, chưa có `families.json`, `image_families.json` hay `selection.json`; chỉ có truy vấn keyword `*_unverified`. Tiền kiểm thật vẫn `blocked` ở 4 mục. Vì vậy **không thể chạy locked test hợp lệ** và không tự tạo nhãn, người duyệt hay selection để vượt gate (quy tắc BACKLOG).

Phần GĐ6 còn mở mà không cần dữ liệu người tạo, theo [báo cáo trước](2026-10-11_GD6_tich-hop-demo-va-tien-kiem.md) mục 6:
1. Không có khóa ngăn mở test nhiều lần; keyword `--split test` thậm chí chạy được không cần xác nhận.
2. Bước 1–7 của quy trình locked test là thao tác tay; chưa có báo cáo đối chiếu PLAN §8.4 và bước ký nghiệm thu.
3. Số đo browser bỏ qua lỗi/hủy.
4. Đổi bộ lọc ảnh chạy lại embedding/OCR trên máy chủ.

## 2. Đã làm

1. **Sổ mở locked test** `scripts/benchmark/locked_ledger.py` → `reports/acceptance/locked_test_ledger.jsonl`: append-only, mỗi dòng mang hash dòng trước; sửa/xóa dòng làm mọi lệnh dừng. Sự kiện `opened`, `run_recorded`, `closed`, `report_written`, `signoff`.
2. **Evaluator chỉ chạy test trong phiên đã mở.** `eval_keyword/voice/image.py --split test` cần `VNSTORE_LOCKED_TEST_ID` của phiên đang mở có modality đó; mỗi modality một lần mỗi phiên; tự ghi hash run vào sổ và `locked_test_id` vào `run.json`. Keyword thêm `--confirm-locked-test`, `--out-root`, `group_id` trong predictions; từ chối `--no-write`/`--allow-unverified` trên test. Train/dev không đổi.
3. **`scripts/benchmark/locked_test.py`** (`open`/`report`/`signoff`/`close`/`status`, có `--dry-run`):
   - `open` chạy lại tiền kiểm (`stage6_readiness.preflight`), chỉ tiếp tục khi `ready_for_locked_test_review`; mở lần hai cần `--rerun-reason` và bị gắn cờ trong mọi báo cáo; chặn khi còn phiên mở.
   - Chạy 3 evaluator trong tiến trình riêng với env **lấy từ run dev được chọn**: xóa mọi `VNSTORE_*` của shell (trừ thư mục cache model/TRT), keyword dùng cấu hình ngôn ngữ của selection, ảnh dùng crop test (không dùng sidecar dev). Log từng evaluator lưu dưới `reports/acceptance/<LT…>/`.
   - Báo cáo đối chiếu PLAN §8.4 với N, số cụm, CI 95% bootstrap theo cụm (group_id/người nói/họ), gồm cả chênh lệch vùng giọng. Trạng thái `met`/`met_uncertain`/`not_met`/`insufficient_sample`/`incomplete_judgments`/`not_measured`; kiểm tra hash run so với sổ trước khi tính. Luôn `benchmark_approved=false`, `awaiting_human_signoff`.
   - `report --browser` gắn số đo browser (chỉ nhóm đúng model đã chọn, ≥ 20 lượt, không lấy nhóm cache); `signoff` chỉ nhận báo cáo đã ghi trong sổ; ký `accepted` khi chưa đạt hết cần `--accept-with-limits` + ghi chú.
   - `stage6_readiness.py` tách `add_input_args`/`write_report` để dùng chung; hành vi CLI không đổi.
4. **Lỗi/hủy trong đo browser.** `measurements.ts` export v2 có `outcomes` (lỗi, hủy/bị thay trước khi vẽ) theo modality, chỉ số đếm; trang `#/diagnostics` hiện tổng. Voice/ảnh đếm lỗi, hủy và yêu cầu bị thay; keyword đếm lỗi và kết quả bị thay trước khi vẽ (không đếm theo cleanup effect vì `StrictMode` gọi hai lần khi mount ở chế độ dev, sẽ ra hủy giả). `browser_timings.py` nhận v1/v2, in bảng thành công/lỗi/hủy/tỉ lệ lỗi.
5. **Cache embedding/OCR khi đổi bộ lọc ảnh.** `QueryCache` trong `app/image/pipeline.py`: khóa SHA-256 ảnh, 8 mục, 120 giây, chỉ trong bộ nhớ, mỗi `ImageService` một cache (catalog/index mới thì rỗng); không lưu khi OCR lỗi. **Chỉ đọc khi trang gửi `reuse=1`** (đổi bộ lọc với ảnh đã chuẩn bị); bấm **Tìm** luôn chạy đầy đủ, evaluator không dùng cache. API trả `visual.query_cache`; mẫu browser có `cached`, CLI tách nhóm cache và không bỏ warmup ở nhóm đó.
   - Bản đầu đọc cache cho mọi request: smoke mobile hỏng vì ảnh đầu trúng cache do desktop vừa tìm trên cùng server → làm lẫn lượt cache vào số đo tìm ảnh. Đã đổi sang `reuse` tường minh.
6. Smoke model thật dùng 3 ảnh bao bì khác nhau (tìm đầy đủ) + 1 lượt đổi bộ lọc (trúng cache), export 10 lượt. Cập nhật [hướng dẫn GĐ6](../../docs/giai-doan-6.md) và [README nghiệm thu](../acceptance/README.md).

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Sổ/evaluator/báo cáo | `.venv/Scripts/python -X utf8 -m pytest backend/tests/test_locked_test.py backend/tests/test_stage6.py -q -p no:cacheprovider` | **38 đạt** (11 mới cho locked test, gồm `open` chạy evaluator thật trong tiến trình con với ASR giả; 6 mới cho browser v2/cache) |
| Cache ảnh qua API | `… pytest backend/tests/test_voice_image_api.py` | 25 đạt; tìm mới không đọc cache, `reuse=1` gọi embedder 0 lần, kết quả lọc giống hệt đường tính lại |
| E2E trọng tâm | `npx.cmd playwright test e2e/stage6.spec.ts e2e/voice_image.spec.ts --reporter=line` | 34 đạt (thêm ca lỗi keyword được đếm ngoài phân bố) |
| Toàn dự án | `.venv/Scripts/python -X utf8 scripts/run_all_tests.py` | **8/8 bước đạt: 569 backend + 2 skip, 22 Pillow, typecheck/build, 116 E2E** ([log](2026-10-11_GD6_hoan-tat-full.log)) |
| Browser model thật | `npx.cmd playwright test --config playwright.smoke.config.ts` trong `frontend` | **2 đạt** (46 s), desktop + mobile giả lập ([log](2026-10-11_GD6_hoan-tat-real-browser.log)) |
| Tiền kiểm dữ liệu thật | `.venv/Scripts/python -X utf8 scripts/benchmark/stage6_readiness.py` | **blocked** đúng như dự kiến ([báo cáo](../acceptance/2026-10-11_053550-610201_stage6-readiness.md)); không inference |
| Sổ mở test | `.venv/Scripts/python -X utf8 scripts/benchmark/locked_test.py status` | "Chưa mở locked test lần nào"; không tạo file sổ |
| Catalog | `sha256sum database.json` | `5448a8f4…` không đổi |

## 4. Số đo — chỉ smoke, không phải benchmark

RTX 5070 Ti, localhost, Chrome desktop và Pixel 7 giả lập; PhoWhisper-small + SigLIP2 + RapidOCR Latin; mic giả phát FLEURS, ảnh gallery Marou. Bỏ 1 lượt warmup mỗi nhóm chạy model, **N=2**: không dùng làm kết luận SLA.

| Thiết bị | Luồng | N | p50 ms | p95 ms |
|---|---|---:|---:|---:|
| Desktop | Keyword | 2 | 51,8 | 55,0 |
| Desktop | Ảnh + OCR (tìm đầy đủ) | 2 | 519,6 | 536,4 |
| Desktop | Ảnh đổi bộ lọc (cache) | 1 | 70,6 | 70,6 |
| Desktop | Voice | 2 | 448,6 | 642,6 |
| Mobile giả lập | Keyword | 2 | 45,5 | 58,1 |
| Mobile giả lập | Ảnh + OCR (tìm đầy đủ) | 2 | 498,1 | 518,3 |
| Mobile giả lập | Ảnh đổi bộ lọc (cache) | 1 | 69,6 | 69,6 |
| Mobile giả lập | Voice | 2 | 535,8 | 539,3 |

0 lỗi, 0 hủy ở cả hai thiết bị. Lượt đầu ảnh desktop 2.022 ms (có nạp model), không phải phép đo cold start có đối chứng. Export: [desktop](../benchmark/2026-10-11_GD6_hoan-tat_browser-desktop.json), [mobile](../benchmark/2026-10-11_GD6_hoan-tat_browser-mobile.json); bảng [desktop](../benchmark/2026-10-11_053849-712158_browser-timings.md), [mobile](../benchmark/2026-10-11_053849-775044_browser-timings.md).

## 5. Khác với kế hoạch

Chưa có báo cáo lựa chọn model cuối và chưa chạy locked test: điều kiện GĐ3–5 (dữ liệu đã duyệt, screening, ablation, selection) chưa có. Đợt này hoàn tất mọi công cụ để khi có dữ liệu, mở test, báo cáo và ký nghiệm thu là các lệnh có kiểm tra, không còn thao tác tay.

## 6. Chưa làm / nợ kỹ thuật

- Sổ là bằng chứng chống sửa, không phải phân quyền: ai đọc được manifest vẫn xem được file test. Xóa cả file sổ không bị phát hiện bởi chính sổ; cần commit sổ sau mỗi lần mở test.
- Keyword không đếm yêu cầu bị thay khi còn chờ phản hồi (xem mục 2.4).
- Cache dùng chung giữa client theo hash ảnh: chỉ trả lại kết quả cho đúng bytes người gửi đã có; vẫn giữ embedding/OCR text tối đa 120 giây trong RAM.
- Tiêu chí hard filter của PLAN §8.4 dựa vào bộ regression backend, không nằm trong báo cáo locked test.
- Smoke vẫn N=2 mỗi nhóm; nghiệm thu độ trễ cần ≥ 20 lượt trên máy/mạng/thiết bị vật lý được chốt.

## 7. Rủi ro và việc đang chặn

Như [README tiến độ](README.md): duyệt/xin quyền 330 sản phẩm, chấm nhãn keyword, thu và duyệt voice/ảnh query, duyệt họ và khóa split, rồi screening GĐ4 → ablation GĐ5 → `selection.json` do người chọn ký tên.

## 8. Bước tiếp theo

Khi tiền kiểm `ready_for_locked_test_review`: `locked_test.py open --dry-run` → `open` → đo browser ≥ 20 lượt trên cấu hình chốt → `report --browser` → người có thẩm quyền `signoff`. Commit sổ và báo cáo sau mỗi bước.
