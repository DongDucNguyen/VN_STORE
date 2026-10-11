# Hồ sơ nghiệm thu GĐ6

Thư mục lưu báo cáo tiền kiểm và nghiệm thu theo từng đợt; không ghi đè lịch sử.

- `*_stage6-readiness.json/.md`: đầu ra `scripts/benchmark/stage6_readiness.py`; **không chạy inference**. `ready_for_locked_test_review` không phải “đạt benchmark”.
- `locked_test_ledger.jsonl`: sổ mở locked test, append-only có chuỗi hash, do `scripts/benchmark/locked_test.py` và các evaluator ghi. **Không sửa tay**; sửa/xóa dòng làm mọi lệnh dừng. Chưa tồn tại cho tới lần mở test đầu tiên.
- `<LT…>/`: log từng evaluator; `*_locked-test-<LT…>.json/.md`: báo cáo đối chiếu PLAN §8.4 (`awaiting_human_signoff` cho tới khi có `signoff`).
- Hồ sơ locked test chỉ được lập sau khi chọn cấu hình trên dev. Ghi selection/hash, người mở test, thời điểm, các run trong `experiments/results/`, số lần mở test, chất lượng theo tác vụ/phân nhóm và tài nguyên/độ trễ thực.
- Các mục chưa đo hoặc chưa đủ mẫu phải ghi rõ; không dùng smoke FLEURS/gallery/fixture để điền vào kết quả test thật.

Hướng dẫn thực hiện và giới hạn công cụ: [GĐ6](../../docs/giai-doan-6.md). Trạng thái dự án: [README tiến độ](../progress/README.md).
