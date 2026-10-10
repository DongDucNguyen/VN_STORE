# GĐ4 — So sánh run voice/ảnh bằng paired bootstrap — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ4–6 (PLAN.md mục 8.3 bước 4: "paired bootstrap theo người nói/họ sản phẩm để ước lượng CI 95%") |
| Trạng thái | ✅ Công cụ xong; chưa có dữ liệu VNStore để dùng thật |
| Người thực hiện | Claude |
| Commit | Chưa commit |

## Đã làm

- `scripts/benchmark/compare_runs.py` so hai run của `eval_voice.py` hoặc `eval_image.py`. Run khác manifest/split/qid hoặc khác cụm của cùng qid thì exit 2, không xuất delta.
- Resample cụm có hoàn lại (voice: `speaker_id`, ảnh: `family_id`); mỗi lượt tính metric cho cả hai run trên cùng mẫu.
  - Voice: WER/CER normalized micro, tính lại từ số lỗi từng clip.
  - Ảnh: chỉ giữ query có metric ở cả hai run.
- CI 95% percentile, 2000 lượt mặc định, seed cố định. **Dưới 5 cụm có dữ liệu thì không báo CI.** Lần chạy thử trên hai run FLEURS (base so với small) lộ ra rằng 1 cụm cho CI thu về một điểm `[-0.0176, -0.0176]`, trông chính xác giả tạo; nay báo "không ước lượng được bất định".
- Hướng dẫn thêm vào README hai bộ benchmark.

## Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| 3 test tổng hợp mới | Cải thiện đồng đều → CI một phía; nửa người nói tốt lên/nửa kém đi → delta −0,05, CI [−0,2; 0,1] chứa 0; run tự so → [0; 0]; 1 cụm → không CI; khác manifest/qid → từ chối; query ảnh thiếu nhãn một bên → loại cả cặp |
| Run FLEURS base vs small | WER normalized 0,127 → 0,109 (−0,018); **không có CI** vì FLEURS không có mã người nói ([báo cáo](../benchmark/2026-10-10_170241-538099_voice-comparison.md)) |
| `scripts/run_all_tests.py` | **7/7**; backend **348 passed, 1 skipped**; **88 E2E passed** |

## Giới hạn

Percentile bootstrap với ít cụm (ví dụ 8 người nói dev) vẫn cho CI hẹp hơn thực tế. Không hiệu chỉnh cho so sánh nhiều cặp. Không dùng để tuning lặp lại trên test.
