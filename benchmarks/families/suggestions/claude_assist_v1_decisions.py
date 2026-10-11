"""Machine-assisted DRAFT suggestions for the seed-004 family review page (not decisions).

Written by Claude (AI) on 11/10/2026 from names, SKUs, prices, materials, source URLs and image cosine only;
images were not inspected one by one. The data team decides each card; build_family_suggestions.py checks these
suggestions are internally consistent with apply_family_review.py rules.

Rule used (from the review page): one family = SKUs that are variants of the same item (size, volume, colour,
gift pack). Different flavour/assortment, different painted design or a different object type = separate.
Indices: F = packet["families"], C = packet["candidates"], S = packet["shared"] (packet 2026-10-11_seed-004).
"""

SIZE = "biến thể kích thước của cùng một món"
COLOR = "cùng món, khác màu/hoàn thiện"
FLAVOR = "khác hương vị/thành phần là sản phẩm khác"
DESIGN = "khác họa tiết vẽ là sản phẩm khác"
OBJECT = "khác loại đồ vật (cùng dòng thiết kế)"

F = {
    0: ("confirm", None, "Bellus S/M/XL: " + SIZE),
    1: ("split", ["A", "A", "A", "B"], "3 bình Red River (lớn/M/S) là một họ; hộp trà tròn là " + OBJECT),
    2: ("split", ["A", "B"], "Bình hoa và hộp trà Thong Dong: " + OBJECT),
    3: ("confirm", None, "Vịnh S/M/L: " + SIZE),
    4: ("confirm", None, "Elephone EL01/EL02: " + COLOR + " (EL02 thêm lá vàng)"),
    5: ("split", ["A", "B", "B"], "Giỏ Ethnic 'cao' khác dáng với 'thấp' M/S (mã OU17/AF26 lẫn nhau) — cần xem ảnh"),
    6: ("confirm", None, "Hộp đá Mountain S/M: " + SIZE),
    7: ("confirm", None, "Hộp đan tre Ethnic S/M: " + SIZE),
    8: ("confirm", None, "Hộp trà Exotic EX08/09/10 cùng tên, cùng giá: " + COLOR + " — kiểm tra ảnh họa tiết"),
    9: ("confirm", None, "Hộp trang sức Exotic M/L: " + SIZE),
    10: ("confirm", None, "Hộp vuông Botanica S/M: " + SIZE),
    11: ("confirm", None, "Hộp vuông Exotic S/M/L: " + SIZE),
    12: ("confirm", None, "Hộp vuông Moonbow S/M/L: " + SIZE),
    13: ("confirm", None, "Khay chữ nhật Moonbow S/L: " + SIZE),
    14: ("confirm", None, "Khay chữ nhật Mountain S/M: " + SIZE),
    15: ("confirm", None, "Khung ảnh Moonbow S/M: " + SIZE),
    16: ("split", ["A", "B", "C"], "3 hộp Napolitains 36 viên khác bộ vị (Flavors/Single Origin/Faiseurs): " + FLAVOR),
    17: ("confirm", None, "Cà Phê Sữa 24G/80G: " + SIZE),
    18: ("split", ["A", "B", "C"], "3 thanh Socola Trail: " + FLAVOR),
    19: ("split", ["A", "A", "B"], "Protein Bar 55G và hộp 10x55G cùng món; Energy Bar 40G " + FLAVOR),
    20: ("split", ["A", "B", "C", "D"], "4 thanh Maison Marou Exclusive: " + FLAVOR),
    21: ("split", ["A", "B", "C"], "3 thanh Marou Bar 35G: " + FLAVOR),
    22: ("confirm", None, "Set 3 Milk by Marou và bản mini: " + SIZE),
    23: ("confirm", None, "Set 6 Faiseurs và bản mini: " + SIZE),
    24: ("confirm", None, "Hộp quà Faiseurs và bản mini: " + SIZE),
    25: ("confirm", None, "Matcha & Coconut bar và mini bar: " + SIZE),
    26: ("split", ["A", "B"], "Bình 36 cm Hoa Sen và Sen Đỏ: " + DESIGN + " (giá khác nhau)"),
    27: ("confirm", None, "Đôi Két 41 cm: hai trang Minh Long trùng tên, giá, ảnh — có thể là tin đăng trùng; báo nhóm dữ liệu"),
    28: ("confirm", None, "Sen Vàng 45/50 cm: " + SIZE),
    29: ("confirm", None, "Lộc Phát Sen vàng nền vàng 28/40 cm: " + SIZE),
    30: ("split", ["A", "B"], "Bộ trà Camellia 0,5 L Hương Biển Kem và Chỉ Vàng: " + DESIGN),
    31: ("confirm", None, "Camellia Văn Lang 0,5/0,8 L: biến thể dung tích"),
    32: ("confirm", None, "Dĩa lót Tulip Ngà 4 màu: " + COLOR),
    33: ("split", ["A", "B"], "Dĩa tròn Jasmine 18 cm và Tulip IFP 22 cm: khác dòng sản phẩm"),
    34: ("split", ["A", "B"], "VH24043 và VH240902 là hai trang sản phẩm Vietcraft khác nhau (pendant light / hanging lampshade)"),
}

SEP = "separate"
MERGE = "merge"
C = {
    0: (SEP, "dĩa lót chén 15 cm và dĩa lót tách 12 cm: khác món"),
    1: (SEP, FLAVOR), 2: (MERGE, "Bellus M/XL — cùng họ đề xuất"), 3: (SEP, FLAVOR),
    4: (MERGE, "Tulip Ngà cam/xanh non — " + COLOR), 5: (SEP, FLAVOR), 6: (SEP, "khác vùng cacao"),
    7: (SEP, "27 cm là dòng men ngọc (URL) khác dòng Sen Vàng 45/50 cm; giá khác hẳn — cần xem ảnh"),
    8: (SEP, "27 cm là dòng men ngọc khác dòng Sen Vàng 45/50 cm"),
    9: (MERGE, "hộp Halloween 6 Single Origin: thanh thường và mini — " + SIZE),
    10: (SEP, FLAVOR), 11: (SEP, "khác vùng cacao"), 12: (MERGE, "Lộc Phát 28/40 cm — cùng họ đề xuất"),
    13: (SEP, "Hoàng Cung và Royal: khác dòng"), 14: (SEP, "khác mã chụp đèn Vietcraft"), 15: (SEP, FLAVOR),
    16: (SEP, "khác mã chụp đèn Vietcraft"), 17: (SEP, FLAVOR), 18: (MERGE, "Faiseurs gift box và mini — cùng họ đề xuất"),
    19: (SEP, DESIGN), 20: (MERGE, "Red River M/S — cùng nhóm bình"), 21: (SEP, "khác mã chụp đèn Vietcraft"),
    22: (SEP, FLAVOR), 23: (SEP, "khác mã chụp đèn Vietcraft"), 24: (SEP, FLAVOR), 25: (SEP, "khác mã chụp đèn Vietcraft"),
    26: (SEP, FLAVOR), 27: (SEP, "khác bộ vị (Flavors vs Single Origin)"), 28: (SEP, "dĩa súp và dĩa tròn: khác món"),
    29: (MERGE, "Tulip Ngà cam/vàng — " + COLOR), 30: (MERGE, "Exotic EX08/09 — cùng họ đề xuất"),
    31: (SEP, "hộp đồng hồ và hộp cigar Keras: " + OBJECT), 32: (SEP, "khác vùng cacao"),
    33: (MERGE, "Bellus M/S — cùng họ đề xuất"), 34: (SEP, FLAVOR), 35: (MERGE, "Exotic EX09/10 — cùng họ đề xuất"),
    36: (SEP, FLAVOR), 37: (SEP, DESIGN), 38: (SEP, DESIGN), 39: (SEP, "khác vùng cacao"),
    40: (SEP, "dĩa súp Jasmine và dĩa tròn Tulip: khác món/dòng"), 41: (MERGE, "Vịnh L/M — cùng họ đề xuất"),
    42: (SEP, FLAVOR), 43: (SEP, DESIGN), 44: (SEP, "Halloween và Trung thu: khác ấn bản/bộ"),
    45: (SEP, DESIGN), 46: (SEP, "khác bộ vị"), 47: (SEP, FLAVOR), 48: (SEP, FLAVOR),
    49: (MERGE, "Tulip Ngà cam/trắng ngà — " + COLOR), 50: (SEP, "khác vùng cacao"), 51: (SEP, DESIGN),
    52: (SEP, "Tứ Linh 50 cm và Hồn Việt 30 cm: " + DESIGN), 53: (SEP, DESIGN),
    54: (SEP, "khăn SenSilk khác mẫu in"), 55: (SEP, "hộp trang sức Cosmos và Exotic: khác dòng"),
    56: (SEP, FLAVOR), 57: (SEP, FLAVOR), 58: (SEP, FLAVOR),
    59: (SEP, "giỏ mây VH24056 (bread basket) và khay mây: khác món, khác trang nguồn"),
    60: (SEP, "khăn SenSilk khác mẫu in"), 61: (SEP, FLAVOR),
    62: (SEP, "Camellia Văn Lang và Chim Lạc: " + DESIGN), 63: (SEP, "Văn Lang và Chim Lạc: " + DESIGN),
    64: (SEP, "hai giỏ seagrass ở hai trang nguồn Vietcraft khác nhau"), 65: (SEP, DESIGN), 66: (SEP, "khác mã chụp đèn Vietcraft"),
    67: (SEP, "khác vùng cacao"), 68: (SEP, DESIGN), 69: (SEP, "Daisy quả ôliu và sen hồng: " + DESIGN),
    70: (SEP, FLAVOR), 71: (SEP, "khác vùng cacao"), 72: (SEP, "Cosmos và Exotic: khác dòng"),
    73: (MERGE, "Lộc Phát 28 cm nền vàng/nền xanh ngọc: " + COLOR + " — gộp vào họ Lộc Phát"),
    74: (SEP, FLAVOR), 75: (SEP, DESIGN), 76: (SEP, FLAVOR), 77: (SEP, "khác vùng cacao"),
    78: (MERGE, "Moonbow M/S — cùng họ đề xuất"), 79: (SEP, DESIGN), 80: (SEP, FLAVOR),
    81: (SEP, "hộp Napolitains và set thanh 80G: khác dạng sản phẩm"), 82: (SEP, DESIGN),
}

S = {
    0: ("exclude", "Ảnh minh họa chung của 7 bộ trà khác họa tiết: tìm bằng ảnh sẽ khớp đều cả 7 (P0.6)"),
    1: ("exclude", "Ảnh minh họa chung của 5 bộ trà khác họa tiết (P0.6)"),
    2: ("exclude", "Ảnh chung của bình Red River và hộp trà — hai họ khác nhau theo gợi ý F1"),
    3: ("keep", "Đôi Két: hai tin của cùng một sản phẩm (cùng họ)"),
    4: ("keep", "Đôi Két: hai tin của cùng một sản phẩm (cùng họ)"),
    5: ("keep", "Sen Vàng 45/50 cm cùng họ"),
    6: ("keep", "Sen Vàng 45/50 cm cùng họ"),
    7: ("keep", "Văn Lang 0,5/0,8 L cùng họ"),
}
