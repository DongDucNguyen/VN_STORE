# Kịch bản video giới thiệu VNStore — “Nét đẹp Việt” (2:00)

> **Ý tưởng chủ đạo: “Từ một giọt nước đến một cánh sen.”**
> Video mở bằng một giọt nước rơi xuống mặt nước tĩnh và khép lại bằng một cánh sen đậu trên mặt nước ấy. Vòng gợn
> nước là sợi chỉ xuyên suốt. Nó cũng chính là hiệu ứng **“Gợn mặt sen”** mà trang web dùng mỗi khi người dùng bấm nút.
> Nhờ vậy, cảnh đời thực và giao diện số nối vào nhau thành một mạch liền.

- Nhạc nền đã dựng sẵn, dài đúng 2:00: [`nhac_nen_2phut.mp3`](nhac_nen_2phut.mp3)
- Danh sách phách để đặt marker khi dựng: [`phach_nhac_2phut.txt`](phach_nhac_2phut.txt)
- Mọi mốc thời gian dưới đây tính theo **timeline video**, khớp 1:1 với file nhạc trên (nhạc bắt đầu ở 0:03.2).

---

## 1. Phân tích đầu vào

### 1.1. Trang web: những gì đáng kể nhất

| Chức năng có thật trong mã nguồn | Điểm “rất Việt” để nhấn vào | Tên gọi trong video |
|---|---|---|
| Chuẩn hóa tiếng Việt (`backend/app/search/normalize.py`, `query_parser.py`): giữ dấu, khớp cả khi gõ không dấu, sửa lỗi gõ, hiểu giá kiểu “500k / tầm 1tr5 / dưới 5 triệu”, hiểu phủ định “không lấy tre”, hiểu kích thước “180 x 65 cm” | Máy hiểu **cách người Việt nói**, không bắt người Việt phải nói như máy | **Sự trân trọng tiếng Việt** |
| Tìm bằng giọng nói: PhoWhisper (mô hình nhận dạng tiếng Việt của VinAI), có bước **xem và sửa lời chép** trước khi tìm, gợi ý theo catalog | Lời nói được lắng nghe và được tôn trọng: không tự ý đoán thay người dùng | **Lắng nghe tiếng Việt** |
| Từ điển Anh–Việt (`lexicon.py`): silk ↔ lụa, bamboo ↔ tre, water hyacinth ↔ lục bình, mother of pearl ↔ xà cừ, lacquer ↔ sơn mài…; giọng nói có chế độ English; tìm theo ngữ nghĩa đa ngôn ngữ (bge-m3) | Bạn bè quốc tế dùng **chính ngôn ngữ của họ** mà vẫn chạm tới tên gọi Việt | **Nhịp cầu năm châu** |
| Tìm bằng ảnh: chụp ảnh, khoanh vùng, thêm yêu cầu (“có quai, dưới 400k”) | Thấy một món đẹp ngoài chợ là tìm được món tương tự | **Một ánh nhìn** |
| Bảng “Nguồn gốc và căn cứ”: mức xác minh, ngày kiểm tra, nguồn; xem theo làng nghề, thương hiệu | Sự tử tế: không nói quá, có căn cứ mới ghi | **Uống nước nhớ nguồn** |
| Trợ lý AI chạy cục bộ: gợi ý theo nhu cầu, so sánh 2–3 món, nhận xét khách quan; không bịa giá hay nguồn gốc; người dùng tự chọn mức ghi nhớ | Tận tâm như người bán hàng quen, thật thà như người làng nghề | **Người bạn tri âm** |
| Hệ chuyển động riêng (`design.md` §7): **Gió qua tre** (bóng tre khẽ lay), **Gợn mặt sen** (gợn lan từ điểm bấm), **Nhịp đan** (thẻ sản phẩm hiện so le), **Sen mở** (nút trợ lý), **Nét tre** (gạch dưới menu trượt), **Qua hiên** (chuyển trang), ảnh thẻ bay sang trang chi tiết, đổi Sáng/Tối bằng hòa màu | Từng cái chạm đều được nghĩ kỹ | **Từng chi tiết nhỏ** |

Catalog thật: 328 sản phẩm đã duyệt, 7 thương hiệu (Minh Long, LY'S, Marou, Hanoia, Kilomet109, Hanhsilk, SenSilk),
gồm gốm sứ, mây tre cói, lụa, sơn mài và đặc sản.

Các câu tìm dưới đây **đã chạy thử trên catalog thật** (`database.json`) và cho kết quả đẹp. Nên quay đúng những câu này:

| Câu gõ | Hệ thống hiểu | Kết quả đầu |
|---|---|---|
| `khăn lụa tầm 1tr5` | “Hiểu ‘tầm 1 tr 5’ là khoảng giá ±20%” → chip **Giá khoảng 1.200.000đ–1.800.000đ** | Khăn Tơ Vẽ Độc Bản – Hand Painted Silk Scarf |
| `giỏ mây không lấy tre` | chip **Không lấy chất liệu tre** | Giỏ đan mây |
| `bìn hoa sen` | “Hiểu ‘bìn’ là ‘bình’ (sửa lỗi gõ)” | Bình hoa 27 cm Sen Vàng, Bình hoa 36 cm Hoa Sen |
| `binh hoa duoi 5 trieu` (không dấu) | chip **Giá dưới 5.000.000đ** | Bình hoa 30 cm Hồn Việt, Bình hoa Sen Vàng |
| `áo nhuộm chàm` | gợi ý lọc “chàm” | Áo khoác Phi vải gai dầu nhuộm chàm |
| `silk scarf` | Tìm thêm cách gọi khác: khăn, scarves, shawl | Khăn Lụa Vẽ Tay Hoa Hồng SenSilk |
| `bamboo basket` | giỏ, baskets | Giỏ đan tre |
| `mother of pearl` | — | Khay tre, xà cừ |
| `water hyacinth` | lục bình | Giỏ đan lục bình, Túi lục bình đan tay đính vỏ sò |

> Không nên quay `lacquer box` vì kết quả đầu lẫn hộp quà sô cô la. `lotus vase` cũng không khớp đủ ý.

### 1.2. Bản nhạc gốc

- Dài **4:47**. Thang âm nổi bật là **D – E – G – A – C**, một thang **ngũ cung** rất gần âm hưởng dân gian Việt.
- Nhịp độ **≈ 92 BPM**: 1 phách ≈ **0,65 s**, 1 ô nhịp (4 phách) ≈ **2,6 s**. Nên cắt hình theo bội số của 0,65 s.
- Cấu trúc đo được:
  - 0:00–0:14: dạo đầu trầm, ấm.
  - 0:15: dàn nhạc vào.
  - 1:32–1:56: đoạn lắng có hai khoảng “thở”.
  - 1:56: nhạc dâng lại.
  - 3:08–3:24: cầu nối nhẹ.
  - 3:24–4:27: cao trào, sáng nhất ở khoảng 3:36–4:04.
  - 4:28: một nhịp thở.
  - 4:32–4:47: câu kết và ngân tự nhiên.

### 1.3. Cách dựng lại nhạc thành 2:00

Bản 2:00 giữ nguyên dạo đầu và đoạn kết gốc (bài vẫn kết tự nhiên, không bị fade cụt). Nó bỏ bớt các đoạn lặp bằng 3 điểm nối:

| Đoạn | Lấy từ nhạc gốc | Nằm ở video | Vai trò |
|---|---|---|---|
| — | (im lặng) | 0:00–0:03.2 | Khoảng lặng cho tiếng giọt nước |
| A | 0:00 → 0:31.3 | 0:02.5–0:33.8 | Dạo đầu + câu nhạc đầu |
| B | 1:34.0 → 2:11.8 | 0:33.8–1:11.6 | Đoạn lắng → nhạc dâng lại |
| C | 3:24.9 → 3:47.0 | 1:11.6–1:33.8 | Vào thẳng cao trào |
| D | 4:21.0 → 4:47.2 | 1:33.8–2:00 | Nhịp thở cuối + câu kết |

Cách chọn và kiểm tra các điểm nối:

- Điểm nối nằm **đúng phách**, và đoạn bị bỏ luôn tròn ô nhịp (96, 120 và 52 phách).
- Mỗi điểm được chọn vì âm sắc và hòa âm hai bên giống nhau. Độ tương đồng của cả 3 điểm thuộc **top 1%** trong mọi cặp vị trí của bài.
- Mỗi chỗ nối có crossfade 0,3 s (equal-power).
- Đã đo lại trên bản dựng: khoảng cách phách qua cả 3 chỗ nối giữ 0,63–0,65 s, âm lượng không hụt.
- **Kết luận đo đạc không thay được đôi tai.** Hãy nghe kỹ ba chỗ 0:33.8, 1:11.6 và 1:33.8. Nếu một chỗ còn “gợn”, dời điểm nối ±1 phách hoặc tăng crossfade lên 0,6 s.

### 1.4. Bản đồ cảm xúc của nhạc 2:00 (mốc để khớp hình)

```
0:00 ░░░ lặng (giọt nước)
0:03.2 ● nốt đầu tiên ─ dạo đầu trầm ấm ──────────────┐
0:17.9 ◆ DÀN NHẠC VÀO (điểm nhấn mạnh)               │ CHƯƠNG I
0:18–0:35 ▓▓▓ đầy đặn, sáng                          ┘
0:36–0:40 ░ lắng  · 0:41 nhấc nhẹ · 0:44 lắng · 0:45 nhấc ┐ CHƯƠNG II
0:47–0:53 ░░ lắng sâu nhất (khoảng thở)              ┘
0:54.0 ◆ NHẠC DÂNG LẠI (điểm nhấn mạnh nhất phần giữa) ┐
0:54–1:11 ▓▓▓ đầy  · 1:07 hụt nhẹ · 1:09 nhấn         │
1:11.6 ◆ VÀO CAO TRÀO                                 │ CHƯƠNG III
1:12–1:35 ████ sáng nhất · đỉnh 1:22 và 1:30–1:32     │
1:35.5 / 1:38.0 ✕ hai cú “ngắt” nhạc (rất hợp để nhấn thao tác) ┘
1:41–1:44.7 ░ nhịp thở cuối  · 1:45.0 ◆ nhấn          ┐ CHƯƠNG IV
1:47.8 ◆ câu kết → 1:56 ngân dần → 1:59.4 hết         ┘
```

---

## 2. Cấu trúc tổng

| Chương | Thời gian | Nội dung | Nhạc |
|---|---|---|---|
| I. Nét đẹp Việt | 0:00–0:35.5 | Vẻ đẹp, sự công phu, tinh tế của sản phẩm thuần Việt | Dạo đầu → dàn nhạc vào |
| II. Tâm huyết & lý do ra đời | 0:35.5–0:54 | Bàn tay người thợ; vì sao có VNStore (ngắn) | Đoạn lắng |
| III. Một ấn phẩm Việt có thể chạm vào | 0:54–1:41 | Các tính năng | Nhạc dâng → cao trào |
| IV. Tôn vinh | 1:41–2:00 | Thông điệp, logo | Nhịp thở → câu kết |

**Năm chuyển cảnh chữ ký**, mỗi cái đặt đúng một bước ngoặt của nhạc:

1. **Giọt nước rơi** (0:03.2): mở phim.
2. **Tà áo dài tung bay** (0:17.9): dàn nhạc vào.
3. **Cành tre lướt qua** (0:54.0): bước vào trang web.
4. **Cánh cò vụt lên** (1:11.6): vào cao trào, mở ra thế giới. Dùng **cò trắng** cho cánh chim: “con cò bay lả bay la” là hình ảnh rất Việt.
5. **Cánh sen lướt qua và đậu xuống mặt nước** (1:41): khép phim, gọi lại giọt nước lúc mở đầu.

---

## 3. Kịch bản chi tiết

Quy ước:

- **HÌNH**: nội dung khung hình.
- **CHỮ**: chữ trên màn hình. Lời dẫn (VO) là tùy chọn; nếu thu VO thì đọc đúng câu CHỮ, giọng nữ trầm, chậm, ấm.
- **CHUYỂN ĐỘNG**: hiệu ứng.
- **ÂM**: hiệu ứng âm thanh (SFX).

### CHƯƠNG I — NÉT ĐẸP VIỆT

#### Cảnh 1 · Giọt nước · 0:00.0–0:03.2
- **HÌNH:** Toàn khung là mặt nước tĩnh, màu xanh rừng thẫm (#183E33) gần như đen, có một vệt sáng ngà rất mờ. Một giọt nước rơi chậm từ trên xuống (quay 120–240 fps, phát chậm). Giọt chạm mặt nước **đúng 0:03.2**, trùng nốt nhạc đầu tiên. Gợn tròn lan ra.
- **CHỮ:** không.
- **CHUYỂN ĐỘNG:** Gợn nước lan chậm, đi theo đường cong `ease-water` (xem §6). Ánh sáng từ từ ấm lên.
- **ÂM:**
  - 0:00: tiếng đêm vườn rất khẽ (côn trùng, gió nhẹ), −30 dB.
  - 0:02.9: tiếng “tách” của giọt nước, đuôi vang dài, đỉnh âm đúng 0:03.2.

#### Cảnh 2 · Những vẻ đẹp không vội vàng · 0:03.2–0:17.9 (dạo đầu, 5 cảnh quay, mỗi cảnh ≈ 2,6–3,2 s)
- **HÌNH** (macro, ánh sáng xiên buổi sớm, độ sâu trường ảnh nông):
  1. *Match cut* từ vòng gợn nước sang miệng bình đất đang xoay trên bàn xoay gốm, hai vòng tròn trùng khít.
  2. Đầu cọ vẽ một nét sen men lam lên thân bình.
  3. Sợi tơ tằm vàng óng kéo ra từ kén, nắng xuyên qua sợi tơ.
  4. Đôi tay đan nan mây, từng nan lách qua nhau.
  5. Mài nước trên mặt sơn mài, lớp vàng và xà cừ dần lộ ra.
- **CHỮ:** font Newsreader, chữ nhỏ vừa, đặt ở 1/3 dưới, mỗi câu hiện bằng fade 480 ms.
  - 0:05.8 — *Có những vẻ đẹp không cần vội.*
  - 0:11.0 — *Một nét men. Một sợi tơ. Một nan tre.*
- **CHUYỂN ĐỘNG:** camera trôi rất chậm (dolly/slide 1–2%/s). Giữa các cảnh dùng hòa hình 12 frame. Không cắt gắt.
- **ÂM:**
  - Tiếng bàn xoay gốm rất khẽ.
  - Tiếng cọ lướt.
  - Tiếng nan mây cọ nhau.
  - Mỗi tiếng ở −28 đến −24 dB, vừa đủ “chạm” vào tai.

#### Cảnh 3 · Tà áo dài tung bay · 0:17.2–0:18.2 (chuyển cảnh chữ ký #2)
- **HÌNH:** Một tà áo dài lụa trắng ngà hoặc hồng sen bay ngang khung từ phải sang trái, quay chậm, chiếm trọn khung. Vạt lụa che kín màn hình đúng **0:17.9**, đúng lúc dàn nhạc vào. Khi vạt lụa rời đi, cảnh mới hiện ra.
- **CÁCH LÀM:** Quay lụa thật trước phông xanh, dùng quạt; hoặc dùng `cutouts/textile-edge.png` trong bộ asset dự án làm lớp phủ. Đặt chế độ luma/track matte để vạt lụa làm “cửa” mở sang cảnh sau. Thêm motion blur.
- **ÂM:** tiếng lụa phất (cloth swish), đỉnh ở 0:17.9, −14 dB.

#### Cảnh 4 · Nét đẹp Việt · 0:18–0:35.5 (dàn nhạc đầy, cắt theo ô nhịp 2,6 s)
- **HÌNH** (sáng hơn, nhiều màu hơn, vẫn thanh lịch):
  1. Thiếu nữ áo dài đi bên đầm sen, hoặc dưới mái ngói rêu phong.
  2. Nón lá dưới nắng, bóng nan nón in lên mặt.
  3. Bình gốm vẽ sen hoàn thiện đặt trên chiếu cói.
  4. Khăn lụa vẽ tay tung nhẹ.
  5. Túi lục bình, giỏ mây xếp bên hiên.
  6. Thanh sô cô la Bến Tre bẻ đôi bên trái cacao.
  7. Hộp sơn mài phản chiếu ánh đèn lồng.
- **CHỮ:**
  - 0:20.5 — **NÉT ĐẸP VIỆT**: tiêu đề lớn, Newsreader. Hiệu ứng *trồi lên từ mặt nạ*, đúng kiểu dòng chữ “Nếp Việt” trên trang chủ (`display-mask`). Trước tiêu đề có dấu vuông nhỏ màu son (#A84432), đúng “dấu biên tập” của web. Giữ 3 s.
  - 0:26.0 — *Công phu trong từng đường nét.*
  - 0:31.2 — *Tinh tế trong từng chất liệu.*
- **CHUYỂN ĐỘNG:**
  - Cắt cảnh đúng phách.
  - Mỗi cảnh có push-in 102% → 100% (đường cong `ease-bamboo`).
  - Cảnh nón lá: xoay nhẹ 3–4°, để nan nón quét sáng như hiệu ứng “Nan nón” của web.
- **ÂM:** không cần SFX dày. Có thể thêm tiếng chim sẻ xa ở cảnh hiên nhà, −30 dB.

### CHƯƠNG II — TÂM HUYẾT & LÝ DO RA ĐỜI

#### Cảnh 5 · Đôi bàn tay · 0:35.5–0:47 (nhạc lắng)
- **HÌNH:**
  1. Cận cảnh đôi bàn tay người thợ già có vết chai, chậm rãi vuốt mép chiếc giỏ vừa đan xong.
  2. Ở 0:41 (nhạc nhấc nhẹ): gương mặt nghệ nhân mỉm cười, ngược sáng.
  3. Ở 0:45: góc bàn nghề với dụng cụ và phoi tre (hoặc dùng ảnh `craft-workbench` của web).
- **CHỮ** (đọc chậm, chia 2 dòng):
  - 0:37 — *Mỗi món đồ là kết tinh của thời gian, kiên nhẫn*
  - 0:40 — *và đôi bàn tay người thợ.*
  (Đây đúng là câu ở chương “04 — Theo dấu bàn tay” trên trang chủ. Video và web nói cùng một giọng.)
- **CHUYỂN ĐỘNG:** gần như tĩnh. Bóng nắng trôi rất chậm qua bàn tay.
- **ÂM:** hơi thở của gió qua mái, tiếng nan tre nhẹ, −28 dB.

#### Cảnh 6 · Lý do ra đời · 0:47–0:53.4 (đoạn lắng sâu nhất, giữ thật tối giản)
- **HÌNH:**
  1. Một món đồ được gói bằng giấy dó, buộc lạt tre.
  2. Ống kính lùi ra con đường làng dẫn ra xa, nắng sớm.
- **CHỮ:**
  - 0:47.5 — *Để những tinh hoa ấy không chỉ nằm lặng lẽ nơi làng nghề,*
  - 0:50.5 — *mà đi xa hơn — đến gần hơn với bạn bè năm châu.*
- **CHUYỂN ĐỘNG:** chữ hiện bằng fade, rồi lướt Y 6 → 0 px trong 480 ms.
- **ÂM:** tiếng gà gáy rất xa hoặc tiếng chim sáo, −32 dB. Cách khác: giữ im, chỉ để nhạc.

#### Cảnh 7 · Cành tre lướt qua · 0:53.4–0:54.6 (chuyển cảnh chữ ký #3)
- **HÌNH:**
  1. Một cành tre vắt ngang khung, lướt nhanh từ phải sang trái, có motion blur, che kín màn hình đúng **0:54.0**, cú nhấn mạnh nhất phần giữa.
  2. Khi cành tre lướt qua: lộ ra **trang chủ VNStore**.
  3. Cành tre giảm tốc rồi “đậu” đúng vào vị trí cành tre ở mép phải của trang chủ. Cành tre thật hóa thành cành tre trên giao diện (match cut).
- **CÁCH LÀM:** Dùng chính file `assets/design-elements/nep-viet-v2/cutouts/bamboo-opening-branch.png` (PNG trong suốt), cùng ảnh với `opening-branch` trên web, nên điểm “đậu” khớp tuyệt đối.
- **CHỮ:** **VNStore ra đời** — nhỏ, xuất hiện cùng lúc cành tre đậu, rồi mờ dần sau 1,2 s.
- **ÂM:** gió lùa lá tre (rustle), từ 0:53.0, đỉnh ở 0:54.0, −12 dB.

### CHƯƠNG III — MỘT ẤN PHẨM VIỆT CÓ THỂ CHẠM VÀO

Quy ước đồ họa chung cho các tính năng: ở góc trên trái có **số chương nhỏ** (01, 02… đúng kiểu `ChapterNo` của web),
**tên tính năng** bằng Newsreader và một dòng phụ bằng Be Vietnam Pro. Khi một hiệu ứng của web xuất hiện, đặt **chú thích nhỏ
in nghiêng** ngay cạnh, ví dụ *“Gợn mặt sen”*. Người xem sẽ thấy cả những chuyển động nhỏ nhất cũng có tên, có ý.

#### Cảnh 8 · Trang chủ “Nếp Việt” · 0:54–1:00
- **HÌNH** (quay màn hình):
  1. Chữ **“Nếp Việt / Trong từng món đồ”** trồi lên; bóng tre bên phải khẽ lay *(chú thích: “Gió qua tre”)*.
  2. Ở 0:57.4: con trỏ rê qua menu Khám phá → Làng nghề → Thương hiệu; vạch mực trượt theo *(chú thích: “Nét tre”)*.
  3. Ở 0:58.7: cuộn mượt xuống “01 Những điều mộc mạc” (nón lá) rồi “02 Một khoảng an yên” (đầm sen).
- **CHỮ:** *Một ấn phẩm Việt — có thể chạm vào.*
- **ÂM:** không SFX. Để nhạc dâng.

#### Cảnh 9 · 01 — Sự trân trọng tiếng Việt · 1:00–1:07
- **Dòng phụ:** *Hiểu cả cách người Việt nói.*
- **HÌNH:**
  1. 1:00–1:04.3: gõ chậm vào ô tìm **`khăn lụa tầm 1tr5`**.
  2. Bấm **Tìm** đúng phách 1:01.9. Nút loang gợn *(chú thích: “Gợn mặt sen”)*.
  3. Trang kết quả hiện dòng **“Hiểu ‘tầm 1 tr 5’ là khoảng giá ±20%”** và chip **Giá khoảng 1.200.000đ–1.800.000đ**. Thẻ sản phẩm hiện so le *(chú thích: “Nhịp đan”)*.
  4. 1:04.3–1:07: ba “thẻ chữ” nổi lên lần lượt theo phách. Mỗi thẻ là câu người dùng gõ, kèm cách hệ thống hiểu:
     - `bìn hoa sen` → *Hiểu “bìn” là “bình”*
     - `giỏ mây không lấy tre` → *Không lấy chất liệu tre*
     - `binh hoa duoi 5 trieu` → *Giá dưới 5.000.000đ*
- **CHỮ cuối cảnh:** *Gõ sai, gõ không dấu, nói “tầm”, nói “không lấy” — vẫn hiểu.*
- **ÂM:**
  - Tiếng gõ phím gỗ rất nhẹ, −26 dB.
  - Tiếng “tách” nhỏ (giọt nước thu nhỏ) khi bấm Tìm.
  - Ba tiếng “pop” mềm như búng giọt nước cho ba thẻ chữ.

#### Cảnh 10 · Lắng nghe tiếng Việt · 1:07–1:11.6
- **HÌNH:**
  1. Chèn cận cảnh một cô gái khẽ nói vào điện thoại: “áo nhuộm chàm”.
  2. Trên web: bấm micro → chấm đỏ “Đang nghe…”, có gợn nhẹ mỗi 1,6 s *(chú thích: “Đang nghe”)*.
  3. Bảng **“Kiểm tra lời nói trước khi tìm”** hiện bản chép lời.
  4. Bấm **“Tìm theo câu này”** đúng phách nhấn 1:09.1.
  5. Kết quả: *Áo khoác Phi vải gai dầu nhuộm chàm*.
- **CHỮ:**
  - *Lời nói ra, được lắng nghe trọn vẹn.*
  - Dòng nhỏ: *Nhận dạng bằng PhoWhisper — mô hình dành riêng cho tiếng Việt.*
- **ÂM:** chính giọng nói (−8 dB, nhạc giảm 4 dB trong 1,5 s).

#### Cảnh 11 · Cánh cò vụt lên · 1:10.9–1:12.2 (chuyển cảnh chữ ký #4)
- **HÌNH:** Một con cò trắng cất cánh từ ruộng lúa hoặc đầm sen, bay vút lên trên khung hình. Sải cánh trắng lướt sát ống kính, quét qua khung đúng **1:11.6**, lúc nhạc vào cao trào. Sau cánh cò là bầu trời rộng mở và cảnh tiếp theo.
- **ÂM:** tiếng vỗ cánh, tiếng “whoosh” nhẹ đi lên, xa xa một tiếng cò kêu, −12 dB.

#### Cảnh 12 · 02 — Nhịp cầu năm châu · 1:12–1:22
- **Tên phụ song ngữ:** *A bridge to the world*.
- **HÌNH:**
  1. Chèn cảnh một du khách nước ngoài ở quán cà phê phố cổ, mở VNStore trên laptop.
  2. Gõ **`silk scarf`** → kết quả là các *Khăn Lụa Vẽ Tay SenSilk*, kèm dòng “Tìm thêm cách gọi khác: khăn, scarves, shawl”.
  3. Ở 1:16: các **cặp từ song ngữ** bay lên như đèn trời, xuất hiện so le theo phách. Chữ Anh viết nghiêng, chữ Việt viết đứng:
     - *Silk* · **Lụa**
     - *Bamboo* · **Tre**
     - *Water hyacinth* · **Lục bình**
     - *Mother of pearl* · **Xà cừ**
     - *Lacquer* · **Sơn mài**
  4. Ở 1:19: chọn “Ngôn ngữ giọng nói: English”, nói **“bamboo basket”** → *Giỏ đan tre*.
- **CHỮ:**
  - *Speak your language. Discover Vietnamese craft.*
  - *Bạn nói bằng ngôn ngữ của bạn — VNStore đáp lại bằng tinh hoa Việt.*
- **ÂM:** mỗi cặp từ hiện kèm một tiếng chuông gió nhỏ (wind chime), −24 dB. Nhạc đang cao trào, nên chỉ thêm rất ít âm.

#### Cảnh 13 · 03 — Một ánh nhìn · 1:22–1:26.5 (đỉnh nhạc 1:22)
- **HÌNH:**
  1. Chèn cảnh tay giơ điện thoại chụp chiếc túi lục bình ở một sạp chợ quê.
  2. Trên web “Tìm bằng ảnh”: ảnh hiện lên, kéo khung **khoanh vùng** quanh chiếc túi.
  3. Gõ thêm “có quai”, bấm **Tìm mẫu tương tự**.
  4. Lưới “Mẫu tương tự” hiện so le *(“Nhịp đan”)*.
- **CHỮ:** *Một ánh nhìn — đã đủ để tìm thấy.*
- **ÂM:** tiếng màn trập máy ảnh dịu (không “cạch” gắt), −18 dB.

#### Cảnh 14 · 04 — Uống nước nhớ nguồn · 1:26.5–1:31
- **HÌNH:**
  1. Bấm một thẻ sản phẩm, ví dụ *Bình hoa 36 cm – Hoa Sen*. Ảnh của thẻ **bay sang** đúng vị trí ảnh lớn ở trang chi tiết (View Transition) *(chú thích: “Qua hiên”)*.
  2. Cuộn xuống khối **“Nguồn gốc và căn cứ”**: bảng Tiêu chí / Mức xác minh / Ngày kiểm tra / Nguồn. Highlight bằng vệt dạ quang màu rơm (#D8BD7A) quét qua cột “Mức xác minh”.
  3. Lướt nhanh trang **Làng nghề** (“Theo dấu bàn tay”).
- **CHỮ:** *Uống nước nhớ nguồn — mỗi nhãn nguồn gốc đều đi kèm căn cứ.*
- **ÂM:** tiếng giấy lật nhẹ, −24 dB.

#### Cảnh 15 · 05 — Người bạn tri âm · 1:31–1:35.5
- **HÌNH:**
  1. Bấm nút hoa sen nhỏ ở góc. Hai cánh sen khẽ mở, bảng trợ lý trượt lên *(chú thích: “Sen mở”)*.
  2. Chọn câu mẫu **“Gợi ý quà tặng mẹ khoảng 500k”**. Câu trả lời hiện dần cùng các thẻ sản phẩm thật.
  3. Lướt qua ba lựa chọn ghi nhớ: *Không lưu · Lưu lịch sử · Ghi nhớ sở thích*.
- **CHỮ:** *Tận tâm như người bán hàng quen — chỉ nói điều có căn cứ.*
- **ÂM:** một tiếng chuông đồng nhỏ, ngân ngắn, khi sen mở, −20 dB.

#### Cảnh 16 · Từng chi tiết nhỏ · 1:35.5–1:41 (đúng hai cú “ngắt” của nhạc)
- **HÌNH:**
  1. Ở **1:35.5** (nhạc ngắt lần 1): bấm **Yêu thích**, trái tim đầy màu rồi nảy nhẹ *(chú thích: “Giữ một món”)*.
  2. Ở **1:38.0** (nhạc ngắt lần 2): đổi Giao diện **Sáng → Tối**. Cả trang hòa màu từ *giấy ngà* sang *đêm trong vườn* (xanh rừng).
  3. 1:38.5–1:41: trang tối với cảnh đầm sen giữa trang.
- **CHỮ:** *Đến cả một cái chạm cũng được chăm chút.*
- **ÂM:**
  - 1:35.5: một tiếng “tinh” rất nhỏ.
  - 1:38.0: tiếng dế và gió đêm khẽ dâng (−30 dB), như đêm buông xuống thật.

### CHƯƠNG IV — TÔN VINH

#### Cảnh 17 · Cánh sen · 1:41–1:47.8 (nhịp thở cuối của nhạc; chuyển cảnh chữ ký #5)
- **HÌNH:**
  1. Một cánh sen hồng rời bông, trôi chéo từ góc trên trái, xoay chậm, lướt sát ống kính. Cánh sen chuyển cảnh từ màn hình web tối sang **đầm sen thật lúc bình minh**.
  2. Cánh sen đậu xuống mặt nước, **gợn tròn lan ra**: đúng vòng gợn của cảnh 1. Phim khép vòng.
- **CHỮ:**
  - 1:42.0 — *Gìn giữ tinh hoa.*
  - 1:45.0 (nhạc nhấn) — ***Tôn vinh nét đẹp Việt.***
- **CÁCH LÀM:** Có thể dựng cánh sen từ `botanical/lotus-botanical-01.png` (đã tách nền), tô màu hồng sen (#AD586C → #DEA5B2) và thêm motion blur nhẹ.
- **ÂM:** tiếng cánh hoa chạm nước rất khẽ (tiếng “tách” của cảnh 1 thu nhỏ, cao độ thấp hơn), −20 dB.

#### Cảnh 18 · Logo · 1:47.8–1:56
- **HÌNH:**
  1. Nền là tranh phong cảnh đồng quê ở chân trang web (`footer-landscape`), phóng rất chậm 100% → 103%.
  2. Dấu hoa sen (`svg/lotus-mark.svg`) được **vẽ nét** trong 1 s.
  3. Wordmark **VNStore** hiện lên.
  4. Bên dưới là khẩu hiệu ***Nếp Việt trong từng món đồ***.
- **CHỮ** (dòng nhỏ dưới cùng, tùy chọn): địa chỉ web hoặc mã QR.
- **ÂM:** chỉ có nhạc.

#### Cảnh 19 · Lặng · 1:56–2:00
- **HÌNH:** Logo đứng yên. Ánh sáng dịu dần rồi fade về nền giấy ngà (#F7F3E8) ở 2:00.
- **ÂM:**
  - 1:56.5: tiếng chim xa và gió tre, −30 dB.
  - 1:59.0: **một giọt nước cuối cùng** rất khẽ, đúng lúc nhạc tắt hẳn.
  - 2:00: hết.

---

## 4. Năm chuyển cảnh chữ ký — cách dựng cho tinh tế

| # | Chuyển cảnh | Mốc | Kỹ thuật gợi ý (Premiere/After Effects/CapCut) |
|---|---|---|---|
| 1 | Giọt nước rơi | 0:03.2 | Quay thật ở tốc độ khung hình cao, hoặc stock. Gợn nước làm displacement map nhẹ lên cảnh bàn xoay gốm để nối bằng match cut |
| 2 | Tà áo dài | 0:17.9 | Lụa quay trước phông xanh làm *track matte*; motion blur 180°; thời lượng 18–24 frame |
| 3 | Cành tre | 0:54.0 | PNG `bamboo-opening-branch.png` lướt kèm *directional blur*, giảm tốc theo `ease-bamboo` rồi khớp vị trí cành tre của web |
| 4 | Cánh cò | 1:11.6 | Clip cò cất cánh (stock); phần cánh lướt sát ống kính làm matte; 12–18 frame |
| 5 | Cánh sen | 1:41 | Lá sen tách nền, xoay 20–40° trong 2 s, động lượng mềm; khi đậu xuống mặt nước thì tạo gợn bằng `svg/water-ripple.svg` |

Nguyên tắc chung: **mỗi chuyển cảnh chỉ một vật thể, một hướng chuyển động**. Không chồng hiệu ứng, không lóe sáng,
không xoay 3D. Vật thể đi qua khung theo hướng đọc (phải sang trái, hoặc từ dưới lên ở cảnh “vươn xa”).

---

## 5. Hiệu ứng âm thanh (SFX)

| Mốc | Âm | Mức (so với nhạc) |
|---|---|---|
| 0:00–0:03 | Đêm vườn: côn trùng, gió | −30 dB |
| 0:03.2 | Giọt nước “tách”, đuôi vang dài | −10 dB (điểm nhấn) |
| 0:03–0:17 | Bàn xoay gốm, cọ, nan mây | −28 đến −24 dB |
| 0:17.9 | Lụa phất | −14 dB |
| 0:35–0:47 | Gió qua mái, nan tre | −28 dB |
| 0:54.0 | Gió lùa lá tre | −12 dB |
| 1:00–1:04 | Gõ phím gỗ; “tách” nhỏ khi bấm Tìm; 3 “pop” | −26 / −20 dB |
| 1:07–1:11 | Giọng nói thật (nhạc giảm 4 dB) | −8 dB |
| 1:11.6 | Vỗ cánh, whoosh lên, tiếng cò | −12 dB |
| 1:16–1:19 | Chuông gió nhỏ cho mỗi cặp từ | −24 dB |
| 1:22 | Màn trập máy ảnh dịu | −18 dB |
| 1:31 | Chuông đồng nhỏ khi sen mở | −20 dB |
| 1:35.5 / 1:38.0 | “Tinh” nhỏ / dế và gió đêm dâng | −22 / −30 dB |
| 1:41–1:45 | Cánh sen chạm nước | −20 dB |
| 1:56.5–2:00 | Chim xa, gió tre, giọt nước cuối ở 1:59.0 | −30 / −22 dB |

- Mix tổng khoảng **−14 LUFS** (chuẩn YouTube và mạng xã hội), đỉnh không vượt −1 dBTP.
- Nhạc là chủ đạo. SFX chỉ để “chạm”, không để “nghe thấy hiệu ứng”.
- Nguồn SFX: Freesound (lọc CC0), Artlist, Epidemic Sound. Tránh SFX kiểu UI điện tử (bíp, click nhựa). Ưu tiên âm thật: nước, gỗ, lụa, đồng.

---

## 6. Ngôn ngữ hình ảnh (lấy từ hệ thiết kế của web để video và web là một)

- **Màu** (`design.md` §4.1):
  - Giấy ngà #F7F3E8
  - Xanh rừng #183E33 (cảnh sen, chân trang)
  - Chữ xanh mực #22352B
  - Hồng sen #AD586C
  - Rơm #D8BD7A
  - Dấu biên tập son #A84432

  Bản màu (grading) tổng: ấm, độ tương phản thấp, vùng tối hơi xanh rêu, vùng sáng màu ngà. Không bão hòa.
- **Chữ:** **Newsreader** cho tiêu đề và câu thơ (400/500), **Be Vietnam Pro** cho dòng phụ và chú thích (400/500). Không dùng thư pháp, không dùng chữ quá dày. Chừa đủ khoảng trên và dưới để dấu tiếng Việt không bị cắt.
- **Nhịp chuyển động** (giống token của web): nhanh 160 ms, chuẩn 240 ms, panel 320 ms, câu chuyện 480 ms.
  - `ease-bamboo`: `cubic-bezier(.22, 1, .36, 1)`. Dùng cho chữ trồi lên, cành tre giảm tốc.
  - `ease-water`: `cubic-bezier(.2, .65, .3, 1)`. Dùng cho gợn nước, hòa hình.

  Trong After Effects, nhập hai đường cong này qua Flow hoặc Ease Copy.
- **Bố cục:** bất đối xứng như trang chủ. Chữ ở 1/3 trái, vật thể ở lề phải, nhiều khoảng thở.

---

## 7. Hướng dẫn quay màn hình web

1. **Chạy bản đầy đủ có model thật** (giọng nói, ảnh, trợ lý), theo `docs/local-workstation.md` và README:
   - Chạy `scripts/run_local.ps1`, rồi `npm --prefix frontend run dev`.
   - **Không** dùng catalog fixture: banner “dữ liệu FIXTURE” sẽ lọt vào hình.
2. **Khung hình:**
   - Chrome cửa sổ 1920×1080, zoom 110–125% để chữ đủ to trên điện thoại.
   - Ẩn thanh dấu trang và tiện ích; dùng chế độ toàn màn hình (F11).
   - Quay **60 fps** (OBS) để hiệu ứng mượt, rồi xuất video 30 fps.
3. **Con trỏ:** đi chậm, theo đường cong. Có thể quay không con trỏ rồi vẽ lại một chấm tròn mềm màu xanh mực trong After Effects.
4. **Chuyển động:** để “Chuyển động: Theo hệ thống” và tắt *giảm chuyển động* của hệ điều hành. Nếu không, Gió qua tre, Nhịp đan, Gợn mặt sen và ảnh bay sang trang chi tiết sẽ bị tắt.
5. **Ảnh bay sang trang chi tiết** cần trình duyệt có View Transitions API (Chrome/Edge bản mới).
6. **Gõ phím:** gõ chậm, đều, khoảng 6–8 ký tự/giây. Hoặc gõ nhanh rồi giãn thời gian ở bước dựng, giữ con trỏ nhấp nháy.
7. **Cuộn trang:** không cuộn bằng chuột thường vì dễ giật. Dùng phím mũi tên hoặc một đoạn script cuộn với tốc độ đều, rồi dựng thêm ease ở bước dựng.
8. **Quay dư** mỗi thao tác 2–3 giây trước và sau, để có chỗ cắt đúng phách.
9. **Trợ lý:** quay ở lượt thứ hai, khi model đã nạp xong. Nếu câu trả lời dài, ở bước dựng chỉ giữ đoạn đầu và các thẻ sản phẩm.

---

## 8. Lưu ý trung thực (để video tinh tế mà không nói quá)

- Ảnh minh họa trên web (tre, sen, nón, bàn tay đan) **là tranh minh họa AI**. Web cũng ghi rõ điều này. Trong video, cảnh nghệ nhân nên là **cảnh quay thật hoặc stock có bản quyền**. Không gán một cảnh cho một làng nghề cụ thể nếu không đúng.
- Khi nói về nguồn gốc, dùng chữ **“có căn cứ / có nguồn”**, không dùng “chứng nhận / bảo đảm”. Bảng nguồn gốc của web phân biệt rõ “Nhà sản xuất công bố” và “Đã đối chiếu nguồn”.
- Phần tiếng Anh: giao diện web hiện là tiếng Việt. Điều web làm được là **hiểu câu tìm và giọng nói tiếng Anh**. Câu chữ trong video giữ đúng ý đó (“Speak your language…”), không nói “giao diện đa ngôn ngữ”.
- Tên thương hiệu và sản phẩm (SenSilk, Minh Long, Marou…) chỉ xuất hiện như trong catalog thật, không dựng cảnh quảng cáo riêng cho thương hiệu.

---

## 9. Checklist dựng

- [ ] Đặt marker theo `phach_nhac_2phut.txt` (166 phách, có timecode 30 fps).
- [ ] Nghe kỹ 3 chỗ nối nhạc 0:33.8 / 1:11.6 / 1:33.8.
- [ ] Năm chuyển cảnh chữ ký khớp đúng 0:03.2 / 0:17.9 / 0:54.0 / 1:11.6 / 1:41.
- [ ] Mỗi câu chữ trên màn hình đứng ít nhất 2 s. Dấu tiếng Việt không bị cắt.
- [ ] Quay đúng những câu tìm đã chạy thử ở §1.1.
- [ ] Không còn banner FIXTURE hay “Chế độ phát triển” trong hình.
- [ ] Xem thử trên điện thoại: chữ đọc được, ánh sáng không bết.
- [ ] Mix khoảng −14 LUFS, kết thúc ở giấy ngà đúng 2:00.
