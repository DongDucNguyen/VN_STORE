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

## Chạy đánh giá

```bash
.venv/Scripts/python scripts/benchmark/eval_voice.py --adapter <module:Class> --split dev --name <ten-run>
```

- Kiểm tra schema, qid trùng, người nói ở nhiều split, file và checksum trước khi chạy model.
- Clip chưa duyệt bản chép lời/đồng ý chỉ chạy được trên train/dev với `--allow-unreviewed` (kết quả ghi `smoke_unreviewed`). Split test cần `--confirm-locked-test` và mọi clip đã duyệt.
- Chạy đúng đường của API: giải mã WAV → chặn im lặng (năng lượng < −60 dBFS) → VAD của adapter nếu có → adapter. Clip bị chặn có bản chép lời rỗng và mã `gate_rejected`.
- Metric: WER/CER raw và normalized theo [asr_metrics.py](../../scripts/benchmark/asr_metrics.py) (âm tiết cách trắng; CER giữ dấu, bỏ khoảng trắng; micro), độ đúng giá/phủ định qua bộ phân tích truy vấn, tỉ lệ bịa chữ trên clip im lặng, độ trễ ASR p50/p95, RTF, WER theo vùng/thiết bị/môi trường.
- Ghi `run.json` + `predictions.jsonl` vào `experiments/results/<thời điểm>_voice_<tên>/`.

### Smoke với FLEURS (không phải bộ VNStore)

Trước khi có dữ liệu, `scripts/benchmark/make_fleurs_smoke.py` tạo bộ smoke trong `artifacts/voice_smoke/` từ FLEURS vi_vn dev (CC-BY-4.0): câu đọc kèm một clip nhiễu trắng. Chạy với `--manifest artifacts/voice_smoke/fleurs-vi-dev/manifest.json --allow-unreviewed`. FLEURS không có mã người nói và không phải truy vấn mua sắm, nên chỉ dùng để kiểm tra adapter. Kết quả đầu tiên nằm trong [báo cáo](../../reports/progress/2026-10-10_GD4_adapter-onnx-model-that.md).

Chưa có: bootstrap CI theo người nói, end-to-end nDCG qua `keyword_qid`, n-best/contextual biasing. Không so WER giữa hai bộ test hoặc hai chính sách chuẩn hóa khác nhau.
