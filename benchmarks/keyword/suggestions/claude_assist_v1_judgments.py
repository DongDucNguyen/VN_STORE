"""Machine-assisted DRAFT relevance suggestions for the seed-004 keyword packets (dev 107 + seed 12).

Written by Claude (AI) on 11/10/2026 from catalog fields only (name, category, materials, colours, price,
claims, aliases, description). These are NOT labels: a human must review every pair in the review page,
and the second independent reviewer must use the packet WITHOUT suggestions (review_protocol.md).

Indices refer to the product order of packet.json (catalog sha 5448a8f4…); build_suggestions.py maps them to
product IDs and refuses to run on another catalog. Pool members that are not listed get 0. Queries with
full=True were checked against the whole catalog (needed when nothing reaches 2).

Policies applied (stated in each reason so reviewers can overrule):
  P1 Minh Long / LY'S item without a material field, query requires "sứ": at most 2, flagged.
  P2 Required attribute (colour, origin, shape, technique) not evidenced in the catalog: 1.
  P3 Price constraint: over budget → 0; product without a price → 1.
  P4 Same item type but a different named product/collection: 1.
"""

TEA = [3, 174, 176, 177, 178, 200, 209, 210, 211]
ML_VASE = [1, 2, 175] + list(range(179, 198)) + list(range(218, 234))
HANOIA_VASE = [20, 21, 60, 62, 63, 65, 66, 67, 68, 69, 72, 73, 74, 78, 92, 108, 123]
PENDANT = [268, 269, 275, 278, 284, 285, 289, 297, 302, 309]
RATTAN_BASKET = [264, 271, 274, 277, 308, 311]
SEAGRASS_BASKET = [279, 286, 312, 318]
RATTAN_TRAY = [272, 283, 298, 303, 305, 314]
SPUN_BOWL = [270, 282, 287, 295, 296, 299, 313]
HANOIA_BOX = [22, 61, 64, 70, 71, 75, 79, 80, 81, 89, 91, 93, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105,
              110, 111, 114, 115]
SILK_SCARF = [33, 34, 35, 53, 54, 59] + list(range(234, 264))
AO_DAI = [44, 45, 46, 47, 48, 49, 50, 51, 52, 56]
KM109 = [24, 25, 26, 27, 28, 29]
CERAMIC = [0, 1, 2, 3, 4, 5] + list(range(174, 234))
SENSILK = list(range(234, 264))

P1 = "P1: chất liệu sứ theo thương hiệu gốm sứ, sản phẩm chưa ghi"


def many(ids, score, reason):
    return {i: (score, reason) for i in ids}


def Q(note, scores, full=False):
    return {"note": note, "scores": scores, "full": full}


S = {}

# ---------- dev: bát đĩa, chén ----------
S["kw-dev-001"] = Q("Cần chén cơm, sứ, màu trắng.", {
    0: (3, "chén cơm sứ, màu trắng (vân xanh)"),
    212: (1, "chén cơm nhưng màu và chất liệu chưa ghi (P2)"),
    5: (1, "dĩa sứ trắng ngà, không phải chén"),
    215: (1, "dĩa lót chén, không phải chén")})
S["kw-dev-002"] = Q("Không dấu của 'chén cơm sứ trắng'; chấm như kw-dev-001.", {
    0: (3, "chén cơm sứ, màu trắng"),
    212: (1, "chén cơm nhưng màu và chất liệu chưa ghi (P2)"),
    5: (1, "dĩa sứ trắng ngà, không phải chén"),
    215: (1, "dĩa lót chén, không phải chén")})
S["kw-dev-003"] = Q("Bát = chén (từ địa phương); cần bát ăn cơm bằng sứ.", {
    0: (3, "chén cơm sứ"),
    212: (2, "chén cơm Jasmine; " + P1),
    201: (1, "bộ đồ ăn 9 món, chưa ghi có bát; chất liệu chưa ghi"),
    198: (1, "dĩa sâu lòng, không phải bát"),
    5: (1, "dĩa sứ, không phải bát"),
    215: (1, "dĩa lót chén")})
S["kw-dev-004"] = Q("Cần dĩa, sứ, trắng ngà.", {
    5: (3, "dĩa sứ trắng ngà"),
    205: (2, "dĩa lót Trắng Ngà; " + P1),
    208: (2, "dĩa tròn Trắng Ngà; " + P1),
    216: (2, "dĩa ăn sáng Trắng Ngà; " + P1),
    201: (1, "bộ đồ ăn trắng ngà, không phải dĩa riêng"),
    **many([202, 203, 204, 206, 207], 1, "dòng Tulip Ngà nhưng màu khác trắng ngà")})
S["kw-dev-005"] = Q("Cần đĩa tròn đường kính 15 cm.", {
    5: (3, "dĩa tròn 15 cm"),
    215: (2, "dĩa 15 cm, không ghi dáng tròn"),
    **many([202, 203, 204, 205, 206, 207], 1, "dĩa lót 15,5 cm, không ghi tròn (ngoài pool)"),
    199: (1, "dĩa tròn nhưng 20 cm"), 217: (1, "dĩa tròn nhưng 18 cm"), 208: (1, "dĩa tròn nhưng 22 cm")})
S["kw-dev-006"] = Q("Không dấu 'dĩa tròn jasmine': dĩa tròn dòng Jasmine.", {
    5: (3, "dĩa tròn Jasmine Lys"), 217: (3, "dĩa tròn Jasmine"),
    214: (2, "dĩa súp Jasmine"), 215: (2, "dĩa lót chén Jasmine"), 213: (2, "dĩa lót tách Jasmine"),
    212: (1, "chén Jasmine, không phải dĩa"), 0: (1, "chén cơm Jasmine Thạch Vân, không phải dĩa"),
    199: (1, "dĩa tròn dòng Camellia"), 208: (1, "dĩa tròn dòng Tulip")})

# ---------- bình hoa ----------
S["kw-dev-007"] = Q("Cần bình hoa họa tiết sen vàng.", {
    **many([2, 185, 186, 187, 188, 189], 3, "bình hoa Sen Vàng"),
    **many([180, 184, 192, 181, 193, 218, 219, 228, 194, 195], 1, "bình hoa sen nhưng không ghi sen vàng (P2)")})
S["kw-dev-008"] = Q("Cần bình hoa men xanh cobalt.", {
    2: (3, "màu xanh cobalt"), 219: (3, "Hoa Sen nền cobalt"),
    197: (2, "Hoa tây cobalt; màu chưa ghi trong trường màu"), 230: (2, "Anh Túc cobalt; màu chưa ghi"),
    188: (1, "nền xanh ngọc, không phải cobalt"),
    **many([1, 179, 180, 182], 1, "bình hoa nhưng không có căn cứ men cobalt (P2)")})
S["kw-dev-009"] = Q("Sản phẩm cụ thể: bình hoa Hồn Việt 30 cm.", {
    1: (3, "đúng sản phẩm"), 60: (1, "bình hoa khác (P4)"), 67: (1, "bình hoa khác (P4)")})
S["kw-dev-039"] = Q("Sản phẩm cụ thể: bình hoa Mystery của Hanoia.", {
    20: (3, "đúng sản phẩm"), **many([21, 65, 66, 67, 68, 78, 108], 1, "bình hoa Hanoia khác (P4)")})
S["kw-dev-040"] = Q("Cần bình (hoa) chất liệu resin, màu đỏ rượu.", {
    21: (3, "resin, có màu đỏ rượu"),
    **many([66, 67, 68], 2, "resin, có màu đỏ (không ghi đỏ rượu)"),
    **many([72, 73, 74], 2, "resin, có màu đỏ (ngoài pool)"),
    20: (1, "resin nhưng màu đen"), 78: (1, "resin nhưng màu đen (ngoài pool)"),
    **many([60, 62, 63], 1, "màu đỏ nhưng vật liệu tổng hợp, không ghi resin (ngoài pool)")})
S["kw-dev-041"] = Q("Không dấu 'bình hoa Vita': sản phẩm cụ thể.", {
    21: (3, "đúng sản phẩm"),
    **many([1, 2, 20, 175, 179, 180, 182, 185, 186, 220], 1, "bình hoa khác (P4)")})

# ---------- bộ trà, ly ----------
S["kw-dev-010"] = Q("Cần bộ ấm chén pha trà.", {**many(TEA, 3, "bộ trà (ấm + chén)")})
S["kw-dev-011"] = Q("Không dấu 'bộ trà sứ chỉ vàng'.", {
    3: (3, "bộ trà sứ viền chỉ vàng"), 210: (2, "bộ trà Chỉ Vàng; " + P1),
    174: (1, "bộ trà sứ, không chỉ vàng"), 176: (1, "bộ trà sứ, không chỉ vàng"),
    **many([177, 178, 200, 209, 211], 1, "bộ trà, không ghi chỉ vàng")})
S["kw-dev-012"] = Q("Cần ấm trà sứ dung tích 0,5 L.", {
    3: (3, "bộ trà sứ, ấm 0,5 L"), 174: (3, "bộ trà sứ 0,5 L"), 200: (2, "bộ trà 0,5 L; " + P1),
    **many([176, 209], 1, "bộ trà 0,8 L"), **many([177, 178], 1, "bộ trà 0,65 L"),
    210: (1, "bộ trà 1,2 L"), 211: (1, "bộ trà 0,8 L")})
S["kw-dev-075"] = Q("'set uống trà' = bộ trà.", {**many(TEA, 3, "bộ trà"), 104: (1, "hộp đựng trà, không phải bộ uống trà")})
S["kw-dev-077"] = Q("Bộ trà giá dưới 1.000.000đ (P3).", {
    3: (3, "bộ trà 874k"), 174: (3, "bộ trà 989k"),
    **many([176, 177, 178, 200, 209, 210, 211], 0, "bộ trà nhưng giá trên 1 triệu")})
S["kw-dev-013"] = Q("Cần cốc sứ có ống hút.", {4: (3, "ly sứ có nắp kèm lỗ ống hút")})
S["kw-dev-014"] = Q("Sản phẩm cụ thể: ly sứ dưỡng sinh.", {4: (3, "đúng sản phẩm")})
S["kw-dev-015"] = Q("Tách = cốc/ly; cần ly uống nước có nắp.", {4: (3, "ly sứ có nắp")})

# ---------- giỏ, khay, đèn, túi (mây tre) ----------
S["kw-dev-016"] = Q("Sản phẩm cụ thể: giỏ tre tròn viền gỗ.", {
    6: (3, "giỏ tre tròn viền gỗ"),
    **many([300, 315, 121, 122, 88], 1, "giỏ tre khác, không viền gỗ (ngoài pool, P4)")})
S["kw-dev-017"] = Q("Không dấu 'giỏ tre đan'.", {
    **many([6, 88, 121, 122, 300, 315], 3, "giỏ đan bằng tre"),
    23: (1, "hộp đan tre, không phải giỏ"), 87: (1, "hộp đan tre, không phải giỏ"),
    10: (1, "giỏ đan nhưng seagrass"), 276: (1, "giỏ đan, chất liệu chưa ghi")})
S["kw-dev-018"] = Q("Oval = bầu dục; cần giỏ mây hình bầu dục.", {
    9: (3, "giỏ mây bầu dục"),
    **many([264, 274, 277, 308, 311], 1, "giỏ mây, hình dáng chưa ghi (P2)"),
    271: (0, "giỏ mây tròn (alias Round), không phải bầu dục")})
S["kw-dev-019"] = Q("Cần giỏ mây bầu dục.", {
    9: (3, "giỏ mây bầu dục"),
    **many([264, 274, 277, 308, 311], 1, "giỏ mây, hình dáng chưa ghi (P2)"),
    271: (0, "giỏ mây tròn")})
S["kw-dev-020"] = Q("Cỏ biển = seagrass; cần giỏ seagrass.", {
    10: (3, "giỏ seagrass"), **many(SEAGRASS_BASKET, 3, "giỏ seagrass (ngoài pool)"),
    **many(RATTAN_BASKET, 1, "giỏ đan nhưng bằng mây"), 276: (1, "giỏ đan (wicker), chất liệu chưa rõ"),
    306: (1, "giỏ macrame, không phải seagrass")})
S["kw-dev-021"] = Q("Giỏ seagrass dùng đựng đồ.", {
    10: (3, "giỏ seagrass đựng đồ"),
    **many([286, 312, 318], 3, "giỏ seagrass, alias Storage Basket"),
    279: (2, "giỏ seagrass (belly basket cho trẻ)"),
    9: (1, "giỏ mây"), 276: (1, "giỏ đựng đồ, chất liệu chưa rõ"), 306: (1, "giỏ macrame")})
S["kw-dev-022"] = Q("Cần chụp đèn đan bằng mây hoặc tre.", {
    **many([268, 269, 278, 284, 285, 289, 297, 302, 309], 3, "chụp đèn đan tre/mây"),
    7: (2, "chụp đèn đan nhưng seagrass"), 275: (1, "chụp đèn wicker, chất liệu chưa rõ")})
S["kw-dev-023"] = Q("Đèn thả trần (pendant) đan cói. Seagrass thường gọi là cói biển — người chấm quyết định.", {
    7: (2, "chụp đèn treo đan seagrass (cói biển?)"),
    **many([268, 278, 284, 285, 289, 297, 302, 309], 1, "đèn thả đan tre/mây, không phải cói"),
    269: (1, "chụp đèn mây, không ghi treo"), 275: (1, "chụp đèn wicker, chất liệu chưa rõ")})
S["kw-dev-024"] = Q("Code-switch: chụp đèn seagrass.", {
    7: (3, "chụp đèn seagrass"), **many([268, 269, 275, 278, 284, 285, 289, 297, 302, 309], 1,
                                         "chụp đèn đan nhưng không phải seagrass (ngoài pool)")})
S["kw-dev-094"] = Q("Lỗi gõ 'chụp đèn đan'.", {
    7: (3, "chụp đèn đan"), **many(PENDANT, 3, "chụp đèn đan")})
S["kw-dev-025"] = Q("Sản phẩm cụ thể: túi lục bình đính vỏ sò.", {8: (3, "đúng sản phẩm"), 292: (1, "giỏ lục bình, không phải túi")})
S["kw-dev-026"] = Q("Không dấu 'túi lục bình'.", {8: (3, "túi lục bình"), 292: (1, "giỏ lục bình, không phải túi")})
S["kw-dev-027"] = Q("Túi xách đan tay dùng đi biển; 'đi biển' không có trong catalog (P2).", {
    8: (2, "túi xách đan tay lục bình; công dụng đi biển chưa ghi")})
S["kw-dev-028"] = Q("Cần khay đan bằng mây.", {
    11: (3, "khay mây"), **many(RATTAN_TRAY, 3, "khay mây"),
    294: (1, "đĩa mây (charger plate), không phải khay (ngoài pool)"),
    301: (1, "khay tre, không phải mây (ngoài pool)"), **many([9, 274, 277], 1, "giỏ mây, không phải khay")})
S["kw-dev-029"] = Q("Khay đựng đồ bằng mây.", {
    11: (3, "khay mây bày đồ/phục vụ"), **many(RATTAN_TRAY, 2, "khay mây, công dụng chưa ghi rõ"),
    294: (1, "đĩa mây"), **many([9, 274, 277], 1, "giỏ mây, không phải khay")})
S["kw-dev-090"] = Q("Khay đan không có nhựa: khay từ vật liệu tự nhiên được ghi rõ.", {
    11: (3, "khay mây"), **many(RATTAN_TRAY, 3, "khay mây (ngoài pool trừ 272)"), 301: (3, "khay tre (ngoài pool)"),
    294: (1, "đĩa mây"), **many([6, 9, 10, 264, 271, 274, 277], 1, "giỏ đan, không phải khay"),
    276: (1, "giỏ đan, chất liệu chưa rõ"), 306: (1, "giỏ macrame")})
S["kw-dev-085"] = Q("Giỏ đan không phải mây.", {
    10: (3, "giỏ seagrass"), **many(SEAGRASS_BASKET, 3, "giỏ seagrass"), 292: (3, "giỏ lục bình"),
    **many([121, 300, 315], 3, "giỏ tre"), 276: (1, "giỏ wicker, chất liệu chưa rõ"), 306: (1, "giỏ macrame, chất liệu chưa ghi"),
    **many(RATTAN_BASKET, 0, "giỏ mây — bị loại trừ")})
S["kw-dev-092"] = Q("Lỗi gõ 'giỏ mây đan'.", {
    9: (3, "giỏ mây"), **many(RATTAN_BASKET, 3, "giỏ mây"), 10: (1, "giỏ seagrass"), 122: (1, "giỏ tre"),
    276: (1, "giỏ đan, chất liệu chưa rõ"), 11: (1, "khay mây, không phải giỏ")})
S["kw-dev-071"] = Q("Đồ đựng trái cây.", {
    9: (3, "mô tả: dùng đựng trái cây"), 280: (3, "alias Oval Fruit Bowl (ngoài pool)"),
    296: (3, "alias Spun Bamboo Fruit Bowl (ngoài pool)"), 277: (1, "giỏ đựng bánh mì"),
    306: (1, "giỏ đựng đồ"), 11: (1, "khay bày đồ (ngoài pool)"), 294: (1, "đĩa mây (ngoài pool)")})

# ---------- gáo dừa, tre cuộn ----------
S["kw-dev-030"] = Q("Sản phẩm cụ thể: bát gáo dừa.", {12: (3, "bát gáo dừa")})
S["kw-dev-031"] = Q("Không dấu 'bát gáo dừa sơn vẽ tay'.", {12: (3, "đúng sản phẩm"), 13: (1, "bát tre phủ sơn (ngoài pool)")})
S["kw-dev-032"] = Q("Chén = bát (địa phương); chén gáo dừa vẽ tay.", {12: (3, "bát gáo dừa vẽ tay")})
S["kw-dev-033"] = Q("Bát tre cuộn (spun bamboo) phủ sơn mài.", {
    13: (3, "bát tre cuộn phủ sơn (lacquer)"), 12: (1, "bát phủ sơn nhưng gáo dừa"),
    **many(SPUN_BOWL, 1, "bát tre cuộn (alias Spun Bamboo), không ghi sơn mài (P2)"),
    280: (1, "bát tre, không ghi cuộn hay sơn")})
S["kw-dev-034"] = Q("Tô = bát; tô tre cuộn.", {
    13: (3, "bát tre cuộn"), **many(SPUN_BOWL, 3, "bát tre cuộn (alias Spun Bamboo, ngoài pool)"),
    280: (1, "bát tre, không ghi cuộn (ngoài pool)")})

# ---------- Hanoia ----------
S["kw-dev-035"] = Q("Hộp sơn mài của Hanoia; sơn mài theo danh mục/thương hiệu, từng sản phẩm không ghi kỹ thuật.", {
    **many(HANOIA_BOX, 2, "hộp Hanoia (danh mục sơn mài)"),
    23: (1, "hộp Hanoia nhưng đan tre"), 87: (1, "hộp Hanoia đan tre"), 117: (1, "khay, không phải hộp"),
    60: (1, "bình Hanoia, không phải hộp")})
S["kw-dev-036"] = Q("Sản phẩm cụ thể: hộp vuông Botanica (size S/M).", {
    22: (3, "hộp vuông Botanica S"), 80: (3, "hộp vuông Botanica M"), 79: (2, "hộp trang sức Botanica"),
    **many([91, 97, 98, 105, 110, 111], 1, "hộp vuông dòng khác (P4)"), 78: (1, "bình Botanica (ngoài pool)")})
S["kw-dev-037"] = Q("Sản phẩm cụ thể: hộp đan tre Ethnic.", {
    23: (3, "hộp đan tre Ethnic S"), 87: (3, "hộp đan tre Ethnic M"),
    **many([88, 121, 122], 1, "giỏ Ethnic, không phải hộp"), **many([267, 281, 304], 1, "hộp tre khác (P4)")})
S["kw-dev-038"] = Q("Không dấu 'hộp tre bọc đồng'.", {
    23: (3, "hộp tre, nắp/đáy đồng"), 87: (3, "hộp tre và đồng"),
    **many([88, 121, 122], 1, "giỏ tre có đồng, không phải hộp"), **many([267, 281, 304], 1, "hộp tre, không có đồng")})

# ---------- sô cô la ----------
CHOC_POOL_042 = [18, 145, 147, 148, 149, 154, 159]
S["kw-dev-042"] = Q("Sô cô la Tiền Giang 70%.", {
    15: (3, "Tiền Giang 70% thanh"), 140: (3, "Tien Giang 70% Napolitain"),
    134: (1, "Tiền Giang nhưng 80%"), 17: (1, "Tiền Giang 68% vị quất"), 139: (1, "70% nhưng Đắk Lắk"),
    **many(CHOC_POOL_042, 1, "sô cô la Marou khác (P4)")})
S["kw-dev-043"] = Q("Sô cô la Lâm Đồng.", {16: (3, "Lâm Đồng 74%"), 141: (3, "Lam Dong 74% Napolitain"),
                                          152: (1, "sô cô la khác"), 326: (1, "set mini, không ghi Lâm Đồng")})
S["kw-dev-044"] = Q("Sô cô la đen Bà Rịa.", {19: (3, "Bà Rịa 76%"), 137: (3, "Ba Ria 76% Napolitain")})
S["kw-dev-045"] = Q("Sô cô la 100% cacao.", {
    18: (3, "100%"), **many([14, 15, 16, 19, 124, 161, 162, 163, 171], 1, "sô cô la nhưng không phải 100%")})
S["kw-dev-046"] = Q("Không dấu 'sô cô la vị quất'.", {17: (3, "vị quất"), **many([18, 163, 328], 1, "sô cô la, không vị quất")})
S["kw-dev-047"] = Q("Sô cô la vị quất Mekong.", {
    17: (3, "quất Mekong"), **many([18, 127, 132, 135, 145, 147, 148, 149, 152, 153], 1, "sô cô la, không vị quất")})
S["kw-dev-048"] = Q("Sô cô la Marou thanh 80 g.", {
    **many([126, 127, 128, 129, 130, 131], 3, "thanh 80G"),
    **many([14, 15, 16, 17, 19, 124, 152, 159], 3, "thanh 80 g (ngoài pool)"),
    132: (2, "set 6 thanh 80G"), 125: (2, "set 6 thanh 80G (ngoài pool)"),
    134: (1, "khối lượng chưa ghi"), **many([145, 148, 149], 1, "thanh 35G")})
S["kw-dev-049"] = Q("Thương hiệu Marou (pool đủ để có đáp án).", {
    **many([135, 143, 146, 150, 151, 159, 160, 164, 165, 173, 326, 329], 3, "sản phẩm Marou")})
S["kw-dev-050"] = Q("Maison Marou: dòng Exclusive; sản phẩm Marou khác coi là cùng thương hiệu.", {
    **many([125, 126, 127, 128, 129, 130, 131], 3, "Maison Marou Exclusive"),
    **many([148, 164], 2, "Marou, không thuộc dòng Maison")})
S["kw-dev-064"] = Q("Sô cô la từ cacao Việt Nam (claim vn_material).", {
    **many([14, 15, 16, 17, 18, 19], 3, "mô tả ghi rõ vùng cacao Việt Nam"),
    **many([148, 149, 321], 2, "Marou có claim vn_material")})
S["kw-dev-076"] = Q("Sô cô la dưới 150.000đ (P3).", {
    **many([14, 15, 16, 19], 3, "140k"),
    **many([142, 143, 144, 146, 150, 153, 172, 173, 328, 329], 3, "dưới 150k (ngoài pool)"),
    **many([17, 18, 161, 162, 163, 169, 170, 171, 132], 0, "vượt 150k")})
S["kw-dev-083"] = Q("Sô cô la giá 140.000đ.", {
    **many([14, 15, 16, 19, 173], 3, "giá 140k"), 152: (1, "155k, gần mức giá")})
S["kw-dev-086"] = Q("Sô cô la không có quất.", {
    **many([14, 16, 18, 19], 3, "single origin, không quất"),
    **many([159, 161, 162, 163, 169, 170, 171], 2, "không có quất theo tên; thành phần đầy đủ chưa ghi"),
    132: (1, "set 6 thanh, có thể gồm thanh quất"), 17: (0, "có quất — bị loại trừ")})
S["kw-dev-093"] = Q("Lỗi gõ 'sô cô la đen'.", {
    **many([14, 15, 16, 17, 18, 19], 3, "sô cô la đen"), 147: (2, "Ironbar 65% dark, hộp 16 thanh"),
    **many([145, 148, 149], 1, "hộp thanh hỗn hợp, không chỉ sô cô la đen")})

# ---------- thời trang ----------
S["kw-dev-051"] = Q("Áo khoác vải gai dầu.", {24: (3, "áo khoác gai dầu"), 28: (3, "áo khoác gai dầu"), 42: (1, "áo khoác đũi tơ tằm")})
S["kw-dev-052"] = Q("Hemp = gai dầu.", {24: (3, "áo khoác gai dầu"), 28: (3, "áo khoác gai dầu"), 42: (1, "áo khoác đũi tơ tằm")})
S["kw-dev-053"] = Q("Không dấu 'áo khoác nhuộm chàm'.", {
    24: (3, "áo khoác nhuộm chàm"), 28: (3, "áo khoác nhuộm chàm"), 42: (1, "áo khoác, không nhuộm chàm"),
    27: (1, "nhuộm chàm nhưng chân váy"), 25: (1, "áo sơ mi nhuộm tự nhiên, không phải áo khoác")})
S["kw-dev-095"] = Q("Lỗi gõ 'áo khoác chàm'.", {24: (3, "áo khoác chàm"), 28: (3, "áo khoác chàm"),
                                              42: (1, "áo khoác, không chàm"), 27: (1, "chân váy chàm")})
S["kw-dev-054"] = Q("Áo sơ mi cotton nhuộm tự nhiên.", {25: (3, "đúng sản phẩm"), 40: (1, "áo sơ mi lụa")})
S["kw-dev-055"] = Q("Sơ mi batik.", {25: (3, "sơ mi sọc batik"), 27: (1, "batik nhưng chân váy"), 40: (1, "sơ mi lụa, không batik")})
S["kw-dev-056"] = Q("Chân váy batik nhuộm chàm.", {27: (3, "đúng sản phẩm"), 26: (1, "váy dài nhuộm chàm, không batik (ngoài pool)")})
S["kw-dev-057"] = Q("Váy lụa dài.", {
    26: (3, "váy dài lụa"), 37: (3, "váy lụa tơ tằm dài"), 43: (2, "váy lụa, độ dài chưa ghi"),
    41: (1, "jumpsuit lụa"), **many([45, 48, 49, 50, 51, 52], 1, "áo dài lụa, không phải váy"),
    39: (1, "áo váy, chất liệu chưa ghi (ngoài pool)")})
S["kw-dev-058"] = Q("Đầm lụa màu đen.", {26: (3, "váy lụa bản đen"), **many([37, 43], 1, "váy lụa, màu chưa ghi (ngoài pool)")})
S["kw-dev-059"] = Q("Vòng cổ bằng vải.", {29: (3, "vòng cổ vải"), 55: (1, "set có vòng lụa, chưa rõ loại vòng (ngoài pool)")})
S["kw-dev-060"] = Q("Trang sức vải thủ công; pool không có đáp án.", {
    29: (3, "vòng cổ vải thủ công (ngoài pool)"), 55: (1, "set có vòng lụa (ngoài pool)")})
S["kw-dev-061"] = Q("Thương hiệu Kilomet109.", {**many(KM109, 3, "sản phẩm Kilomet109")})
S["kw-dev-062"] = Q("km109 = Kilomet109; pool không chứa sản phẩm nào của hãng.", {**many(KM109, 3, "sản phẩm Kilomet109 (ngoài pool)")})
S["kw-dev-074"] = Q("Quần áo nhuộm thực vật; chàm/quả mun là thuốc nhuộm thực vật nhưng catalog không ghi 'thực vật'.", {
    25: (3, "nhuộm tự nhiên"), 24: (2, "nhuộm chàm"), 28: (2, "nhuộm chàm"), 27: (2, "nhuộm chàm"),
    26: (2, "nhuộm quả mun/chàm (ngoài pool)")})
S["kw-dev-088"] = Q("Áo không nhuộm chàm; phần lớn không ghi cách nhuộm.", {
    25: (2, "áo sơ mi nhuộm tự nhiên, không ghi chàm"), 36: (2, "áo lụa"), 42: (2, "áo khoác đũi"), 39: (2, "áo váy"),
    **many([45, 46, 47, 48, 51, 52, 56], 2, "áo dài lụa, không nhuộm chàm theo dữ liệu"),
    **many([24, 28], 0, "nhuộm chàm — bị loại trừ"), 27: (0, "chân váy nhuộm chàm")})

# ---------- nguồn gốc / nhu cầu ----------
S["kw-dev-063"] = Q("Đồ sứ Bình Dương: catalog chỉ ghi Hanoia ra đời ở Bình Dương (không phải đồ sứ); "
                   "sứ Minh Long không có căn cứ nơi sản xuất.", {
    **many(CERAMIC, 1, "đồ sứ, không có căn cứ Bình Dương (P2)")}, full=True)
S["kw-dev-065"] = Q("Đồ mây tre đan có claim sản xuất tại Việt Nam.", {
    6: (3, "giỏ tre, made_in_vn"), 11: (3, "khay mây, made_in_vn"),
    **many([264, 271, 274, 277, 297, 308, 311], 3, "mây tre, made_in_vn"),
    9: (1, "giỏ mây, chưa có claim xuất xứ"), 23: (1, "hộp tre Hanoia, made_in_vn chưa xác minh")})
S["kw-dev-066"] = Q("Đồ thủ công truyền thống (claim traditional_craft).", {
    20: (2, "claim traditional_craft"), **many([12, 24, 28], 2, "claim traditional_craft (ngoài pool)"),
    39: (1, "chỉ có claim vn_material"), 10: (1, "đan tay nhưng không có claim truyền thống"),
    25: (1, "không có claim truyền thống"), 317: (1, "đan tay, không có claim truyền thống")})
S["kw-dev-067"] = Q("Quà tặng mẹ, làm thủ công (vẽ tay).", {
    247: (3, "khăn vẽ tay, 'Quà tặng mẹ'"),
    **many([250, 252, 260, 261], 2, "khăn vẽ tay ghi quà tặng"),
    **many([238, 240, 241, 242], 1, "quà tặng nhưng in 3D, không thủ công"), 55: (1, "set quà tặng, thủ công chưa ghi")})
S["kw-dev-068"] = Q("Quà tặng đối tác, sang trọng.", {
    240: (3, "'Quà tặng đối tác'"), 242: (2, "'Quà tặng doanh nghiệp'"), 241: (2, "'Quà tặng sự kiện'"),
    **many([238, 261], 2, "quà tặng cao cấp"), 258: (2, "quà tặng 'kiệt tác lụa Việt'"), 252: (2, "quà tặng vẽ tay"),
    **many([250, 247, 55, 98, 322], 1, "quà tặng nhưng không ghi đối tác/sang trọng")})
S["kw-dev-069"] = Q("Đồ trang trí phòng khách; 'phòng khách' không có trong catalog.", {
    **many([20, 21, 65, 74, 183, 184], 2, "bình hoa trang trí"),
    **many([265, 266, 290, 291, 316], 2, "đồ trang trí mây tre"), 104: (1, "hộp trà")})
S["kw-dev-070"] = Q("Quà Tết cho sếp; không sản phẩm nào ghi Tết.", {
    **many([238, 240, 242, 261], 2, "quà tặng cao cấp/đối tác/doanh nghiệp, không ghi Tết"),
    **many([239, 241, 247, 250, 252, 260, 55, 98, 113], 1, "quà tặng chung")})
S["kw-dev-072"] = Q("Quà lưu niệm Việt Nam cho người nước ngoài.", {
    **many([250, 254, 259, 258], 2, "khăn lụa ghi quà tặng/đặc trưng Việt Nam"),
    167: (2, "hộp quà '6 Flavors of Vietnam'"),
    **many([34, 55, 1, 266], 1, "có thể làm quà, không ghi lưu niệm")})
S["kw-dev-073"] = Q("Đồ dùng bàn ăn.", {
    201: (3, "bộ đồ ăn"), 216: (3, "dĩa ăn sáng"), 288: (2, "lồng bàn tre"), 283: (1, "khay mây phục vụ")})
S["kw-dev-089"] = Q("Đồ sứ không phải màu trắng.", {
    2: (2, "bình xanh cobalt, vàng; " + P1 + " (ngoài pool)"),
    **many([187, 188], 2, "bình nền vàng/xanh ngọc; " + P1 + " (ngoài pool)"),
    **many([203, 204, 207], 2, "dĩa lót màu cam/vàng/xanh non; " + P1 + " (ngoài pool)"),
    0: (1, "có màu trắng (vân xanh)"), **many([3, 4, 174, 176], 1, "đồ sứ, màu chưa ghi"),
    5: (0, "trắng ngà — bị loại trừ")})

# ---------- giá ----------
S["kw-dev-078"] = Q("Bình hoa giá 2–5 triệu (P3).", {
    **many([1, 2, 21, 187, 188], 3, "giá trong khoảng 2–5 triệu"),
    **many([20, 175, 179, 180, 181, 182, 185, 186], 0, "giá trên 5 triệu")})
S["kw-dev-079"] = Q("Chén/dĩa dưới 100.000đ (P3).", {
    **many([0, 5, 202, 205, 212, 213, 214, 215, 217], 3, "chén/dĩa dưới 100k"),
    **many([199, 203, 204, 207], 0, "trên 100k")})
S["kw-dev-080"] = Q("Đồ sứ giá khoảng 300.000đ.", {
    4: (3, "ly sứ 333k"), 199: (2, "dĩa 252k; " + P1 + " (ngoài pool)"),
    0: (0, "63k, xa mức giá"), 3: (0, "874k, xa mức giá")})
S["kw-dev-081"] = Q("Quà tặng dưới 500.000đ; pool không có đáp án.", {
    148: (3, "Gift Box 345k (ngoài pool)"), 322: (3, "gift box 485k (ngoài pool)"), 325: (3, "gift box 480k (ngoài pool)"),
    154: (2, "set quà Trung thu 498k (ngoài pool)"), 164: (1, "set 220k, không ghi quà tặng"),
    **many([238, 240, 241, 242, 55], 0, "quà tặng nhưng vượt 500k")})
S["kw-dev-082"] = Q("Không dấu 'bình hoa trên 10 triệu' (P3).", {
    **many([20, 175, 179, 180, 181, 182, 184, 185, 186, 190], 3, "bình hoa trên 10 triệu"),
    **many([1, 2], 0, "dưới 10 triệu")})
S["kw-dev-084"] = Q("Hộp trang trí dưới 1 triệu (P3).", {
    23: (3, "hộp đan tre 950k"), **many([267, 281, 304], 1, "hộp tre chưa có giá (ngoài pool)"),
    **many([71, 79, 81, 89, 96], 0, "hộp trên 1 triệu")})

# ---------- phủ định, lỗi gõ ----------
S["kw-dev-087"] = Q("Bình hoa không làm bằng resin.", {
    **many([1, 2, 175, 179, 180, 181, 182, 184, 185, 186, 193], 2, "bình Minh Long, không ghi resin; " + P1),
    69: (1, "vật liệu polymer, không ghi resin"), 20: (0, "resin — bị loại trừ")})
S["kw-dev-091"] = Q("Lỗi gõ 'bình hoa'.", {**many([1, 179, 182, 184, 190, 191, 192, 197, 223, 225, 231], 3, "bình hoa")})

# ---------- không có đáp án (đã rà toàn catalog) ----------
S["kw-dev-096"] = Q("Nước mắm Phú Quốc: catalog không có thực phẩm này.", {}, full=True)
S["kw-dev-097"] = Q("Nón lá Huế: không có nón.", {}, full=True)
S["kw-dev-098"] = Q("Khăn lụa Vạn Phúc: có khăn lụa nhưng không sản phẩm nào ghi Vạn Phúc.", {
    **many(SILK_SCARF, 1, "khăn lụa, không có căn cứ Vạn Phúc (P2)"), 55: (1, "set khăn, không có căn cứ Vạn Phúc")}, full=True)
S["kw-dev-099"] = Q("Cà phê Buôn Ma Thuột: không có cà phê.", {
    **many([152, 153, 163], 1, "sô cô la vị cà phê sữa, không phải cà phê")}, full=True)
S["kw-dev-100"] = Q("Gốm Bát Tràng: không sản phẩm nào ghi Bát Tràng.", {
    **many(CERAMIC, 1, "gốm sứ, không có căn cứ Bát Tràng"),
    **many([310, 314, 319], 1, "có gốm, không có căn cứ Bát Tràng")}, full=True)
S["kw-dev-101"] = Q("Tranh sơn mài: không có tranh.", {
    20: (1, "bình nền sơn mài hình chim công, không phải tranh"),
    **many([109, 113], 1, "khung ảnh, không phải tranh")}, full=True)
S["kw-dev-102"] = Q("Bàn ghế mây: có bàn mây (nhãn nháp cũ 'không có đáp án' không còn đúng).", {
    293: (2, "bàn mây (alias Rattan Ball Coffee Table), không có ghế"),
    310: (1, "tên 'Bàn mây, gốm' nhưng alias là Plate — dữ liệu catalog có thể dịch sai, cần nhóm dữ liệu kiểm tra")}, full=True)
S["kw-dev-103"] = Q("Sản phẩm đang giảm giá: 30 khăn SenSilk có giá gốc cao hơn giá bán "
                   "(nhãn nháp cũ 'không có đáp án' không còn đúng).", {
    **many(SENSILK, 3, "có original_price_vnd cao hơn giá bán")}, full=True)
S["kw-dev-104"] = Q("Ốp lưng điện thoại: không có.", {**many([82, 83], 1, "giá đỡ điện thoại, không phải ốp lưng")}, full=True)
S["kw-dev-105"] = Q("Gạo ST25: không có.", {}, full=True)
S["kw-dev-106"] = Q("Áo dài cưới: có áo dài nhưng không sản phẩm nào ghi dùng cho cưới.", {
    **many(AO_DAI, 1, "áo dài, không ghi dùng cho cưới")}, full=True)
S["kw-dev-107"] = Q("Nồi đất kho cá: không có.", {}, full=True)

# ---------- seed 12 ----------
S["kw-seed-001"] = Q("Sô cô la Bến Tre.", {14: (3, "Bến Tre 78%"), 136: (3, "Ben Tre 78% Napolitain")})
S["kw-seed-002"] = Q("Bình hoa dưới 5 triệu (P3).", {
    **many([1, 2, 21, 187, 188], 3, "dưới 5 triệu"), **many([20, 175, 179, 180, 181, 182, 185, 186], 0, "trên 5 triệu")})
S["kw-seed-003"] = Q("Túi lục bình có quai.", {8: (3, "túi lục bình, quai tròn"), 292: (1, "giỏ lục bình")})
S["kw-seed-004"] = Q("Chén cơm sứ.", {0: (3, "chén cơm sứ"), 212: (2, "chén cơm; " + P1), 215: (1, "dĩa lót chén"), 5: (1, "dĩa sứ")})
S["kw-seed-005"] = Q("Không dấu 'đồ sơn mài'.", {
    20: (3, "nền sơn mài"), 12: (2, "phủ sơn lacquer"), 13: (2, "phủ sơn lacquer"),
    **many([64, 71, 82, 83, 120], 2, "Hanoia, danh mục sơn mài")})
S["kw-seed-006"] = Q("Áo nhuộm chàm.", {24: (3, "áo khoác chàm"), 28: (3, "áo khoác chàm"), 27: (1, "chân váy chàm"),
                                       26: (1, "váy chàm (ngoài pool)"), 25: (1, "nhuộm tự nhiên, không ghi chàm")})
S["kw-seed-007"] = Q("Giỏ mây.", {9: (3, "giỏ mây"), **many(RATTAN_BASKET, 3, "giỏ mây"),
                                   **many([283, 298, 303], 1, "khay mây, không phải giỏ")})
S["kw-seed-008"] = Q("Bộ ấm trà.", {**many(TEA, 3, "bộ trà")})
S["kw-seed-009"] = Q("Cốc sứ có nắp.", {4: (3, "ly sứ có nắp")})
S["kw-seed-010"] = Q("Váy lụa.", {26: (3, "váy lụa"), 37: (3, "váy lụa tơ tằm"), 43: (3, "váy sóng lụa tơ tằm"),
                                  39: (1, "áo váy, chất liệu chưa ghi"), 41: (1, "jumpsuit lụa (ngoài pool)"),
                                  **many([49, 50], 1, "áo dài lụa, không phải váy")})
S["kw-seed-011"] = Q("Nồi cơm điện: không có.", {}, full=True)
S["kw-seed-012"] = Q("Giày thể thao: không có.", {}, full=True)


# ---------- bổ sung 11/10 sau catalog seed-006 (chất liệu/màu được điền làm pool đổi) ----------
# Theo product_id; cùng rubric và chính sách P1–P4. Chỉ các cặp mới vào pool.
ML_DISH_WHITE = "dĩa sứ màu trắng/trắng ngà, không phải chén/bát"
EXTRA_BY_ID = {
    "kw-dev-001": {
        "p-minhlong-dia-sup-23-cm-nha-hang-jasmine-trang-1074662795": (1, ML_DISH_WHITE),
        "p-minhlong-bo-do-an-09-san-pham-timeless-ifp-trang-nga-1073043775": (1, "bộ đồ ăn trắng ngà, không ghi có chén"),
        "p-minhlong-dia-tron-22-cm-tulip-ifp-trang-nga-1073434927": (1, ML_DISH_WHITE),
        "p-minhlong-dia-lot-15-5-cm-tulip-nga-trang-nga-1073397147": (1, ML_DISH_WHITE),
        "p-minhlong-dia-tron-18-cm-n-hang-jasmine-trang-1074870370": (1, ML_DISH_WHITE),
        "p-sensilk-handmade-silk-embroidery-scarf-khan-lua-theu-13339": (0, "khăn lụa"),
        "p-sensilk-vietnam-silk-art-khan-lua-ve-tay-cao-cap-ngoc-14289": (0, "khăn lụa")},
    "kw-dev-002": {
        "p-minhlong-dia-sup-23-cm-nha-hang-jasmine-trang-1074662795": (1, ML_DISH_WHITE),
        "p-minhlong-bo-do-an-09-san-pham-timeless-ifp-trang-nga-1073043775": (1, "bộ đồ ăn trắng ngà, không ghi có chén"),
        "p-minhlong-dia-tron-22-cm-tulip-ifp-trang-nga-1073434927": (1, ML_DISH_WHITE),
        "p-minhlong-dia-lot-15-5-cm-tulip-nga-trang-nga-1073397147": (1, ML_DISH_WHITE),
        "p-minhlong-dia-tron-18-cm-n-hang-jasmine-trang-1074870370": (1, ML_DISH_WHITE),
        "p-vietcraft-dia-tre-vh25022-622": (0, "đĩa tre"), "p-vietcraft-guong-trang-tri-may-vh2604-1407": (0, "gương mây"),
        "p-vietcraft-gio-dan-may-vh24062-1076": (0, "giỏ mây")},
    "kw-dev-003": {
        **{pid: (1, "dĩa sứ, không phải bát") for pid in (
            "p-minhlong-dia-lot-15-5-cm-tulip-nga-mau-cam-1073396034", "p-minhlong-dia-lot-15-5-cm-tulip-nga-dau-rung-1073395896",
            "p-minhlong-dia-lot-15-5-cm-tulip-nga-mau-vang-1073396807", "p-minhlong-dia-tron-20-cm-camellia-tu-linh-1072195597")},
        "p-vietcraft-gio-tre-dan-tron-vh24026": (0, "giỏ tre"), "p-vietcraft-vat-trang-tri-may-vh25034-1007": (0, "đồ trang trí mây")},
    "kw-dev-004": {
        "p-minhlong-dia-sup-23-cm-nha-hang-jasmine-trang-1074662795": (1, "dĩa sứ màu trắng, không phải trắng ngà"),
        "p-minhlong-dia-tron-18-cm-n-hang-jasmine-trang-1074870370": (1, "dĩa sứ màu trắng, không phải trắng ngà")},
    "kw-dev-011": {"p-vietcraft-khay-tre-xa-cu-vh25019-189": (0, "khay tre")},
    "kw-dev-044": {pid: (0, "không phải sô cô la Bà Rịa") for pid in (
        "p-vietcraft-bat-gao-dua-son-ve-tay", "p-minhlong-binh-hoa-40-cm-sen-khac-nen-den-1071550827",
        "p-vietcraft-khay-may-gom-vh24105-746", "p-minhlong-bo-tra-0-65-l-daisy-qua-oliu-1071226520",
        "p-vietcraft-bat-tre-vh24041-1257", "p-vietcraft-chup-den-may-vh24072-1050")},
    "kw-dev-045": {
        **{pid: (1, "sô cô la nhưng không phải 100%") for pid in (
            "p-marou-so-co-la-marou-coconut-milk-with-dried-fruit-55-8456113094864",
            "p-marou-so-co-la-marou-popped-rice-with-pho-spice-65-8456113062096",
            "p-marou-so-co-la-marou-marou-bar-65-peanuts-ginger-8249761071312")},
        "p-vietcraft-bat-gao-dua-son-ve-tay": (0, "bát gáo dừa"),
        "p-sensilk-100-mulberry-silk-scarf-khan-lua-ve-tay-hoa-14429": (0, "khăn lụa (100% tơ tằm, không phải cacao)")},
    "kw-dev-046": {"p-hanhsilk-ao-dai-ngu-than-lua-to-tam-3417": (0, "áo dài")},
    "kw-dev-058": {pid: (0, "không phải đầm lụa") for pid in (
        "p-minhlong-chen-com-11-5-cm-jasmine-chi-xanh-duong-1074464445",
        "p-sensilk-khan-lua-qua-tang-to-tam-cao-cap-in-3d-klvi01-13169",
        "p-minhlong-binh-hoa-40-cm-sen-khac-nen-den-1071550827")},
    "kw-dev-064": {
        **{pid: (2, "Marou có claim vn_material") for pid in (
            "p-marou-so-co-la-marou-marou-bar-box-of-16x35g-8249761333456",
            "p-marou-so-co-la-marou-set-of-6-chocolate-napolitain-8249759170768",
            "p-marou-so-co-la-marou-6-flavors-of-vietnam-chocolate-8249799409872",
            "p-marou-so-co-la-marou-ironbar-65-box-of-16x40g-8249764118736")},
        "p-marou-so-co-la-marou-dong-nai-72-single-origin-8249759891664": (3, "tên ghi vùng cacao Đồng Nai"),
        "p-minhlong-dia-lot-15-5-cm-tulip-nga-mau-vang-1073396807": (0, "dĩa sứ")},
    "kw-dev-080": {"p-sensilk-khan-lua-thoi-trang-in-sen-silk-klvi04-qua-tang-13268": (0, "khăn lụa, không phải đồ sứ")},
    "kw-dev-089": {pid: (0, "khăn lụa, không phải đồ sứ") for pid in (
        "p-sensilk-khan-lua-qua-tang-ve-tay-mau-don-sensilk-100-14275",
        "p-sensilk-khan-lua-thoi-trang-in-sen-silk-klvi04-qua-tang-13268")},
    "kw-dev-091": {"p-minhlong-binh-hoa-loc-phat-40-cm-binh-hoa-sen-vang-nen-1071463134": (3, "bình hoa"),
                   "p-minhlong-binh-hoa-sen-vang-27cm": (3, "bình hoa")},
    "kw-dev-093": {pid: (0, "không phải sô cô la") for pid in (
        "p-vietcraft-chup-den-may-vh24072-1050", "p-minhlong-binh-hoa-40-cm-sen-khac-nen-den-1071550827",
        "p-sensilk-khan-lua-viet-nam-ve-tay-hoa-ngoc-lan-qua-tang-14291",
        "p-sensilk-silk-square-printed-scarf-khan-lua-in-sen-thai-13734")},
    "kw-seed-005": {"p-marou-so-co-la-marou-maison-marou-exclusive-bar-8249755173072": (0, "sô cô la"),
                    "p-marou-so-co-la-marou-ironbar-65-dark-chocolate-energy-8249763889360": (0, "sô cô la"),
                    "p-minhlong-binh-hoa-52-cm-rong-do-1074965041": (0, "bình sứ, không phải sơn mài")},
}
