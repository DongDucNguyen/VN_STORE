# VNStore — Việc ưu tiên tiếp theo (backlog sống)

Cập nhật mới nhất **12/10/2026**: đã triển khai [bốn nhóm cải thiện voice](2026-10-12_GD5-6_cai-thien-tim-kiem-giong-noi.md), hồ sơ ở [docs/voice-improvements](../../docs/voice-improvements/README.md). Hiện tại là **seed-006-enriched, 330 sản phẩm/328 published/814 ảnh**, voice 0 clip. Các đoạn ghi seed-004/draft bên dưới là bối cảnh lịch sử đã được các đợt 11/10 cập nhật. Kiểm thử mới: 632 backend + 22 Pillow + 126 E2E; 4 smoke ONNX đạt.

**Việc tiếp theo cho voice:** thu/duyệt pilot có tag English, code_switch, nói nhỏ/xa, nhầm n/l; chấm relevance; chạy `experiments/configs/voice-improvements.json` trên dev. UI review/gợi ý, ngôn ngữ theo request và quality đã xong. Gain/high-pass còn tắt mặc định; không tự tạo nhãn hoặc mở locked test để thay cho dữ liệu thiếu. Xem [protocol](../../docs/voice-improvements/05-evaluation.md).

Cập nhật: 11/10/2026, [GĐ6 tích hợp demo và tiền kiểm](2026-10-11_GD6_tich-hop-demo-va-tien-kiem.md), sau [rà soát GĐ5](2026-10-11_GD5_ra-soat-va-hoan-thien.md). Catalog `seed-004-hanhsilk-materials` (`5448a8f4…`), 330 draft, 814 ảnh. Packet/trang hiện hành: keyword `2026-10-11_seed-004_*`, duyệt họ `2026-10-11_seed-004`. GĐ6 đã xong toàn bộ phần công cụ ([hoàn tất](2026-10-11_GD6_hoan-tat-khoa-locked-test.md)): sổ mở test, `locked_test.py` mở/chạy/báo cáo/ký; tiền kiểm locked test vẫn blocked. Cần P0 do con người → screening GĐ4 → chọn cấu hình GĐ5 → locked test GĐ6. Chưa nghiệm thu GĐ5/GĐ6.

Khác với các báo cáo theo đợt (không sửa lại), file này **được sửa mỗi phiên**: đánh dấu việc xong, thêm việc mới phát hiện, sắp lại thứ tự. Khi làm một mục thì ghi báo cáo đợt như thường lệ ([TEMPLATE](TEMPLATE.md)), rồi cập nhật mục đó ở đây kèm link báo cáo.

## 0. Hiện trạng một đoạn

Các luồng chính của **mã nguồn demo** đã có; chưa đồng nghĩa hoàn thành nghiệm thu PLAN:
- catalog/API/UI tìm bằng chữ;
- tìm bằng giọng nói/ảnh qua ONNX (4 cấu hình PhoWhisper base/base-fp16/small/small-int8 + Silero VAD, 3 adapter ảnh SigLIP2-base/DINOv2-base/OpenCLIP ViT-B-32); `screen_models.py` chạy mọi cấu hình và lập bảng chất lượng + chi phí (RAM, VRAM, dung lượng, cold start, lỗi/OOM) vào `reports/model_selection/`;
- công cụ thu dữ liệu (`#/collect/voice`, `#/collect/image`), nhập, audit, đánh giá và so sánh có CI;
- công cụ duyệt nhãn: `#/review/voice` (bản chép lời), packet pool + trang chấm judgment ảnh, packet keyword toàn catalog hoặc theo pool (107 truy vấn dev), `compare_reviews.py` đối chiếu hai người duyệt voice/ảnh; protocol latency cố định.

Điểm nghẽn là **dữ liệu do con người tạo**, chưa có gì:
- 330/330 sản phẩm còn `draft`, 0 published (catalog `seed-004-hanhsilk-materials`);
- 814/814 ảnh có quyền `unknown`;
- 74/330 sản phẩm chưa có giá;
- 96 sản phẩm có dưới 2 ảnh, 128 thiếu chất liệu (9 Hanhsilk đã bổ sung từ mô tả nguồn ngày 11/10); 2 sản phẩm chưa có claim Việt đủ điều kiện công bố (`p-lys-dia-tron-jasmine-trang-nga-15cm`, `p-vietcraft-gio-may-bau-duc-vh24040`);
- 12 truy vấn keyword seed + 107 truy vấn dev ứng viên chưa duyệt; packet pool trên catalog seed-004: seed 138 cặp, dev 1.361 cặp (+ no-match chấm đủ catalog) chờ chấm;
- **0 clip giọng nói, 0 ảnh query thật**.

Mọi số đo model hiện chỉ là smoke (FLEURS, leave-one-out gallery), chưa chọn được model theo PLAN §8.3. Bảng smoke mới nhất: [voice 4 cấu hình](../model_selection/2026-10-11_104115-083089_voice-screening.md), [ảnh 3 adapter](../benchmark/2026-10-11_103215-244030_image-gallery-sanity.md).

## 1. Bắt đầu phiên mới — đọc trước

| Việc | Lệnh / ghi chú |
|---|---|
| Kiểm thử toàn bộ (phải đạt trước và sau khi sửa) | `.venv/Scripts/python scripts/run_all_tests.py` — gần nhất: **8/8, 582 backend (+2 skip), 22 Pillow, typecheck/build, 120 E2E**, typecheck/build ([gợi ý máy 11/10](2026-10-11_GD3_goi-y-may-cham-keyword-va-duyet-ho.md)); riêng **2 smoke browser model thật** đạt ([GĐ6 hoàn tất](2026-10-11_GD6_hoan-tat-khoa-locked-test.md)). Sandbox có thể chặn thư mục tạm/tiến trình trình duyệt: cần chạy trong môi trường được phép. E2E đôi khi hỏng vì `net::ERR_NO_BUFFER_SPACE`: xem log trước khi kết luận |
| Test model thật (tùy chọn) | `VNSTORE_RUN_ML_TESTS=1 .venv-ml/Scripts/python -m pytest backend/tests/test_ml_adapters.py` — 6/6 |
| Hai môi trường Python | `.venv` (API, test, script; không có Pillow/ML) và `.venv-ml` (thêm onnxruntime-gpu, Pillow…, theo `backend/requirements-ml.txt`) |
| **PyTorch bị chặn** | Windows Application Control chặn DLL của torch trên máy này. **Không tìm cách vượt chính sách.** Chỉ dùng ONNX Runtime; việc cần torch (fine-tune, tự export ONNX) phải làm trên máy khác. TensorRT 10.16 (`backend/requirements-ml-trt.txt`) nạp được; bật bằng `VNSTORE_ML_TRT=1` (fp16 bị chặn với ASR vì cho kết quả hỏng) |
| E2E dùng adapter GIẢ | `tests.fakes:FakeASR`, `ByteHistogramEmbedder` + micro giả của Chrome; số đo E2E không phải benchmark |
| Chạy demo với model thật | Xem README mục "Model thật (ONNX Runtime)"; chỉ mục ảnh ở `artifacts/indexes/image/` (dựng lại bằng `scripts/build_indexes/build_image_index.py` khi ảnh/model đổi) |
| Shell trên Windows | Heredoc chứa một số ký tự đặc biệt (ví dụ `'` trong văn bản tiếng Việt, `\\`) có thể lỗi trong Bash tool; khi đó ghi script Python vào thư mục scratchpad rồi chạy. Thêm `-X utf8` khi in tiếng Việt |
| Commit | **Chỉ người dùng được commit** (yêu cầu 10/10). Claude không `git commit`/push/amend, không stage; chỉ báo những gì đã đổi |
| Thư mục staging của collector khác | `tmp_data/` (đợt 002) đã được kiểm tra, nhập và xóa ngày 10/10 theo yêu cầu. Nếu lại có thư mục do chương trình khác đang ghi: **không chạm vào** cho tới khi người dùng cho phép; nhập bằng `scripts/import_raw/import_staging.py` |

**Quy tắc không được vi phạm** (PLAN + các đợt trước):
- Không tự tạo nhãn/judgment/transcript_review, không ghi tên người duyệt thay người, không đổi `usage_rights` sang trạng thái có quyền, không chuyển `draft` sang `published` khi chưa có người duyệt.
- Không sửa báo cáo cũ (chỉ "Đính chính" kèm ngày); số đo trên fixture/smoke không ghi là kết quả benchmark.
- Sửa catalog qua importer (`scripts/import_raw/safe_import.py`), không sửa tay `database.json`. Kiểm tra hash DB trước/sau.
- Không chạy split `test` để tinh chỉnh; locked test chỉ chạy một lần sau khi chốt cấu hình trên dev.

## 2. P0 — Đang chặn tiến độ (cần người; Claude chỉ hỗ trợ)

### P0.1 Commit working tree
- Người dùng đã commit phần duyệt họ và registry tại `8261b59`; lượt xác nhận sau commit đạt. Hồ sơ kiểm chứng mới chưa commit; **người dùng tự commit**, agent không stage/commit/push.

### P0.2 Duyệt 330 sản phẩm draft + quyền ảnh → published đầu tiên
- **Vì sao**: chế độ mặc định hiện hiển thị 0 sản phẩm; baseline keyword và benchmark ảnh cần catalog ổn định.
- **Ai**: nhóm dữ liệu (xin phép 7 thương hiệu/nhà sản xuất: Minh Long/Lys, Marou, Hanoia, Kilomet109, Vietcraft, Hanhsilk, SenSilk). Có thể publish dần từng phần, không cần chờ đủ 330.
- **Cách**: checklist [data_collection/README.md](../../data_collection/README.md) và [docs/huong-dan-nhap-lieu.md](../../docs/huong-dan-nhap-lieu.md). Chạy `.venv/Scripts/python scripts/validate_catalog/readiness.py` để xem từng sản phẩm còn thiếu gì.
- **Xong khi**: ≥1 sản phẩm `published` có `reviewed_at`, ảnh có quyền kèm bằng chứng; readiness báo đạt.
- **Lưu ý**: đổi DB sẽ làm lệch `catalog_sha256` của packet keyword và manifest ảnh, nên phải đối chiếu lại nhãn, không chỉ thay hash. Chỉ mục ảnh sẽ báo `index_stale`, cần dựng lại.

### P0.3 Chấm packet keyword → baseline keyword đầu tiên
- **Ai**: 2 người chấm + 1 người phân xử.
- **Cách**:
  1. Mở packet pool trên catalog `seed-004-hanhsilk-materials`: [seed 12 truy vấn](../../artifacts/keyword_review/2026-10-11_seed-006_seed-12-pool/index.html) và [dev 107 truy vấn](../../artifacts/keyword_review/2026-10-11_seed-006_dev-107-pool/index.html). Packet seed-003/seed-002 đã lệch hash, audit từ chối. Tạo lại bằng `prepare_review.py --pool-top 10 --random 5` nếu mất. Chấm rồi xuất JSONL; hai người dùng cùng một packet. Nhãn nháp chỉ xét 30 sản phẩm cũ; một số truy vấn "no-match" nháp (ví dụ "bàn ghế mây", "áo dài cưới") nay có thể có đáp án.
     **Có gợi ý máy (11/10)**: người chấm thứ nhất/người phân xử có thể dùng packet `…_assisted` ([seed](../../artifacts/keyword_review/2026-10-11_seed-006_seed-12-pool_assisted/index.html), [dev](../../artifacts/keyword_review/2026-10-11_seed-006_dev-107-pool_assisted/index.html)): 6.422 cặp đã có điểm gợi ý kèm lý do, chỉ áp khi bấm, export ghi số đã sửa. **Người chấm thứ hai dùng packet không gợi ý.** Xem [benchmarks/keyword/README.md](../../benchmarks/keyword/README.md#packet-có-gợi-ý-máy-thêm-11102026).
  2. `scripts/benchmark/audit_reviews.py` → phân xử theo [review_protocol.md](../../benchmarks/keyword/review_protocol.md).
  3. `eval_keyword.py --split dev`.
- **Xong khi**: có run keyword `evaluation_status` khác `smoke_unverified` trên dev, kèm nDCG@10/Success@5 (mục tiêu PLAN: Success@5 ≥ 85%).

### P0.4 Thu dữ liệu giọng nói (pilot rồi mở rộng)
- **Ai**: quản lý dự án (mẫu đồng ý, tuyển người, phân split theo người nói 24/8/8) và người điều phối phiên.
- **Cách**:
  1. Rà soát bộ câu train `tr01–tr24` / test `te01–te24` (Claude soạn 11/10) trong [prompts.ts](../../frontend/src/collect/prompts.ts); mỗi split đọc bộ riêng, dev giữ `p01–p24`. Thu bằng `#/collect/voice` (chọn split trước, trang hiện đúng bộ câu).
  2. Nhập: `scripts/benchmark/import_voice_session.py <zip> --dry-run`, rồi nhập thật.
  3. Người duyệt mở zip ở `#/review/voice`, nghe lại, sửa câu, xác nhận, xuất zip đã duyệt; nhập bằng `import_voice_session.py` (phiên mới) hoặc `apply_voice_review.py` (phiên đã nhập).
  4. Xem [benchmarks/voice/README.md](../../benchmarks/voice/README.md).
- **Xong khi (pilot)**: 2–3 người nói, ~60 clip dev đã duyệt. **Mục tiêu PLAN**: 600 clip / 40 người, cân đối Bắc/Trung/Nam, có clip ồn/im lặng/ngoài catalog.

### P0.7 Duyệt họ sản phẩm → families.json
- **Ai**: nhóm dữ liệu. Mở [trang hiện hành](../../artifacts/family_review/2026-10-11_seed-006/index.html) hoặc [trang có gợi ý máy](../../artifacts/family_review/2026-10-11_seed-006_assisted/index.html) (126 thẻ đều có gợi ý kèm lý do, đã kiểm nhất quán; xem kỹ thẻ ghi "cần xem ảnh"), xuất quyết định, chạy `scripts/benchmark/apply_family_review.py`. Trang và CLI từ chối mâu thuẫn tách/gộp; nạp được bản nháp của hai trang seed-003 (nội dung đề xuất trùng khớp).
- **Xong khi**: `benchmarks/families/families.json` có `status: reviewed`. Sau đó **khóa split ảnh**: `plan_splits.py propose --families benchmarks/families/families.json [--design-lines …]`, xem `image_families.md`, rồi `plan_splits.py lock … --locked-by <tên>` ([benchmarks/splits/README.md](../../benchmarks/splits/README.md)). Có thể làm cùng P0.6 (thẻ "Ảnh dùng chung").

### P0.6 Quyết định ảnh minh họa dùng chung trong gallery
- **Vì sao**: 2 ảnh minh họa (Minh Long `…-sm-04`, `…-sm-05`) có mặt ở 7 và 5 bộ trà khác hoa văn; truy vấn ảnh khớp đều các sản phẩm đó. Đợt 001 đã loại ảnh chung tương tự. 2 sản phẩm chỉ có ảnh dùng chung ([báo cáo](2026-10-10_GD3_de-xuat-ho-san-pham.md), `shared_image_clusters`).
- **Ai**: nhóm dữ liệu quyết định giữ/loại; nếu loại, Claude cập nhật bằng importer có diff, dựng lại chỉ mục.

### P0.5 Thu ảnh query độc lập
- **Ai**: nhóm dữ liệu (phân họ sản phẩm vào split 120/40/40, chụp ảnh thật).
- **Cách**:
  1. Thu bằng `#/collect/image`, chỉ chụp họ thuộc split của phiên theo kế hoạch đã khóa (P0.7).
  2. Nhập: `scripts/benchmark/import_image_session.py <zip> --families … --split-plan benchmarks/splits/image_families.json`; script tự chạy audit.
  3. Chạy `python scripts/benchmark/audit_image_pixels.py` để tìm ảnh gần trùng.
  4. Tạo packet `prepare_image_review.py --split dev --adapter app.ml.image:SigLIP2Base --adapter app.ml.image:DINOv2Base --out …`, người chấm điền judgment + đánh giá độc lập trên trang, áp bằng `apply_image_judgments.py`.
- **Xong khi (pilot)**: ~60 query dev có judgment, gồm ảnh no-match và ảnh khó (nền phức tạp, nhiều vật, ánh sáng vàng, bao bì có chữ).

## 3. P1 — Claude làm được ngay, giảm việc tay cho P0

P1.1–P1.16 đã xong phần công cụ — xem "Đã xong gần đây". Registry thật vẫn cần nhóm dữ liệu duyệt (P0.7); không tự tạo để vượt kiểm tra.

### P1.17 Chuyển bản nháp trang chấm keyword khi catalog đổi (tùy chọn)
- Trang duyệt họ đã có `--carry-drafts-from` (11/10). Trang keyword vẫn khóa bản nháp theo hash catalog; mỗi lần catalog đổi (P0.2 publish dần) người chấm phải làm lại. Có thể cho nạp điểm của cặp (qid, sản phẩm) không đổi query và sản phẩm không đổi nội dung hiển thị, đánh dấu phần pool mới cần chấm. Cần quy tắc rõ để không mang nhãn sang sản phẩm đã sửa.

### ~~P1.15 Chuẩn bị packet relevance từ transcript voice đã duyệt~~ — xong 11/10, `prepare_voice_queries.py` ([báo cáo](2026-10-11_GD3_dong-bo-seed-004-va-khoa-split.md))
- P1.13 đã hỗ trợ `eval_voice.py --queries`, nhưng nhóm dữ liệu vẫn phải chuẩn bị query keyword đúng bản chép lời và gắn `keyword_qid`.
- Thêm công cụ sinh query nháp từ transcript đã duyệt, giữ split theo người nói, phát hiện câu/group trùng giữa split; tạo packet bằng công cụ keyword hiện có, kèm mapping qid có hash.
- Chỉ đưa nhãn vào evaluator sau khi người chấm xác nhận; không tự tạo relevance hoặc chép nhãn từ câu gần nghĩa. Khi áp mapping cần kiểm tra transcript/catalog chưa đổi và không ghi đè liên kết đã có.
- Có thể làm bằng fixture trước khi có clip thật; dữ liệu thực vẫn do P0.4/P0.3 cung cấp.

## 4. P2 — Sau khi có dữ liệu dev

GĐ5 đã triển khai `SearchConfig`, OCR Latin ONNX, crop/multi-view và `ablate.py`/`calibrate_no_match.py`; xem [lệnh và điều kiện](../../docs/giai-doan-5.md). Những việc “thử/hiệu chỉnh” bên dưới hiện có công cụ cho ngôn ngữ, VAD, RRF, OCR, crop và ngưỡng; **kết luận chất lượng vẫn chờ nhãn**. Semantic, denoise, contextual biasing/n-best, remove-background và fine-tune chưa triển khai/chưa được chọn. Không bật các biến thể smoke làm mặc định.

| Việc | Ghi chú |
|---|---|
| Sàng lọc model trên dev (PLAN §8.3 bước 2–3) | **Công cụ sẵn sàng** (11/10): `screen_models.py run --modality voice\|image --split dev` (+ `--queries` voice; `--families --split-plan` ảnh) chạy 4 cấu hình voice / 3 ảnh trong `experiments/configs/screening.json`, so bootstrap với cấu hình tốt nhất, gợi ý 2 ứng viên khi dev đã duyệt và ≥5 cụm. Người chọn ghi lý do vào `reports/model_selection/` |
| Hiệu chỉnh ngưỡng trên dev | VAD (0,5; 250 ms), năng lượng −60 dBFS, `RRF_K=60`, `IMAGE_TOP_K=50`, ngưỡng no-match ảnh (dựa vào `top_similarity` mà `eval_image.py` ghi) |
| Gộp hạng ảnh + chữ (RRF) | Catalog 330: ảnh gallery của một giỏ mây chỉ ảnh → hạng 1, thêm chữ "bằng mây" → hạng 7, vì BM25 với từ chung xếp hàng chục giỏ mây khác ngang ảnh. Thử RRF có trọng số/`RRF_K` khác, chỉ dùng chữ làm bộ lọc/boost khi từ quá chung; đo trên dev có nhãn ([báo cáo](2026-10-10_GD1_nhap-dot-002.md)) |
| No-match keyword: khớp lỏng qua trường không dấu | Smoke trên nhãn nháp: 10/12 truy vấn no-match vẫn có kết quả, ví dụ "nước mắm Phú Quốc" → "bát tre cuộn phủ sơn", "gạo ST25" → "bát gáo dừa" ([báo cáo](2026-10-10_GD3_truy-van-keyword-dev.md)). Thử tỉ lệ âm tiết tối thiểu phải khớp, hạ trọng số khớp không dấu khi bản có dấu khác nghĩa, hoặc ngưỡng điểm; **chỉ đánh giá trên dev đã duyệt** (Success@5 không được giảm, false accept no-match giảm) |
| OCR bao bì (PLAN §7.2 bước 3) | Đã triển khai RapidOCR Latin ONNX + weighted RRF, smoke catalog và kiểm thử tích hợp đạt. Còn chấm độ đúng OCR và lợi ích retrieval trên bao bì query độc lập đã duyệt; cold start/lỗi startup được ghi riêng, không được bỏ qua khi chọn cấu hình |
| Semantic retrieval BGE-M3 (PLAN §5 bước 7) | Chỉ sau khi có baseline keyword; dùng bản ONNX; giữ nếu cải thiện nDCG trên dev đủ bù độ trễ |
| Thêm ứng viên model | OpenCLIP đã thêm 11/10 (`OpenCLIPViTB32`, đối chiếu hai bản export độc lập). ViCLIP-OT, Qwen3-ASR, PhoWhisper-medium: chưa có bản ONNX tin cậy; cần máy chạy được torch để export, hoặc tìm export chính thức. Ghi provenance như PhoWhisper-small (so hash trọng số) |
| Locked test (PLAN §8.3 bước 4) | **Công cụ đủ** (11/10): `locked_test.py open --dry-run` → `open` (chạy lại tiền kiểm, ghi sổ chống sửa, chạy 3 evaluator với env dev đã chọn) → `report --browser …` → `signoff` do người có thẩm quyền. Evaluator từ chối split test ngoài phiên đã mở. Tiền kiểm hiện blocked; sổ trống. Làm theo [GĐ6](../../docs/giai-doan-6.md); commit sổ sau mỗi bước |
| Nghiệm thu độ trễ browser/mạng thực | Đã có `#/diagnostics`, export v2 đếm lỗi/hủy, `browser_timings.py` tách nhóm cache. Smoke 20 lượt local chỉ chứng minh tích hợp (N=2 mỗi nhóm). Cần phiên đo ≥ 20 lượt/nhóm trên thiết bị vật lý và mạng được chốt, rồi `locked_test.py report --browser` |

## 5. Nợ kỹ thuật nhỏ (làm khi tiện)

- Tiền xử lý ảnh (NumPy) chưa được đối chiếu số học với image processor của Transformers; cần máy có torch để so.
- Bản ONNX PhoWhisper-small là của bên thứ ba (`huuquyet`); nên tự export lại và so đầu ra khi có môi trường torch hợp lệ.
- 26 thư mục `artifacts/keyword-review-test-*` do E2E cũ để lại (test nay đã tự dọn); xóa tay được.
- ~~Trang `#/image` gửi lại ảnh mỗi lần đổi bộ lọc (một lượt embedding mới)~~: 11/10 đổi bộ lọc gửi `reuse=1`, máy chủ dùng lại embedding/OCR trong bộ nhớ (8 ảnh, 120 giây); ~70 ms so với ~520 ms tìm đầy đủ trên smoke.
- Keyword chưa đếm yêu cầu bị thay khi còn chờ phản hồi trong số đo browser (tránh hủy giả do StrictMode); nếu cần, chuyển tải dữ liệu keyword sang AbortController như trang ảnh.
- Pool keyword/ảnh hiện chỉ gồm các baseline đang có; khi thêm hệ thống mới (BGE-M3, OCR…) cần pool bổ sung và chấm thêm.
- ~~Protocol latency chưa đo RAM CPU~~: run có `resources.peak_rss_mb` + dung lượng file model từ 11/10. Đỉnh VRAM vẫn là của toàn máy (bảng sàng lọc báo thêm phần tăng so với lúc rảnh).
- `assets/` 283 MB sau đợt 002 (ảnh gốc, vài PNG 5 MB) + hồ sơ đợt 65 MB: cân nhắc Git LFS/lưu ngoài repo (người dùng quyết định khi commit).
- 9 tên sản phẩm viết hoa toàn bộ và nhiều tên song ngữ/Anh (Marou, Vietcraft) giữ như nguồn; cần biên tập khi duyệt.
- Truy vấn "sản phẩm đang giảm giá" khớp "Giá đỡ điện thoại" qua từ "giá"; cân nhắc khi xử lý no-match.
- TensorRT small có cache (11/10, [báo cáo](2026-10-11_GD4_sang-loc-model-va-chi-phi.md)): p95 1.032/1.057 ms qua hai lượt (CUDA 1.134), cold start 12–13 s, **đỉnh RAM 5,4 GB** (CUDA 1,4 GB). `artifacts/trt-cache` vẫn không tự dọn engine cũ khi đổi model/driver.
- Starlette cảnh báo `httpx` deprecated trong test (1 warning); cân nhắc `httpx2` khi nâng cấp phụ thuộc.

## 6. Khi xong một mục

1. Ghi báo cáo đợt mới `YYYY-MM-DD_GD<số>_<chủ-đề>.md` (có lệnh kiểm chứng và kết quả).
2. Cập nhật bảng trạng thái và dòng "Kiểm tra gần nhất" trong [README tiến độ](README.md).
3. Sửa file này: chuyển mục sang "Đã xong" bên dưới (kèm link), thêm việc mới phát hiện.

## Đã xong gần đây

- 11/10: [bổ sung tự động + 600 truy vấn](2026-10-11_GD1-2_bo-sung-tu-dong.md) — `enrich_from_archive.py` điền chất liệu/màu có căn cứ từ trang nguồn lưu (catalog seed-006); `criteria_labels.py` + 481 câu mới (train 300, dev +61, test 120 chưa nhãn); baseline nhãn máy dev 0,920 / train 0,859. Việc mới cho GĐ5: no-match, "đầm"→váy, xen tiếng Anh, truy vấn nhu cầu, giá bằng chữ, alias km109. Test 120 câu cần người chấm trước locked test.
- 11/10: [GĐ2 baseline nhãn máy](2026-10-11_GD2_baseline-nhan-may.md) — chủ dự án chọn cho máy chấm 100%; `machine_labels.py` + `eval_keyword.py --machine-labels` (trạng thái `machine_labeled`, cấm cho test). Success@5 0,953, nDCG@10 0,851; no-match nhận nhầm 13/13. P0.3 chỉ còn nếu muốn baseline do người duyệt.
- 11/10: [publish 328 sản phẩm, demo nội bộ](2026-10-11_GD1_publish-demo-noi-bo.md) — chủ dự án xác nhận đã duyệt nguồn; bỏ qua xác minh quyền ảnh qua `publication_policy` (quyền vẫn `unknown`); 2 sản phẩm thiếu tiêu chí Việt giữ draft; dựng lại chỉ mục ảnh, đề xuất họ, packet `seed-005` và gợi ý máy. P0.2 xong phần publish; quyền ảnh còn mở nếu công bố ra ngoài.
- 11/10: [gợi ý máy cho chấm keyword và duyệt họ](2026-10-11_GD3_goi-y-may-cham-keyword-va-duyet-ho.md) — 119 truy vấn / 6.422 cặp và 126 thẻ duyệt họ có điểm/quyết định gợi ý kèm lý do; packet/trang `…_assisted`; chỉ áp khi người bấm, export ghi `assist`, audit cảnh báo khi cả hai người chấm dùng gợi ý. Không tạo nhãn, không ghi `families.json`.
- 11/10: [GĐ6 hoàn tất khóa locked test](2026-10-11_GD6_hoan-tat-khoa-locked-test.md) — sổ `locked_test_ledger.jsonl` append-only có chuỗi hash; `eval_*.py --split test` chỉ chạy trong phiên `locked_test.py open`, một lần mỗi modality; `locked_test.py` chạy cấu hình dev đã chọn, báo cáo PLAN §8.4 với CI theo cụm, gắn số đo browser, ký nghiệm thu; export browser v2 đếm lỗi/hủy; cache embedding/OCR khi đổi bộ lọc ảnh. **8/8 bước đạt, 569 backend (+2 module ML skip), 22 Pillow, typecheck/build, 116 E2E, 2 smoke model thật đạt.** Tiền kiểm thật vẫn blocked; chưa mở test.
- 11/10: [GĐ6 tích hợp demo và tiền kiểm](2026-10-11_GD6_tich-hop-demo-va-tien-kiem.md) — handoff voice không tìm lặp, hủy/chặn response cũ và giải phóng micro, `#/diagnostics`, xuất/tổng hợp độ trễ browser, tiền kiểm selection/test và smoke ONNX/OCR thật qua Chrome desktop/mobile. **550 backend, 22 Pillow, 114 E2E, 2 smoke browser thật đạt**; 18 số đo, ảnh chụp/log đã lưu. Chưa chọn model cuối hoặc chạy locked test; dữ liệu/nhãn/selection vẫn chờ.
- 11/10: [rà soát và hoàn thiện GĐ5](2026-10-11_GD5_ra-soat-va-hoan-thien.md) — sửa readiness theo từng metric/tác vụ, khóa split ảnh, hash nhãn keyword, cold start/lỗi OCR, validation ma trận/crop và cô lập lỗi cấu hình OCR. Thêm 22 regression; toàn bộ 8/8 bước đạt (529 backend, 22 Pillow, 104 E2E), 2 tích hợp model thật đạt. Chưa nghiệm thu GĐ5 vì thiếu dev đã duyệt/ứng viên GĐ4.
- 11/10 (trưa): GĐ4 — adapter ảnh thứ 3 `OpenCLIPViTB32` (OpenCLIP ViT-B-32 laion2B, MIT; bản thị giác của Immich khớp bản export onnx-community, cosine ≥ 0,9999998 trên 41 ảnh); run ghi đỉnh RAM và dung lượng file model; `screen_models.py` + `experiments/configs/screening.json` lập bảng sàng lọc chất lượng + chi phí, ghi lỗi/OOM, bootstrap và Pareto; smoke FLEURS 4 cấu hình voice, gallery 3 adapter ảnh, TensorRT small có cache ([báo cáo](2026-10-11_GD4_sang-loc-model-va-chi-phi.md)). Chưa có dữ liệu dev thật nên chưa chọn model.
- 11/10 (sáng sớm): hoàn tất đồng bộ catalog `seed-004-hanhsilk-materials` (9 chất liệu Hanhsilk do phiên trước nhập qua `safe_import` nhưng chưa ghi báo cáo): dựng lại chỉ mục DINOv2, đề xuất họ (nội dung không đổi), trang duyệt họ seed-004 có `--carry-drafts-from`; **tách bộ câu voice theo split** và chặn câu ở hai split; **P1.15** `prepare_voice_queries.py` draft/apply; **P1.16** `plan_splits.py` lập/khóa split ảnh theo họ, `--split-plan` trong audit/nhập/áp/đánh giá ảnh, locked test cần kế hoạch khóa ([báo cáo](2026-10-11_GD3_dong-bo-seed-004-va-khoa-split.md)).
- 11/10: P1.13 đo nDCG/Success của ASR và transcript chuẩn trên cùng clip đủ nhãn, kiểm tra liên kết/cùng catalog/split, so run kèm bootstrap theo người nói; P1.14 nhập danh tính/họ catalog hoặc ngoài catalog trên trang chấm ảnh, apply với registry đúng hash và audit rò split. [Báo cáo phân tích và triển khai](2026-10-11_GD4_ra-soat-voice-retrieval-va-duyet-ho.md). Chưa có chất lượng benchmark thật; dữ liệu/nhãn/registry vẫn chờ người duyệt.
- 11/10: xác nhận lại commit `8261b59`, 8/8 bước đạt, 439 backend + 1 skip, 22 Pillow, 100 E2E; 814 ảnh/API đúng hash. Không phát hiện lỗi trong phạm vi đã kiểm tra, không sửa mã nguồn ([báo cáo](2026-10-11_GD3_xac-nhan-sau-commit.md)).
- 11/10: P1.12 registry họ cho audit/import/apply/evaluator ảnh; chặn hai SKU anh em vượt split bằng mã họ khác; yêu cầu registry ngoài smoke, ghi hash vào run và kiểm tra khi compare. 29 test mới; 439 backend, 22 Pillow, 100 E2E đạt. Manifest thật vẫn 0 query, chưa có registry đã duyệt ([báo cáo](2026-10-11_GD3_registry-ho-va-chong-ro-split.md)).
- 11/10: P1.11 bảo vệ kết quả duyệt họ: chặn mâu thuẫn gộp bắc cầu/khác họ, gộp ngược nhóm đã tách, mã nhóm trùng, metadata sai; UI báo trước khi xuất. 19 test backend mới; 410 backend, 22 Pillow, 100 E2E đạt. Audit 814 ảnh/API đúng hash; cập nhật số liệu và packet hiện hành ([báo cáo](2026-10-11_GD3_ra-soat-va-bao-ve-duyet-ho.md)).
- 11/10: P1.10 trang duyệt họ có ảnh + `apply_family_review.py` → `families.json` ([báo cáo](2026-10-11_GD3_trang-duyet-ho-san-pham.md)).
- 10/10 (khuya): P1.9 đề xuất họ sản phẩm `propose_families.py`: 279 họ (35 nhiều thành viên), phát hiện 8 cụm ảnh dùng chung giữa sản phẩm khác nhau ([báo cáo](2026-10-10_GD3_de-xuat-ho-san-pham.md)).
- 10/10 (khuya): P1.4 nhập đợt 002 — 300 sản phẩm từ collector riêng, kiểm tra kỹ (checksum, trùng, đối chiếu record, lỗi bóc tách) rồi nhập bằng `import_staging.py` qua `safe_import`; catalog `seed-003-dot-002` 330 sản phẩm; dựng lại chỉ mục ảnh, packet pool mới; xóa `tmp_data/` ([báo cáo](2026-10-10_GD1_nhap-dot-002.md)).
- 10/10 (khuya): P1.8 TensorRT EP tùy chọn (`VNSTORE_ML_TRT=1`, profile shape động, cache engine): cùng WER/Hit@1, p95 ASR −2–9%, ảnh −6–7%, cold start 37–42 giây khi dựng engine; fp16 hỏng với PhoWhisper nên bị chặn; không bật mặc định ([báo cáo](2026-10-10_GD4_tensorrt.md)).
- 10/10 (khuya): P1.6 packet keyword theo pool + trang duyệt/audit hỗ trợ pool, `compare_reviews.py` đối chiếu hai người duyệt voice/ảnh ([báo cáo](2026-10-10_GD3_pool-keyword-va-doi-chieu.md)); P1.7 profile: int8 chậm trên CUDA vì `MatMulInteger` chạy CPU, fp16 (`PhoWhisperBaseFp16`) không nhanh hơn, small fp32 trên CPU p95 2,4 giây ([báo cáo](2026-10-10_GD4_profile-int8-fp16.md)); bộ lọc trên `#/image` + `filters` cho `/search/image` ([báo cáo](2026-10-10_GD6_bo-loc-tim-anh.md)).
- 10/10 (tối): P1.1 trang duyệt bản chép lời `#/review/voice` + `apply_voice_review.py` ([báo cáo](2026-10-10_GD3_duyet-ban-chep-loi.md)); P1.2 packet pool + trang chấm judgment ảnh + `apply_image_judgments.py` ([báo cáo](2026-10-10_GD3_cham-judgment-anh.md)); P1.3 107 truy vấn keyword dev ứng viên + packet ([báo cáo](2026-10-10_GD3_truy-van-keyword-dev.md)); P1.5 protocol latency, 2 lượt chênh p95 1,7% ([báo cáo](2026-10-10_GD4_protocol-latency.md)); nợ nhỏ: `cachedHealth` TTL 15 giây, bước test Pillow trong `run_all_tests.py`, E2E tự dọn packet tạm.
- 10/10: khung voice/ảnh ([báo cáo](2026-10-10_GD4_khung-adapter-voice-anh.md)), adapter ONNX + smoke ([báo cáo](2026-10-10_GD4_adapter-onnx-model-that.md)), công cụ thu âm ([báo cáo](2026-10-10_GD3_cong-cu-thu-am.md)) và thu ảnh ([báo cáo](2026-10-10_GD3_cong-cu-thu-anh.md)), so sánh bootstrap ([báo cáo](2026-10-10_GD4_so-sanh-bootstrap.md)).
