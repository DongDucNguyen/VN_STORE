# Prompt và nguồn ảnh concept VNStore

Ngày: 17/10/2026. Công cụ: `image_gen.imagegen` tích hợp; không dùng CLI/API fallback. Cả ba ảnh là ảnh mới, không dùng ảnh người dùng làm tham chiếu, nền không trong suốt. Prompt được ghi nguyên văn bên dưới.

Ảnh phục vụ duyệt phong cách/bố cục, không xác nhận sản phẩm, giá, địa danh hoặc nguồn gốc. Nội dung HTML và dữ liệu thật khi triển khai phải theo [design.md](../../design.md). Các khác biệt của ảnh đã ghi ở §1 tài liệu đó. PNG nguyên trang không phải asset production.

## Trang chủ desktop

Tệp: [01-home-desktop.png](mockups/01-home-desktop.png).

```text
Use case: ui-mockup
Asset type: high fidelity desktop homepage design concept for the existing Vietnamese product discovery website VNStore.
Primary request: A refined, unmistakably Vietnamese website, modern editorial product discovery, bamboo, a genuine Vietnamese conical palm-leaf hat (nón lá), and lotus pond, beautifully art-directed rather than generic ecommerce.
Composition: one flat front-facing browserless web page mockup, landscape canvas about 1536x1024. Show the header, complete hero, 5 category links and beginning of product grid. No devices, no perspective, no mockup background outside the webpage.
Palette: warm rice-paper ivory #F7F3E8, deep bamboo green #214B3B, ink #22352B, straw #D8BD7A, restrained lotus rose #AD586C. Large whitespace, crisp fine borders and small corner radii.
Header: VNStore left, links "Khám phá", "Làng nghề", "Thương hiệu", "Yêu thích"; small outlined heart. Simple elegant lotus/bamboo geometric mark. Do not add cart, checkout, sale badges or account icons.
Hero layout: left 45 percent is ivory solid with generous margins, small eyebrow "TRE • SEN • NẾP VIỆT", large sophisticated Vietnamese serif heading "Chạm vào nếp Việt", short subheading "Khám phá sản phẩm, chất liệu và làng nghề Việt.", prominent horizontal search input labelled "Bạn đang tìm món gì?" plus mic icon, camera icon and deep green "Tìm" button. Under it two simple chips "Gốm sứ" and "Mây tre đan".
Hero right 55 percent: rich cinematic photoreal Vietnamese lotus pond in early morning light, pink lotus blossoms, broad lotus leaves, a few delicate bamboo stems framing at right, natural rough bamboo bench in foreground with ONE authentic Vietnamese conical straw hat resting on it. Elegant quiet atmosphere, nuanced natural light, no people, no temples, no foreign architectural stereotypes. Image clean rectangle with subtle arched corner only at upper right, no cloud-like blobs. Do not overlay text over busy photo.
Below hero: five restrained category tiles labelled "Gốm sứ", "Mây tre đan", "Dệt may", "Gỗ & sơn mài", "Đặc sản". Small editorial objects, not emoji.
Below: heading "Những món đồ mang hồn Việt" and four beautifully photographed product cards: white ceramic tea set, woven water hyacinth bag, ivory silk scarf with lotus motif, premium chocolate. Tiny product captions, prices shown as "Giá tham khảo" without numeric claims, heart outline buttons; no star ratings or origin certification seals.
Floating compact button "Trợ lý" lower right.
Typography: beautiful editorial serif headings supporting correct Vietnamese diacritics; highly legible modern sans UI. Realistic production-ready interface hierarchy. Accurate main Vietnamese text; do not cram dense paragraphs.
Constraints: concept mockup only, no invented verified craft provenance, no e-commerce purchase controls, no giant decorative text, no neon, no generic AI gradients, no pagoda/red lantern imagery.
```

## Tìm kiếm và chi tiết desktop

Tệp: [02-search-product-desktop.png](mockups/02-search-product-desktop.png).

```text
Use case: ui-mockup
Asset type: high fidelity two-screen desktop design review board for VNStore, a Vietnamese product discovery website.
Primary request: two large crisp browserless desktop webpage mockups side by side on one landscape canvas. LEFT: product search results. RIGHT: product detail. Small labels "02 / TÌM KIẾM" and "03 / CHI TIẾT" above the mockups. Both equally large and legible. Rich realistic product photography. This is a concept, not actual catalog data.
Art direction consistent across both: warm rice-paper #F7F3E8, deep bamboo green #214B3B, ink #22352B, straw #D8BD7A, restrained lotus rose. Elegant Vietnamese serif headings, sans-serif body controls, restrained leaf linework at edges, minimal fine borders, radius 8px, spacious aligned grid. No generic gradients or glowing UI.
LEFT screen: header VNStore with lotus outline mark and tiny nav. Search field "túi đan có quai" with microphone, camera and green Tìm button. Heading "Tìm một món hợp ý". A subtle pale green active filter chip "Có quai". Left narrow filter sidebar "Bộ lọc" with "Chất liệu", "Khoảng giá", "Làng nghề". Right 2x2 product grid featuring four distinct realistic handwoven Vietnamese bags, cream background, heart outline in each image corner, captions and "Giá tham khảo". At bottom a small "Xem thêm" outlined button. Product photos are on neutral clean backgrounds; bamboo accent only in page masthead. No arbitrary sorting controls.
RIGHT screen: same compact header. Small breadcrumb "Khám phá / Mây tre đan". Large product photo of a natural woven water-hyacinth bag with rounded handles on left, three thumbnail images below. On right heading "Túi đan có quai", muted caption "Chất liệu và thông tin sản phẩm", bold "Giá tham khảo", green primary button "Hỏi trợ lý" and outline "Yêu thích". Below clear sections "Chất liệu & kích thước" and "Nguồn gốc và căn cứ" with fine ruled rows, mini link "Xem nguồn". Add small line "Chưa có đánh giá" in reviews area. Leave whitespace; no fake badges, no ratings stars, no claims of verified origin.
Constraints: UI should look practical, precise and premium; show enough full screen content to understand layouts. Vietnamese diacritics correct. NO cart, buy button, shipping, discounts or checkout. NO invented numeric product prices, manufacturer names, origin claims or certification seals. Subtle bamboo-and-lotus identity without ornamental clutter. No phones or perspective.
```

## Trang chủ, ảnh và trợ lý mobile

Tệp: [03-mobile-home-image-assistant.png](mockups/03-mobile-home-image-assistant.png).

```text
Use case: ui-mockup
Asset type: high-fidelity mobile UI design review board, Vietnamese product discovery website VNStore.
Primary request: Three flat mobile screen rectangles placed side by side on a warm ivory board, no device frames, no perspective, large readable UI. Labels above each "04 / TRANG CHỦ", "05 / TÌM BẰNG ẢNH", "06 / TRỢ LÝ". All screens same height, complete visible including bottom UI. Portrait screen aspect about 390x844, canvas landscape.
Style: warm rice-paper #F7F3E8, bamboo green #214B3B, dark ink #22352B, lotus rose #AD586C. Elegant Vietnamese serif headings, contemporary readable sans-serif interface. Thin lines, subtle rounded corners, no shadows except tiny overlay shadow, no gradients. Vietnamese bamboo, lotus pond, conical nón lá clearly present only in first screen.
Screen 1: simple VNStore header with lotus outline mark, search icon and menu. Large title "Chạm vào nếp Việt", subheading "Khám phá sản phẩm Việt". A search input "Bạn đang tìm món gì?" with separate microphone and camera controls. Below a wide photographic Vietnamese lotus pond at dawn, bamboo leaves and one authentic conical straw hat resting on bamboo bench in foreground. Under photo two category chips "Gốm sứ" / "Mây tre đan", heading "Gợi ý khám phá", two product card photos: ceramic tea set and woven bag. Bottom nav has labelled controls "Khám phá", "Tìm kiếm", "Yêu thích", "Trợ lý". No cart.
Screen 2: VNStore header, back icon, title "Tìm bằng ảnh", tiny helper "Chọn ảnh và khoanh vùng món đồ". Two buttons "Chụp ảnh" / "Chọn ảnh". Big clean preview photo of a woven bag on pale background with rectangular green crop corners. Input label "Yêu cầu thêm" and input "có quai, dưới 400k". Full width dark green button "Tìm mẫu tương tự". Below heading "Mẫu tương tự", two small product preview thumbnails, no numeric match score. Same bottom navigation as screen 1. No foliage covering controls, no fancy scanning beam.
Screen 3: full screen assistant chat. Header with lotus line icon and "Trợ lý VNStore", small "Ghi nhớ" link and clearly visible X close. Intro "Mình giúp bạn tìm món hợp ý." Compact pale panel with heading "Lưu cuộc trò chuyện?" and three RADIO choices "Không lưu", "Lưu lịch sử", "Ghi nhớ sở thích"; first selected; button "Lưu lựa chọn". One right aligned bubble "Mình tìm quà tân gia." One left aligned bubble "Bạn muốn chọn gốm hay đồ đan?" with two choice chips "Gốm sứ" and "Mây tre đan". Small assistant product preview card image with title "Gợi ý từ danh mục". Bottom composer input "Nhắn cho trợ lý" plus mic and "Gửi" button. No bottom navigation within chat. No fake testimonials or numerical ratings.
Constraints: polished practical mobile UI, legible main text with correct diacritics, accessible generous touch areas. No invented provenance claims, no buy button, no discounts, no account login. Images only illustrate concept products. No extra navigation categories beyond specified. Sparse typography, avoid long generated paragraphs.
```

