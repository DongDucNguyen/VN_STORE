# Phân tích nhãn đã duyệt và sửa tìm kiếm — 15/10/2026

Đã đối chiếu hai file với nhãn máy nguồn, triển khai ba sửa đổi tìm kiếm và đo trước/sau trên cùng các truy vấn đủ nhãn. Nhãn gốc, ghi chú và quyết định người duyệt được giữ nguyên. Đây là chẩn đoán train/dev có cả bằng chứng suy ra theo phạm vi, không phải nghiệm thu benchmark độc lập.

## Dữ liệu

| Nhóm | Số cặp |
|---|---:|
| Toàn bộ | 125.579 |
| Incorrect, có điểm sửa | 1.453 |
| Correct trực tiếp | 124 |
| Chấp nhận suy ra theo phạm vi đã xem | 82.422 |
| Tổng có bằng chứng duyệt | 83.999 |
| Chưa kiểm định | 41.580 |

- 480 truy vấn trong file toàn bộ; 354 truy vấn có bằng chứng duyệt: 174 train, 180 dev.
- 250 truy vấn đã duyệt có đủ 330 sản phẩm; **104 truy vấn chỉ có nhãn cho một phần catalog**. Cặp không có dòng nhãn cũng là chưa biết, khác với 41.580 dòng `unreviewed` đã liệt kê.
- File đã duyệt khớp chính xác tập `is_human_reviewed=true` trong file toàn bộ. Không có cặp trùng hay điểm sai kiểu. Điểm 0 giữ là số nguyên, điểm sửa chưa cung cấp giữ `null`.
- **1.451 điểm thực sự thay đổi**. Hai thao tác Incorrect giữ nguyên điểm (1→1 và 2→2); không tự chuyển chúng thành Correct.
- **1.049 cặp đi qua ngưỡng phù hợp 1/2**, ảnh hưởng đến Success/Recall và `has_answer` khi dựng tập nhãn mới.

| Điểm máy → điểm cuối | Số cặp Incorrect |
|---|---:|
| 1 → 2 | 935 |
| 1 → 0 | 140 |
| 2 → 3 | 129 |
| 0 → 1 | 119 |
| 0 → 2 | 55 |
| 0 → 3 | 32 |
| 1 → 3 | 17 |
| 3 → 2 | 14 |
| 2 → 0 | 10 |
| 1 → 1; 2 → 2 | 1 mỗi loại |

Ghi chú thường gặp: đúng loại nhưng khác xuất xứ (244 + 69 ghi chú theo hai cách viết), sai giá thành (52), sai chất liệu (43 với cách viết phổ biến nhất), chưa rõ công dụng (42), sai mục đích (40). Có 425 bản ghi Incorrect không có ghi chú. Đây là đếm nguyên văn, không phải toàn bộ số lỗi của mỗi nguyên nhân.

Quy tắc máy thường cho 1 khi sai thuộc tính, còn người duyệt nhiều lần chấp nhận 2. Cần thống nhất rubric, **không đổi hàng loạt 1 thành 2**. Nhóm suy ra còn giữ nhiều điểm máy; tỷ lệ đồng ý trên 83.999 cặp không đo độ chính xác của một lần chấm độc lập. Nhãn máy 0–3 cũng không phải điểm BM25 của hệ thống tìm kiếm.

## Đã sửa

1. **Phủ định họa tiết:** `không có họa tiết sen` trước đây chỉ xử lý “họa”, để “tiết sen” tham gia tìm kiếm tích cực; `khong ve sen` gặp lỗi tương tự. Parser nhận cụm họa tiết/hoa văn/vẽ, lấy họa tiết và lọc trên tên, alias, trường motifs. Không lấy thương hiệu hoặc mô tả chung làm bằng chứng họa tiết. “Vẽ tay” được phân biệt với tên họa tiết.
2. **Đơn vị tương đương:** 800 ml ↔ 0,8 L; 650 ml ↔ 0,65 L; kg ↔ g; cm ↔ mm. Chỉ mục số đo riêng không làm đổi độ dài tài liệu/điểm BM25 của câu không có số đo. Tiền, số trần, kích thước ghép và đại lượng khác loại không bị gộp.
3. **Tên gọi hộp bút:** thêm “hộp đựng bút”, “hộp bút”, “ống cắm bút”, “pen holder” vào từ điển. Không gắn qid/product_id hoặc điểm nhãn vào logic tìm kiếm.

Mã: [engine.py](../../backend/app/search/engine.py), [query_parser.py](../../backend/app/search/query_parser.py), [normalize.py](../../backend/app/search/normalize.py), [lexicon.py](../../backend/app/search/lexicon.py).

## Đo trước/sau

Chạy trên 328 sản phẩm published, cấu hình mặc định, không bật semantic model. Hai lần dùng cùng hash đầu vào và chế độ hiển thị. nDCG dùng gain `2^rel−1`, chỉ tính câu có nhãn phù hợp và toàn bộ kết quả trả về trong top 10 đã có nhãn. Thiếu nhãn trả `null`; không xóa sản phẩm khỏi thứ hạng. IDCG của pool chỉ dựa trên nhãn đã biết.

| Tập | Câu đủ nhãn chung | nDCG@10 trước | Sau | Tăng / giảm |
|---|---:|---:|---:|---:|
| Train đã duyệt, gồm suy ra | 174 | 0,8620 | **0,8743** | 6 / 0 |
| Dev đã duyệt, gồm suy ra | 132 | 0,9019 | **0,9019** | 0 / 0 |
| Dev chỉ xác nhận trực tiếp | 12 | 0,9020 | 0,9020 | 0 / 0 |

Train chỉ xác nhận trực tiếp không có câu đủ nhãn top 10 để tính nDCG; không coi chúng là điểm 0. Success@5 giữ nguyên: train 0,9713 trên 174 câu; dev 0,9872 trên 156 câu. Số câu đủ nhãn giữa các cutoff khác nhau.

| Câu cải thiện | nDCG@10 trước | Sau |
|---|---:|---:|
| bình hoa không có họa tiết sen | 0,2051 | 1,0000 |
| binh hoa khong ve sen | 0,1389 | 1,0000 |
| ấm trà 800ml | 0,6327 | 0,7995 |
| ấm 650ml | 0,6524 | 0,7863 |
| bình hoa cao 40 cm | 0,6973 | 0,7916 |
| hộp đựng bút | 0,3728 | 0,4597 |

Không kết luận đã sửa hết xếp hạng: “hộp đựng bút” mới cải thiện một phần; “khay trang trí bàn trà” vẫn có kết quả sai loại. Cả 17 câu dev đủ nhãn toàn catalog nhưng không có sản phẩm đạt ≥2 vẫn trả kết quả (false accept = 1,0). Cần hiệu chỉnh khả năng từ chối câu không có đáp án trên nhãn nhất quán; đợt này chưa thay ngưỡng toàn hệ thống.

## Nhãn cần phân xử

So câu sau khi bỏ dấu phát hiện 4 trường hợp sản phẩm có điểm khác nhau. Bỏ dấu có thể gây nhập nhằng; công cụ chỉ nêu ứng viên, không tự chọn điểm thắng.

| Sản phẩm / cặp câu | Điểm và bằng chứng |
|---|---|
| Elephone `af26el01`: `kw-seed-005` / `kw-train-son-mai-1` | “do son mai” = 0, “đồ sơn mài” = 3; **cả hai sửa trực tiếp** |
| Elephone `af26el02`: cùng hai câu trên | 0 / 3; **cả hai sửa trực tiếp** |
| Chén Jasmine Chỉ Xanh Dương: `kw-dev-001` / `kw-dev-002` | “chén cơm sứ trắng” = 3 trực tiếp; bản không dấu = 1 suy ra |
| Ironbar 65% Box Of 16X40G: `kw-dev-093` / `kw-train-socola-den-1` | “sô cô là đen” = 2; “sô cô la đen” = 1; đều suy ra |

Có 4 nhóm ứng viên tương đương ở cả train và dev: đồ sơn mài, sô cô la đen, giỏ mây, nồi cơm điện. Xem `query_variant_checks` trong JSON sau sửa để biết đầy đủ qid, product_id và ghi chú. Cần thống nhất nhóm và chia lại trước đánh giá độc lập; không sửa split chỉ để thay đổi điểm báo cáo.

## Kiểm tra nguồn và tái lập

[analyze_reviewed_pairs.py](../../scripts/benchmark/analyze_reviewed_pairs.py) kiểm tra schema, cặp trùng, quan hệ điểm gốc/sửa/cuối, trạng thái/bằng chứng, tập con, qid/query/product/điểm với nhãn nguồn và hash catalog. Công cụ tách bốn trạng thái, từ chối split test, ghi ma trận từng nhóm, dự đoán từng câu, hash mã nguồn và so sánh trên **giao của các câu đủ nhãn**.

Catalog working tree dùng CRLF: hash byte `52ba684ed1da2381a06cb354ab1c95f458d68b781b52518b59bc65100262265e`. Sau duy nhất CRLF→LF, hash khớp nguồn `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`. Công cụ ghi rõ ngoại lệ xuống dòng, không bỏ qua thay đổi nội dung. Không thay kiểm tra hash của evaluator chính thức.

Tham chiếu `manual_export` và `scope` được giữ nguyên. Công cụ không xác thực danh tính hoặc file bằng chứng bên ngoài, không tạo `verified=true`, người chấm hay thời gian chấm. Không xuất cặp chưa duyệt thành nhãn chuẩn.

```powershell
.venv/Scripts/python -X utf8 scripts/benchmark/analyze_reviewed_pairs.py --evaluate --baseline reports/benchmark/2026-10-15_reviewed-pairs-before.json --out artifacts/reviewed-pairs-rerun.json
.venv/Scripts/python -m pytest backend/tests/test_reviewed_pairs.py backend/tests/test_keyword_gd5.py -q
```

Kết quả: [trước sửa](2026-10-15_reviewed-pairs-before.json), [sau sửa và so sánh](2026-10-15_reviewed-pairs-after.json). Không chạy lại ghi đè báo cáo trước sửa bằng mã mới.

Kiểm thử toàn backend: **807 passed, 5 skipped** (87,74 giây). Sau bổ sung kiểm tra xung đột nhãn và hai test cuối, chạy lại hai module liên quan: **79 passed**. Có cảnh báo deprecation Starlette/httpx; không có test thất bại. Không sửa giao diện hay gọi model ngoài.
