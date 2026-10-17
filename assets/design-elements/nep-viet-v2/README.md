# Nếp Việt v2 — bộ elements

Mở **[index.html](index.html)** trực tiếp trong trình duyệt để xem 36 elements, đổi nền kiểm tra alpha và thử bốn nhịp chuyển động. Không cần chạy backend hay cài thêm thư viện để xem.

Bộ ảnh đi theo [design.md](../../../design.md): mỗi chương có một điểm nhấn Việt Nam; khoảng trống và nội dung giữ vai trò chính. Đây là bộ master để triển khai, chưa phải giao diện ứng dụng đã tích hợp.

## Trong thư mục

| Nhóm | Số lượng được chọn | Nội dung |
|---|---:|---|
| `cutouts/` | 5 PNG | Nhánh tre, bóng tre sạch, bình gốm, nón lá, mép lụa |
| `botanical/` | 2 PNG | Sen nở và cụm lá/gương sen tách nền |
| `scenes/` | 3 PNG | Đầm sen desktop, đầm sen mobile, phong cảnh footer |
| `textures/` | 1 PNG | Cận cảnh nan đan |
| `editorial/` | 2 PNG | Bàn tay đan và góc bàn nghề |
| `categories/` | 5 PNG | Gốm, đan, dệt, gỗ-sơn, đặc sản đóng gói |
| `svg/` | 18 SVG | 6 hình trang trí/motion và 12 icon tác vụ |

Có thêm **một bản không được chọn**: `cutouts/bamboo-shadow.png` còn mảng nền trắng, giữ để đối chiếu QA. Chỉ dùng `cutouts/bamboo-shadow-clean.png`; bản cũ không có trong gallery hay danh sách assets của manifest.

## Sắp đặt theo hành trình

| Vị trí | Elements | Quy tắc |
|---|---|---|
| Mở đầu | Nhánh tre + bóng, một bình gốm nhỏ | Tre nằm ở mép phải; gốm ở góc thấp. Không đưa nón và đầm sen lên đây. Chữ/search đứng yên, nền tre không che input. |
| Chương danh mục | Nón lá + năm ảnh danh mục | Nón ló một phần từ mép chương. Ảnh danh mục đứng riêng, không phủ hoạ tiết lên vật thể. |
| Khoảng nghỉ giữa trang | Đầm sen desktop/mobile | Một cảnh rộng tĩnh, focal point ảnh ngang khoảng 67% chiều ngang. Mobile có bố cục riêng, không phải cùng một cảnh crop chính xác. |
| Lề nhóm sản phẩm | Macro đan hoặc một botanical | Dùng một chất liệu ở một vùng nhìn; không tile và không đặt ảnh sau thông tin sản phẩm. |
| Câu chuyện nghề | Bàn tay / bàn nghề + mép lụa | Chọn ảnh chính/phụ; vải ở mép. Caption xác định đây là minh họa AI. |
| Chân trang | Phong cảnh nét mực | Cảnh bám đáy; links trên phần nền đặc. Không animate phong cảnh lớn. |

Thông số kích thước, dung lượng, SHA-256, vai trò, vị trí, alt gợi ý, mobile variant và route đề xuất nằm trong **[manifest.json](manifest.json)**. Các route là nhãn vai trò để tích hợp, không phải URL router đã đấu nối.

## Cách dùng ảnh

- PNG alpha giữ nền trong suốt gốc. Botanical có phần cánh/lá tô ngà bên trong silhouette; đây là tranh nét khắc có màu nền vật thể, không phải nét đơn sắc có thể tint tùy ý.
- Bóng tre sạch nên dùng opacity `0.08–0.16`, `mix-blend-mode: multiply` trong wrapper `isolation: isolate`; kiểm lại khi tích hợp dark mode. Không cần bóng ở mọi nền.
- Ảnh trang trí: `alt=""`, `aria-hidden="true"`, `pointer-events: none`. Chỉ clip wrapper artwork, tránh clip focus ring/control của section.
- Ảnh biên tập/danh mục: dùng alt mô tả đúng hình. Không dùng tên làng nghề, nghệ nhân hay thương hiệu không có trong nguồn dữ liệu.
- Ảnh dưới màn hình đầu: `loading="lazy"`, `decoding="async"`; luôn khai báo width/height đúng trong manifest để giữ layout ổn định.
- Hai panorama ngang thực tế **2172 × 724px**; chưa đạt đề xuất source ≥2400px của design.md. Không phóng lớn để giả độ phân giải. Các PNG còn là master dung lượng lớn; cần tạo biến thể AVIF/WebP và đo ngân sách trước khi đưa lên production.
- Ảnh hàng thật và các bản crop sản phẩm tiếp tục lấy từ `assets/products/`; bộ này không tạo sản phẩm giả thay catalog.

Ví dụ tham chiếu (điều chỉnh đường dẫn theo thư mục public lúc tích hợp):

```html
<picture>
  <source media="(max-width: 640px)" srcset="scenes/lotus-midpage-mobile.png">
  <img src="scenes/lotus-midpage-desktop.png" width="2172" height="724"
       alt="" loading="lazy" decoding="async">
</picture>
```

Đặt aspect-ratio cho wrapper theo breakpoint dựa trên kích thước thực trong manifest; tránh giữ khung ngang 3:1 cho ảnh mobile dọc.

## SVG và chuyển động

`motion.css` cung cấp bốn nhịp: `nv-bamboo`, `nv-ripple`, `nv-weave`, `nv-lotus`; thêm `nv-motion` và bật class `is-playing` khi cần. `gallery.js` là ví dụ phát một lần, hủy khi ra viewport/tab ẩn, và tôn trọng reduced motion kể cả thay đổi runtime.

| SVG | Nhóm để thao tác |
|---|---|
| `bamboo-motion.svg` | `stems`, `leaves-upper`, `leaves-lower` |
| `lotus-mark.svg` | `petal-center`, `petal-left`, `petal-right` |
| `non-la-lines.svg` | `outline`, `ribs-a`, `ribs-b` |
| `water-ripple.svg` | `ripple-inner`, `ripple-middle`, `ripple-outer` |
| `bamboo-divider.svg`, `weave-divider.svg` | Dải phân đoạn tĩnh |

Nhúng SVG inline để điều khiển nhóm bên trong. Nếu nhiều instance trong một DOM, đổi tiền tố ID theo instance và cập nhật selector tương ứng. SVG trong `<img>` không nhận `currentColor` từ phần tử cha; muốn đổi màu hãy nhúng inline và đặt `style="color: ..."` trên root SVG hoặc dùng CSS mask cho icon đơn sắc. Không animate màu bằng filter trong production.

Icon gồm: search, microphone, camera, heart, chat, menu, close, arrow, filter, check, home, source. Nét thống nhất 1.75, không đưa chi tiết văn hóa vào tác vụ khiến khó nhận biết. Accessible name đặt trên nút chứa icon.

Nội dung luôn hiện khi chưa có JS. Motion chỉ dùng transform/opacity, không loop trang trí, không chờ animationend mới thực hiện action. Đây là mẫu nhịp, chưa phải phép đo 60fps của VNStore.

## Nguồn và kiểm tra

18 ảnh được tạo bằng **imagegen tích hợp**; prompt gốc và prompt sửa bóng tre lưu ở [PROMPTS.md](PROMPTS.md). 18 SVG được viết trực tiếp cho dự án. Ảnh AI phục vụ minh họa mỹ thuật, không phải ảnh tư liệu chứng minh xuất xứ hoặc hình của sản phẩm đang bán.

- [alpha-inspection.html](alpha-inspection.html) / [alpha-inspection.png](alpha-inspection.png): đối chiếu alpha trên nền ngà và xanh, có cả bản bóng tre cũ để thấy khác biệt.
- `build-gallery.cjs`: tạo lại manifest/gallery từ assets, không sửa PNG.
- `inspect-alpha.cjs`: kiểm tra trực quan ảnh tách nền.
- `verify.cjs`: kiểm ảnh, đường dẫn, responsive, chuyển động và reduced motion; kết quả ở `qa/verification.json`.

Các script kiểm tra dùng Playwright đã có trong `frontend/node_modules`; gallery tự nó không cần dependency.
