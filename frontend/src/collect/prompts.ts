// Câu mẫu cho phiên thu âm benchmark voice (PLAN.md mục 6.2): tên thương hiệu, địa danh/làng nghề,
// từ thủ công, giá, đơn vị, phủ định, câu tự nhiên, xen tiếng Anh, nhu cầu ngoài catalog.
// Người nói đọc tự nhiên; người duyệt nghe lại và sửa reference_text nếu người nói đọc khác câu mẫu.
// Mỗi split có bộ câu riêng, không trùng nhau (11/10/2026): nếu người nói train đọc đúng câu của test thì
// fine-tune ASR học thuộc văn bản test, và nhãn relevance không gắn được cho cùng câu ở hai split.
// Script nhập/duyệt từ chối một câu (sau chuẩn hóa) xuất hiện ở hai split.
// Sửa/thêm câu ở đây; giữ id cũ ổn định để không lẫn bản ghi giữa các phiên; không chuyển câu sang split khác
// sau khi đã có clip.
export type Split = "train" | "dev" | "test";

export interface Prompt {
  id: string;
  text: string;
  tags: string[];
}

export const PROMPT_SETS: Record<Split, Prompt[]> = {
  train: [
    { id: "tr01", text: "khăn lụa tơ tằm vẽ tay làm quà tặng", tags: ["material", "natural"] },
    { id: "tr02", text: "bình hoa Minh Long vẽ sen màu", tags: ["brand", "craft"] },
    { id: "tr03", text: "sô cô la Marou Tiền Giang bảy mươi phần trăm", tags: ["brand", "place"] },
    { id: "tr04", text: "khay sơn mài Hanoia size lớn", tags: ["brand", "craft", "code_switch"] },
    { id: "tr05", text: "giỏ tre đan tròn viền gỗ", tags: ["material"] },
    { id: "tr06", text: "áo dài lụa dưới năm triệu", tags: ["material", "price"] },
    { id: "tr07", text: "khăn lụa SenSilk không lấy màu đỏ", tags: ["brand", "negation"] },
    { id: "tr08", text: "bộ trà Camellia khoảng một triệu ba", tags: ["price"] },
    { id: "tr09", text: "dĩa sứ trắng hai mươi phân", tags: ["unit"] },
    { id: "tr10", text: "chụp đèn bằng tre treo trần", tags: ["material"] },
    { id: "tr11", text: "hộp đựng trang sức hoa văn Exotic", tags: ["natural"] },
    { id: "tr12", text: "vải đũi tơ tằm để may vest", tags: ["material"] },
    { id: "tr13", text: "sô cô la đen dưới hai trăm nghìn để làm quà", tags: ["price", "natural"] },
    { id: "tr14", text: "gương trang trí khung mây", tags: ["material"] },
    { id: "tr15", text: "khăn quàng cổ lụa in hoa sen", tags: ["craft"] },
    { id: "tr16", text: "túi cói đan tay đi biển", tags: ["material", "natural"] },
    { id: "tr17", text: "bình gốm men rạn Bát Tràng", tags: ["place", "craft"] },
    { id: "tr18", text: "đèn bàn đan seagrass handmade", tags: ["code_switch"] },
    { id: "tr19", text: "khung ảnh sơn mài khảm xà cừ", tags: ["craft", "material"] },
    { id: "tr20", text: "giỏ đựng đồ không phải bằng nhựa", tags: ["negation"] },
    { id: "tr21", text: "áo sơ mi cotton nhuộm tự nhiên của Kilomet một trăm linh chín", tags: ["brand", "material"] },
    { id: "tr22", text: "lọ hoa nhỏ để bàn làm việc từ năm trăm nghìn đến một triệu", tags: ["price", "natural"] },
    { id: "tr23", text: "cà phê Buôn Ma Thuột một ký", tags: ["place", "unit", "out_of_catalog"] },
    { id: "tr24", text: "máy sấy tóc mini", tags: ["out_of_catalog"] },
  ],
  // Bộ câu đầu tiên (10/10/2026), giữ id p01–p24.
  dev: [
    { id: "p01", text: "tìm cho mình cái túi cói dưới ba trăm nghìn", tags: ["price", "natural"] },
    { id: "p02", text: "bình gốm Bát Tràng dưới năm trăm nghìn", tags: ["place", "price"] },
    { id: "p03", text: "giỏ mây đan có quai", tags: ["material"] },
    { id: "p04", text: "giỏ đan không lấy nhựa", tags: ["negation"] },
    { id: "p05", text: "bình hoa Minh Long", tags: ["brand"] },
    { id: "p06", text: "bộ trà sứ Minh Long khoảng một triệu", tags: ["brand", "price"] },
    { id: "p07", text: "sô cô la Marou Bến Tre", tags: ["brand", "place"] },
    { id: "p08", text: "sô cô la đen trên một trăm nghìn", tags: ["price"] },
    { id: "p09", text: "áo khoác nhuộm chàm của Kilomet một trăm linh chín", tags: ["brand", "craft"] },
    { id: "p10", text: "váy lụa nhuộm tự nhiên", tags: ["material", "craft"] },
    { id: "p11", text: "chụp đèn đan seagrass", tags: ["code_switch", "material"] },
    { id: "p12", text: "túi lục bình đan tay đính vỏ sò", tags: ["material", "craft"] },
    { id: "p13", text: "khay mây đan tay để bàn", tags: ["material"] },
    { id: "p14", text: "bát tre cuộn phủ sơn mài", tags: ["material", "craft"] },
    { id: "p15", text: "hộp sơn mài Hanoia", tags: ["brand", "craft"] },
    { id: "p16", text: "chén cơm sứ trắng dưới một trăm nghìn", tags: ["price"] },
    { id: "p17", text: "ly sứ có nắp không lấy màu đỏ", tags: ["negation"] },
    { id: "p18", text: "quà tặng mẹ làm thủ công từ hai trăm đến năm trăm nghìn", tags: ["price", "natural"] },
    { id: "p19", text: "đồ gốm men lam vẽ sen", tags: ["craft"] },
    { id: "p20", text: "một triệu rưỡi mua được bình hoa nào", tags: ["price", "natural"] },
    { id: "p21", text: "vòng cổ vải handmade", tags: ["code_switch"] },
    { id: "p22", text: "trà Thái Nguyên nửa ký", tags: ["place", "unit"] },
    { id: "p23", text: "khăn lụa Vạn Phúc màu xanh", tags: ["place", "material"] },
    { id: "p24", text: "nồi cơm điện giá rẻ", tags: ["out_of_catalog"] },
    // Bổ sung 12/10/2026: câu ứng viên cho nhóm lỗi mới, chưa phải transcript chuẩn.
    { id: "p25", text: "I am looking for a handmade silk scarf", tags: ["english", "natural"] },
    { id: "p26", text: "Marou dark chocolate gift box", tags: ["english", "brand"] },
    { id: "p27", text: "tìm khăn lụa silk scarf màu xanh", tags: ["code_switch", "material"] },
    { id: "p28", text: "bát sứ trắng dùng ăn cơm", tags: ["phrase", "quiet_speech"] },
    { id: "p29", text: "khăn lụa màu nâu làm quà", tags: ["confusion_n_l", "far_mic"] },
  ],
  test: [
    { id: "te01", text: "khăn lụa Hanhsilk thêu hoa sen", tags: ["brand", "craft"] },
    { id: "te02", text: "sô cô la Marou Lâm Đồng", tags: ["brand", "place"] },
    { id: "te03", text: "bình hoa men lam cao bốn mươi phân", tags: ["craft", "unit"] },
    { id: "te04", text: "khay mây hình chữ nhật có tay cầm", tags: ["material"] },
    { id: "te05", text: "bộ ấm chén sứ trên hai triệu", tags: ["price"] },
    { id: "te06", text: "chén ăn cơm không lấy hoa văn", tags: ["negation"] },
    { id: "te07", text: "hộp sơn mài đựng trà làm quà Tết", tags: ["craft", "natural"] },
    { id: "te08", text: "váy lụa tơ tằm dáng dài", tags: ["material"] },
    { id: "te09", text: "giỏ seagrass có nắp đậy", tags: ["code_switch", "material"] },
    { id: "te10", text: "bình hoa Vita của Hanoia", tags: ["brand"] },
    { id: "te11", text: "khăn lụa vẽ tay dưới một triệu rưỡi", tags: ["price"] },
    { id: "te12", text: "ly sứ dưỡng sinh có ống hút", tags: ["natural"] },
    { id: "te13", text: "đĩa sứ Camellia tứ linh", tags: ["craft"] },
    { id: "te14", text: "đèn trần đan mây cho phòng khách", tags: ["material", "natural"] },
    { id: "te15", text: "áo khoác vải gai dầu nhuộm chàm", tags: ["material", "craft"] },
    { id: "te16", text: "sô cô la nhân hạt điều khoảng hai trăm nghìn", tags: ["price"] },
    { id: "te17", text: "rổ tre đan không có quai", tags: ["negation", "material"] },
    { id: "te18", text: "vải lụa Hà Đông may áo dài", tags: ["place", "material"] },
    { id: "te19", text: "set quà chocolate cho đồng nghiệp", tags: ["code_switch", "natural"] },
    { id: "te20", text: "bình hoa Sen Vàng hai mươi bảy phân", tags: ["unit"] },
    { id: "te21", text: "khung ảnh Moonbow cỡ vừa", tags: ["natural"] },
    { id: "te22", text: "khay đá marble trắng", tags: ["material", "code_switch"] },
    { id: "te23", text: "nón lá Huế", tags: ["place", "out_of_catalog"] },
    { id: "te24", text: "tủ lạnh hai cửa tiết kiệm điện", tags: ["out_of_catalog"] },
  ],
};

export const SPLITS: Split[] = ["train", "dev", "test"];

export function isSplit(v: string): v is Split {
  return (SPLITS as string[]).includes(v);
}
