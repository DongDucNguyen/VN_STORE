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
| `keyword_qid` | Tùy chọn: qid của bộ keyword có nhãn relevance, để đo end-to-end sau này |
| `consent` | `{status: unknown|granted, evidence}`; `granted` phải có evidence |
| `transcript_review` | `null` hoặc `{reviewed_by, reviewed_at}` sau khi người thứ hai nghe lại tên riêng |

## Thu âm bằng trang `#/collect/voice`

Chạy frontend (`npm run dev`) rồi mở `http://localhost:5173/#/collect/voice` trên máy/điện thoại của phiên thu. Trang này không cần backend và không gửi audio đi đâu.

1. Người điều phối nhập mã người nói, vùng giọng (người nói tự khai), mã thiết bị, môi trường, **split nhóm dữ liệu đã phân cho người nói này** và mã hồ sơ đồng ý, rồi tích ô đồng ý. Thiếu một mục thì nút ghi bị khóa.
2. Người nói đọc tự nhiên từng câu mẫu ([prompts.ts](../../frontend/src/collect/prompts.ts), 24 câu gồm thương hiệu, làng nghề, giá, phủ định, xen tiếng Anh và một nhu cầu ngoài catalog), sau đó nghe lại hoặc ghi lại. Mỗi lượt tối đa 10 giây.
3. Bấm **Tải file zip của phiên**: file gồm `manifest.json` đúng schema 1.0.0 và `raw/<qid>.wav` (16 kHz mono PCM16), với qid = `<người nói>-<thời điểm>-<mã câu>`.
4. Nhóm dữ liệu nhập file:

```bash
.venv/Scripts/python scripts/benchmark/import_voice_session.py voice-<...>.zip --dry-run   # kiểm tra
.venv/Scripts/python scripts/benchmark/import_voice_session.py voice-<...>.zip             # nhập
```

Script kiểm tra tên file trong zip, schema, hash, WAV giải mã được theo giới hạn API, qid trùng và người nói ở nhiều split; có lỗi thì không ghi gì. `reference_text` ban đầu là câu mẫu. Người duyệt phải nghe lại, sửa câu nếu người nói đọc khác, rồi mới điền `transcript_review` (dùng trang `#/review/voice` bên dưới). Ghi âm trên trình duyệt có thể đã qua khử vọng (echo cancellation), còn khử ồn được tắt.

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

Chưa có: end-to-end nDCG qua `keyword_qid`, n-best/contextual biasing. Bootstrap CI theo người nói: xem mục dưới. Không so WER giữa hai bộ test hoặc hai chính sách chuẩn hóa khác nhau.

## So sánh hai run (paired bootstrap)

```bash
.venv/Scripts/python scripts/benchmark/compare_runs.py --left experiments/results/<run A> --right experiments/results/<run B>
```

Chỉ so khi cùng manifest, split và tập qid; lệch thì exit 2. Resample theo **người nói** có hoàn lại, cho delta và CI 95% của WER/CER normalized (micro, tính lại từ số lỗi). Dưới 5 cụm có dữ liệu thì không báo CI (ví dụ FLEURS chỉ có 1 cụm vì không có mã người nói). Báo cáo ghi vào `reports/benchmark/`. CI chứa 0 nghĩa là chưa phân biệt được hai cấu hình; công cụ không tự chọn model.
