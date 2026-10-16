# Chọn model cho trợ lý tư vấn — 16/10/2026

**Kết luận:** chạy demo bằng **Qwen/Qwen3-4B-Instruct-2507** (bản ONNX q4f16 `onnx-community/Qwen3-4B-Instruct-2507-ONNX@2bdfea44`, Apache-2.0) trên GPU, prompt/luồng **`assistant-2026-10-16.v3.3`**. Không dùng API trả phí (chủ dự án: không có ngân sách API, ưu tiên cục bộ).

Đây là **sàng lọc kỹ thuật trên split dev**, không phải locked test. Nhóm `kw` dùng nhãn người duyệt; các nhóm còn lại do trợ lý lập trình soạn và duyệt tự động theo ủy quyền của chủ dự án ([benchmarks/assistant](../../benchmarks/assistant/README.md)). Mỗi nhóm phụ chỉ có 4–32 ca, nên chênh lệch một ca đã thấy trên điểm tổng.

## 1. Ứng viên và điều kiện chạy

| Ứng viên | Bản ONNX | License | Chạy được trên máy demo? |
|---|---|---|---|
| Qwen3-4B-Instruct-2507 | q4f16, 2,9 GB | Apache-2.0 | ✅ ORT 1.20.2 CUDA |
| Qwen3-1.7B (tắt suy luận) | q4f16, 1,4 GB | Apache-2.0 | ✅ ORT 1.20.2 CUDA |
| Llama-3.2-3B-Instruct | q4f16, 2,4 GB | Llama 3.2 Community | ✅ ORT 1.20.2 CUDA |
| Qwen3.5-4B (phần văn bản) | q4f16, 2,8 GB | Apache-2.0 | ❌ loại, xem dưới |
| Gemma-4-E2B-it (phần văn bản) | q4f16, 3,1 GB | Apache-2.0 | ❌ loại, xem dưới |

Tất cả tải về đều kiểm SHA-256 theo revision ghim (`scripts/download_llm_models.py`).

**Qwen3.5-4B và Gemma-4-E2B bị loại vì không chạy được đủ nhanh trên máy demo, không phải vì chất lượng:**
- đồ thị dùng GroupQueryAttention 11 đầu vào; ORT 1.20.2 (bản CUDA duy nhất chạy với driver 566.14) báo `INVALID_GRAPH`;
- ORT 1.24 DirectML: nạp được nhưng giải mã sai từ token thứ hai;
- ORT 1.24 CPU: tiếng Việt đúng và tự nhiên, nhưng chỉ 3,7 token/s (Qwen3.5-4B) và 6,6 token/s (Gemma-4-E2B). Câu trả lời khoảng 150–300 token sẽ mất 25–80 giây, vượt ngưỡng p95 ≤ 30 s.

Nếu nâng driver NVIDIA lên bản hỗ trợ CUDA ≥ 12.8 và dùng ORT CUDA mới, nên sàng lọc lại hai model này.

**Lỗi runtime đã vòng qua:** ORT 1.20 CUDA trả NaN ở lượt có KV cache rỗng (mọi model, mọi độ dài). `app/ml/llm.py` tính KV của token mở đầu chat template một lần trên CPU, rồi tiếp tục trên GPU. Do attention nhân quả, kết quả tương đương chạy toàn bộ. Có test hồi quy model thật trong `backend/tests/test_llm_adapter.py`.

## 2. Sàng lọc v1 — cùng prompt, cùng mã (106 kịch bản `screen`)

| Model | Score | kw S@3 | need hit@3 | no-match | multi | trung thực đánh giá | JSON hợp lệ | dự phòng | p50 / p95 | token/s | VRAM sau nạp / đỉnh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-4B-Instruct | **0,794** | 0,800 | 0,750 | 4/4 | 0,500 | 100% | 100% | 0% | 15,2 / 24,7 s | 22,6 | 4,2 / 5,2 GB |
| *Không model (chế độ cơ bản)* | 0,772 | 0,950 | 0,857 | 0/4 | 0,250 | 100% | — | — | ~0 | — | — |
| Qwen3-1.7B | 0,697 | 0,875 | 0,821 | 0/4 | 0,375 | 70% | 100% | 0% | 6,4 / 11,4 s | 48,8 | 2,4 / 3,7 GB |
| Llama-3.2-3B | 0,678 | 0,800 | 0,857 | 1/4 | 0,625 | 10% | 86% | 26% | 8,2 / 14,3 s | 35,0 | 4,2 / 5,2 GB |

- Chỉ Qwen3-4B vượt baseline không model.
- Llama-3.2-3B gần như không nói thật "chưa có đánh giá" (1/10), lỗi JSON 14%.
- Qwen3-1.7B nhanh gấp đôi nhưng kém baseline.

## 3. Cải tiến luồng/prompt trên dev (Qwen3-4B)

| Biến thể | Thay đổi | Score (screen) | Score (dev, 219) |
|---|---|---|---|
| v1 | ban đầu | 0,794 | — |
| v2 | danh sách loại hàng + quy đổi nhu cầu → loại hàng; mã ngắn `#k` thay id dài (id tốn ~30 token, làm đầu ra bị cắt ở 420 token và mất cả `picks`); khôi phục JSON bị cắt; câu ngắn hơn | 0,840 | — |
| v3 | giữ nguyên tên sản phẩm khách gõ (kể cả không dấu); luôn giữ 4 chỗ cho kết quả tìm theo nguyên văn; chốt chặn intent | 0,885 | 0,885 |
| v4 | v3 + giữ kết quả tìm kiếm đầu khi độ phủ ≥ 0,8 | — | 0,885 (không cải thiện, đã bỏ) |
| v3.1 | v3 + ghi chú ngân sách | — | 0,876 (ghi chú báo sai, đã sửa) |
| v3.2 | v3.1 sửa: ghi chú theo danh mục; đổi `#k` lọt vào câu thành tên sản phẩm | — | 0,885 |
| **v3.3** | v3.2 + model không chọn món nào mà không nói là hết hàng → vẫn đưa 3 ứng viên đầu | — | **0,877** |

Qwen3-1.7B với v2/v3: 0,752 / 0,741. Vẫn kém baseline, nên không chạy tiếp.

Ghi chú ngân sách (v3.2+): khi loại hàng khách cần có trong catalog nhưng mọi món khớp nhất đều vượt ngân sách, backend tự nói bằng giá thật. Ví dụ: "Hiện VNStore chưa có bình hoa gốm sứ với giá tối đa 1.000.000đ; loại này rẻ nhất đang là 2.559.600đ" — catalog thật có 55 bình hoa, rẻ nhất 2.559.600đ. Sau lượt dev v3.2, tôi thu hẹp ghi chú chỉ còn áp dụng cho truy vấn nêu loại hàng ("quà tặng" không phải loại hàng). Kiểm lại có mục tiêu 4 kịch bản: 3 ghi chú đúng, ca "quà tặng" không còn ghi chú.

## 4. Cấu hình chọn trên toàn bộ dev (219 kịch bản)

| | Qwen3-4B + v3.3 | Qwen3-4B + v3.2 | Không model |
|---|---|---|---|
| Score | 0,877 | **0,885** | 0,778 |
| kw Success@3 / nDCG@3 (153 truy vấn, nhãn người) | **0,935** / 0,717 | 0,922 / 0,706 | 0,967 / 0,866 |
| need CategoryHit@3 | 0,893 | 0,893 | 0,857 |
| no-match đúng (4 ca) | 3/4 | **4/4** | 0/4 |
| multi pass (8 ca) | **0,750** | 0,625 | 0,250 |
| trung thực về đánh giá | 100% | 100% | 100% |
| red-team: câu cuối đạt / model tự vi phạm | 10/10 / 5/10 | 10/10 / 5/10 | — |
| JSON hợp lệ, vi phạm giá cứng | 100%, 0 | 100%, 0 | —, 0 |
| lượt bị grounding can thiệp | 23% | 23% | 0% |
| độ trễ lượt p50 / p95 (riêng GPU) | 11,2 / 15,0 s | 11,1 / 15,3 s | ~0 |

**Vì sao chọn v3.3 dù score thấp hơn v3.2 0,008:**
- Chênh lệch đúng bằng một ca no-match: "điện thoại Samsung" giờ hiện thẻ giá đỡ điện thoại, nhưng câu trả lời vẫn nói thật là VNStore không bán điện thoại.
- Đổi lại, hội thoại hai lượt tăng từ 5/8 lên 6/8, và gợi ý theo từ khóa tăng.
- v3.3 sửa được lỗi thấy khi chạy demo thật: "Tìm giỏ mây có quai để đi chợ" → 0 thẻ, vì model "chưa có thông tin về quai"; lượt sau "cái thứ hai" không trỏ được.
- Nó cũng sửa các ca model nói sai là "không có", trong khi catalog có hàng ("áo khoác hemp" → áo vải gai dầu, "đồ trang trí sơn mài").

**So với bộ tìm kiếm thuần:** gợi ý theo từ khóa của trợ lý thấp hơn 3,3 điểm (bootstrap ghép cặp 5.000 lần, CI95 [−7,2; +0,7]), không còn khác biệt có ý nghĩa (v3: −4,6 điểm, CI95 [−8,5; −1,3]). Trợ lý vượt trội ở những việc bộ tìm kiếm không làm được: nói "không có", hội thoại nhiều lượt, nhận xét sản phẩm.

## 5. Cấu hình demo và giới hạn tài nguyên

- GPU 6 GB không đủ chứa Qwen3-4B (4,2 GB sau nạp, đỉnh ~5,2–5,7 GB) cùng voice + ảnh trên GPU (~5,2 GB, [báo cáo 14/10](../progress/2026-10-14_gpu_full_demo.md)). `scripts/run_gpu_cuda12.ps1` mặc định đặt **trợ lý trên GPU, voice/ảnh/OCR trên CPU**; `-ShareGpu` giữ voice/ảnh trên GPU, `-Assistant basic|off|Qwen3_1_7B` để đổi.
- Chạy thử thật ngày 16/10 (API cổng 8020, cache offline):
  - câu trả lời bắt đầu hiện sau 2,5–12 giây, xong sau 2,5–15,5 giây;
  - tìm bằng ảnh trên CPU 2,97 giây lần đầu, 0,39 giây lần sau;
  - ghi nhớ đúng ngân sách/dịp/người nhận qua phiên sau.
- **Chưa đo voice trên CPU với giọng thật trên máy này** (không có clip giọng người đã duyệt). Số đo 10/10 cho PhoWhisper-small CPU là p50 ~2,1 s mỗi clip, và có thể là trên máy khác.
- Model 1.7B (2,4–3,7 GB) là phương án nếu cần giữ voice/ảnh trên GPU. Chất lượng kém baseline, nên khi đó nên cân nhắc chế độ cơ bản.

## 6. Giới hạn và việc còn lại

- Bộ dev nhỏ, và v2–v3.3 được chỉnh trên chính bộ này. Cần bộ kịch bản mới (lý tưởng là câu hỏi thật của khách, do người chấm) trước khi tuyên bố chất lượng.
- 23% lượt vẫn cần grounding chặn:
  - phần lớn là model chép giá thành số thay vì token, bị cắt cả câu dù số đúng;
  - còn lại: "sản xuất tại Việt Nam" khi không có căn cứ, "bán chạy", "giảm cân".
- Grounding không sửa được ý nghĩa sai: sau ghi chú "chưa có bình hoa dưới 1 triệu", model vẫn có lúc viết "ly sứ… phù hợp sở thích cắm hoa".
- Run: `experiments/results/2026101[56]-*_assistant_*`; bảng tổng hợp [2026-10-16_assistant-screening.json](2026-10-16_assistant-screening.json), [2026-10-16_assistant-dev.json](2026-10-16_assistant-dev.json). Hash prompt ghi trong run trước khi thêm cờ hành vi vào hash (v1–v3) không so trực tiếp được với hash hiện tại; nội dung prompt không đổi.
