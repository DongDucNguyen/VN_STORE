# VNStore — Việc ưu tiên tiếp theo (backlog sống)

Cập nhật: 11/10/2026, sau [nối registry họ vào audit/import/evaluator ảnh](2026-10-11_GD3_registry-ho-va-chong-ro-split.md). Catalog vẫn `seed-003-dot-002`, 330 sản phẩm, 814 ảnh; P1.12 đã xong, tiếp theo P1.13 và P1.14.

Khác với các báo cáo theo đợt (không sửa lại), file này **được sửa mỗi phiên**: đánh dấu việc xong, thêm việc mới phát hiện, sắp lại thứ tự. Khi làm một mục thì ghi báo cáo đợt như thường lệ ([TEMPLATE](TEMPLATE.md)), rồi cập nhật mục đó ở đây kèm link báo cáo.

## 0. Hiện trạng một đoạn

Các luồng chính của **mã nguồn demo** đã có; chưa đồng nghĩa hoàn thành nghiệm thu PLAN:
- catalog/API/UI tìm bằng chữ;
- tìm bằng giọng nói/ảnh qua ONNX (4 cấu hình PhoWhisper base/base-fp16/small/small-int8 + Silero VAD, 2 adapter ảnh SigLIP2-base/DINOv2-base); các lần chạy GPU trước được ghi trong báo cáo GĐ4;
- công cụ thu dữ liệu (`#/collect/voice`, `#/collect/image`), nhập, audit, đánh giá và so sánh có CI;
- công cụ duyệt nhãn: `#/review/voice` (bản chép lời), packet pool + trang chấm judgment ảnh, packet keyword toàn catalog hoặc theo pool (107 truy vấn dev), `compare_reviews.py` đối chiếu hai người duyệt voice/ảnh; protocol latency cố định.

Điểm nghẽn là **dữ liệu do con người tạo**, chưa có gì:
- 330/330 sản phẩm còn `draft`, 0 published (catalog `seed-003-dot-002`);
- 814/814 ảnh có quyền `unknown`;
- 74/330 sản phẩm chưa có giá;
- 96 sản phẩm có dưới 2 ảnh, 137 thiếu chất liệu; 2 sản phẩm chưa có claim Việt đủ điều kiện công bố (`p-lys-dia-tron-jasmine-trang-nga-15cm`, `p-vietcraft-gio-may-bau-duc-vh24040`);
- 12 truy vấn keyword seed + 107 truy vấn dev ứng viên chưa duyệt; packet pool trên catalog mới: seed 138 cặp, dev 1.361 cặp (+ no-match chấm đủ catalog) chờ chấm;
- **0 clip giọng nói, 0 ảnh query thật**.

Mọi số đo model hiện chỉ là smoke (FLEURS, leave-one-out gallery), chưa chọn được model theo PLAN §8.3.

## 1. Bắt đầu phiên mới — đọc trước

| Việc | Lệnh / ghi chú |
|---|---|
| Kiểm thử toàn bộ (phải đạt trước và sau khi sửa) | `.venv/Scripts/python scripts/run_all_tests.py` — mốc gần nhất: 8/8, 439 backend (+1 skip), 22 test Pillow (qua `.venv-ml`), 100 E2E. Sandbox có thể chặn thư mục tạm/tiến trình trình duyệt: cần chạy trong môi trường được phép. E2E đôi khi hỏng vì `net::ERR_NO_BUFFER_SPACE`: xem log trước khi kết luận |
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
- Commit `e89cfd0`, `08320a6` đã làm sạch working tree đầu phiên tối 10/10. Các đợt sau đó chưa commit; **người dùng tự commit**, Claude không commit.

### P0.2 Duyệt 330 sản phẩm draft + quyền ảnh → published đầu tiên
- **Vì sao**: chế độ mặc định hiện hiển thị 0 sản phẩm; baseline keyword và benchmark ảnh cần catalog ổn định.
- **Ai**: nhóm dữ liệu (xin phép 7 thương hiệu/nhà sản xuất: Minh Long/Lys, Marou, Hanoia, Kilomet109, Vietcraft, Hanhsilk, SenSilk). Có thể publish dần từng phần, không cần chờ đủ 330.
- **Cách**: checklist [data_collection/README.md](../../data_collection/README.md) và [docs/huong-dan-nhap-lieu.md](../../docs/huong-dan-nhap-lieu.md). Chạy `.venv/Scripts/python scripts/validate_catalog/readiness.py` để xem từng sản phẩm còn thiếu gì.
- **Xong khi**: ≥1 sản phẩm `published` có `reviewed_at`, ảnh có quyền kèm bằng chứng; readiness báo đạt.
- **Lưu ý**: đổi DB sẽ làm lệch `catalog_sha256` của packet keyword và manifest ảnh, nên phải đối chiếu lại nhãn, không chỉ thay hash. Chỉ mục ảnh sẽ báo `index_stale`, cần dựng lại.

### P0.3 Chấm packet keyword → baseline keyword đầu tiên
- **Ai**: 2 người chấm + 1 người phân xử.
- **Cách**:
  1. Mở packet pool trên catalog `seed-003-dot-002`: [seed 12 truy vấn](../../artifacts/keyword_review/2026-10-10_seed-003_seed-12-pool/index.html) và [dev 107 truy vấn](../../artifacts/keyword_review/2026-10-10_seed-003_dev-candidates-107-pool/index.html). Packet cũ (seed-002) đã lệch hash, audit từ chối. Tạo lại bằng `prepare_review.py --pool-top 10 --random 5` nếu mất. Chấm rồi xuất JSONL; hai người dùng cùng một packet. Nhãn nháp chỉ xét 30 sản phẩm cũ; một số truy vấn "no-match" nháp (ví dụ "bàn ghế mây", "áo dài cưới") nay có thể có đáp án.
  2. `scripts/benchmark/audit_reviews.py` → phân xử theo [review_protocol.md](../../benchmarks/keyword/review_protocol.md).
  3. `eval_keyword.py --split dev`.
- **Xong khi**: có run keyword `evaluation_status` khác `smoke_unverified` trên dev, kèm nDCG@10/Success@5 (mục tiêu PLAN: Success@5 ≥ 85%).

### P0.4 Thu dữ liệu giọng nói (pilot rồi mở rộng)
- **Ai**: quản lý dự án (mẫu đồng ý, tuyển người, phân split theo người nói 24/8/8) và người điều phối phiên.
- **Cách**:
  1. Thu bằng `#/collect/voice` (24 câu mẫu, [prompts.ts](../../frontend/src/collect/prompts.ts)).
  2. Nhập: `scripts/benchmark/import_voice_session.py <zip> --dry-run`, rồi nhập thật.
  3. Người duyệt mở zip ở `#/review/voice`, nghe lại, sửa câu, xác nhận, xuất zip đã duyệt; nhập bằng `import_voice_session.py` (phiên mới) hoặc `apply_voice_review.py` (phiên đã nhập).
  4. Xem [benchmarks/voice/README.md](../../benchmarks/voice/README.md).
- **Xong khi (pilot)**: 2–3 người nói, ~60 clip dev đã duyệt. **Mục tiêu PLAN**: 600 clip / 40 người, cân đối Bắc/Trung/Nam, có clip ồn/im lặng/ngoài catalog.

### P0.7 Duyệt họ sản phẩm → families.json
- **Ai**: nhóm dữ liệu. Mở [trang hiện hành](../../artifacts/family_review/2026-10-11_seed-003-validated/index.html) (35 họ, 83 ứng viên ảnh, 8 cụm ảnh dùng chung), xuất quyết định, chạy `scripts/benchmark/apply_family_review.py`. Trang và CLI từ chối mâu thuẫn tách/gộp; nạp được bản nháp cùng proposal từ trang cũ.
- **Xong khi**: `benchmarks/families/families.json` có `status: reviewed`; dùng `family_id` này khi chia split ảnh/keyword. Có thể làm cùng P0.6 (thẻ "Ảnh dùng chung").

### P0.6 Quyết định ảnh minh họa dùng chung trong gallery
- **Vì sao**: 2 ảnh minh họa (Minh Long `…-sm-04`, `…-sm-05`) có mặt ở 7 và 5 bộ trà khác hoa văn; truy vấn ảnh khớp đều các sản phẩm đó. Đợt 001 đã loại ảnh chung tương tự. 2 sản phẩm chỉ có ảnh dùng chung ([báo cáo](2026-10-10_GD3_de-xuat-ho-san-pham.md), `shared_image_clusters`).
- **Ai**: nhóm dữ liệu quyết định giữ/loại; nếu loại, Claude cập nhật bằng importer có diff, dựng lại chỉ mục.

### P0.5 Thu ảnh query độc lập
- **Ai**: nhóm dữ liệu (phân họ sản phẩm vào split 120/40/40, chụp ảnh thật).
- **Cách**:
  1. Thu bằng `#/collect/image`.
  2. Nhập: `scripts/benchmark/import_image_session.py <zip>`; script tự chạy audit.
  3. Chạy `python scripts/benchmark/audit_image_pixels.py` để tìm ảnh gần trùng.
  4. Tạo packet `prepare_image_review.py --split dev --adapter app.ml.image:SigLIP2Base --adapter app.ml.image:DINOv2Base --out …`, người chấm điền judgment + đánh giá độc lập trên trang, áp bằng `apply_image_judgments.py`.
- **Xong khi (pilot)**: ~60 query dev có judgment, gồm ảnh no-match và ảnh khó (nền phức tạp, nhiều vật, ánh sáng vàng, bao bì có chữ).

## 3. P1 — Claude làm được ngay, giảm việc tay cho P0

P1.1–P1.12 đã xong — xem "Đã xong gần đây". Registry thật vẫn cần nhóm dữ liệu duyệt (P0.7); không tự tạo để vượt kiểm tra.

### P1.13 Hoàn thiện đo voice end-to-end theo PLAN §8.2
- `eval_voice.py` đã đo WER/CER, giá/phủ định và latency; chưa có liên kết nhãn relevance để đo nDCG/Success của tìm kiếm từ ASR so với transcript chuẩn.
- Chuẩn bị hợp đồng liên kết query/judgment cùng catalog, kiểm tra coverage và evaluator bằng fixture; chỉ báo chất lượng thật khi có nhãn đã duyệt. Chưa đạt tiêu chí “Success@5 giảm không quá 10 điểm phần trăm”.

### P1.14 Nhập family_review trên trang chấm ảnh
- Backend/schema/apply đã hỗ trợ; hiện người duyệt phải thêm family_review vào JSON export.
- Bổ sung chọn vật thể thuộc catalog hay ngoài catalog, tên/mã họ từ registry đã duyệt, ghi căn cứ và người/thời điểm; xuất và áp qua audit với `--families`. Không suy họ từ relevance. Thêm E2E cho query similar/no-match và nháp chưa đủ.

## 4. P2 — Sau khi có dữ liệu dev

| Việc | Ghi chú |
|---|---|
| Sàng lọc model trên dev (PLAN §8.3 bước 2–3) | `eval_voice.py`/`eval_image.py` cho mọi adapter, rồi `compare_runs.py` (CI theo người nói/họ, cần ≥5 cụm). Chọn 2 ứng viên mỗi modality |
| Hiệu chỉnh ngưỡng trên dev | VAD (0,5; 250 ms), năng lượng −60 dBFS, `RRF_K=60`, `IMAGE_TOP_K=50`, ngưỡng no-match ảnh (dựa vào `top_similarity` mà `eval_image.py` ghi) |
| Gộp hạng ảnh + chữ (RRF) | Catalog 330: ảnh gallery của một giỏ mây chỉ ảnh → hạng 1, thêm chữ "bằng mây" → hạng 7, vì BM25 với từ chung xếp hàng chục giỏ mây khác ngang ảnh. Thử RRF có trọng số/`RRF_K` khác, chỉ dùng chữ làm bộ lọc/boost khi từ quá chung; đo trên dev có nhãn ([báo cáo](2026-10-10_GD1_nhap-dot-002.md)) |
| No-match keyword: khớp lỏng qua trường không dấu | Smoke trên nhãn nháp: 10/12 truy vấn no-match vẫn có kết quả, ví dụ "nước mắm Phú Quốc" → "bát tre cuộn phủ sơn", "gạo ST25" → "bát gáo dừa" ([báo cáo](2026-10-10_GD3_truy-van-keyword-dev.md)). Thử tỉ lệ âm tiết tối thiểu phải khớp, hạ trọng số khớp không dấu khi bản có dấu khác nghĩa, hoặc ngưỡng điểm; **chỉ đánh giá trên dev đã duyệt** (Success@5 không được giảm, false accept no-match giảm) |
| OCR bao bì (PLAN §7.2 bước 3) | Thử RapidOCR/PaddleOCR bản ONNX (chạy được không cần torch), đo trên ảnh bao bì Marou/Minh Long; gộp hạng bằng RRF như ảnh+chữ |
| Semantic retrieval BGE-M3 (PLAN §5 bước 7) | Chỉ sau khi có baseline keyword; dùng bản ONNX; giữ nếu cải thiện nDCG trên dev đủ bù độ trễ |
| Thêm ứng viên model | OpenCLIP, ViCLIP-OT, Qwen3-ASR, PhoWhisper-medium: chưa có bản ONNX tin cậy; cần máy chạy được torch để export, hoặc tìm export chính thức. Ghi provenance như PhoWhisper-small (so hash trọng số) |
| Locked test (PLAN §8.3 bước 4) | Chỉ một lần, sau khi chốt cấu hình trên dev; `--confirm-locked-test` |

## 5. Nợ kỹ thuật nhỏ (làm khi tiện)

- Tiền xử lý ảnh (NumPy) chưa được đối chiếu số học với image processor của Transformers; cần máy có torch để so.
- Bản ONNX PhoWhisper-small là của bên thứ ba (`huuquyet`); nên tự export lại và so đầu ra khi có môi trường torch hợp lệ.
- 26 thư mục `artifacts/keyword-review-test-*` do E2E cũ để lại (test nay đã tự dọn); xóa tay được.
- Trang `#/image` gửi lại ảnh mỗi lần đổi bộ lọc (một lượt embedding mới); có thể cache embedding của ảnh truy vấn nếu cần.
- Pool keyword/ảnh hiện chỉ gồm các baseline đang có; khi thêm hệ thống mới (BGE-M3, OCR…) cần pool bổ sung và chấm thêm.
- Protocol latency chưa đo RAM CPU (peak RSS); đỉnh VRAM là của toàn máy.
- `assets/` 283 MB sau đợt 002 (ảnh gốc, vài PNG 5 MB) + hồ sơ đợt 65 MB: cân nhắc Git LFS/lưu ngoài repo (người dùng quyết định khi commit).
- 9 tên sản phẩm viết hoa toàn bộ và nhiều tên song ngữ/Anh (Marou, Vietcraft) giữ như nguồn; cần biên tập khi duyệt.
- Truy vấn "sản phẩm đang giảm giá" khớp "Giá đỡ điện thoại" qua từ "giá"; cân nhắc khi xử lý no-match.
- TensorRT: chưa đo hai lượt lặp và cold start có cache cho small; `artifacts/trt-cache` không tự dọn engine cũ khi đổi model/driver.
- Starlette cảnh báo `httpx` deprecated trong test (1 warning); cân nhắc `httpx2` khi nâng cấp phụ thuộc.

## 6. Khi xong một mục

1. Ghi báo cáo đợt mới `YYYY-MM-DD_GD<số>_<chủ-đề>.md` (có lệnh kiểm chứng và kết quả).
2. Cập nhật bảng trạng thái và dòng "Kiểm tra gần nhất" trong [README tiến độ](README.md).
3. Sửa file này: chuyển mục sang "Đã xong" bên dưới (kèm link), thêm việc mới phát hiện.

## Đã xong gần đây

- 11/10: P1.12 registry họ cho audit/import/apply/evaluator ảnh; chặn hai SKU anh em vượt split bằng mã họ khác; yêu cầu registry ngoài smoke, ghi hash vào run và kiểm tra khi compare. 29 test mới; 439 backend, 22 Pillow, 100 E2E đạt. Manifest thật vẫn 0 query, chưa có registry đã duyệt ([báo cáo](2026-10-11_GD3_registry-ho-va-chong-ro-split.md)).
- 11/10: P1.11 bảo vệ kết quả duyệt họ: chặn mâu thuẫn gộp bắc cầu/khác họ, gộp ngược nhóm đã tách, mã nhóm trùng, metadata sai; UI báo trước khi xuất. 19 test backend mới; 410 backend, 22 Pillow, 100 E2E đạt. Audit 814 ảnh/API đúng hash; cập nhật số liệu và packet hiện hành ([báo cáo](2026-10-11_GD3_ra-soat-va-bao-ve-duyet-ho.md)).
- 11/10: P1.10 trang duyệt họ có ảnh + `apply_family_review.py` → `families.json` ([báo cáo](2026-10-11_GD3_trang-duyet-ho-san-pham.md)).
- 10/10 (khuya): P1.9 đề xuất họ sản phẩm `propose_families.py`: 279 họ (35 nhiều thành viên), phát hiện 8 cụm ảnh dùng chung giữa sản phẩm khác nhau ([báo cáo](2026-10-10_GD3_de-xuat-ho-san-pham.md)).
- 10/10 (khuya): P1.4 nhập đợt 002 — 300 sản phẩm từ collector riêng, kiểm tra kỹ (checksum, trùng, đối chiếu record, lỗi bóc tách) rồi nhập bằng `import_staging.py` qua `safe_import`; catalog `seed-003-dot-002` 330 sản phẩm; dựng lại chỉ mục ảnh, packet pool mới; xóa `tmp_data/` ([báo cáo](2026-10-10_GD1_nhap-dot-002.md)).
- 10/10 (khuya): P1.8 TensorRT EP tùy chọn (`VNSTORE_ML_TRT=1`, profile shape động, cache engine): cùng WER/Hit@1, p95 ASR −2–9%, ảnh −6–7%, cold start 37–42 giây khi dựng engine; fp16 hỏng với PhoWhisper nên bị chặn; không bật mặc định ([báo cáo](2026-10-10_GD4_tensorrt.md)).
- 10/10 (khuya): P1.6 packet keyword theo pool + trang duyệt/audit hỗ trợ pool, `compare_reviews.py` đối chiếu hai người duyệt voice/ảnh ([báo cáo](2026-10-10_GD3_pool-keyword-va-doi-chieu.md)); P1.7 profile: int8 chậm trên CUDA vì `MatMulInteger` chạy CPU, fp16 (`PhoWhisperBaseFp16`) không nhanh hơn, small fp32 trên CPU p95 2,4 giây ([báo cáo](2026-10-10_GD4_profile-int8-fp16.md)); bộ lọc trên `#/image` + `filters` cho `/search/image` ([báo cáo](2026-10-10_GD6_bo-loc-tim-anh.md)).
- 10/10 (tối): P1.1 trang duyệt bản chép lời `#/review/voice` + `apply_voice_review.py` ([báo cáo](2026-10-10_GD3_duyet-ban-chep-loi.md)); P1.2 packet pool + trang chấm judgment ảnh + `apply_image_judgments.py` ([báo cáo](2026-10-10_GD3_cham-judgment-anh.md)); P1.3 107 truy vấn keyword dev ứng viên + packet ([báo cáo](2026-10-10_GD3_truy-van-keyword-dev.md)); P1.5 protocol latency, 2 lượt chênh p95 1,7% ([báo cáo](2026-10-10_GD4_protocol-latency.md)); nợ nhỏ: `cachedHealth` TTL 15 giây, bước test Pillow trong `run_all_tests.py`, E2E tự dọn packet tạm.
- 10/10: khung voice/ảnh ([báo cáo](2026-10-10_GD4_khung-adapter-voice-anh.md)), adapter ONNX + smoke ([báo cáo](2026-10-10_GD4_adapter-onnx-model-that.md)), công cụ thu âm ([báo cáo](2026-10-10_GD3_cong-cu-thu-am.md)) và thu ảnh ([báo cáo](2026-10-10_GD3_cong-cu-thu-anh.md)), so sánh bootstrap ([báo cáo](2026-10-10_GD4_so-sanh-bootstrap.md)).
