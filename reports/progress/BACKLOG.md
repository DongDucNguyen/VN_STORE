# VNStore — Việc ưu tiên tiếp theo (backlog sống)

Cập nhật: 10/10/2026, sau [so sánh bootstrap](2026-10-10_GD4_so-sanh-bootstrap.md).

Khác với các báo cáo theo đợt (không sửa lại), file này **được sửa mỗi phiên**: đánh dấu việc xong, thêm việc mới phát hiện, sắp lại thứ tự. Khi làm một mục thì ghi báo cáo đợt như thường lệ ([TEMPLATE](TEMPLATE.md)), rồi cập nhật mục đó ở đây kèm link báo cáo.

## 0. Hiện trạng một đoạn

Toàn bộ phần **mã nguồn** cho demo đã có:
- catalog/API/UI tìm bằng chữ;
- tìm bằng giọng nói/ảnh với 5 adapter ONNX chạy trên GPU (PhoWhisper base/small/small-int8 + Silero VAD, SigLIP2-base, DINOv2-base);
- công cụ thu dữ liệu (`#/collect/voice`, `#/collect/image`), nhập, audit, đánh giá và so sánh có CI.

Điểm nghẽn là **dữ liệu do con người tạo**, chưa có gì:
- 30/30 sản phẩm còn `draft`, 0 published;
- 45/45 ảnh có quyền `unknown`;
- 14/30 sản phẩm chưa có giá;
- 12 truy vấn keyword seed chưa duyệt, packet 360 cặp chờ chấm;
- **0 clip giọng nói, 0 ảnh query thật**.

Mọi số đo model hiện chỉ là smoke (FLEURS, leave-one-out gallery), chưa chọn được model theo PLAN §8.3.

## 1. Bắt đầu phiên mới — đọc trước

| Việc | Lệnh / ghi chú |
|---|---|
| Kiểm thử toàn bộ (phải đạt trước và sau khi sửa) | `.venv/Scripts/python scripts/run_all_tests.py` — mốc gần nhất: 7/7, 348 backend (+1 skip), 88 E2E |
| Test model thật (tùy chọn) | `VNSTORE_RUN_ML_TESTS=1 .venv-ml/Scripts/python -m pytest backend/tests/test_ml_adapters.py` — 6/6 |
| Hai môi trường Python | `.venv` (API, test, script; không có Pillow/ML) và `.venv-ml` (thêm onnxruntime-gpu, Pillow…, theo `backend/requirements-ml.txt`) |
| **PyTorch bị chặn** | Windows Application Control chặn DLL của torch trên máy này. **Không tìm cách vượt chính sách.** Chỉ dùng ONNX Runtime; việc cần torch (fine-tune, tự export ONNX) phải làm trên máy khác |
| E2E dùng adapter GIẢ | `tests.fakes:FakeASR`, `ByteHistogramEmbedder` + micro giả của Chrome; số đo E2E không phải benchmark |
| Chạy demo với model thật | Xem README mục "Model thật (ONNX Runtime)"; chỉ mục ảnh ở `artifacts/indexes/image/` (dựng lại bằng `scripts/build_indexes/build_image_index.py` khi ảnh/model đổi) |
| Shell trên Windows | Heredoc chứa một số ký tự đặc biệt có thể lỗi trong Bash tool; khi đó ghi script Python vào thư mục scratchpad rồi chạy. Thêm `-X utf8` khi in tiếng Việt |
| Working tree | Đầu phiên 10/10 còn **rất nhiều thay đổi chưa commit** (chỉ có commit "Upload version 1"). Kiểm tra `git status`, nhắc người dùng commit trước khi làm việc lớn |

**Quy tắc không được vi phạm** (PLAN + các đợt trước):
- Không tự tạo nhãn/judgment/transcript_review, không ghi tên người duyệt thay người, không đổi `usage_rights` sang trạng thái có quyền, không chuyển `draft` sang `published` khi chưa có người duyệt.
- Không sửa báo cáo cũ (chỉ "Đính chính" kèm ngày); số đo trên fixture/smoke không ghi là kết quả benchmark.
- Sửa catalog qua importer (`scripts/import_raw/safe_import.py`), không sửa tay `database.json`. Kiểm tra hash DB trước/sau.
- Không chạy split `test` để tinh chỉnh; locked test chỉ chạy một lần sau khi chốt cấu hình trên dev.

## 2. P0 — Đang chặn tiến độ (cần người; Claude chỉ hỗ trợ)

### P0.1 Commit working tree
- **Vì sao**: rủi ro mất việc; phiên sau khó biết thay đổi nào của đợt nào.
- **Ai**: người dùng. Message gợi ý có trong lịch sử hội thoại 10/10; có thể tách commit theo đợt (taxonomy/công cụ GĐ2–3 và voice/ảnh GĐ4).
- **Xong khi**: `git status` sạch (trừ file sinh ra trong `artifacts/`, vốn bị `.gitignore`).

### P0.2 Duyệt 30 sản phẩm draft + quyền ảnh → published đầu tiên
- **Vì sao**: chế độ mặc định hiện hiển thị 0 sản phẩm; baseline keyword và benchmark ảnh cần catalog ổn định.
- **Ai**: nhóm dữ liệu (xin phép 5 thương hiệu: Minh Long/Lys, Marou, Hanoia, Kilomet109, Vietcraft).
- **Cách**: checklist [data_collection/README.md](../../data_collection/README.md) và [docs/huong-dan-nhap-lieu.md](../../docs/huong-dan-nhap-lieu.md). Chạy `.venv/Scripts/python scripts/validate_catalog/readiness.py` để xem từng sản phẩm còn thiếu gì.
- **Xong khi**: ≥1 sản phẩm `published` có `reviewed_at`, ảnh có quyền kèm bằng chứng; readiness báo đạt.
- **Lưu ý**: đổi DB sẽ làm lệch `catalog_sha256` của packet keyword và manifest ảnh, nên phải đối chiếu lại nhãn, không chỉ thay hash. Chỉ mục ảnh sẽ báo `index_stale`, cần dựng lại.

### P0.3 Chấm packet keyword 360 cặp → baseline keyword đầu tiên
- **Ai**: 2 người chấm + 1 người phân xử.
- **Cách**:
  1. Mở [trang duyệt](../../artifacts/keyword_review/2026-10-10_seed-002-taxonomy/index.html), chấm, rồi xuất JSONL.
  2. `scripts/benchmark/audit_reviews.py` → phân xử theo [review_protocol.md](../../benchmarks/keyword/review_protocol.md).
  3. `eval_keyword.py --split dev`.
- **Xong khi**: có run keyword `evaluation_status` khác `smoke_unverified` trên dev, kèm nDCG@10/Success@5 (mục tiêu PLAN: Success@5 ≥ 85%).

### P0.4 Thu dữ liệu giọng nói (pilot rồi mở rộng)
- **Ai**: quản lý dự án (mẫu đồng ý, tuyển người, phân split theo người nói 24/8/8) và người điều phối phiên.
- **Cách**:
  1. Thu bằng `#/collect/voice` (24 câu mẫu, [prompts.ts](../../frontend/src/collect/prompts.ts)).
  2. Nhập: `scripts/benchmark/import_voice_session.py <zip> --dry-run`, rồi nhập thật.
  3. Người duyệt nghe lại, sửa `reference_text`, điền `transcript_review`.
  4. Xem [benchmarks/voice/README.md](../../benchmarks/voice/README.md).
- **Xong khi (pilot)**: 2–3 người nói, ~60 clip dev đã duyệt. **Mục tiêu PLAN**: 600 clip / 40 người, cân đối Bắc/Trung/Nam, có clip ồn/im lặng/ngoài catalog.

### P0.5 Thu ảnh query độc lập
- **Ai**: nhóm dữ liệu (phân họ sản phẩm vào split 120/40/40, chụp ảnh thật).
- **Cách**:
  1. Thu bằng `#/collect/image`.
  2. Nhập: `scripts/benchmark/import_image_session.py <zip>`; script tự chạy audit.
  3. Chạy `python scripts/benchmark/audit_image_pixels.py` để tìm ảnh gần trùng.
  4. Người duyệt điền `independence_review` và `judgment`.
- **Xong khi (pilot)**: ~60 query dev có judgment, gồm ảnh no-match và ảnh khó (nền phức tạp, nhiều vật, ánh sáng vàng, bao bì có chữ).

## 3. P1 — Claude làm được ngay, giảm việc tay cho P0

### P1.1 Trang duyệt bản chép lời (`#/review/voice`)
- **Vì sao**: P0.4 hiện phải sửa `reference_text` và `transcript_review` trực tiếp trong JSON.
- **Làm**: mở zip của phiên (đọc định dạng zip "store" do [zip.ts](../../frontend/src/collect/zip.ts) tạo, chỉ cần đọc local header), phát từng clip, sửa câu, nhập tên người duyệt, xuất zip mới. Tùy chọn: hiện bản chép lời của PhoWhisper làm gợi ý nhưng **không tự điền**. `import_voice_session.py` cần nhận thêm bản đã duyệt, hoặc thêm script áp review vào manifest theo qid.
- **Xong khi**: E2E ghi → duyệt → nhập đạt; manifest có `transcript_review` do người nhập.

### P1.2 Pool + trang chấm judgment cho ảnh query
- **Vì sao**: PLAN §8.1 yêu cầu gom top kết quả của mọi baseline cộng mẫu ngẫu nhiên để chấm; hiện chưa có công cụ.
- **Làm**:
  1. Script tạo packet: với mỗi query trong `benchmarks/image/manifest.json`, lấy top 10 của SigLIP2, DINOv2 và baseline giả, cộng vài sản phẩm ngẫu nhiên, rồi sinh trang HTML chấm offline, tương tự `scripts/benchmark/prepare_review.py` + `review_template.html` của keyword.
  2. Script áp kết quả chấm vào `judgment`, chạy audit.
- **Xong khi**: chấm xong một packet thử trên dữ liệu tổng hợp (E2E/pytest), audit `recorded_checks_passed` với judgment do người nhập.

### P1.3 Mở rộng bộ truy vấn keyword (12 → ~100 dev → 600)
- **Làm**:
  1. Soạn truy vấn ứng viên theo ý định: tìm món cụ thể, nhu cầu ("quà tặng mẹ"), giá, phủ định, không dấu/Telex, vùng miền ("ly/cốc", "chén/bát"), thương hiệu/làng nghề, no-match ~10–15%.
  2. Ghi `verified=false`, nhóm `group_id` cho các câu diễn đạt lại.
  3. Sinh packet bằng `prepare_review.py`.
- **Xong khi**: file JSONL mới + packet chờ chấm; tuyệt đối không tự ghi nhãn đã duyệt.

### P1.4 Mở rộng catalog 30 → 300 (đợt 002+)
- **Hiện trạng**: 30 sản phẩm thuộc 5 nhóm gốc (mây tre cói 7, gốm sứ 6, thực phẩm 6, dệt may 6, gỗ/sơn mài 5); 8 sản phẩm không có brand; 19/30 chỉ có 1 ảnh. Mục tiêu PLAN: ~60/nhóm, 2–4 ảnh/sản phẩm.
- **Làm**: theo pipeline sẵn có: `data_collection/raw/*.json` → `scripts/import_raw/build_drafts.py` → `safe_import.py` (giữ chỉnh sửa biên tập, diff, snapshot) → `collect_images.py`/`apply_images.py`. Nguồn ưu tiên là website chính thức. Không bịa giá; thiếu giá thì để `null`.
- **Xong khi**: catalog mới validate đạt, báo cáo thiếu dữ liệu, chỉ mục ảnh dựng lại, `run_all_tests` đạt. Mọi sản phẩm mới vẫn là `draft`.
- **Lưu ý**: đổi catalog sẽ vô hiệu hóa packet/manifest đang gắn hash cũ; nên chốt với người dùng trước khi làm, nếu P0.3/P0.5 đang chấm dở.

### P1.5 Protocol đo latency cố định
- **Vì sao**: hai lượt cùng cấu hình PhoWhisper-base cho p95 506 so với 916 ms; chưa so được độ trễ.
- **Làm**:
  - Thêm vào `eval_voice.py`/`eval_image.py`: số lượt lặp, warm-up, ghi tên GPU/driver/provider ORT và peak VRAM (`nvidia-smi --query-gpu=memory.used`), cảnh báo khi máy đang tải.
  - Đo riêng cold start.
  - Profile bản int8 (chậm ~3 lần trên CUDA EP); thử `PhoWhisperSmall` fp16 hoặc TensorRT EP.
- **Xong khi**: hai lượt liên tiếp cùng cấu hình cho p95 chênh <10%.

## 4. P2 — Sau khi có dữ liệu dev

| Việc | Ghi chú |
|---|---|
| Sàng lọc model trên dev (PLAN §8.3 bước 2–3) | `eval_voice.py`/`eval_image.py` cho mọi adapter, rồi `compare_runs.py` (CI theo người nói/họ, cần ≥5 cụm). Chọn 2 ứng viên mỗi modality |
| Hiệu chỉnh ngưỡng trên dev | VAD (0,5; 250 ms), năng lượng −60 dBFS, `RRF_K=60`, `IMAGE_TOP_K=50`, ngưỡng no-match ảnh (dựa vào `top_similarity` mà `eval_image.py` ghi) |
| OCR bao bì (PLAN §7.2 bước 3) | Thử RapidOCR/PaddleOCR bản ONNX (chạy được không cần torch), đo trên ảnh bao bì Marou/Minh Long; gộp hạng bằng RRF như ảnh+chữ |
| Semantic retrieval BGE-M3 (PLAN §5 bước 7) | Chỉ sau khi có baseline keyword; dùng bản ONNX; giữ nếu cải thiện nDCG trên dev đủ bù độ trễ |
| Thêm ứng viên model | OpenCLIP, ViCLIP-OT, Qwen3-ASR, PhoWhisper-medium: chưa có bản ONNX tin cậy; cần máy chạy được torch để export, hoặc tìm export chính thức. Ghi provenance như PhoWhisper-small (so hash trọng số) |
| Locked test (PLAN §8.3 bước 4) | Chỉ một lần, sau khi chốt cấu hình trên dev; `--confirm-locked-test` |

## 5. Nợ kỹ thuật nhỏ (làm khi tiện)

- Trang `#/image` chưa có bảng bộ lọc như trang tìm chữ (chỉ có ô "Yêu cầu thêm").
- `cachedHealth()` ở frontend không làm mới trạng thái model cho đến khi tải lại trang.
- Tiền xử lý ảnh (NumPy) chưa được đối chiếu số học với image processor của Transformers; cần máy có torch để so.
- Bản ONNX PhoWhisper-small là của bên thứ ba (`huuquyet`); nên tự export lại và so đầu ra khi có môi trường torch hợp lệ.
- Bộ test Pillow `scripts/benchmark/tests/test_image_pixels.py` chưa nằm trong `run_all_tests.py`; có thể thêm bước tùy chọn chạy bằng `.venv-ml`.
- Starlette cảnh báo `httpx` deprecated trong test (1 warning); cân nhắc `httpx2` khi nâng cấp phụ thuộc.

## 6. Khi xong một mục

1. Ghi báo cáo đợt mới `YYYY-MM-DD_GD<số>_<chủ-đề>.md` (có lệnh kiểm chứng và kết quả).
2. Cập nhật bảng trạng thái và dòng "Kiểm tra gần nhất" trong [README tiến độ](README.md).
3. Sửa file này: chuyển mục sang "Đã xong" bên dưới (kèm link), thêm việc mới phát hiện.

## Đã xong gần đây

- 10/10: khung voice/ảnh ([báo cáo](2026-10-10_GD4_khung-adapter-voice-anh.md)), adapter ONNX + smoke ([báo cáo](2026-10-10_GD4_adapter-onnx-model-that.md)), công cụ thu âm ([báo cáo](2026-10-10_GD3_cong-cu-thu-am.md)) và thu ảnh ([báo cáo](2026-10-10_GD3_cong-cu-thu-anh.md)), so sánh bootstrap ([báo cáo](2026-10-10_GD4_so-sanh-bootstrap.md)).
