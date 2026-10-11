# Bộ đánh giá tìm bằng giọng nói

Mục tiêu PLAN §6.2, §8.1: 600 clip của 40 người nói, chia theo **người nói** 24/8/8 cho train/dev/test. Đây là mục tiêu; hiện [manifest.json](manifest.json) có **0 clip** (`pending_collection`).

## Cấu trúc

```text
benchmarks/voice/
  manifest.json          danh sách clip, hiện rỗng
  manifest.schema.json   hợp đồng dữ liệu 1.0.0
  raw/                   file WAV do người thu cung cấp, bị .gitignore loại trừ
```

Audio giọng nói là dữ liệu cá nhân. Manifest chỉ dùng mã người nói (`speaker_id`), không ghi tên, số điện thoại hay email. Giữ văn bản đồng ý ở kho do quản lý dự án quản lý; `consent.evidence` là mã tham chiếu tới hồ sơ đó.

## Các trường mỗi clip

| Trường | Cách điền |
|---|---|
| `qid` | ID duy nhất, chữ thường/số/gạch nối/gạch dưới |
| `audio_path`, `sha256` | `raw/<tên>.wav` (WAV PCM 16-bit, 8–48 kHz, ≤15 giây — cùng giới hạn API) và SHA-256 của file |
| `reference_text` | Bản chép lời chuẩn do người nghe ghi, giữ dấu, viết số như người nói nói ("ba trăm nghìn"). `null` cho clip im lặng/chỉ tiếng ồn |
| `speaker_id` | Mã người nói; một người chỉ thuộc **một** split |
| `region` | `bac`, `trung`, `nam`, `khac`, `unknown` — vùng giọng theo người nói tự khai |
| `device`, `environment` | Mã thiết bị; `quiet`, `noisy`, `cafe`, `street`, `unknown` |
| `split` | `train`, `dev`, `test` |
| `tags` | Tùy chọn: `brand`, `price`, `negation`, `code_switch`, `out_of_catalog`… để lọc ca khó |
| `keyword_qid` | qid của bộ keyword có nhãn relevance; bắt buộc cho mỗi clip có lời nói khi chạy `--queries`, bỏ trống cho im lặng |
| `consent` | `{status: unknown|granted, evidence}`; `granted` phải có evidence |
| `transcript_review` | `null` hoặc `{reviewed_by, reviewed_at}` sau khi người thứ hai nghe lại tên riêng |

## Thu âm bằng trang `#/collect/voice`

Chạy frontend (`npm run dev`) rồi mở `http://localhost:5173/#/collect/voice` trên máy/điện thoại của phiên thu. Trang này không cần backend và không gửi audio đi đâu.

1. Người điều phối nhập mã người nói, vùng giọng (người nói tự khai), mã thiết bị, môi trường, **split nhóm dữ liệu đã phân cho người nói này** và mã hồ sơ đồng ý, rồi tích ô đồng ý. Thiếu một mục thì nút ghi bị khóa.
2. Người nói đọc tự nhiên từng câu mẫu **của split đã chọn** ([prompts.ts](../../frontend/src/collect/prompts.ts): mỗi split 24 câu riêng gồm thương hiệu, làng nghề, giá, phủ định, xen tiếng Anh, nhu cầu ngoài catalog; dev giữ bộ `p01–p24` cũ, train `tr01–tr24`, test `te01–te24`), sau đó nghe lại hoặc ghi lại. Mỗi lượt tối đa 10 giây. Đã ghi câu nào thì không đổi split được nữa.
3. Bấm **Tải file zip của phiên**: file gồm `manifest.json` đúng schema 1.0.0 và `raw/<qid>.wav` (16 kHz mono PCM16), với qid = `<người nói>-<thời điểm>-<mã câu>`.
4. Nhóm dữ liệu nhập file:

```bash
.venv/Scripts/python scripts/benchmark/import_voice_session.py voice-<...>.zip --dry-run   # kiểm tra
.venv/Scripts/python scripts/benchmark/import_voice_session.py voice-<...>.zip             # nhập
```

Script kiểm tra tên file trong zip, schema, hash, WAV giải mã được theo giới hạn API, qid trùng, người nói ở nhiều split và **câu ở nhiều split**; có lỗi thì không ghi gì.

**Bộ câu tách theo split (11/10/2026).** Trước đây mọi người nói đọc cùng 24 câu. Như vậy fine-tune ASR trên người nói train sẽ học thuộc đúng văn bản của test, và một câu ở cả dev lẫn test không gắn được nhãn keyword (evaluator từ chối cùng câu ở hai split). Nay `import_voice_session.py`, `apply_voice_review.py` và `load_manifest` của `eval_voice.py` từ chối khi một câu, sau chuẩn hóa của `asr_metrics.py` (NFC, chữ thường, bỏ dấu câu, giữ dấu tiếng Việt), xuất hiện ở hai split. Nếu người nói đọc nhầm sang câu của split khác thì ghi lại câu đúng hoặc bỏ clip. Hai bộ train/test mới do Claude soạn theo catalog `seed-004`; nhóm dữ liệu cần rà soát trước phiên thu đầu tiên. `reference_text` ban đầu là câu mẫu. Người duyệt phải nghe lại, sửa câu nếu người nói đọc khác, rồi mới điền `transcript_review` (dùng trang `#/review/voice` bên dưới). Ghi âm trên trình duyệt có thể đã qua khử vọng (echo cancellation), còn khử ồn được tắt.

## Duyệt bản chép lời bằng trang `#/review/voice` (thêm 10/10/2026)

Mở `http://localhost:5173/#/review/voice` và chọn file zip của phiên (zip từ `#/collect/voice`, hoặc zip đã duyệt một phần; zip bị nén lại bằng công cụ hệ điều hành vẫn đọc được). Trang kiểm tra SHA-256 từng clip trước khi hiển thị.

1. Nhập **người duyệt** (tên hoặc mã của chính người đang nghe).
2. Với từng clip: nghe, sửa ô "Bản chép lời" cho đúng điều người nói thực sự nói (giữ dấu, viết số như lời nói), hoặc đánh dấu "Im lặng / chỉ tiếng ồn" (`reference_text = null`). Tích **Đã nghe và xác nhận**. Sửa chữ sau khi xác nhận sẽ bỏ xác nhận.
3. Tùy chọn: **Gợi ý từ ASR** (chỉ hiện khi backend có model voice) gửi clip tới máy chủ VNStore và hiện bản của model bên dưới để tham khảo. Gợi ý **không** được điền vào ô.
4. **Tải zip đã duyệt**: cùng định dạng zip thu âm; clip đã xác nhận có `transcript_review = {reviewed_by, reviewed_at}`, clip chưa xác nhận giữ nguyên.

Nhập kết quả:

```bash
# phiên chưa nhập: nhập thẳng zip đã duyệt
.venv/Scripts/python scripts/benchmark/import_voice_session.py voice-<...>-reviewed-<...>.zip
# phiên đã nhập bản gốc: chỉ áp reference_text + transcript_review theo qid
.venv/Scripts/python scripts/benchmark/apply_voice_review.py voice-<...>-reviewed-<...>.zip --dry-run
.venv/Scripts/python scripts/benchmark/apply_voice_review.py voice-<...>-reviewed-<...>.zip
```

`apply_voice_review.py` kiểm tra zip như khi nhập, yêu cầu qid đã có trong manifest, cùng `sha256` và mọi trường khác (người nói, split, đồng ý…) giống hệt. Clip đã được một lượt khác duyệt chỉ được thay khi thêm `--replace-reviewed`. Có lỗi thì không ghi gì. Script không tạo tên người duyệt; mọi giá trị lấy từ zip người duyệt xuất.

Hai người duyệt độc lập cùng một phiên (mỗi người xuất zip riêng) thì đối chiếu trước khi nhập:

```bash
.venv/Scripts/python scripts/benchmark/compare_reviews.py voice <zip-A> <zip-B>
```

Công cụ chỉ so clip cả hai đã xác nhận; bản chép lời khác nhau (sau NFC và gộp khoảng trắng, vẫn giữ dấu) là bất đồng, kèm CER giữa hai bản. Exit 2 = cần phân xử; người phân xử duyệt lại các clip đó trên trang và xuất lượt mới. Báo cáo vào `reports/benchmark/`.

## Chạy đánh giá

```bash
.venv/Scripts/python scripts/benchmark/eval_voice.py --adapter <module:Class> --split dev --name <ten-run>
```

- Kiểm tra schema, qid trùng, người nói ở nhiều split, file và checksum trước khi chạy model.
- Clip chưa duyệt bản chép lời/đồng ý chỉ chạy được trên train/dev với `--allow-unreviewed` (kết quả ghi `smoke_unreviewed`). Split test cần `--confirm-locked-test` và mọi clip đã duyệt.
- Chạy đúng đường của API: giải mã WAV → chặn im lặng (năng lượng < −60 dBFS) → VAD của adapter nếu có → adapter. Clip bị chặn có bản chép lời rỗng và mã `gate_rejected`.
- Metric: WER/CER raw và normalized theo [asr_metrics.py](../../scripts/benchmark/asr_metrics.py) (âm tiết cách trắng; CER giữ dấu, bỏ khoảng trắng; micro), độ đúng giá/phủ định qua bộ phân tích truy vấn, tỉ lệ bịa chữ trên clip im lặng, độ trễ ASR p50/p95, RTF, WER theo vùng/thiết bị/môi trường.
- Độ trễ theo [latency_protocol.py](../../scripts/benchmark/latency_protocol.py): `--latency-rounds` (mặc định 3) lượt đo trên cùng tập clip, báo p50/p95 từng lượt, p50/p95 gộp và `p95_spread_pct`. Cold start tách riêng (`adapter_load_ms`, `cold_first_call_ms` — lần gọi đầu có nạp model). `run.json` ghi GPU/driver, phiên bản và provider ONNX Runtime, đỉnh VRAM (`nvidia-smi`, toàn máy) và cảnh báo nếu GPU đang có tải khác trước khi đo.
- Ghi `run.json` + `predictions.jsonl` vào `experiments/results/<thời điểm>_voice_<tên>/`.

### Smoke với FLEURS (không phải bộ VNStore)

Trước khi có dữ liệu, `scripts/benchmark/make_fleurs_smoke.py` tạo bộ smoke trong `artifacts/voice_smoke/` từ FLEURS vi_vn dev (CC-BY-4.0): câu đọc kèm một clip nhiễu trắng. Chạy với `--manifest artifacts/voice_smoke/fleurs-vi-dev/manifest.json --allow-unreviewed`. FLEURS không có mã người nói và không phải truy vấn mua sắm, nên chỉ dùng để kiểm tra adapter. Kết quả đầu tiên nằm trong [báo cáo](../../reports/progress/2026-10-10_GD4_adapter-onnx-model-that.md).

Chưa có: n-best/contextual biasing. Bootstrap CI theo người nói: xem mục dưới. Không so WER giữa hai bộ test hoặc hai chính sách chuẩn hóa khác nhau.

### Chuẩn bị nhãn relevance cho bản chép lời đã duyệt (P1.15, thêm 11/10/2026)

```bash
# 1. Truy vấn nháp CHƯA CÓ NHÃN từ clip đã duyệt, chưa liên kết (một split mỗi lần):
.venv/Scripts/python scripts/benchmark/prepare_voice_queries.py draft --split dev --out benchmarks/voice/relevance/<ngay>_dev     --keyword-file benchmarks/keyword/dev_candidates_unverified.jsonl
# 2. Packet chấm như keyword, hai người chấm + phân xử (benchmarks/keyword/review_protocol.md):
.venv/Scripts/python scripts/benchmark/prepare_review.py --queries benchmarks/voice/relevance/<ngay>_dev/queries.jsonl     --include-drafts --pool-top 10 --random 5 --out artifacts/keyword_review/<thu-muc-moi>
.venv/Scripts/python scripts/benchmark/audit_reviews.py --packet artifacts/keyword_review/<thu-muc-moi>/packet.json --include-drafts --review <a>.jsonl --review <b>.jsonl
# 3. Gắn keyword_qid vào manifest (dry-run trước), rồi đo bằng eval_voice.py --queries <nhãn-đã-phân-xử>.jsonl:
.venv/Scripts/python scripts/benchmark/prepare_voice_queries.py apply benchmarks/voice/relevance/<ngay>_dev/links.json <nhan-da-phan-xu>.jsonl --dry-run
```

- **Bước draft** chỉ lấy clip có `transcript_review`, có lời nói, consent `granted` và chưa có `keyword_qid`; báo số clip bị bỏ theo lý do. Mỗi câu (sau chuẩn hóa) thành một truy vấn `vq-<split>-<hash>` và giữ danh sách `voice_clips`. Các câu đọc từ cùng câu mẫu (đuôi qid `-p01`…) chung `group_id = vg-<mã câu>`, kể cả khi người nói đọc khác câu mẫu. `relevance` rỗng, `verified=false`, `labeled_by=unlabeled-voice-draft`: không phải nhãn.
- `links.json` ghi clip → qid kèm hash bản chép lời, hash catalog, hash manifest và truy vấn. `--keyword-file` dừng lại nếu cùng câu đã có ở split khác của bộ keyword; câu trùng cùng split chỉ được liệt kê, không tự dùng nhãn cũ.
- **Bước apply** chỉ ghi khi đủ các điều kiện sau, nếu không thì không ghi gì:
  - catalog hiện tại trùng catalog lúc tạo nháp và `catalog_sha256` của nhãn;
  - nhãn `verified`, query khớp bản chép lời và cùng split, no-match chấm đủ catalog;
  - bản chép lời chưa đổi hoặc chưa bị bỏ duyệt từ bước draft;
  - clip chưa liên kết qid khác (không ghi đè).

  Manifest mới được kiểm tra lại schema, file, hash và split trước khi thay nguyên khối.

### Chất lượng tìm kiếm từ ASR so với transcript chuẩn (P1.13)

```bash
.venv-ml/Scripts/python scripts/benchmark/eval_voice.py --adapter app.ml.asr:PhoWhisperSmall --split dev --queries benchmarks/keyword/<nhan-da-duyet>.jsonl --name voice-retrieval
```

Chạy sau khi thu clip, duyệt transcript và chấm relevance của đúng bản chép lời. Không dùng sẵn relevance của một câu có ý nghĩa gần giống. Manifest thật hiện vẫn rỗng, chưa có kết quả chất lượng VNStore.

- Mỗi clip có lời nói cần `keyword_qid` tồn tại, cùng split; `reference_text` phải khớp `query` sau chuẩn hóa của `asr_metrics.py` (giữ dấu, không quy đổi số). Nhãn cần `catalog_sha256` khớp catalog hiện tại. Kiểm tra toàn bộ file để phát hiện liên kết/split sai trước khi nạp model.
- Mặc định tìm trên published; dùng `--include-drafts` để đo nội bộ trên draft. Nhãn phải thuộc đúng tập sản phẩm hiển thị. No-match phải có nhãn cho toàn gallery. Clip im lặng không liên kết relevance và vẫn được đo hallucination riêng.
- Chạy cùng `SearchEngine` cho transcript chuẩn và kết quả ASR. ASR rỗng hoặc gate chặn tương ứng danh sách kết quả rỗng, giống API. Không dùng hành vi duyệt catalog của truy vấn trống.
- `metrics.retrieval.paired.ndcg_10` và `.success_5` có `reference`, `asr`, `drop`, `n`, `eligible_qids`. **drop = chuẩn − ASR**; Success drop 0,10 tương ứng giảm 10 điểm phần trăm. Chỉ lấy trung bình trên cùng cặp clip đủ nhãn ở cutoff. Thiếu nhãn trả null và ghi `incomplete_qids`, không coi là relevance 0. nDCG dùng gain `2^rel-1`; Success dùng relevance ≥2. IDCG theo nhãn đã chấm trong pool.
- `no_match` báo false accept riêng; `by_group` tách vùng giọng, thiết bị và môi trường. Predictions lưu cả hai danh sách top 20, metric từng clip và kết quả chưa chấm ở top 10.
- `run.retrieval` ghi hash JSONL, liên kết qid, hash mã tìm kiếm, visibility và chính sách metric. `status` là `reviewed_pool`, `incomplete_judgments` hoặc `smoke_unreviewed`. Nhãn chưa duyệt chỉ chạy train/dev với `--allow-unreviewed`; không dùng smoke để chọn model.
- Đây là **chất lượng retrieval end-to-end offline**. `asr_ms` vẫn chỉ đo lời gọi adapter, không phải độ trễ từ trình duyệt đến kết quả. Không tự kết luận đạt PLAN từ một pool nhỏ/thiếu nhãn.

## Sàng lọc nhiều cấu hình (GĐ4, thêm 11/10/2026)

```bash
.venv-ml/Scripts/python scripts/benchmark/screen_models.py run --modality voice --split dev [--queries <nhãn>.jsonl]
```

- Cấu hình nằm trong [experiments/configs/screening.json](../../experiments/configs/screening.json): 4 cấu hình PhoWhisper (base, base-fp16, small, small-int8). Mỗi cấu hình chạy evaluator trong **tiến trình riêng** để RAM/VRAM/cold start không lẫn nhau; `env` chỉ nhận biến `VNSTORE_*` (ví dụ `VNSTORE_ML_DEVICE=cpu`, `VNSTORE_ML_TRT=1`).
- Lỗi, OOM, timeout được ghi thành dòng riêng của bảng, không bị bỏ qua (PLAN §8.3 bước 2). Manifest chưa có mẫu thì báo `pending_collection` và không ghi bảng. Không nhận split `test`.
- Bảng ghi vào `reports/model_selection/<thời điểm>_voice-screening.{md,json}`: WER/CER, WER của vùng giọng kém nhất, độ đúng giá/phủ định, bịa chữ khi im lặng, Success@5 từ ASR và mức giảm so với transcript chuẩn (khi có `--queries`); độ trễ p50/p95 phần model, cold start, đỉnh VRAM toàn máy và phần tăng so với lúc rảnh, đỉnh RAM tiến trình, dung lượng file model (tính từ file adapter đã nạp). Mỗi cấu hình so với cấu hình có metric chính tốt nhất bằng paired bootstrap theo người nói; ★ là Pareto theo (metric chính, p95, dung lượng, đỉnh RAM, VRAM tăng thêm).
- Có run smoke thì tiêu đề là "SMOKE" và không có gợi ý ứng viên. Chỉ khi mọi run là dev đã duyệt và đủ ≥5 cụm, bảng mới gợi ý 2 ứng viên: tốt nhất theo metric chính, và cấu hình rẻ nhất trong nhóm chưa phân biệt được với nó (PLAN §8.3 bước 3, 6). Người quyết định vẫn phải xem phân nhóm, lỗi và ghi lý do.
- `summarize <run_dir>…` lập bảng từ các run đã có; khác manifest/split/tập query/catalog thì exit 2.
- Metric chính: Success@5 từ ASR nếu mọi run có nhãn retrieval, nếu không thì WER chuẩn hóa.
- Smoke FLEURS 11/10/2026: [bảng](../../reports/model_selection/2026-10-11_104115-083089_voice-screening.md) (31 clip, 1 cụm, không dùng để chọn).

## So sánh hai run (paired bootstrap)

```bash
.venv/Scripts/python scripts/benchmark/compare_runs.py --left experiments/results/<run A> --right experiments/results/<run B>
```

Chỉ so khi cùng manifest, split và tập qid; lệch thì exit 2. Resample theo **người nói** có hoàn lại, cho delta và CI 95% của WER/CER normalized (micro, tính lại từ số lỗi). Dưới 5 cụm có dữ liệu thì không báo CI (ví dụ FLEURS chỉ có 1 cụm vì không có mã người nói). Báo cáo ghi vào `reports/benchmark/`. CI chứa 0 nghĩa là chưa phân biệt được hai cấu hình; công cụ không tự chọn model.

Với run có retrieval, cả hai phải có cùng catalog, file nhãn, liên kết qid, visibility, chính sách metric và mã tìm kiếm; kết quả từ transcript chuẩn cũng phải khớp. Báo thêm CI theo người nói cho nDCG/Success từ ASR, mức giảm so với chuẩn và false accept; chỉ giữ clip có metric ở cả hai run. Run ASR-only cũ vẫn so WER/CER được với nhau.
