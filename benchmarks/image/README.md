# Thu thập query ảnh độc lập

Mục tiêu PLAN §8: 600 ảnh query độc lập, khoảng 200 họ sản phẩm; chia theo họ 120/40/40 cho train/dev/test. Ảnh + text là bộ bổ sung 120 truy vấn. Đây là mục tiêu, chưa phải số liệu đã thu.

Hiện [manifest.json](manifest.json) có **0 query**, gắn với `seed-002-taxonomy` và bật draft để bao phủ 30 sản phẩm hiện tại. Không dùng 45 ảnh gallery làm query đánh giá. Không có model/embedding/metric ảnh trong đợt này.

## Cấu trúc

```text
benchmarks/image/
  manifest.json           danh sách query và trạng thái review, hiện rỗng
  manifest.schema.json    hợp đồng dữ liệu 1.0.0
  raw/                    file do người thu thập cung cấp, bị .gitignore loại trừ
```

Ảnh query, ảnh gốc và văn bản đồng ý có thể chứa thông tin riêng tư; manifest chỉ cần mã người/phiên và tham chiếu hồ sơ bằng chứng, không cần tên thật, email hoặc địa chỉ nhà. Giữ bản gốc và bằng chứng quyền trong kho được nhóm dữ liệu quản lý. Không tự ghi `owned` hoặc người duyệt thay cho người cung cấp.

## Quy trình thu và nhập

1. Chụp ảnh query thật bằng điện thoại hoặc nhận nguồn có quyền dùng. Bao gồm nền phức tạp, ánh sáng khác, che một phần, nhiều vật thể, bao bì có chữ và no-match. Đối chiếu ảnh với gallery để tránh cùng ảnh/phiên chụp hoặc bản gần trùng.
2. Lưu ảnh dưới `raw/` cạnh manifest. Giữ checksum ảnh gốc **trước mọi crop/resize/augment** ở `source_asset_sha256`, cùng `source_asset_id` ổn định. `sha256` là checksum file query thực sự được dùng. Nếu query là file gốc, hai hash giống nhau.
3. Gán `family_id`, `capture_session_id`, `source_asset_id` trước chia split. Các mẫu chung bất kỳ nhóm nào phải ở cùng split, kể cả ảnh biến đổi và truy vấn thêm text. Mã nhóm khác nhau không tự chứng minh ảnh độc lập; người duyệt cần kiểm tra thực tế.
4. Ghi quyền và tham chiếu bằng chứng. Chưa rõ thì để `unknown`/`null`; không đổi quyền chỉ để audit qua.
5. Người duyệt ghi `independence_review` sau đối chiếu gallery và nguồn/phiên. Ghi `judgment` sau chấm; thiếu thì giữ `null`, không biến thiếu nhãn thành điểm 0.
6. Chạy audit và sửa lỗi. Review/phân xử, kiểm tra ảnh giải mã được, gần trùng, tỷ lệ split và khóa test vẫn cần thực hiện riêng trước benchmark.

Lấy hash trên PowerShell:

```powershell
(Get-FileHash -Algorithm SHA256 -LiteralPath benchmarks/image/raw/<ten-file>).Hash.ToLowerInvariant()
```

`<ten-file>` là chỗ cần thay, không phải file đã có. Dùng dấu `/` trong `image_path`, chỉ nhận đường dẫn bên trong `raw/`; không dùng đường dẫn tuyệt đối, `..`, dấu `\` hoặc NTFS stream. Audit giới hạn file 1 byte đến 25 MiB.

## Các trường mỗi sample

| Trường | Cách điền |
|---|---|
| `qid` | ID duy nhất, chữ thường/số/gạch nối/gạch dưới, tối đa 120 ký tự |
| `task` | `exact`, `similar` hoặc `image_text` |
| `text_vi` | Nội dung yêu cầu bổ sung cho `image_text`; `null` với hai tác vụ còn lại |
| `split` | `train`, `dev`, `test`; chỉ chốt sau kiểm tra nhóm |
| `family_id` | Họ sản phẩm của vật thể được chụp, kể cả vật thể ngoài catalog |
| `capture_session_id` | Phiên chụp/nguồn gần trùng, không đặt lại ID khi crop hoặc đổi text |
| `source_asset_id` | ID ảnh gốc, chung cho mọi biến thể từ ảnh đó |
| `source_asset_sha256` | Hash bytes ảnh gốc trước biến đổi; lưu được nguồn gốc crop/augment |
| `image_path`, `sha256` | Đường dẫn tương đối từ thư mục manifest và hash file query |
| `source_url` | URL HTTP(S) nếu có; ảnh tự chụp có thể `null` |
| `usage_rights` | `{status, evidence}`; status `unknown`, `owned`, `licensed`, `permission_granted`; status có quyền phải có evidence không rỗng |
| `independence_review` | `null` hoặc `{independent, reviewed_by, reviewed_at, note}`; `independent=false` bị chặn |
| `judgment` | `null` hoặc `{has_answer, relevance, exact_product_id, exact_variant_sku, reviewed_by, reviewed_at}` |

Ngày giờ review phải là ISO 8601 hợp lệ có múi giờ, ví dụ `2026-10-10T15:00:00+07:00`. Trường ngày giờ/người duyệt là hồ sơ cần nhập đúng thực tế, không phải chỗ để sao chép giá trị ví dụ.

Relevance dùng số nguyên 0..3, phù hợp từ 2. `has_answer` phải khớp việc có điểm >=2. Pool chưa chấm đủ được phép cho query có đáp án; **no-match cần nhãn cho toàn bộ gallery đang hiển thị**, không chấp nhận `relevance={}` để khẳng định không có đáp án. Công cụ không xác minh chất lượng phán đoán.

Với `exact` có đáp án, `exact_product_id` phải thuộc catalog hiển thị và có điểm >=2; `exact_variant_sku` có thể `null` nếu chỉ biết product, hoặc SKU phải thuộc product đó. Các query cùng exact product không được chia qua split dù đổi tên family. `similar`, `image_text` và no-match phải để cả hai trường exact là `null`.

## Chạy audit

Chạy từ gốc workspace, dùng dependency hiện có trong `backend/requirements.txt`:

```bash
.venv/Scripts/python scripts/benchmark/audit_image_queries.py
```

Có thể chọn `--manifest`, `--catalog`, `--report-dir`. Mỗi lần ghi cặp Markdown/JSON có timestamp dưới `reports/benchmark/`, kèm hash manifest/catalog/schema/code; không sửa dữ liệu.

| Trạng thái | Ý nghĩa | Exit |
|---|---|---|
| `pending_collection` | Manifest hợp lệ nhưng chưa có query | 0 |
| `pending_review` | Có file nhưng còn quyền/nhãn/review độc lập chưa ghi | 0 |
| `recorded_checks_passed` | Các kiểm tra và hồ sơ đã khai báo đạt; không phải phê duyệt benchmark | 0 |
| `invalid` | Sai schema/hash/file/tham chiếu, rò split hoặc dùng lại gallery | 1 |

Mọi trạng thái đều có `benchmark_approved=false`. Exit 0 không có nghĩa đã có bộ test đủ dùng. Báo cáo đếm riêng tổng query, số hash ảnh duy nhất, họ sản phẩm, split, tác vụ và mục chờ duyệt.

## Những gì audit kiểm tra và chưa kiểm tra

- Kiểm tra catalog/schema, khóa catalog hash, quyền được khai báo có bằng chứng, ID/nhãn/SKU, file có thật/khác rỗng/đúng checksum/đúng thư mục.
- Chặn ảnh query hoặc hash ảnh gốc trùng byte với gallery, kể cả gallery có draft/archived. Hash gallery dùng cả giá trị khai báo và file đọc được.
- Chặn rò split qua family, phiên chụp, ID/hash ảnh gốc, hash query và exact product. ID ảnh gốc chỉ có một checksum. Ảnh + text có thể dùng cùng ảnh trong **cùng split**, nhưng phải có provenance nhất quán và nhận cảnh báo trùng byte; không tính số query như số ảnh độc lập.
- Không giải mã ảnh, không phát hiện mọi file giả/hỏng định dạng, gần trùng hay ảnh gốc khai sai; `hash_verified` chỉ nói về bytes. Không xác minh quyền/danh tính/nhãn hoặc độc lập thực tế. Cần người duyệt và bước giải mã/dedup trước dùng dữ liệu cho model.
- Chưa kiểm tra đa dạng danh mục, đủ tỷ lệ split/no-match, phát hiện nội dung riêng tư tự động, CI bootstrap, embedding hay model inference. Không tự khóa test và không coi split do người nhập ghi là đã nghiệm thu.

Khi DB thay đổi, giữ manifest cũ làm hồ sơ, đối chiếu lại gallery/nhãn và tạo phiên bản thu thập mới; không chỉ thay catalog hash để bỏ lỗi. Xem [báo cáo triển khai](../../reports/progress/2026-10-10_GD3_khung-thu-query-anh.md).

## Giải mã ảnh và gợi ý gần trùng (tùy chọn)

Đã bổ sung `scripts/benchmark/audit_image_pixels.py` để thực hiện bước sau audit cấu trúc. Công cụ dùng Pillow trong môi trường riêng với dependency tại [requirements-images.txt](../../scripts/benchmark/requirements-images.txt); không yêu cầu thêm Pillow vào API runtime. Trên máy hiện tại, **Python hệ thống** (`python`) có Pillow 12.3.0 và jsonschema 4.26.0, còn `.venv` chưa có Pillow.

```bash
python scripts/benchmark/audit_image_pixels.py --review-out artifacts/image_review/<thu-muc-moi>
python -m unittest discover -s scripts/benchmark/tests -p test_image_pixels.py -v
```

Thay `<thu-muc-moi>` bằng thư mục chưa tồn tại. Có thể bỏ `--review-out` nếu chỉ cần JSON/Markdown. Không ghi đè trang review cũ. Cần chuẩn bị môi trường với `python -m pip install -r scripts/benchmark/requirements-images.txt` trên máy chưa có các dependency này; dùng đúng interpreter đã cài chúng.

Quy trình kiểm tra:

1. Chạy lại audit manifest/catalog; nếu invalid thì dừng trước giải mã. Kiểm tra input hash trước/sau scan và hash bytes trước giải mã.
2. Giải mã toàn bộ ảnh gallery có file (kể cả draft/archived) và query. Chấp nhận JPEG/PNG/WebP tĩnh, tối đa 25 MiB/file và 20 triệu pixel; không bật chế độ chấp nhận ảnh bị cắt. SVG/GIF/animation hoặc format khác bị từ chối, cần chuẩn hóa qua quy trình nhập liệu riêng.
3. So kích thước lưu trong DB với kích thước ảnh mã hóa. Áp dụng EXIF orientation, ghép alpha trên nền trắng và chuyển RGB **trong bộ nhớ**, không sửa file gốc. Lưu hash pixel kèm kích thước, tách với SHA-256 bytes.
4. Tính dHash 64 bit: ảnh xám resize LANCZOS 9×8, so pixel trái/phải theo hàng. Gợi ý cặp có Hamming distance ≤6 mặc định; đổi bằng `--threshold 0..64`. Ngưỡng này chưa được hiệu chỉnh trên dataset độc lập.
5. Phân biệt cặp gallery cùng/khác sản phẩm, query cùng/khác split và query–gallery. Cặp liên quan query–gallery hoặc query khác split cần ưu tiên duyệt. Ảnh ít tương phản được đánh dấu để lưu ý dHash dễ trùng.

| Trạng thái | Ý nghĩa | Exit |
|---|---|---|
| `invalid` | Audit trước đó sai, ảnh không giải mã được, hash/kích thước sai hoặc scan không đầy đủ | 1 |
| `requires_visual_review` | Có ứng viên query–gallery hoặc query khác split cần đối chiếu | 2 |
| `pending_collection` / `pending_review` / `recorded_checks_passed` | Giữ trạng thái audit manifest nếu scan đạt và không có cặp ưu tiên cao | 0 |

Mọi trạng thái vẫn có `benchmark_approved=false`. Các cặp gallery gần nhau được liệt kê dù manifest chưa có query. Trang HTML chỉ đọc, không ghi quyết định duyệt hoặc xóa ảnh; các file ảnh được liên kết trực tiếp nên cần giữ cấu trúc thư mục khi mở lại.

**Không dùng dHash để tự loại dữ liệu.** Cùng bố cục bao bì hoặc hình dáng trên nền trắng có thể cho hash gần nhau dù sản phẩm/màu/chữ khác nhau. Ngược lại, crop mạnh, đổi nền, góc chụp hoặc ánh sáng có thể khiến ảnh cùng nguồn vượt ngưỡng. Distance 0 cũng không chứng minh trùng pixel. Hash pixel sau chuẩn hóa không xét profile ICC và có thể coi ảnh khác metadata/ẩn dưới alpha là tương đương trên nền trắng. Độ giống không chứng minh xuất xứ hay quyền sử dụng.

Bộ test ảnh là **bộ riêng**, chưa được chạy bởi `scripts/run_all_tests.py` vì môi trường backend không có Pillow. Không dùng 22 test fixture này làm benchmark retrieval.

Kết quả gallery hiện tại: [45 ảnh giải mã được, 19 cặp gợi ý](../../reports/benchmark/2026-10-10_152959-680994_image-pixels.md), [trang đối chiếu](../../artifacts/image_review/2026-10-10_pixel-audit/index.html). Chưa có query thật; chưa có quyết định nghiệm thu toàn bộ cặp gần trùng.

## Chạy đánh giá retrieval (thêm 10/10/2026, GĐ4)

```bash
.venv/Scripts/python scripts/benchmark/eval_image.py --adapter <module:Class> --split dev --name <ten-run>
```

- Chạy `audit()` của `audit_image_queries.py` trước; manifest `invalid` thì dừng, chưa có query dùng được thì báo trạng thái và không ghi kết quả.
- Chỉ chấm query có `judgment`, không bị đánh dấu `independent=false`. Query chưa có review độc lập/quyền chỉ chạy trên train/dev với `--allow-unreviewed` (ghi `smoke_unreviewed`). Split test cần `--confirm-locked-test`, không nhận `--allow-unreviewed`.
- Gallery là ảnh catalog theo `include_drafts` của manifest. Chỉ mục dựng trong bộ nhớ, hoặc nạp từ `--index-dir` nếu khớp model/tiền xử lý/ảnh.
- Query đi đúng đường của API: embedding → cosine gộp theo sản phẩm → `SearchEngine.search_visual` với `text_vi`. Do đó giá/phủ định trong `text_vi` là bộ lọc cứng.
- Metric dùng [retrieval_metrics.py](../../scripts/benchmark/retrieval_metrics.py): exact Recall@1/5/10 và MRR@10 theo product; similar/image_text nDCG@10, mAP@10 và Success@5. Có sản phẩm chưa chấm trong top K thì metric là `null`.
- No-match chưa có ngưỡng; báo trung vị `top_similarity` của query có/không có đáp án để chọn ngưỡng trên dev.
- Độ trễ theo [latency_protocol.py](../../scripts/benchmark/latency_protocol.py): `--latency-rounds` lượt đo embedding, cold start tách riêng (nạp adapter, dựng/nạp chỉ mục, lần embed đầu), GPU/driver/provider ORT, đỉnh VRAM, cảnh báo máy bận.
- Ghi `run.json` + `predictions.jsonl` vào `experiments/results/<thời điểm>_image_<tên>/`. Mọi run vẫn có `benchmark_approved=false`.

## Thu ảnh bằng trang `#/collect/image` (thêm 10/10/2026)

Mở `http://localhost:5173/#/collect/image`. Nếu backend đang chạy, trang gợi ý mã họ sản phẩm từ catalog; không có backend thì nhập tay được.

1. Nhập thông tin phiên: mã người chụp, mã phiên chụp (nơi/thời điểm), split đã phân, quyền sử dụng (`owned`/`permission_granted`/`licensed`) và mã bằng chứng quyền. Thiếu mục nào thì không thêm được ảnh.
2. Mỗi ảnh: chọn họ sản phẩm (`family_id`) và tác vụ (`exact`, `similar`, `image_text` kèm yêu cầu bằng chữ), rồi chụp/chọn ảnh. Ảnh được mã hóa lại JPEG q95, cạnh ≤2048 px, để **bỏ EXIF/GPS**; `source_asset_sha256` giữ hash bytes ảnh gốc. Dùng lại cùng ảnh gốc (ví dụ thêm yêu cầu chữ) sẽ giữ cùng `source_asset_id`.
3. Tải zip (`samples.json` + `raw/<qid>.jpg`) rồi nhập:

```bash
.venv/Scripts/python scripts/benchmark/import_image_session.py image-<...>.zip --dry-run
.venv/Scripts/python scripts/benchmark/import_image_session.py image-<...>.zip
```

Script kiểm tên file, hash và qid, rồi chạy `audit()` trên manifest đã gộp. Audit `invalid` (ví dụ cùng họ sản phẩm ở hai split, ảnh trùng gallery) thì xóa file vừa ghi và giữ nguyên manifest. Sau khi nhập, trạng thái là `pending_review`: người duyệt điền `independence_review` và `judgment` trước khi chạy `eval_image.py` (dùng packet chấm bên dưới).

## Chấm judgment bằng packet pool (thêm 10/10/2026)

PLAN §8.1 yêu cầu gom top kết quả của mọi baseline, cộng mẫu ngẫu nhiên, rồi mới chấm.

```bash
.venv-ml/Scripts/python scripts/benchmark/prepare_image_review.py --split dev \
    --adapter app.ml.image:SigLIP2Base --adapter app.ml.image:DINOv2Base \
    --out artifacts/image_judgment/<thu-muc-moi>
```

- Với mỗi query chưa có `judgment` (thêm `--include-judged` để chấm lại): lấy top `--top-k` (mặc định 10) theo cosine ảnh của từng adapter. Với `image_text`, thêm top của ảnh + chữ (bộ lọc cứng) và BM25 trên `text_vi`. Cộng `--random` (mặc định 5) sản phẩm ngẫu nhiên, cố định theo `--seed` và qid. Chỉ mục nạp từ `artifacts/indexes/image/` nếu khớp, không thì dựng trong bộ nhớ.
- Pool được xáo theo hash: người chấm không thấy thứ hạng hay model nào tìm ra (nguồn chỉ lưu trong `packet.json` → `pool_sources`). Phần còn lại của gallery vẫn có trong trang, vì no-match cần nhãn cho toàn bộ gallery.
- Mở `index.html` (offline, tự lưu nháp trong trình duyệt, có Lưu/Nạp bản nháp). Mỗi query: chấm 0–3 hết danh sách chính. Nếu chưa có sản phẩm đạt 2–3 thì phải chấm cả phần còn lại. Query `exact` có đáp án phải chọn sản phẩm đúng (và SKU nếu biết). Ô đánh giá **độc lập với gallery** bắt buộc kèm ghi chú. Đổi nhãn sau khi xác nhận sẽ bỏ xác nhận.
- **Xuất judgment đã xác nhận** tạo file JSON gồm các query đã xác nhận hoặc đã đánh giá độc lập. Áp vào manifest:

```bash
.venv/Scripts/python scripts/benchmark/apply_image_judgments.py image-judgments-<id>.json --dry-run
.venv/Scripts/python scripts/benchmark/apply_image_judgments.py image-judgments-<id>.json
```

Script yêu cầu `catalog_sha256` của file chấm = manifest = `database.json` hiện tại, qid có trong manifest và `sha256` ảnh không đổi. Judgment/independence_review đã có chỉ được thay khi thêm `--replace-judged`. Sau khi gộp, script chạy `audit()` trên bản tạm; nếu `invalid` (no-match thiếu nhãn gallery, exact chưa được chấm ≥2, sản phẩm ẩn…) thì không ghi gì. Packet chỉ dùng để chấm nhãn; với split test, không xem kết quả model để chỉnh cấu hình.

Hai người chấm độc lập cùng packet (profile trình duyệt riêng để không chung nháp) thì đối chiếu:

```bash
.venv/Scripts/python scripts/benchmark/compare_reviews.py image <image-judgments-A.json> <image-judgments-B.json>
```

So `has_answer`, sản phẩm/SKU exact, đánh giá độc lập và điểm trên các sản phẩm cả hai cùng chấm; sản phẩm chỉ một người chấm được đếm riêng. Exit 2 = cần phân xử.

## So sánh hai run (paired bootstrap)

```bash
.venv/Scripts/python scripts/benchmark/compare_runs.py --left experiments/results/<run A> --right experiments/results/<run B>
```

Chỉ so khi cùng manifest, split và tập qid; lệch thì exit 2. Resample theo **họ sản phẩm** có hoàn lại, cho delta và CI 95% của Recall@1/5, MRR@10, nDCG@10, mAP@10, Success@5 (chỉ query đủ nhãn ở cả hai run). Dưới 5 cụm có dữ liệu thì không báo CI (ví dụ FLEURS chỉ có 1 cụm vì không có mã người nói). Báo cáo ghi vào `reports/benchmark/`. CI chứa 0 nghĩa là chưa phân biệt được hai cấu hình; công cụ không tự chọn model.
