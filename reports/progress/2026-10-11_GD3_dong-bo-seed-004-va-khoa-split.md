# GĐ1–3 — Đồng bộ catalog seed-004, tách câu voice theo split, chuẩn bị nhãn voice, kế hoạch khóa split ảnh — 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1 (catalog), GĐ2 (packet keyword), GĐ3 (bộ nhãn, khóa split) — PLAN.md mục 8.1, 8.3 bước 1, mục 9 |
| Trạng thái | 🟡 Đã xong phần công cụ trong khả năng của agent; nghiệm thu GĐ1–3 vẫn chờ dữ liệu và người duyệt |
| Người thực hiện | Claude (Claude Code) |
| Catalog | `seed-004-hanhsilk-materials`, 330 draft / 814 ảnh / 23 danh mục |
| SHA-256 catalog | `5448a8f4f8161e14cda4f6c3bac921c46af4c02be359dfe20c8ddd312572cecb` (không đổi trong phiên này) |
| Commit gốc | `8261b59`; thay đổi của phiên trước và phiên này **chưa commit** (người dùng tự commit) |

## 1. Mục tiêu đợt này

Yêu cầu: phân tích tiến độ và hoàn thành công việc của GĐ1, GĐ2, GĐ3. Điều kiện hoàn thành theo PLAN mục 9:

| GĐ | Điều kiện PLAN | Hiện trạng sau phiên |
|---|---|---|
| 1 | database.json validate được, nguồn/ảnh hợp lệ, có báo cáo thiếu dữ liệu | Validate 0 lỗi; 814/814 ảnh đúng hash; có báo cáo readiness. **Chưa đạt "ảnh hợp lệ" về quyền**: 814 ảnh quyền `unknown`, 0 published. Cần người xin phép và duyệt |
| 2 | Luồng xem/tìm keyword chạy trực tiếp từ JSON, baseline có số đo | Luồng chạy, có packet chấm trên catalog hiện hành. **Chưa có baseline** vì chưa có nhãn do người chấm |
| 3 | Không trùng người/ảnh gốc giữa split, rubric được rà soát | Công cụ chặn rò theo người nói, **câu**, họ, phiên chụp, ảnh gốc. **Mới có** kế hoạch phân họ vào split, khóa được sau khi có registry. Chưa có clip/ảnh query, chưa duyệt registry, chưa khóa split |

Agent không được tạo nhãn, tên người duyệt, quyền ảnh hay chuyển `published` (quy tắc BACKLOG mục 1). Vì vậy "hoàn thành" ở đây là hoàn tất mọi việc agent làm được và gỡ các điểm chặn kỹ thuật. Ba điều kiện nghiệm thu trên vẫn cần con người.

## 2. Phân tích tiến độ lúc bắt đầu

- Kiểm thử mốc: **2 bước lỗi**, gồm 1 backend `test_packet_from_current_proposal` và 2 E2E duyệt họ desktop/mobile. Nguyên nhân là `benchmarks/families/proposal.json` vẫn dựng cho catalog cũ.
- Một phiên làm việc trước, lúc 02:52 sau báo cáo GĐ4 (02:46), đã sửa catalog sang `seed-004-hanhsilk-materials` **mà chưa ghi báo cáo**. Lượt sửa thêm chất liệu cho 9 sản phẩm Hanhsilk qua `safe_import`, kèm script chạy lại được. Phiên đó dừng giữa chừng: đã dựng lại packet keyword `2026-10-11_seed-004_*`, manifest ảnh và chỉ mục SigLIP2, nhưng **chưa** dựng lại chỉ mục DINOv2, đề xuất họ và trang duyệt họ. README/BACKLOG vẫn trỏ tới packet và trang seed-003 đã lệch hash. Nếu nhóm dữ liệu chấm trên trang cũ, kết quả sẽ bị audit từ chối.
- Đã kiểm tra lượt sửa này: script yêu cầu hash catalog đầu vào, so response API gốc và từng bản ghi theo hash, yêu cầu câu chất liệu nguyên văn trong mô tả của chính sản phẩm, không đổi `draft`, quyền, giá hay claim. Đây là sửa dữ liệu có nguồn, không phải tạo nhãn. Giữ nguyên và ghi hồ sơ.
- Phát hiện lỗi thiết kế GĐ3: **mọi người nói ở train/dev/test đọc cùng 24 câu mẫu**. Hệ quả:
  - fine-tune ASR trên người nói train học thuộc đúng văn bản test, tức rò văn bản dù không trùng người nói;
  - evaluator keyword từ chối cùng một câu ở hai split, nên không thể gắn `keyword_qid` cho clip dev và test cùng lúc. Lỗi này không lộ ra vì manifest voice còn rỗng.
- GĐ3 chưa có công cụ **khóa split**: `benchmarks/splits/` rỗng. Người thu ảnh tự khai split cho phiên và rò rỉ chỉ phát hiện sau khi thu; không có kế hoạch phân 120/40/40 họ trước khi chụp như P0.5 yêu cầu.

## 3. Đã làm

### 3.1 Hoàn tất đồng bộ catalog seed-004 (GĐ1/GĐ2/GĐ3)

- Dựng lại chỉ mục DINOv2 (814 vector, 32 giây). Cả hai chỉ mục ảnh nay mang hash `5448a8f4…`.
- Chạy lại `propose_families.py`. Đề xuất mới **giống hệt** bản cũ, chỉ khác `catalog_sha256`, `catalog_version`, `generated_at` (đã so từng khóa).
- `prepare_family_review.py --carry-drafts-from` (mới): catalog đổi làm đổi hash proposal dù nội dung giữ nguyên, nên trước đây người duyệt mất bản nháp mỗi lần catalog đổi. P0.2 publish dần sẽ gặp lại tình huống này nhiều lần. Trang mới chỉ nhận bản nháp (file hoặc localStorage) của trang cũ khi họ, ứng viên ảnh, cụm ảnh dùng chung và mã họ từng sản phẩm trùng khớp. File quyết định vẫn mang hash proposal hiện tại.
- Tạo [trang duyệt họ seed-004](../../artifacts/family_review/2026-10-11_seed-004/index.html) (35 họ, 83 ứng viên ảnh, 8 cụm ảnh dùng chung), nạp được bản nháp của hai trang seed-003.
- Đối chiếu packet keyword seed-004 với seed-003: cùng truy vấn và số cặp (138; 1.361). Riêng `kw-seed-010` (“váy lụa”) đổi pool vì BM25 đổi thứ hạng sau khi thêm chất liệu (`p-hanhsilk-khan-lua-thuy-an-dai-570` vào top 10), kéo theo 4 sản phẩm ngẫu nhiên được chọn lại.
- Ghi hồ sơ cho lượt sửa chất liệu: [README đợt](../../data_collection/batches/2026-10-11_hanhsilk-materials/README.md), snapshot trong [data_collection/README.md](../../data_collection/README.md). Cập nhật link packet/trang hiện hành trong README keyword, họ, ảnh.

### 3.2 Bộ câu voice riêng cho từng split (GĐ3)

- [prompts.ts](../../frontend/src/collect/prompts.ts): `PROMPT_SETS` gồm train `tr01–tr24`, dev giữ nguyên `p01–p24`, test `te01–te24`. 72 câu không trùng nhau sau chuẩn hóa. Mỗi bộ cân đối thẻ thương hiệu, địa danh, chất liệu, giá, đơn vị, phủ định, xen tiếng Anh, câu tự nhiên, 1–2 câu ngoài catalog. Câu train/test do Claude soạn theo catalog seed-004; **nhóm dữ liệu cần rà soát trước phiên thu đầu tiên**.
- Trang `#/collect/voice`: chưa chọn split thì chưa hiện câu; chỉ hiện bộ câu của split đã chọn; đã ghi thì khóa split.
- `eval_voice.check_text_splits` được gọi trong `load_manifest`, `import_voice_session.merge` và `apply_voice_review.plan`. Hàm từ chối một câu (chuẩn hóa `asr_metrics`: NFC, chữ thường, bỏ dấu câu, giữ dấu) ở hai split, kể cả khi người duyệt sửa bản chép lời thành câu của split khác.

### 3.3 P1.15 — Chuẩn bị nhãn relevance từ bản chép lời đã duyệt (GĐ3/GĐ4)

`scripts/benchmark/prepare_voice_queries.py`:
- `draft --split S --out DIR [--keyword-file …]`:
  - chỉ lấy clip có `transcript_review`, có lời nói, consent `granted`, chưa có `keyword_qid`; báo số clip bị bỏ theo lý do;
  - mỗi câu thành một truy vấn `vq-<split>-<hash>` **không có nhãn** (`relevance={}`, `verified=false`), giữ danh sách `voice_clips`;
  - các câu từ cùng câu mẫu chung `group_id = vg-<mã câu>`, kể cả khi người nói đọc khác câu mẫu;
  - ghi `queries.jsonl` + `links.json` (clip → qid, hash bản chép lời, hash catalog/manifest/truy vấn);
  - dừng nếu câu đã có ở split khác của bộ keyword; câu trùng cùng split chỉ được liệt kê, không dùng lại nhãn.
- Người chấm dùng `prepare_review.py` và `audit_reviews.py` như keyword. Đã thử: packet tạo được, trang chấm giữ trường phụ khi xuất.
- `apply LINKS LABELS [--dry-run]` chỉ ghi `keyword_qid` khi đủ các điều kiện sau, nếu không thì không ghi gì:
  - nhãn `verified`;
  - catalog trùng lúc tạo nháp và trùng `catalog_sha256` của nhãn;
  - query khớp bản chép lời, cùng split; no-match chấm đủ catalog;
  - bản chép lời chưa đổi hoặc chưa bị bỏ duyệt;
  - clip chưa liên kết qid khác (không ghi đè).

  Manifest mới được ghi ra file tạm và `load_manifest` kiểm tra lại trước khi thay nguyên khối.

### 3.4 Kế hoạch và khóa split ảnh theo họ (GĐ3)

`scripts/benchmark/plan_splits.py`:
- `propose --families families.json` (hoặc `--preview` từ proposal chưa duyệt):
  - đơn vị = họ đã duyệt ∪ họ dùng chung ảnh gallery ∪ các dòng thiết kế được chọn bằng `--design-lines`;
  - phân tầng theo danh mục chiếm đa số;
  - đơn vị lớn trước, mỗi đơn vị vào split thiếu nhiều nhất theo số họ (mặc định 60/20/20), hòa thì theo hash(seed, mã đơn vị); cùng đầu vào và seed cho cùng kết quả;
  - ghi JSON + Markdown, không ghi đè file đã có.
- `lock PLAN --locked-by <tên>`: chỉ khóa kế hoạch `proposed` dựng từ registry đã duyệt, sau khi kiểm tra catalog, proposal và registry chưa đổi. Tên do người khóa nhập.
- `audit_image_queries.py --split-plan` (cũng có trong `import_image_session.py`, `apply_image_judgments.py`, `eval_image.py`) báo `split_plan_mismatch` khi query của một họ nằm khác split kế hoạch. Kế hoạch preview bị từ chối; `proposed` chỉ cảnh báo. `eval_image.py --split test` **bắt buộc** kế hoạch `locked`.
- Bản xem trước [image_families.preview.md](../../benchmarks/splits/image_families.preview.md), dựng từ proposal chưa duyệt nên **không dùng để thu**: 169/55/55 họ (60,6/19,7/19,7%), đơn vị lớn nhất 6 họ. Tài liệu: [benchmarks/splits/README.md](../../benchmarks/splits/README.md), bảng đơn vị chia cho cả ba modality.

## 4. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Mốc trước khi sửa | `.venv/Scripts/python scripts/run_all_tests.py` | 2 bước lỗi: backend 454 đạt / 1 lỗi (+1 skip), E2E 102 đạt / 2 lỗi — cùng nguyên nhân proposal lệch catalog |
| Toàn bộ sau khi sửa | `.venv/Scripts/python scripts/run_all_tests.py` | **8/8 bước đạt**, exit code 0: 474 backend (+1 skip), 22 Pillow, 104 E2E (desktop + mobile), typecheck và build frontend |
| Test mới | `pytest tests/test_voice_queries.py tests/test_split_plan.py` + test bổ sung trong `test_family_review.py`, `test_voice_image_benchmark.py` | 10 + 6 + 1 + 2 đạt. Mỗi ca chặn của `apply` đã đối chiếu thông báo lỗi đúng lý do (chưa duyệt, bản chép lời đổi, liên kết khác, catalog đổi, query khác, no-match thiếu, thiếu nhãn, câu ở split khác) |
| Catalog | `scripts/validate_catalog/validate.py`, `scripts/validate_catalog/readiness.py` | 0 lỗi, 0 cảnh báo; 814 ảnh valid; 0/330 đạt kỹ thuật (chặn bởi `image_rights` ở cả 330). Báo cáo: [chất lượng seed-004](../data_quality/2026-10-11_seed-004-hanhsilk-materials.md), [readiness](../data_quality/2026-10-11_031800-146711_publication-readiness.md) |
| Hash catalog | `sha256sum database.json` | `5448a8f4…` trước và sau phiên; phiên này không sửa catalog |
| Audit ảnh trên manifest thật | `scripts/benchmark/audit_image_queries.py` | `pending_collection`, 0 query; báo cáo có dòng kế hoạch split |
| Đề xuất họ | so khóa JSON cũ/mới | Chỉ khác `catalog_sha256`, `catalog_version`, `generated_at` |

Số liệu catalog sau đợt Hanhsilk: 128 sản phẩm thiếu chất liệu (trước 137), 74 có biến thể thiếu giá, 96 sản phẩm dưới 2 ảnh, 814/814 ảnh quyền `unknown`, 2 sản phẩm thiếu claim Việt đủ điều kiện.

## 5. Số đo

Không có số đo benchmark. Số đếm trong bản xem trước split là đếm họ trên proposal chưa duyệt. Mọi test dùng fixture và nhãn tổng hợp.

## 6. Khác với kế hoạch

- PLAN không yêu cầu tách câu voice theo split; bổ sung để tránh rò văn bản khi fine-tune ASR và để nhãn keyword gắn được.
- Dòng thiết kế mặc định **không** gộp khi chia split. Gộp hết (`--design-lines all`) nối 24 họ bát đĩa Minh Long qua các âm tiết chung ("chim", "hằng", "hương"), làm dev/test chỉ còn 2/1 họ bát đĩa. Chọn từng dòng thật (ví dụ `hanoia:moonbow,minhlong:camellia`) cho 62/19/19%. Nhóm dữ liệu quyết định khi khóa.

## 7. Chưa làm / nợ kỹ thuật

- Không sửa thêm catalog (giá, ảnh, chất liệu còn thiếu) để tránh làm lệch hash các packet vừa đồng bộ trước khi nhóm dữ liệu chấm. Nếu muốn, có thể làm đợt bổ sung có nguồn như Hanhsilk, nhưng phải dựng lại packet một lần nữa.
- Trang chấm keyword chưa có cơ chế chuyển bản nháp khi catalog đổi như trang duyệt họ. Pool có thể thay đổi theo catalog nên cần quy tắc riêng.
- Chưa có kế hoạch người nói voice dạng file (24/8/8). Hiện người điều phối phân người nói; script chặn trùng người nói/câu giữa split.
- Bộ câu train/test chưa được người rà soát.

## 8. Rủi ro và việc đang chặn

Như [BACKLOG P0](BACKLOG.md): quyền ảnh và duyệt 330 draft (GĐ1); chấm packet keyword seed-004 (GĐ2); duyệt họ → `families.json` → `plan_splits.py propose/lock`, thu clip và ảnh query (GĐ3).

## 9. Bước tiếp theo

1. Người dùng xem và commit thay đổi của hai phiên (seed-004 + phiên này).
2. Nhóm dữ liệu: rà soát 48 câu mẫu train/test; chấm packet keyword seed-004; duyệt họ trên trang seed-004 → `apply_family_review.py` → `plan_splits.py propose --families …` → khóa.
3. Sau khi có clip đã duyệt: `prepare_voice_queries.py draft` → chấm → `apply`, rồi `eval_voice.py --queries`.
