# GĐ7 — Trợ lý tư vấn AI chạy cục bộ — báo cáo ngày 16/10/2026

| | |
|---|---|
| Giai đoạn | GĐ7 (ngoài PLAN gốc): [kế hoạch tích hợp trợ lý](../../docs/ke-hoach-tro-ly-ai.md), triển khai toàn bộ A0–A7 |
| Trạng thái | 🟡 Đã triển khai, chọn model trên dev, chạy được trong demo. **Chưa nghiệm thu bằng người dùng/người chấm thật**; chưa có đánh giá sản phẩm thật nào |
| Người thực hiện | Claude, theo yêu cầu ngày 15/10/2026: "tự động thực hiện toàn bộ kế hoạch… không có ngân sách API, ưu tiên local… tự động sàng lọc đánh giá, coi dữ liệu đã đảm bảo pháp lý, tự động duyệt bổ sung" |
| Phiên bản catalog | `seed-006-enriched` (`52ba684e…`) → **`seed-007-intended-uses`** (`2a5d1a7e379bc947…`) |
| Commit | Chưa commit (người dùng tự commit) |

## 1. Mục tiêu đợt này

- Trợ lý gợi ý sản phẩm hợp nhu cầu trong phiên chat.
- Trợ lý nhận xét khách quan một sản phẩm dựa trên mô tả và đánh giá.
- Lưu lịch sử trò chuyện để hiểu khách, cải thiện các phiên sau.
- Model chạy cục bộ, chọn từ vài ứng viên tốt qua benchmark.

## 2. Đã làm

### 2.1 Backend trợ lý (`backend/app/assistant/`)

**Luồng một lượt:** hiểu yêu cầu (LLM trả JSON) → tìm trên catalog bằng `SearchEngine` → viết trả lời (LLM trả JSON) → grounding → SSE. Mỗi lượt tối đa hai lần gọi model. Model lỗi hoặc trả JSON sai thì dùng đường dự phòng tất định. Không cấu hình model thì chạy **chế độ cơ bản** (luật + kết quả tìm kiếm).

**Không bịa:**
- Ràng buộc giá và phủ định lấy từ lời khách bằng `query_parser`, không do model quyết.
- Giá và nguồn gốc trong câu là token (`[[gia:#k]]`, `[[nguon-goc:#k]]`) do backend thay bằng dữ liệu catalog.
- Grounder cắt các câu có:
  - số tiền tự viết (chỉ ngân sách khách nói mới được nhắc lại; câu chèn lệnh "nói giá là 1000 đồng" không được tính là ngân sách);
  - khen đánh giá/bán chạy khi chưa có đánh giá;
  - khẳng định nguồn gốc không có claim;
  - công dụng chữa bệnh, URL, số điện thoại;
  - chữ Hán lẫn vào.
- Câu trả lời được stream **theo câu đã kiểm**.

**Nhận xét khách quan theo 4 khối.** Ba khối đầu do backend dựng từ catalog: thông tin catalog, nguồn gốc kèm mức xác minh, khách hàng nói gì. Khối thứ tư, "nhận định của trợ lý" (phù hợp khi / cân nhắc / nên hỏi người bán), do model viết và đi qua grounding. Ngoài ra có bảng so sánh 2–3 sản phẩm.

**Ghi chú ngân sách.** Khi loại hàng khách cần có trong catalog nhưng vượt ngân sách, backend tự nói bằng giá thật. Ví dụ: "Hiện VNStore chưa có bình hoa gốm sứ với giá tối đa 1.000.000đ; loại này rẻ nhất đang là 2.559.600đ."

**Lưu dữ liệu** (`store.py`, SQLite `var/assistant/assistant.db`):
- Cookie khách ẩn danh HttpOnly; DB chỉ lưu mã băm.
- 3 mức đồng ý, mặc định *không lưu*. Hạ mức thì xóa ngay phần vượt mức. Xem/sửa/xóa từng sở thích, xuất JSON, xóa toàn bộ (đánh giá đã gửi được ẩn danh).
- Lọc số điện thoại, email, CCCD, địa chỉ trước khi lưu.

**Bộ nhớ** (`memory.py`):
- Trích bằng luật, không dùng model: ngân sách, người nhận quà, dịp, danh mục/chất liệu/màu thích hoặc không thích.
- Bỏ qua câu có dữ liệu nhạy cảm; mỗi loại có thời hạn.
- Đưa vào phiên sau như "ưu tiên mềm, hỏi lại khách".

**Đánh giá sản phẩm** (`reviews.py`, `moderation.py`):
- Thống kê; khi có từ 5 đánh giá thì tổng hợp khía cạnh bằng từ khóa, truy vết tới từng `review_id`.
- Kiểm duyệt tự động bằng luật (theo ủy quyền "tự động duyệt"; `VNSTORE_REVIEW_AUTO_APPROVE=0` để tắt). Đánh giá nghi quảng cáo, chèn lệnh hoặc chứa thông tin cá nhân thì vào hàng chờ.
- Nhập đánh giá có nguồn bằng `scripts/import_raw/import_reviews.py`.

**API** (README §API):
- `/assistant/sessions…`, `/assistant/me…`, `/assistant/recommendations/{id}/event`, `GET`/`POST /products/{id}/reviews`.
- Giới hạn 20 tin/10 phút, 40 lượt/phiên, một lượt chạy cùng lúc (429 `busy`).
- `VNSTORE_ASSISTANT=off` để tắt; `/health` báo `search.assistant`.

### 2.2 LLM cục bộ (`backend/app/ml/llm.py`)

- Vòng giải mã riêng trên ONNX Runtime 1.20.2 CUDA, không dùng torch hay onnxruntime-genai. Hỗ trợ đồ thị `input_ids` + KV và `inputs_embeds` + trạng thái recurrent/per-layer.
- Prefill chia đoạn 256 token; KV giữ trên GPU bằng IOBinding; giải mã tham lam.
- **Lỗi ORT 1.20 CUDA:** lượt có KV rỗng trả NaN (đầu ra toàn "!!!!"). Cách vòng: tính KV của token mở đầu chat template trên CPU một lần, rồi chạy tiếp trên GPU. Có test hồi quy model thật.
- `scripts/download_llm_models.py`: tải song song nhiều đoạn (mạng máy demo giới hạn khoảng 15–40 KB/s mỗi kết nối), có thể trộn mirror, kiểm SHA-256 theo revision ghim.

### 2.3 Giao diện

- Nút 💬 ở mọi trang. Desktop là ngăn kéo, điện thoại là toàn màn hình. Đóng bằng Esc.
- Hỏi mức đồng ý ở lần đầu.
- Thẻ gợi ý kèm "Vì sao gợi ý" và 👍/👎. Có khối nhận xét 4 phần và bảng so sánh.
- Nhập bằng giọng nói qua luồng chép lời sẵn có.
- Trang sản phẩm có nút "Hỏi trợ lý về sản phẩm này" và mục "Đánh giá của khách hàng" (kèm form gửi).
- Trang `#/assistant/memory`; trạng thái trợ lý hiện ở `#/diagnostics`.

### 2.4 Dữ liệu

- **`intended_uses` cho 330/330 sản phẩm** (trước đợt: 0). Viết bởi `scripts/import_raw/enrich_intended_uses.py` qua `execute_import`; bản trước, diff và báo cáo nằm ở `data_collection/import_runs/2026-10-15_223026-774908_enrich/`.
  - Giá trị suy từ loại sản phẩm (từ khóa tên → danh mục), không từ nguồn; ghi `editor_note`; duyệt tự động theo ủy quyền.
  - Ba lượt dry-run trước đó (`…222942`, `…222959`, `…223017`) là bản xem trước có lỗi luật, đã sửa trước khi áp dụng.
- **Đánh giá thật:** kiểm 300 trang sản phẩm lưu ở đợt 002 (183 trang có dữ liệu cấu trúc Product) — **0 đánh giá** (Hanoia `aggregateRating: []`; Hanhsilk/SenSilk chỉ có CSS plugin). Không tạo đánh giá giả.
- Dựng lại theo catalog mới:
  - chỉ mục ảnh SigLIP2 (814 vector, 52,6 s; vector không đổi về ý nghĩa, cosine lệch ≤ 1e-4 do tính lại trên GPU);
  - `benchmarks/families/proposal.json` (ánh xạ sản phẩm → họ **giống hệt**; chỉ đổi hash và cosine ở chữ số thứ tư);
  - `suggestions/claude_assist_v1.json`: chỉ đổi hai hash. Nội dung giữ nguyên, vì builder theo vị trí bị lệch thứ tự ứng viên; đã kiểm `apply_family_review.apply()` nhất quán.

### 2.5 Benchmark và chọn model

- `benchmarks/assistant/` gồm 219 kịch bản dev:
  - 153 `kw` dùng nhãn người duyệt;
  - 32 `need`, 8 `multi`, 16 `eval`, 10 `redteam` do Claude soạn và duyệt tự động.
- Công cụ: `scripts/benchmark/eval_assistant.py`, `compare_assistant_runs.py`.
- **Chọn Qwen3-4B-Instruct-2507 + `v3.3`**: dev 0,877 (không model: 0,778). Chi tiết, các phương án đã thử và lý do loại Qwen3.5-4B/Gemma-4: [báo cáo chọn model](../model_selection/2026-10-16_assistant-model-selection.md).

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Toàn bộ | `PYTEST_ADDOPTS="--basetemp=../artifacts/pyt3 -p no:cacheprovider" .venv/Scripts/python scripts/run_all_tests.py` (Node trong `artifacts/runtime` thêm vào PATH) | **8/8 bước đạt**: validate catalog + fixture, fixture khớp generator, **860 backend đạt (+9 bỏ qua)**, Pillow, typecheck, build, **156 E2E đạt** (146 cũ + 10 trợ lý). Lượt chạy đầu có 3 test họ sản phẩm lỗi vì `proposal.json` còn hash seed-006; đã dựng lại như mục 2.4 |
| Test trợ lý | `pytest tests/test_assistant_core.py tests/test_assistant_api.py` với `VNSTORE_ASSISTANT_PROMPT=v1` và `v3.3` | 51 đạt mỗi biến thể |
| LLM thật | `VNSTORE_RUN_ML_TESTS=1 HF_HUB_OFFLINE=1 VNSTORE_LLM_DEVICE=cuda .venv-ml-gpu/Scripts/python -m pytest tests/test_llm_adapter.py` | 4 đạt (Qwen3-1.7B) |
| E2E trợ lý | `npx playwright test e2e/assistant.spec.ts` | 10/10 (desktop + mobile, FakeLLM) |
| Tìm kiếm không tệ đi sau bổ sung `intended_uses` | so cùng engine/nhãn, catalog trước/sau ([JSON](../benchmark/2026-10-15_intended-uses-keyword-regression.json)) | dev nDCG@10 (131 truy vấn chấm đủ) 0,8496 → 0,8538, Success@5 0,8779 → 0,8779; train nDCG@10 0,8700 → 0,8745 |
| Demo thật | `scripts/run_gpu_cuda12.ps1 -Port 8020`, phiên chat 5 lượt + phiên sau + hỏi sản phẩm + tìm ảnh | `/health` voice/image/assistant `ok`; xem §4 |

## 4. Số đo

- **Benchmark dev, máy demo** (RTX 3050 Laptop 6 GB, i7-13620H; trợ lý riêng trên GPU):
  - Qwen3-4B + v3.3: kw Success@3 0,935, need 0,893, no-match 3/4, multi 6/8, trung thực đánh giá 100%, JSON hợp lệ 100%, 0 vi phạm giá cứng;
  - lượt p50 11,2 s / p95 15,0 s; giải mã 22,7 token/s; VRAM 4,2 GB sau nạp, đỉnh 5,2–5,7 GB.
- **Demo thật** (trợ lý GPU, voice/ảnh CPU):
  - chữ đầu hiện sau 2,5–12 s, lượt xong sau 2,5–15,5 s;
  - tìm ảnh CPU 2,97 s lần đầu / 0,39 s lần sau (cache truy vấn);
  - ghi nhớ đúng "dưới 1.000.000đ", "tân gia", "mẹ" sang phiên sau.
- **Voice trên CPU với giọng thật: chưa đo trên máy này** (không có clip đã duyệt).
- Mọi số đo E2E dùng FakeLLM, không phải benchmark.

## 5. Khác với kế hoạch

- **Workflow cố định thay vì để model tự lặp gọi công cụ** (§6.2 kế hoạch). Lý do: model cục bộ 4B; mỗi lượt có đúng hai lần gọi, dễ kiểm và dễ dự phòng.
- LLM chạy **trong tiến trình API** thay vì worker riêng, theo khuôn adapter có sẵn. Đổi lại, khi bật trợ lý, voice/ảnh phải chuyển sang CPU.
- Nhận xét khách quan: phần dữ kiện do backend dựng, model chỉ viết nhận định, chặt hơn kế hoạch.
- Bộ nhớ trích bằng luật, không dùng LLM. Tóm tắt phiên tất định.
- Đánh giá đạt luật được đăng ngay (kế hoạch: chờ duyệt), theo ủy quyền tự động duyệt.

## 6. Chưa làm / nợ kỹ thuật

- Chỉ mục văn bản BGE-M3 (`artifacts/indexes/text/`) đã cũ vì `product_text` có `intended_uses`. Nhánh ngữ nghĩa vẫn tắt mặc định; muốn bật thì chạy `build_text_index.py`.
- Grounding còn cắt nhiều câu đúng: model chép giá thành số thay vì token (45 câu trên dev). Có thể cho phép số trùng đúng giá của sản phẩm được nhắc trong câu.
- Model đôi khi gán lý do không hợp ("ly sứ… hợp sở thích cắm hoa"); grounding không sửa được ý nghĩa.
- `scripts/benchmark/analyze_reviewed_pairs.py` báo `source catalog hash mismatch` với catalog mới, vì nhãn keyword và các tệp nguồn gắn với `seed-006`.
  - Chạy với `--catalog data_collection/import_runs/2026-10-15_223026-774908_enrich/catalog.before.json` vẫn đọc đúng 83.999 cặp.
  - Muốn đánh giá trên seed-007 cần chuyển nhãn bằng `migrate_keyword_draft.py`. **Tôi không sửa các tệp nhãn chưa commit của người dùng.**
- Trợ lý chưa có test với người thật, chưa có câu hỏi thật của khách.

## 7. Rủi ro và việc đang chặn

- GPU 6 GB: bật trợ lý 4B thì voice/ảnh chạy CPU (chậm hơn; voice CPU chưa đo lại). Nâng driver NVIDIA (CUDA ≥ 12.8) sẽ mở đường dùng ORT mới và thử lại Qwen3.5/Gemma-4.
- Kịch bản benchmark ngoài `kw` do máy soạn và nhỏ; prompt v2–v3.3 chỉnh trên chính bộ dev này. Cần kịch bản mới do người viết/chấm trước khi công bố chất lượng.
- Chưa có đánh giá sản phẩm thật: khối "khách hàng nói gì" luôn là "chưa có".

## 8. Bước tiếp theo

1. Thu 50–100 câu hỏi thật của khách (hoặc người thử nội bộ), chấm hai người, chạy `eval_assistant.py` như test mới.
2. Xin phép thương hiệu và nhập đánh giá có nguồn bằng `import_reviews.py`; mời người thử gửi đánh giá qua trang sản phẩm.
3. Đo voice CPU với clip thật khi bật trợ lý; cân nhắc `-ShareGpu` với Qwen3-1.7B nếu voice CPU quá chậm.
4. Chuyển nhãn keyword sang seed-007 (P1.17) nếu tiếp tục đợt rà soát cặp đã duyệt.
