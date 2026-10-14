# Rà soát bộ ảnh test search image — 13/10/2026

**Kết luận:** có **44 file ảnh trong toàn bộ `tmp_data`**, trong đó **40 ảnh thuộc bộ test**. Các file test là ảnh tải thực từ URL Internet: lần kiểm tra này đọc lại cả 40 URL và thu được bytes khớp SHA-256 của 40 file cục bộ. Bộ ảnh đạt yêu cầu chuẩn bị đầu vào cho thử thủ công, nhưng **chưa đủ để xác nhận hệ thống tìm kiếm tốt hoặc nghiệm thu model**. Chất lượng tuyển chọn cần cải thiện: một số ảnh khác xa catalog, 10 ảnh trùng gallery, và toàn bộ ảnh chưa có nhãn relevance đã duyệt.

## 1. Phạm vi kiểm tra

Hiểu `tmp_dât` trong yêu cầu là `tmp_data` đang có và được mở trong IDE. Chỉ tạo hồ sơ rà soát trong `tmp_data/audit-2026-10-13/` và bổ sung liên kết hướng dẫn bên trong tmp_data. Không đổi ảnh, manifest nguồn, nhãn, chia split, catalog, ứng dụng hoặc báo cáo bên ngoài. Không thêm ảnh để làm thay đổi mẫu đang được kiểm tra.

Đã đọc lại manifest, danh sách lựa chọn, script tải/kiểm tra, hồ sơ nguồn, 50 ca thử; kiểm đếm file từ filesystem; giải mã bằng Pillow; gọi hàm kiểm tra ảnh thật của backend mà không khởi động ứng dụng; đối chiếu hash với 814 ảnh gallery; xem hai contact sheet bao phủ 40 ảnh; kiểm tra taxonomy/tên hàng hiện hành và yêu cầu benchmark trong PLAN/README ảnh.

Hồ sơ chính:

- [local_checks.json](local_checks.json): kiểm đếm, kích thước, checksum, pixel hash, gallery, catalog và nhãn.
- [remote_checks.json](remote_checks.json): URL, HTTP response và hash tải lại của từng ảnh; dữ liệu ảnh từ lượt kiểm tra chỉ xử lý trong RAM.
- [outside_comparison.json](outside_comparison.json): đối chiếu phạm vi chỉ đọc bên ngoài thư mục.
- [audit.py](audit.py): mã kiểm tra có thể chạy lại với Python `-B`; mọi báo cáo nằm trong thư mục audit.

## 2. Chính xác có bao nhiêu ảnh?

| Cách đếm | Số lượng | Giải thích |
|---|---:|---|
| `images/similar_candidate/` | 25 | 5 ảnh mỗi nhóm sản phẩm lớn; là ứng viên, không phải 25 ca đã xác nhận có đáp án |
| `images/negative_candidate/` | 5 | Laptop/bàn phím, xe đạp và bóng; dự định thử ngoài phạm vi catalog |
| `images/gallery_control/` | 10 | 2 ảnh mỗi nhóm; tải lại từ chính nguồn ảnh catalog |
| **Ảnh test đang dùng** | **40** | Khớp đúng manifest, không thiếu và không có file thừa trong `images/` |
| `excluded/` | 2 | Ảnh đã loại, giữ để truy vết; không được đưa vào ca thử |
| `preview/` | 2 | Contact sheet tạo từ các ảnh trên, không phải 2 query mới |
| **Tổng file ảnh trong tmp_data** | **44** | 40 + 2 + 2 |
| Ảnh tải từ Internet còn lưu, tính cả ảnh loại | 42 | Không tính 2 contact sheet |
| Ca thử trong `test_cases.json` | 50 | 40 ca ảnh thuần và 10 ca ảnh + chữ dùng lại ảnh; không phải 50 ảnh |

40 ảnh test có tổng **13.414.892 bytes = 12,79 MiB**. Toàn bộ 44 file ảnh có **14.645.918 bytes ≈ 13,97 MiB**. Định dạng bộ test: **34 JPEG, 4 PNG, 2 WebP**. File JSON trong `evidence/`, ví dụ `search-10.json`, là phản hồi tìm kiếm/metadata; không phải file ảnh.

## 3. Ảnh có thật và dùng được không?

### Bằng chứng kỹ thuật vừa kiểm tra

| Kiểm tra | Kết quả | Giới hạn kết luận |
|---|---|---|
| Pillow verify + load | 44/44 file ảnh đọc/giải mã được | Không phải HTML lỗi đổi đuôi; không tự chứng minh chất lượng xếp hạng |
| Hàm `app.media.inspect_image` | 40/40 ảnh test đạt | Kiểm đầu vào API, chưa phải gọi endpoint với model |
| Hash/byte/kích thước/format so manifest | 40/40 khớp | Hồ sơ khớp file hiện tại |
| Đối chiếu nguồn đã lưu | 30/30 Commons khớp metadata ứng viên; 10/10 đối chứng khớp URL/hash ảnh catalog | URL metadata không phải xác nhận danh tính sản phẩm của mọi ảnh |
| Đọc lại URL ảnh qua Internet | 40/40 HTTP 200, giải mã được và cùng SHA-256 với bản local | Xác nhận file tồn tại ở URL vào thời điểm kiểm tra; nguồn có thể đổi về sau |
| Trùng byte trong 40 ảnh | 0 cặp | Khác bytes không bảo đảm độc lập về vật thể/phiên chụp |
| Trùng pixel sau chỉnh EXIF, nền trắng, RGB | 0 cặp | Không phát hiện hết crop/góc chụp khác từ cùng vật thể |
| Trùng byte với 814 ảnh gallery | Chính xác 10 ảnh đối chứng | 25% bộ ảnh không thể là query đánh giá độc lập |

Kích thước các ảnh từ 296–3000 px theo chiều rộng, 240–3000 px theo chiều cao; ảnh lớn nhất 3000×3000 = 9 MP. File lớn nhất 705.474 bytes, thấp hơn 8 MiB. Mọi ảnh vượt mức tối thiểu 32 px/chiều và thấp hơn 40 MP của backend. Có ảnh nhỏ như `web-046` 600×240 và `web-072` 296×285; hợp lệ để tìm ảnh nhưng không thích hợp để mặc định OCR chữ nhỏ sẽ rõ.

Quan sát cho thấy ảnh chụp đồ vật, ảnh sản phẩm, ảnh bảo tàng, ảnh ngoài trời và cảnh phố; có hình dạng/nền/ánh sáng thực, không phải bộ placeholder do script vẽ. Script thu thập giữ bytes nguồn; chỉ contact sheet là ảnh ghép do công cụ tạo. Tuy nhiên, **ảnh tải thật từ Internet không đồng nghĩa ảnh khách hàng VNStore chụp thật**, và kiểm tra này không phải giám định để khẳng định mọi nguồn chưa từng chỉnh sửa hoặc dùng công cụ tạo ảnh. Đặc biệt ảnh sản phẩm có thể đã được tách nền/chỉnh màu tại nguồn.

## 4. Nội dung có sát bài toán không?

Catalog hiện hành: `seed-006-enriched`, 330 sản phẩm, 328 published, 814 ảnh. Nhóm published: gốm 65; mây tre/cói 66; dệt may 66; gỗ/sơn mài 65; thực phẩm 66. Bộ test phủ đủ 5 tên nhóm, nhưng **phủ nhóm lớn chưa đồng nghĩa phủ loại hàng, SKU, biến thể hoặc tình huống thực tế**.

| Ảnh | Nội dung quan sát | Đánh giá sử dụng |
|---|---|---|
| `web-000` | Ấm gốm vỡ/khuyết, kiểu cổ | Hữu ích như ca khó; không đại diện mặt hàng nguyên vẹn bình thường |
| `web-001`, `web-005` | Ấm trà kiểu châu Âu, ảnh sưu tập | Có cùng loại vật thể với bộ trà; phong cách khác catalog Minh Long, không coi là exact |
| `web-006`, `web-008` | Bình sứ cổ ở không gian trưng bày | Có thể thử hình dáng/hoa văn và ánh sáng khó; khác dòng sản phẩm hiện hành |
| `web-010`, `web-011` | Giỏ có quai chứa trứng/nấm ngoài trời | Tốt để thử ảnh có nền phức tạp, vật chứa và crop |
| `web-017`, `web-019`, `web-021` | Giỏ/sàng đan; một ảnh nhiều giỏ | Có ích cho chất liệu nhìn thấy và nhiều vật thể; không suy chắc mây/tre/cói từ ảnh |
| `web-022`, `web-023` | Hai góc/phần hoa văn trong bộ ảnh khăn Ấn Độ | Thử hoa văn; cùng bộ nguồn nên cần kiểm tra quan hệ vật thể/phiên chụp, không mặc định độc lập |
| `web-029`, `web-030`, `web-031` | Nón, nón trong cảnh phố, nón trưng bày | Rà tên toàn catalog không có mặt hàng nón; không mặc định là ca có đáp án cùng loại. Ảnh cảnh phố cần crop rõ mục tiêu |
| `web-034` | Bức/bộ tranh sơn mài trong bảo tàng | Có ích cho chất liệu/hoa văn ở mức thăm dò; không thay ảnh hộp/bình đang bán |
| `web-036`, `web-037` | Hộp sơn mài có trang trí | Gần với loại hàng hộp hơn; chưa có nhãn sản phẩm nào là phù hợp |
| `web-038`, `web-039` | Hộp nghi lễ tròn, ảnh cùng bảo tàng | Ca tương tự có điều kiện; cần duyệt họ/nguồn, không tự coi hai họ độc lập |
| `web-046`, `web-047`, `web-049` | Chocolate thương hiệu khác, có bao bì/mở gói | Tốt để thử tương tự và khác thương hiệu; không phải Marou exact |
| `web-052`, `web-053` | Bao bì cà phê | Catalog có 0 sản phẩm trong `thuc-pham-ca-phe`, không có tên hàng cà phê/coffee; toàn 66 thực phẩm thuộc bánh kẹo, thương hiệu Marou. Hai ảnh này nên thử khác loại hàng, không gán positive vì cùng nhóm thực phẩm |
| `web-057`, `web-060` | Laptop và bàn phím | Âm tính dễ; hai ảnh chỉ bao phủ một nhóm đồ điện tử gần nhau |
| `web-063` | Xe đạp trước tường nhiều hình vẽ | Âm tính có nền rối; vật cần tìm nhỏ hơn nền |
| `web-071`, `web-072` | Quả bóng trên nền sân/cỏ | Âm tính dễ; ảnh 072 độ phân giải nhỏ |
| `control-030`…`control-039` | Ảnh catalog của chén, bộ trà, giỏ, túi, bình, hộp, khăn, chocolate | Có product ID nguồn và trùng byte gallery; tốt cho đối chứng luồng, không có tính độc lập |

**Điểm yếu cụ thể của đợt chọn ảnh trước:** nhãn nhóm dựa nhiều vào taxonomy rộng và từ khóa nguồn. Ít nhất **5/25 ảnh `similar_candidate`** (3 ảnh nón + 2 ảnh cà phê) không nên được hiểu là ca “catalog chắc chắn có loại hàng phù hợp”. Chúng vẫn hữu ích để thử khác loại hàng hoặc kết quả sai; không phải file hỏng và chưa đủ căn cứ để tự gán no-match chính thức cho toàn gallery. Đợt audit giữ nguyên manifest để không biến nhận xét thành nhãn đã duyệt.

Các thiếu hụt bao phủ rõ ràng: không có query ngoài gallery về trang phục dù catalog có 24 sản phẩm thuộc `det-may-thoi-trang`; chưa có ảnh ngoài gallery của đèn/nội thất đan dù catalog có 14 sản phẩm thuộc `may-tre-coi-noi-that`; thiếu ảnh chén/đĩa/ly bên ngoài gallery; nhiều ảnh gốm/sơn mài là hiện vật cổ. Bộ âm tính 5 ảnh chủ yếu là ba nhóm vật thể dễ khác biệt, thiếu đồ gần giống nhưng sai mẫu, chất liệu, màu hoặc thương hiệu.

## 5. Có đủ điều kiện xác nhận “tìm kiếm tốt” không?

**Chưa đủ.** Phân biệt các mức kiểm chứng:

| Mục tiêu | Trạng thái hiện tại |
|---|---|
| Có file ảnh Internet cục bộ, mở và upload được theo giới hạn | Đạt kiểm tra đầu vào |
| Bắt đầu thử tay: toàn ảnh, crop, thêm chữ, xem kết quả | Có đầu vào để thực hiện; cần đọc đúng vai trò từng ảnh |
| Xác nhận ứng dụng chạy end-to-end với model thật | Chưa thực hiện trong đợt thu/audit này |
| Xác nhận tìm đúng SKU bằng ảnh mới | Chưa đủ: 10 ảnh biết product ID đều trùng gallery |
| Xác nhận tìm tương tự tốt | Chưa đủ: 0 ảnh có relevance judgment đã ghi |
| Xác nhận ảnh + tiếng Việt cải thiện hoặc giữ đúng ràng buộc | Chưa đủ: 10 ca chữ đều dùng ảnh gallery, không có expected relevance và chưa đo |
| Xác nhận OCR tiếng Việt tốt | Chưa đủ: không có transcript OCR chuẩn, đa phần bao bì ngoài gallery dùng chữ Latin/ngoại ngữ |
| Xác nhận no-match tốt | Chưa đủ: 5 candidate không có nhãn toàn gallery và chưa đo false accept/false reject |
| So model, chọn ngưỡng, công bố metric hoặc nghiệm thu | Chưa đủ nhãn, độc lập, nhóm/split và kết quả chạy |

Những điều kiện còn thiếu có thể đếm được:

- **0/40** `judgment` khác null; không có đáp án relevance 0–3 để tính nDCG/Success hoặc exact ID đã duyệt cho ảnh độc lập.
- **0/40** được ghi nhận `independence_review.independent=true` và **0/40** được chia split. 10 ảnh đối chứng đã khai báo không độc lập; 30 ảnh còn lại chưa được chứng nhận độc lập.
- Không có bộ nhãn họ đã duyệt cho bộ tmp. Trong benchmark hiện có proposal họ và split preview; manifest ảnh chính thức vẫn **0 mẫu**. Không đồng nhất tệp đề xuất với registry/split khóa.
- **10/10 ca ảnh + text tái sử dụng gallery**. Ví dụ bình `control-034` + “hộp sơn mài”, túi lục bình `control-033` + “bằng tre”, giỏ không quai rõ ràng `control-032` + “có quai”: có thể là yêu cầu đổi thuộc tính/loại hàng hợp lệ, nhưng cần ghi ý định và đáp án mong muốn riêng; không dùng product nguồn làm đáp án mặc định.
- Chưa có prediction/top-k, latency, cấu hình model, Recall@K, nDCG@10, false accept/reject cho bộ này. Đạt kiểm tra file không có nghĩa tìm kiếm đã đạt.
- `ocr_weight=0` và `image_min_similarity=null` là mặc định trong mã nguồn. Không suy môi trường đang chạy chắc chắn dùng mặc định; cần ghi cấu hình thực khi đo. Ảnh âm tính vẫn có thể được trả top tương tự khi không dùng ngưỡng no-match.

## 6. Quyền, nguồn và tính độc lập

30 ảnh Commons có khai báo giấy phép trong metadata nguồn: 11 CC BY-SA 4.0, 11 CC0, 2 Public domain, 1 CC BY-SA 2.0, 3 CC BY 2.0, 2 CC BY-SA 3.0. Đây là hồ sơ nguồn, không phải lời xác nhận quyền do người kiểm tra tự cấp. Ba bản ghi (`web-000`, `web-001`, `web-005`) trống trường tác giả nhưng có credit tổ chức/nguồn; cần đối chiếu cách ghi công nếu sử dụng tiếp.

10 ảnh gallery vẫn có quyền `unknown` theo catalog. Bộ tmp dùng schema riêng với `source_declared`, không thể đưa nguyên manifest này vào evaluator chính thức vốn có hợp đồng quyền/nhãn/đường dẫn khác. Đây là giới hạn đã được ghi, không phải lý do sửa quyền thành `licensed` để vượt kiểm tra.

30 bản ảnh Commons có thể là thumbnail/bản phân giải nguồn cung cấp; đã lưu URL ảnh gốc và bản thực tải. Kiểm tra online khớp **bản đã tải**, không tuyên bố đã băm ảnh gốc độ phân giải đầy đủ. Nếu chuyển thành dữ liệu benchmark, cần chuẩn hóa provenance và nhóm các bản cùng nguồn trước khi chia split.

Hash bytes/pixel khác nhau không chứng minh khác họ hoặc khác phiên chụp. Hai ảnh khăn là ví dụ cần duyệt theo nguồn/nội dung dù không trùng hash. dHash ở kiểm tra trước chỉ phát hiện cặp Marou gần nhau; đó là gợi ý về bố cục, không đủ để chứng minh những cặp khác độc lập.

## 7. Cần gì trước khi xác nhận chất lượng?

Thứ tự có ý nghĩa hơn việc chỉ tải thêm nhiều ảnh:

1. **Chốt định nghĩa tốt và đáp án.** Tách exact-SKU, similar, ảnh + text và no-match; định nghĩa đúng SKU, mức relevance, cách kiểm giá/phủ định. Ghi cấu hình và catalog dùng đánh giá.
2. **Thu query mới sát catalog.** Với sản phẩm có đáp án, cần ảnh vật thể thực ở góc/nền/ánh sáng khác, độc lập với ảnh bán hàng. Thêm ảnh trang phục, bát/đĩa/ly, đèn/túi, hộp/bình sơn mài hiện hành và bao bì Việt có chữ. Ảnh online mới vẫn phải kiểm trùng nguồn/phiên, không mặc định độc lập.
3. **Bổ sung âm tính khó và điều kiện chụp có chủ đích.** Đồ gần giống khác chất liệu/biến thể, nhãn gần nhau, crop mất quai, vật nhỏ, che khuất, ánh sáng vàng, mờ/rung, nhiều vật thể; phân nhóm có căn cứ. Không dùng biến đổi cùng ảnh làm những mẫu độc lập.
4. **Duyệt dữ liệu.** Quyền và nguồn; identity/họ/phiên; người chấm relevance; một phần có hai người chấm/phân xử. No-match theo protocol hiện hành cần đối chiếu toàn gallery đang hiển thị. Ảnh và phiên bản thêm chữ cùng nguồn phải cùng split.
5. **Đo baseline và so sánh trên cùng bộ.** Ghi top-k, Recall@1/5/10 exact, nDCG@10 similar/image_text, Success@5, vi phạm giá/phủ định, false accept/reject, p50/p95; crop/OCR có và không để thấy tác dụng thực. Không chỉnh ngưỡng bằng locked test.

PLAN đặt mục tiêu **600 ảnh query độc lập / khoảng 200 họ**, cộng **120 query ảnh + text**, nhóm họ 120/40/40 cho train/dev/test và khoảng 10–15% no-match. Giai đoạn sàng lọc nêu 60–100 mẫu/modality; có thể bắt đầu pilot đã duyệt ở quy mô này, nhưng đó không phải ngưỡng tự bảo đảm chất lượng. 30 ảnh chưa trùng byte hiện tại chỉ bằng 5% mục tiêu 600 về số file, và **số đã được duyệt độc lập vẫn là 0**. 5/40 = 12,5% âm tính chỉ khớp tỷ lệ bề ngoài; mẫu số có gallery và chưa có nhãn, nên không chứng minh đã đạt thiết kế benchmark.

Đợt này chỉ đánh giá tình trạng và ghi bằng chứng. Chưa tự tải bù dữ liệu, đổi nhãn, chạy model hoặc thực hiện kế hoạch nghiệm thu trên.

## 8. Kết luận về yêu cầu ban đầu và phạm vi ghi

Yêu cầu “tạo folder và tải ảnh Internet để test search image, bên ngoài chỉ đọc” đã được đáp ứng về file, nguồn và khả năng dùng làm đầu vào. Cần diễn đạt chính xác hơn: **40 ảnh test hợp lệ, không phải 40 ảnh query độc lập hoặc bộ đã chứng minh tìm kiếm tốt**. Mức đại diện nội dung chỉ phù hợp thử ban đầu; bộ cần tuyển chọn/gán nhãn/bổ sung trước nghiệm thu.

Ảnh nguồn và manifest được giữ nguyên trong lần audit này. Việc kiểm tra dùng `-B` để tránh sinh bytecode ngoài thư mục, không chạy test/build/server/index. Báo cáo đối chiếu ngoài tmp_data ghi số file/metadata/hash và các khác biệt nếu có; không suy “mọi bytes của model/dependency đã được băm” từ kiểm tra metadata.
