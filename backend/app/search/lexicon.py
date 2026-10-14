"""Từ vựng tìm kiếm nằm ngoài catalog (GĐ5): dịch Anh–Việt, cách viết khác, viết tắt thương hiệu.

Đây là tri thức ngôn ngữ chung, không phải dữ kiện về sản phẩm, nên giữ trong mã tìm kiếm thay vì
`search_dictionary` của database.json (đổi catalog làm lệch hash của nhãn/packet/chỉ mục ảnh). Khi catalog
được sửa lần tới có thể chuyển sang `search_dictionary` qua importer.

Nguồn từ: toàn bộ từ tiếng Anh có nghĩa xuất hiện trong tên/alias sản phẩm của catalog seed-006 (Marou, Vietcraft,
Kilomet109, Hanhsilk…) dịch sang tiếng Việt thông dụng, cộng các cách gõ phổ biến của "sô cô la". Không thêm
thuộc tính cho sản phẩm; chỉ mở rộng truy vấn với trọng số thấp hơn từ người dùng gõ.
"""
from __future__ import annotations

# relation: translation (Anh ↔ Việt), spelling (cách viết khác cùng nghĩa), abbreviation (viết tắt).
# category_ids rỗng: áp dụng mọi danh mục. Mỗi nhóm là các cách nói tương đương nhau; "sources" (nếu có) giới hạn
# những cách nói được phép kích hoạt mở rộng, dùng khi một chiều mơ hồ ("lạc" còn là "chim Lạc", "red" trong
# "Red River" không chắc là màu đỏ).
LEXICON: list[dict] = [
    {"id": "lex-socola", "relation": "spelling", "terms": ["sô cô la", "socola", "chocolate", "chocolat"]},
    {"id": "lex-km109", "relation": "abbreviation", "terms": ["km109", "kilomet109"]},
    # Hương vị/thành phần sô cô la (tên nguồn Marou bằng tiếng Anh).
    {"id": "lex-sua", "relation": "translation", "terms": ["sữa", "milk"]},
    {"id": "lex-dua", "relation": "translation", "terms": ["dừa", "coconut"]},
    {"id": "lex-hat-dieu", "relation": "translation", "terms": ["hạt điều", "cashew", "cashews"]},
    {"id": "lex-gung", "relation": "translation", "terms": ["gừng", "ginger"]},
    {"id": "lex-ot", "relation": "translation", "terms": ["ớt", "chili"]},
    {"id": "lex-thuan-chay", "relation": "translation", "terms": ["thuần chay", "vegan"]},
    {"id": "lex-dau-phong", "relation": "translation", "terms": ["đậu phộng", "peanut", "peanuts"]},
    {"id": "lex-lac", "relation": "translation", "terms": ["lạc", "đậu phộng", "peanut", "peanuts"], "sources": ["lạc"]},
    {"id": "lex-que", "relation": "translation", "terms": ["quế", "cinnamon"]},
    {"id": "lex-vung", "relation": "translation", "terms": ["vừng", "mè", "sesame"]},
    {"id": "lex-hat-bi", "relation": "translation", "terms": ["hạt bí", "pumpkin seeds"]},
    {"id": "lex-vani", "relation": "translation", "terms": ["vani", "vanilla"]},
    {"id": "lex-quat", "relation": "translation", "terms": ["quất", "kumquat"]},
    {"id": "lex-ca-phe", "relation": "translation", "terms": ["cà phê", "coffee"]},
    {"id": "lex-muoi-bien", "relation": "translation", "terms": ["muối biển", "sea salt"]},
    {"id": "lex-matcha", "relation": "translation", "terms": ["trà xanh", "matcha"]},
    {"id": "lex-trai-cay", "relation": "translation", "terms": ["trái cây", "hoa quả", "fruit", "fruits"]},
    {"id": "lex-com", "relation": "translation", "terms": ["cốm", "popped rice"]},
    {"id": "lex-kieu-mach", "relation": "translation", "terms": ["kiều mạch", "buckwheat"]},
    {"id": "lex-gia-vi", "relation": "translation", "terms": ["gia vị", "spice", "spices"]},
    {"id": "lex-sc-den", "relation": "translation", "terms": ["sô cô la đen", "dark chocolate"]},
    {"id": "lex-sc-trang", "relation": "translation", "terms": ["sô cô la trắng", "white chocolate"]},
    {"id": "lex-trung-thu", "relation": "translation", "terms": ["trung thu", "mid autumn"]},
    {"id": "lex-qua-tang", "relation": "translation", "terms": ["quà tặng", "gift"]},
    # Đồ gia dụng, trang trí, mây tre (Vietcraft, Hanoia).
    {"id": "lex-gio", "relation": "translation", "terms": ["giỏ", "basket", "baskets"]},
    {"id": "lex-khay", "relation": "translation", "terms": ["khay", "tray"]},
    {"id": "lex-bat", "relation": "translation", "terms": ["bát", "bowl", "bowls"]},
    {"id": "lex-canh", "relation": "translation", "terms": ["canh", "súp", "soup"], "sources": ["canh", "soup"],
     "note": "Đĩa/bát đựng canh ~ đĩa súp; một chiều để 'súp' không kéo theo nghĩa khác của 'canh'."},
    {"id": "lex-dia", "relation": "translation", "terms": ["đĩa", "plate", "dish"]},
    {"id": "lex-lot-ly", "relation": "translation", "terms": ["lót ly", "coaster"]},
    {"id": "lex-binh-hoa", "relation": "translation", "terms": ["bình hoa", "vase", "flower vase"]},
    {"id": "lex-chup-den", "relation": "translation", "terms": ["chụp đèn", "lampshade"]},
    {"id": "lex-den-long", "relation": "translation", "terms": ["đèn lồng", "lantern"]},
    {"id": "lex-de-nen", "relation": "translation", "terms": ["đế nến", "candle holder"]},
    {"id": "lex-guong", "relation": "translation", "terms": ["gương", "mirror"]},
    {"id": "lex-bo-tra", "relation": "translation", "terms": ["bộ trà", "tea set"]},
    {"id": "lex-am-tra", "relation": "translation", "terms": ["ấm trà", "teapot"]},
    {"id": "lex-coc", "relation": "translation", "terms": ["cốc", "mug", "cup"]},
    {"id": "lex-hop", "relation": "translation", "terms": ["hộp", "box"]},
    {"id": "lex-nha-thu-cung", "relation": "translation", "terms": ["thú cưng", "pet"]},
    {"id": "lex-do-giat", "relation": "translation", "terms": ["đồ giặt", "quần áo bẩn", "laundry"]},
    {"id": "lex-banh-mi", "relation": "translation", "terms": ["bánh mì", "bread"]},
    {"id": "lex-tre-em", "relation": "translation", "terms": ["trẻ em", "kid", "kids"]},
    {"id": "lex-trang-tri", "relation": "translation", "terms": ["trang trí", "decor", "decorative"]},
    {"id": "lex-thu-cong", "relation": "translation", "terms": ["thủ công", "handmade", "handcrafted"]},
    {"id": "lex-dan-tay", "relation": "translation", "terms": ["đan tay", "handwoven", "woven"]},
    {"id": "lex-ve-tay", "relation": "translation", "terms": ["vẽ tay", "hand painted"]},
    # Chất liệu.
    {"id": "lex-tre", "relation": "translation", "terms": ["tre", "bamboo"]},
    {"id": "lex-may", "relation": "translation", "terms": ["mây", "rattan", "wicker"]},
    {"id": "lex-co-bien", "relation": "translation", "terms": ["cỏ biển", "seagrass"]},
    {"id": "lex-luc-binh", "relation": "translation", "terms": ["lục bình", "water hyacinth"]},
    {"id": "lex-xa-cu", "relation": "translation", "terms": ["xà cừ", "mother of pearl"]},
    {"id": "lex-son-mai", "relation": "translation", "terms": ["sơn mài", "lacquer"]},
    {"id": "lex-gom", "relation": "translation", "terms": ["gốm", "ceramic"]},
    {"id": "lex-su", "relation": "translation", "terms": ["sứ", "porcelain"]},
    {"id": "lex-lua", "relation": "translation", "terms": ["lụa", "silk"]},
    # Thời trang, phụ kiện (Hanhsilk, SenSilk, Kilomet109).
    {"id": "lex-khan", "relation": "translation", "terms": ["khăn", "scarf", "scarves", "shawl"]},
    {"id": "lex-khan-tay", "relation": "translation", "terms": ["khăn tay", "handkerchief"]},
    {"id": "lex-theu", "relation": "translation", "terms": ["thêu", "embroidery"]},
    {"id": "lex-vay", "relation": "translation", "terms": ["váy", "dress"]},
    {"id": "lex-dam", "relation": "translation", "terms": ["đầm", "váy", "dress"], "sources": ["đầm"],
     "note": "Đầm = váy liền; một chiều để 'váy' không kéo bình hoa 'Đầm Sen'."},
    {"id": "lex-chan-vay", "relation": "translation", "terms": ["chân váy", "skirt"]},
    {"id": "lex-ao-khoac", "relation": "translation", "terms": ["áo khoác", "jacket", "coat"]},
    {"id": "lex-ao-so-mi", "relation": "translation", "terms": ["áo sơ mi", "shirt"]},
    {"id": "lex-vong-co", "relation": "translation", "terms": ["vòng cổ", "necklace"]},
    {"id": "lex-tui-xach", "relation": "translation", "terms": ["túi xách", "handbag"]},
    {"id": "lex-trang-suc", "relation": "translation", "terms": ["trang sức", "jewelry", "jewellery"]},
    # Màu thường gặp trong tên tiếng Anh.
    {"id": "lex-trang", "relation": "translation", "terms": ["white", "trắng"], "sources": ["white"]},
    {"id": "lex-den", "relation": "translation", "terms": ["black", "đen"], "sources": ["black"]},
    {"id": "lex-do", "relation": "translation", "terms": ["red", "đỏ"], "sources": ["red"]},
]

# Viết tắt thương hiệu dùng để nhận ra gợi ý bộ lọc (Vocabulary), cùng lý do với LEXICON.
BRAND_ABBREVIATIONS: dict[str, str] = {"km109": "brand-kilomet109"}
